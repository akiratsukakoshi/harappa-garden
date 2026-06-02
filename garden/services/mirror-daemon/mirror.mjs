// garden-mirror-daemon
//
// Subscribes to CouchDB _changes feed of the LiveSync vault and writes
// decrypted plain MD files to MIRROR_DIR. One-way (CouchDB -> MD).
//
// Required env:
//   COUCHDB_URL       e.g. http://garden-couchdb:5984
//   COUCHDB_USER      CouchDB admin user
//   COUCHDB_PASS      CouchDB admin password
//   E2EE_PASSPHRASE   LiveSync E2EE passphrase
//   DATABASE          (default: gakuchovault)
//   MIRROR_DIR        (default: /mirror)
//   STATE_FILE        (default: /data/state.json)

import { decrypt as decryptHkdf } from "octagonal-wheels/encryption/hkdf";
import fs from "node:fs/promises";
import path from "node:path";

const cfg = {
  url: (process.env.COUCHDB_URL || "").replace(/\/+$/, ""),
  user: process.env.COUCHDB_USER,
  pass: process.env.COUCHDB_PASS,
  db: process.env.DATABASE || "gakuchovault",
  passphrase: process.env.E2EE_PASSPHRASE,
  mirrorDir: process.env.MIRROR_DIR || "/mirror",
  stateFile: process.env.STATE_FILE || "/data/state.json",
  // S27: vault 外管理パスは CouchDB → fs に展開しない(LiveSync 起因の巻き戻し事故対策)。
  // ADR docs/decisions/2026-06-02-board-and-log-out-of-vault.md
  excludePrefixes: (process.env.EXCLUDE_PREFIXES || "")
    .split(",").map((s) => s.trim()).filter(Boolean),
};

for (const k of ["url", "user", "pass", "passphrase"]) {
  if (!cfg[k]) {
    console.error(`[fatal] missing env: ${k.toUpperCase()}`);
    process.exit(1);
  }
}

const auth = "Basic " + Buffer.from(`${cfg.user}:${cfg.pass}`).toString("base64");

function log(level, msg) {
  const ts = new Date().toISOString();
  console.log(`${ts} [${level}] ${msg}`);
}

async function ccGet(p) {
  const res = await fetch(`${cfg.url}/${cfg.db}/${p}`, {
    headers: { Authorization: auth },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`GET ${p} -> ${res.status} ${body.slice(0, 200)}`);
  }
  return res.json();
}

async function ccPostJson(p, body) {
  const res = await fetch(`${cfg.url}/${cfg.db}/${p}`, {
    method: "POST",
    headers: {
      Authorization: auth,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`POST ${p} -> ${res.status} ${t.slice(0, 200)}`);
  }
  return res.json();
}

const b64ToU8 = (s) => Uint8Array.from(Buffer.from(s, "base64"));

let state = { last_seq: 0, path_by_id: {} };
try {
  state = JSON.parse(await fs.readFile(cfg.stateFile, "utf8"));
  log("init", `loaded state: last_seq=${state.last_seq}, tracked=${Object.keys(state.path_by_id).length}`);
} catch {
  log("init", "no prior state; full sync will run");
}

async function saveState() {
  await fs.mkdir(path.dirname(cfg.stateFile), { recursive: true });
  const tmp = cfg.stateFile + ".tmp";
  await fs.writeFile(tmp, JSON.stringify(state, null, 2));
  await fs.rename(tmp, cfg.stateFile);
}

const syncParams = await ccGet("_local/obsidian_livesync_sync_parameters");
const pbkdf2Salt = b64ToU8(syncParams.pbkdf2salt);
log("init", `pbkdf2Salt loaded (${pbkdf2Salt.length} bytes)`);

const chunkCache = new Map();
const CHUNK_CACHE_MAX = 5000;

async function fetchChunks(ids) {
  const missing = ids.filter((id) => !chunkCache.has(id));
  if (missing.length > 0) {
    for (let i = 0; i < missing.length; i += 100) {
      const batch = missing.slice(i, i + 100);
      const res = await ccPostJson("_all_docs?include_docs=true", { keys: batch });
      for (const row of res.rows) {
        if (row.doc && row.doc.data) {
          chunkCache.set(row.id, row.doc.data);
        }
      }
    }
  }
  if (chunkCache.size > CHUNK_CACHE_MAX) {
    const drop = chunkCache.size - CHUNK_CACHE_MAX;
    let i = 0;
    for (const key of chunkCache.keys()) {
      if (i++ >= drop) break;
      chunkCache.delete(key);
    }
  }
  return ids.map((id) => chunkCache.get(id));
}

function safeJoin(base, p) {
  const dest = path.join(base, p);
  const rel = path.relative(base, dest);
  if (rel.startsWith("..") || path.isAbsolute(rel)) return null;
  return dest;
}

async function writeMirror(docPath, content) {
  const dest = safeJoin(cfg.mirrorDir, docPath);
  if (!dest) {
    log("warn", `skip (path escape): ${docPath}`);
    return;
  }
  await fs.mkdir(path.dirname(dest), { recursive: true });
  const tmp = dest + ".tmp." + process.pid + "." + Date.now();
  await fs.writeFile(tmp, content);
  await fs.rename(tmp, dest);
}

async function deleteMirror(docPath) {
  const dest = safeJoin(cfg.mirrorDir, docPath);
  if (!dest) return;
  try {
    await fs.unlink(dest);
  } catch (e) {
    if (e.code !== "ENOENT") throw e;
  }
}

function isMdPath(p) {
  return typeof p === "string" && p.toLowerCase().endsWith(".md");
}

async function syncDoc(doc) {
  if (!doc) return;
  // S27 vault 外移行: 除外プレフィックスはどんな状態でも fs に反映しない(削除も put も skip)
  const checkPath = doc.path || state.path_by_id[doc._id];
  if (checkPath && cfg.excludePrefixes.some((p) => checkPath.startsWith(p))) {
    return;
  }
  if (doc._deleted) {
    const knownPath = state.path_by_id[doc._id];
    if (knownPath) {
      await deleteMirror(knownPath);
      delete state.path_by_id[doc._id];
      log("del", knownPath);
    }
    return;
  }
  if (doc.type !== "plain" && doc.type !== "newnote") return;
  if (!isMdPath(doc.path)) return;
  if (!Array.isArray(doc.children) || doc.children.length === 0) return;

  const encrypted = await fetchChunks(doc.children);
  const parts = [];
  for (let i = 0; i < doc.children.length; i++) {
    if (!encrypted[i]) {
      log("err", `missing chunk ${doc.children[i]} for ${doc.path}`);
      return;
    }
    try {
      parts.push(await decryptHkdf(encrypted[i], cfg.passphrase, pbkdf2Salt));
    } catch (e) {
      log("err", `decrypt failed for ${doc.path} chunk ${i}: ${e.message}`);
      return;
    }
  }
  const content = parts.join("");
  await writeMirror(doc.path, content);
  state.path_by_id[doc._id] = doc.path;
  log("put", `${doc.path} (${content.length}B)`);
}

if (state.last_seq === 0) {
  log("init", "full sync starting...");
  await fs.mkdir(cfg.mirrorDir, { recursive: true });
  let startkey = null;
  let total = 0;
  let writes = 0;
  while (true) {
    const params = new URLSearchParams({
      include_docs: "true",
      limit: "200",
    });
    if (startkey) {
      params.set("startkey", JSON.stringify(startkey));
      params.set("skip", "1");
    }
    const res = await ccGet("_all_docs?" + params.toString());
    if (res.rows.length === 0) break;
    for (const row of res.rows) {
      if (!row.doc) continue;
      if (row.id.startsWith("_")) continue;
      if (row.id.startsWith("h:")) continue;
      total++;
      const before = state.path_by_id[row.id];
      await syncDoc(row.doc);
      if (state.path_by_id[row.id] !== before) writes++;
    }
    startkey = res.rows[res.rows.length - 1].id;
    if (res.rows.length < 200) break;
  }
  const meta = await ccGet("");
  state.last_seq = meta.update_seq;
  await saveState();
  log("init", `full sync done (${total} docs visited, ${writes} files written)`);
}

log("live", `subscribing _changes since=${state.last_seq}`);
let saveCounter = 0;
async function runChangesLoop() {
  const params = new URLSearchParams({
    feed: "continuous",
    include_docs: "true",
    since: state.last_seq,
    heartbeat: "30000",
  });
  const res = await fetch(`${cfg.url}/${cfg.db}/_changes?` + params.toString(), {
    headers: { Authorization: auth },
  });
  if (!res.ok || !res.body) {
    throw new Error(`_changes -> ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) {
      log("live", "feed closed by server");
      return;
    }
    buf += decoder.decode(value, { stream: true });
    let nl;
    while ((nl = buf.indexOf("\n")) !== -1) {
      const line = buf.slice(0, nl);
      buf = buf.slice(nl + 1);
      if (!line) continue;
      let change;
      try {
        change = JSON.parse(line);
      } catch {
        continue;
      }
      if (change.last_seq) continue;
      if (!change.id) continue;
      if (change.id.startsWith("_") || change.id.startsWith("h:")) {
        state.last_seq = change.seq;
      } else {
        try {
          await syncDoc(change.doc);
        } catch (e) {
          log("err", `syncDoc(${change.id}): ${e.message}`);
        }
        state.last_seq = change.seq;
      }
      if (++saveCounter % 10 === 0) await saveState();
    }
  }
}

let backoff = 1000;
for (;;) {
  try {
    await runChangesLoop();
    await saveState();
    backoff = 1000;
  } catch (e) {
    log("err", `changes loop: ${e.message}`);
    await saveState().catch(() => {});
    await new Promise((r) => setTimeout(r, backoff));
    backoff = Math.min(backoff * 2, 30000);
  }
}
