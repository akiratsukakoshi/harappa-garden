// garden-writeback-daemon
//
// Watches MIRROR_DIR for .md changes and pushes them back to CouchDB
// (LiveSync E2EE format). The reverse direction of mirror-daemon.
//
// Loop prevention: before pushing, decrypt current CouchDB doc and compare
// content. If equal (mirror-daemon just wrote it), skip.
//
// Required env (same as mirror-daemon):
//   COUCHDB_URL       e.g. http://garden-couchdb:5984
//   COUCHDB_USER
//   COUCHDB_PASS
//   E2EE_PASSPHRASE
//   DATABASE          (default: gakuchovault)
//   MIRROR_DIR        (default: /mirror)
//   DEBOUNCE_MS       (default: 1500)

import { encrypt, decrypt } from "octagonal-wheels/encryption/hkdf";
import { xxhashNew } from "octagonal-wheels/hash/xxhash";
import { fallbackMixedHashEach } from "octagonal-wheels/hash/purejs";
import fs from "node:fs/promises";
import { watch as fsWatch } from "node:fs";
import path from "node:path";

// LiveSync constants (mirrored from obsidian-livesync source)
const SALT_OF_ID = "a83hrf7fy7sa8g31";   // shared.const.behabiour.ts:15
const PREFIX_ENCRYPTED_CHUNK = "h:+";         // shared.const.behabiour.ts:34

const cfg = {
  url: (process.env.COUCHDB_URL || "").replace(/\/+$/, ""),
  user: process.env.COUCHDB_USER,
  pass: process.env.COUCHDB_PASS,
  db: process.env.DATABASE || "gakuchovault",
  passphrase: process.env.E2EE_PASSPHRASE,
  mirrorDir: process.env.MIRROR_DIR || "/mirror",
  debounceMs: parseInt(process.env.DEBOUNCE_MS || "1500", 10),
  // Only push files under these path prefixes. Seeds (claude -p) only write to
  // hmc_tasks/ and garden/; everything else in the vault is the user's personal
  // notes that are never edited VPS-side. Scoping avoids touching them entirely.
  scopePrefixes: (process.env.WRITEBACK_SCOPE || "hmc_tasks/,garden/")
    .split(",").map((s) => s.trim()).filter(Boolean),
};

// LiveSync "Case-Sensitive = OFF" stores the canonical doc _id as the LOWERCASED
// path, while the `path` field keeps the original case (and so does the file on disk).
// We must mirror this: _id = lowercase(path), path = original. Using the original-case
// path as _id creates duplicate docs (observed S15).
const toDocId = (docPath) => docPath.toLowerCase();
const inScope = (docPath) => cfg.scopePrefixes.some((p) => docPath.startsWith(p));

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
  return { ok: res.ok, status: res.status, body: res.ok ? await res.json() : await res.text().catch(() => "") };
}

async function ccPutJson(docId, body) {
  const res = await fetch(`${cfg.url}/${cfg.db}/${encodeURIComponent(docId)}`, {
    method: "PUT",
    headers: { Authorization: auth, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { ok: res.ok, status: res.status, body: res.ok ? await res.json() : await res.text().catch(() => "") };
}

async function ccHead(docId) {
  const res = await fetch(`${cfg.url}/${cfg.db}/${encodeURIComponent(docId)}`, {
    method: "HEAD",
    headers: { Authorization: auth },
  });
  return res.ok;
}

const b64ToU8 = (s) => Uint8Array.from(Buffer.from(s, "base64"));

// load pbkdf2 salt once
let pbkdf2Salt;
{
  const r = await ccGet("_local/obsidian_livesync_sync_parameters");
  if (!r.ok) {
    console.error(`[fatal] cannot fetch sync params: ${r.status} ${r.body}`);
    process.exit(1);
  }
  pbkdf2Salt = b64ToU8(r.body.pbkdf2salt);
  log("init", `pbkdf2Salt loaded (${pbkdf2Salt.length} bytes)`);
}

// xxhash + hashedPassphrase init (matches LiveSync XXHash64HashManager)
const xxhash = await xxhashNew();
// hashedPassphrase: SALT_OF_ID + passphrase[0:trunc(len*3/4)]
const usingLetters = Math.trunc((cfg.passphrase.length / 4) * 3);
const passphraseForHash = SALT_OF_ID + cfg.passphrase.substring(0, usingLetters);
const hashedPassphrase = fallbackMixedHashEach(passphraseForHash);
log("init", `hashedPassphrase computed (len=${hashedPassphrase.length})`);

// Compute encrypted chunk ID exactly as LiveSync does:
//   "h:+" + xxhash.h64(`${piece}-${hashedPassphrase}-${piece.length}`).toString(36)
// (h64 returns a BigInt; .toString(36) yields base36 like "22e9mmpqjhdlr")
function computeEncryptedChunkId(piece) {
  return PREFIX_ENCRYPTED_CHUNK + xxhash.h64(`${piece}-${hashedPassphrase}-${piece.length}`).toString(36);
}

async function decryptChunks(ids) {
  const out = [];
  for (let i = 0; i < ids.length; i += 100) {
    const batch = ids.slice(i, i + 100);
    const res = await fetch(`${cfg.url}/${cfg.db}/_all_docs?include_docs=true`, {
      method: "POST",
      headers: { Authorization: auth, "Content-Type": "application/json" },
      body: JSON.stringify({ keys: batch }),
    });
    if (!res.ok) throw new Error(`_all_docs(chunks) -> ${res.status}`);
    const j = await res.json();
    for (const row of j.rows) {
      if (!row.doc || !row.doc.data) {
        throw new Error(`chunk missing: ${row.id || "(unknown)"}`);
      }
      out.push(await decrypt(row.doc.data, cfg.passphrase, pbkdf2Salt));
    }
  }
  return out.join("");
}

function isTargetMd(filePath) {
  if (!filePath) return false;
  if (!filePath.endsWith(".md")) return false;
  // skip hidden files / tmp files
  const base = path.basename(filePath);
  if (base.startsWith(".")) return false;
  if (base.includes(".tmp.")) return false;
  return true;
}

function toDocPath(absPath) {
  const rel = path.relative(cfg.mirrorDir, absPath);
  if (rel.startsWith("..") || path.isAbsolute(rel)) return null;
  return rel;
}

async function pushChange(docPath) {
  if (!inScope(docPath)) return; // never touch out-of-scope (personal notes)
  let content;
  let stat;
  try {
    stat = await fs.stat(path.join(cfg.mirrorDir, docPath));
    if (!stat.isFile()) return;
    content = await fs.readFile(path.join(cfg.mirrorDir, docPath), "utf8");
  } catch (e) {
    if (e.code === "ENOENT") {
      // file deleted -> handle in deletion path
      return await pushDelete(docPath);
    }
    throw e;
  }

  const docId = toDocId(docPath);

  // fetch current CouchDB doc (by canonical lowercase _id)
  const cur = await ccGet(encodeURIComponent(docId));
  let existing = null;
  if (cur.ok) {
    existing = cur.body;
  } else if (cur.status !== 404) {
    throw new Error(`GET ${docId} -> ${cur.status} ${cur.body}`);
  }

  // loop prevention: if existing children decrypt to same content AND chunks use the
  // correct LiveSync-encrypted format (h:+ prefix), skip. Otherwise force a re-push.
  if (existing && Array.isArray(existing.children) && existing.children.length > 0 && !existing._deleted) {
    const allCorrectPrefix = existing.children.every((id) => id.startsWith(PREFIX_ENCRYPTED_CHUNK));
    if (allCorrectPrefix) {
      try {
        const cdbContent = await decryptChunks(existing.children);
        if (cdbContent === content) {
          log("skip", `${docPath} (no change vs CouchDB)`);
          return;
        }
      } catch (e) {
        log("warn", `decrypt comparison failed for ${docPath}: ${e.message} — pushing anyway`);
      }
    } else {
      log("upgrade", `${docPath} has non-encrypted chunk IDs, re-pushing with correct format`);
    }
  }

  // encrypt as single chunk
  const encrypted = await encrypt(content, cfg.passphrase, pbkdf2Salt);
  const chunkId = computeEncryptedChunkId(content);

  // ensure chunk exists
  const chunkExists = await ccHead(chunkId);
  if (!chunkExists) {
    const r = await ccPutJson(chunkId, {
      _id: chunkId,
      data: encrypted,
      type: "leaf",
      e_: true,
    });
    if (!r.ok && r.status !== 409) {
      throw new Error(`PUT chunk ${chunkId} -> ${r.status} ${r.body}`);
    }
  }

  // upsert main doc — _id is canonical lowercase, path keeps original case
  const now = Date.now();
  const newDoc = {
    _id: docId,
    path: docPath,
    type: "plain",
    mtime: stat.mtimeMs ? Math.floor(stat.mtimeMs) : now,
    ctime: existing?.ctime || (stat.ctimeMs ? Math.floor(stat.ctimeMs) : now),
    size: Buffer.byteLength(content, "utf8"),
    children: [chunkId],
    eden: {},
  };
  if (existing && existing._rev) {
    newDoc._rev = existing._rev;
  }

  const r = await ccPutJson(docId, newDoc);
  if (!r.ok) {
    if (r.status === 409) {
      log("warn", `409 conflict for ${docPath} — will retry on next change`);
      return;
    }
    throw new Error(`PUT ${docId} -> ${r.status} ${r.body}`);
  }

  log("put", `${docPath} (${content.length}B, rev=${r.body.rev})`);
}

async function pushDelete(docPath) {
  const docId = toDocId(docPath);
  const cur = await ccGet(encodeURIComponent(docId));
  if (!cur.ok) {
    if (cur.status === 404) return; // already gone
    throw new Error(`GET ${docId} -> ${cur.status} ${cur.body}`);
  }
  if (cur.body._deleted) return;

  const r = await ccPutJson(docId, {
    _id: docId,
    _rev: cur.body._rev,
    _deleted: true,
  });
  if (!r.ok) {
    if (r.status === 409) {
      log("warn", `409 conflict on delete ${docPath}`);
      return;
    }
    throw new Error(`PUT (delete) ${docId} -> ${r.status} ${r.body}`);
  }
  log("del", docPath);
}

// debounce per-path
const pending = new Map(); // docPath -> { timer, lastSeen }
function schedulePush(docPath) {
  const existing = pending.get(docPath);
  if (existing) clearTimeout(existing.timer);
  const timer = setTimeout(async () => {
    pending.delete(docPath);
    try {
      await pushChange(docPath);
    } catch (e) {
      log("err", `push(${docPath}): ${e.message}`);
    }
  }, cfg.debounceMs);
  pending.set(docPath, { timer, lastSeen: Date.now() });
}

// ---- periodic reconcile scan (reliable backbone) ----
// Node's fs.watch(recursive) silently drops events for existing-file modifications
// over time (observed S14→S15). The scan is the source of truth; fs.watch is a
// best-effort low-latency fast-path on top.
const SCAN_INTERVAL_MS = parseInt(process.env.SCAN_INTERVAL_MS || "15000", 10);
const lastMtime = new Map(); // docPath -> mtimeMs seen at last scan

async function walkMd(dir, acc = []) {
  let entries;
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch {
    return acc;
  }
  for (const ent of entries) {
    const abs = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (ent.name.startsWith(".")) continue; // skip hidden dirs
      await walkMd(abs, acc);
    } else if (ent.isFile() && isTargetMd(abs)) {
      acc.push(abs);
    }
  }
  return acc;
}

let scanRunning = false;
async function reconcileScan() {
  if (scanRunning) return;
  scanRunning = true;
  try {
    // Only walk scoped directories (hmc_tasks/, garden/) — never the whole vault
    const files = [];
    for (const prefix of cfg.scopePrefixes) {
      await walkMd(path.join(cfg.mirrorDir, prefix), files);
    }
    for (const abs of files) {
      const docPath = toDocPath(abs);
      if (!docPath || !inScope(docPath)) continue;
      try {
        const st = await fs.stat(abs);
        const prev = lastMtime.get(docPath);
        if (prev === undefined || st.mtimeMs > prev) {
          lastMtime.set(docPath, st.mtimeMs);
          // pushChange dedups via content comparison; safe to call on every mtime bump
          schedulePush(docPath);
        }
      } catch {
        /* file vanished mid-scan; ignore */
      }
    }
  } finally {
    scanRunning = false;
  }
}

// initial: ensure mirror dir exists
await fs.mkdir(cfg.mirrorDir, { recursive: true });

// fs.watch fast-path (best effort; may silently stop — scan is the backbone)
let watcher;
try {
  watcher = fsWatch(cfg.mirrorDir, { recursive: true }, (eventType, filename) => {
    if (!filename) return;
    const abs = path.join(cfg.mirrorDir, filename);
    if (!isTargetMd(abs)) return;
    const docPath = toDocPath(abs);
    if (!docPath || !inScope(docPath)) return;
    schedulePush(docPath);
  });
  watcher.on("error", (e) => log("err", `watcher: ${e.message}`));
} catch (e) {
  log("warn", `fs.watch unavailable (${e.message}); relying on scan only`);
}

log("watch", `fs.watch on ${cfg.mirrorDir} + reconcile scan every ${SCAN_INTERVAL_MS}ms (debounce=${cfg.debounceMs}ms)`);

// run an initial reconcile, then schedule periodic scans
await reconcileScan();
log("init", `initial reconcile done (${lastMtime.size} md files tracked)`);
setInterval(() => reconcileScan().catch((e) => log("err", `scan: ${e.message}`)), SCAN_INTERVAL_MS);

// keep alive
process.on("SIGTERM", () => {
  log("init", "SIGTERM received, shutting down");
  if (watcher) watcher.close();
  process.exit(0);
});
process.on("SIGINT", () => {
  log("init", "SIGINT received, shutting down");
  if (watcher) watcher.close();
  process.exit(0);
});
