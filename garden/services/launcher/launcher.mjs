#!/usr/bin/env node
// garden launcher — Phase 3a A-1 本番ランチャー
//
// 用途: cron から呼ばれ、指定された種(seed)を1回実行する。
// 入口: `node launcher.mjs --seed daily-pilot/morning-briefing`
//
// 実装範囲(セッション13、初版):
//   1. frontmatter パース(YAML)
//   2. trigger 検証(本ランチャーは cron 種専用)
//   3. computed_inputs の評価(シェル展開)
//   4. prompt 変数置換({key} → 値)
//   5. claude -p 起動 + ログ書き込み
//   6. 並行制御(flock 相当の lockfile)
//   7. 状態永続化(state.json: last_fired / last_outcome)
//
// 実装範囲外(後追い):
//   - on_failure.retry の自動化(初版は単発試行)
//   - on_failure.fallback の LINE 通知発火(初版はログ書き込みのみ)
//   - audit の種ファイル書き戻し(state.json に分離)
//   - event 種(watcher daemon が別途、本ランチャー外)
//   - board ファイル書き戻し経路

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync, execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---- 設定 ----
const SEEDS_ROOT = process.env.GARDEN_SEEDS_ROOT || path.resolve(__dirname, '../../seeds');
const LOG_ROOT = process.env.GARDEN_LOG_ROOT || '/home/vps-harappa/garden/log';
const STATE_FILE = process.env.GARDEN_STATE_FILE || path.resolve(__dirname, 'state.json');
const LOCK_DIR = process.env.GARDEN_LOCK_DIR || '/tmp';
const CLAUDE_BIN = process.env.CLAUDE_BIN || `${process.env.HOME}/.npm-global/bin/claude`;
const CLAUDE_TIMEOUT_MS = parseInt(process.env.CLAUDE_TIMEOUT_MS || '600000', 10); // 10 分

// ---- cron secrets の読み込み(S59: claude -p 認証トークン)----
// cron は最小 env で起動するため、`claude -p` の認証情報(CLAUDE_CODE_OAUTH_TOKEN)を
// ここで env ファイルから読み込んで process.env に注入する。spawn 時に {...process.env}
// で claude へ継承される。ファイルは chmod 600 / gitignore、値は repo に置かない(secret)。
// 既に env にある変数は上書きしない(手動実行時の優先)。
const CRON_SECRETS_FILE = process.env.GARDEN_CRON_SECRETS || `${process.env.HOME}/.claude/cron-secrets.env`;
try {
  for (const line of fs.readFileSync(CRON_SECRETS_FILE, 'utf8').split('\n')) {
    const m = /^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/.exec(line);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
} catch { /* ファイル不在ならスキップ(既存 env のまま) */ }

// ---- CLI 引数 ----
function parseArgs(argv) {
  const args = { seed: null, dryRun: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--seed') args.seed = argv[++i];
    else if (a === '--dry-run') args.dryRun = true;
    else if (a === '-h' || a === '--help') {
      console.log('Usage: node launcher.mjs --seed <plot>/<seed-name> [--dry-run]');
      process.exit(0);
    } else {
      console.error(`unknown arg: ${a}`);
      process.exit(2);
    }
  }
  if (!args.seed) {
    console.error('missing --seed <plot>/<seed-name>');
    process.exit(2);
  }
  return args;
}

// ---- minimal YAML frontmatter parser (top-level + nested objects・arrays・blocks) ----
// 本実装で使う種 frontmatter の範囲に限定した最小 YAML 解析。
// 完全な YAML 仕様の実装ではない。
//
// サポート:
//   - スカラー: 文字列(quoted / unquoted)、数値、null、true/false
//   - インデントによるネスト(2 空白)
//   - シーケンス(`- item`)
//   - ブロックスカラー(`|`、`>` は単純化して `|` 同等扱い)
//   - コメント(`#` で行末まで)
//
// 仕様外(失敗する):
//   - フロースタイル(`{a: b, c: d}`、`[a, b, c]`)
//   - 複雑なアンカー / 参照
function extractFrontmatter(raw) {
  // 種ファイルは frontmatter を `---` で 2 回はさむ + 本文を持つ
  // ただし frontmatter の中に `---` を含む種定義(`type: seed` 等のみ)はないと仮定
  if (!raw.startsWith('---\n')) {
    throw new Error('frontmatter not found (does not start with "---")');
  }
  const end = raw.indexOf('\n---\n', 4);
  if (end < 0) {
    throw new Error('frontmatter end "---" not found');
  }
  const fm = raw.slice(4, end);
  const body = raw.slice(end + 5);
  return { fm, body };
}

function parseYaml(text) {
  const lines = text.split('\n');
  // 行を { indent, key, value, raw } の構造に変換しつつ、コメント・空行は無視
  // 簡易再帰下降パーサ
  let pos = 0;

  function peek() {
    while (pos < lines.length) {
      const ln = lines[pos];
      const trimmed = ln.replace(/\s+#.*$/, '').replace(/^#.*$/, '');
      if (trimmed.trim() === '') { pos++; continue; }
      return ln;
    }
    return null;
  }

  function consume() {
    const ln = peek();
    if (ln !== null) pos++;
    return ln;
  }

  function indentOf(ln) {
    let n = 0;
    while (n < ln.length && ln[n] === ' ') n++;
    return n;
  }

  function parseScalar(s) {
    s = s.trim();
    if (s === '' || s === 'null' || s === '~') return null;
    if (s === 'true') return true;
    if (s === 'false') return false;
    if (/^-?\d+$/.test(s)) return parseInt(s, 10);
    if (/^-?\d+\.\d+$/.test(s)) return parseFloat(s);
    // quoted
    if ((s.startsWith('"') && s.endsWith('"')) ||
        (s.startsWith("'") && s.endsWith("'"))) {
      return s.slice(1, -1);
    }
    return s;
  }

  // ブロックスカラー(| or >)を読む
  function readBlockScalar(parentIndent) {
    const buf = [];
    while (pos < lines.length) {
      const ln = lines[pos];
      if (ln.trim() === '') { buf.push(''); pos++; continue; }
      const indent = indentOf(ln);
      if (indent <= parentIndent) break;
      buf.push(ln.slice(parentIndent + 2));
      pos++;
    }
    // 末尾空行は 1 つだけに正規化
    while (buf.length > 1 && buf[buf.length - 1] === '') buf.pop();
    return buf.join('\n') + (buf.length > 0 ? '\n' : '');
  }

  // マップを読む(parentIndent + 2 のキー群)
  function parseMap(parentIndent) {
    const result = {};
    while (true) {
      const ln = peek();
      if (ln === null) break;
      const indent = indentOf(ln);
      if (indent < parentIndent + 2) break; // 親レベルへ戻る
      if (indent > parentIndent + 2) {
        // ネストが深すぎる(broken yaml) — 無視
        consume();
        continue;
      }
      const content = ln.slice(indent).replace(/\s+#.*$/, '');
      const colonIdx = content.indexOf(':');
      if (colonIdx < 0) {
        // `- ...` トップレベルの場合はマップではなくシーケンス、ここでは扱わない
        break;
      }
      const key = content.slice(0, colonIdx).trim();
      const valuePart = content.slice(colonIdx + 1).trimEnd();
      consume();
      if (valuePart.trim() === '|' || valuePart.trim() === '>') {
        result[key] = readBlockScalar(indent);
      } else if (valuePart.trim() === '') {
        // 次の行を見る
        const next = peek();
        if (next === null) {
          result[key] = null;
        } else {
          const nIndent = indentOf(next);
          if (nIndent <= indent) {
            result[key] = null;
          } else if (next.slice(nIndent).startsWith('- ')) {
            result[key] = parseSeq(indent);
          } else {
            result[key] = parseMap(indent);
          }
        }
      } else {
        result[key] = parseScalar(valuePart);
      }
    }
    return result;
  }

  function parseSeq(parentIndent) {
    const result = [];
    while (true) {
      const ln = peek();
      if (ln === null) break;
      const indent = indentOf(ln);
      if (indent < parentIndent + 2) break;
      const content = ln.slice(indent);
      if (!content.startsWith('- ')) break;
      const valuePart = content.slice(2).replace(/\s+#.*$/, '').trimEnd();
      consume();
      if (valuePart.trim() === '') {
        // 次の行が ネストマップ
        result.push(parseMap(indent));
      } else if (valuePart.includes(':') && !valuePart.startsWith('"') && !valuePart.startsWith("'")) {
        // インラインキー値 `- key: value`(初手のキーをマップに)
        const obj = {};
        const colonIdx = valuePart.indexOf(':');
        const k = valuePart.slice(0, colonIdx).trim();
        const v = valuePart.slice(colonIdx + 1).trim();
        obj[k] = v === '' ? null : parseScalar(v);
        // 続くインデント行を同マップへ
        while (true) {
          const cont = peek();
          if (cont === null) break;
          const cIndent = indentOf(cont);
          if (cIndent <= indent + 2) break;
          // pos を 一旦進めてマップとして処理
          const subMap = parseMap(indent + 2 - 2);
          Object.assign(obj, subMap);
          break;
        }
        result.push(obj);
      } else {
        result.push(parseScalar(valuePart));
      }
    }
    return result;
  }

  // トップレベルはマップ(parentIndent = -2 として indent 0 を許す)
  return parseMap(-2);
}

// ---- computed_inputs 評価 ----
function evaluateComputedInputs(rawInputs, extraVars) {
  const result = { ...extraVars };
  if (!rawInputs || typeof rawInputs !== 'object') return result;
  for (const [k, v] of Object.entries(rawInputs)) {
    if (typeof v !== 'string') { result[k] = v; continue; }
    // `$(...)` シェル展開
    const m = v.match(/^\$\((.+)\)$/);
    if (m) {
      try {
        const out = execSync(m[1], { encoding: 'utf8', timeout: 15000 }).trim();
        result[k] = out;
      } catch (e) {
        result[k] = `<eval_error: ${e.message}>`;
      }
    } else {
      // `{var}` 置換は後でまとめて行うので、ここでは文字列のまま
      result[k] = v;
    }
  }
  // 2nd pass: `{var}` 内部参照を解決(例: `target_file: "{event.path}"`)
  for (const [k, v] of Object.entries(result)) {
    if (typeof v !== 'string') continue;
    result[k] = substituteVars(v, result);
  }
  return result;
}

function substituteVars(s, vars) {
  return s.replace(/\{([a-zA-Z_][a-zA-Z0-9_.]*)\}/g, (_, key) => {
    if (key in vars) return String(vars[key]);
    // ドット記法(event.path 等)に対応
    const parts = key.split('.');
    let cur = vars;
    for (const p of parts) {
      if (cur && typeof cur === 'object' && p in cur) cur = cur[p];
      else return `{${key}}`; // 未解決はそのまま残す
    }
    return String(cur);
  });
}

// ---- ロック処理 ----
function pidAlive(pid) {
  if (!pid) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return e.code === 'EPERM'; // 権限エラー = プロセス自体は存在する
  }
}

function acquireLock(seedName) {
  const lockFile = path.join(LOCK_DIR, `garden-launcher-${seedName.replace(/\//g, '_')}.lock`);
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const fd = fs.openSync(lockFile, 'wx');
      fs.writeFileSync(fd, `pid=${process.pid}\nstarted=${new Date().toISOString()}\n`);
      return { fd, lockFile, acquired: true };
    } catch (e) {
      if (e.code !== 'EEXIST') throw e;
      // stale 判定: 記録 pid が死んでいれば残骸とみなして乗っ取る
      // (S43: claude SIGTERM 後の process.exit で finally が走らず lock が残り、
      //  次回発火が exit 3 で黙ってスキップされる事故の対策)
      let stale = false;
      try {
        const m = /pid=(\d+)/.exec(fs.readFileSync(lockFile, 'utf8'));
        stale = !m || !pidAlive(parseInt(m[1], 10));
      } catch {
        stale = true; // 読めない lock も残骸扱い
      }
      if (!stale || attempt > 0) {
        return { fd: null, lockFile, acquired: false };
      }
      console.error(`[lock] stale lock (dead pid) — removing: ${lockFile}`);
      try { fs.unlinkSync(lockFile); } catch {}
    }
  }
  return { fd: null, lockFile, acquired: false };
}

function releaseLock(lock) {
  if (lock.fd !== null) {
    try { fs.closeSync(lock.fd); } catch {}
    try { fs.unlinkSync(lock.lockFile); } catch {}
  }
}

// ---- 状態管理 ----
function loadState() {
  if (!fs.existsSync(STATE_FILE)) return { seeds: {} };
  try { return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); }
  catch { return { seeds: {} }; }
}

function saveState(state) {
  const dir = path.dirname(STATE_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

function updateAudit(state, seedKey, outcome, extra = {}) {
  if (!state.seeds[seedKey]) state.seeds[seedKey] = {};
  state.seeds[seedKey].last_fired = new Date().toISOString();
  state.seeds[seedKey].last_outcome = outcome;
  Object.assign(state.seeds[seedKey], extra);
  saveState(state);
}

// ---- ログ ----
function ensureLogDir(logPath) {
  const dir = path.dirname(logPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function appendLog(logPath, msg) {
  fs.appendFileSync(logPath, msg);
}

// ---- MCP フラグ構築 ----
// 種 frontmatter の execute.mcp ブロックを claude -p の CLI フラグ列に変換する。
//   mcp:
//     config: ".mcp.json"            → --mcp-config .mcp.json
//     strict: true                   → --strict-mcp-config
//     permission_mode: "acceptEdits" → --permission-mode acceptEdits
//     allowed_tools: [a, b]          → --allowedTools a,b
// 未指定(mcp なし)の種は空配列を返し、従来どおりの起動になる。
function buildMcpArgs(mcp) {
  if (!mcp || typeof mcp !== 'object') return [];
  const out = [];
  if (mcp.config) {
    out.push('--mcp-config', String(mcp.config));
    if (mcp.strict) out.push('--strict-mcp-config');
  }
  if (mcp.permission_mode) {
    out.push('--permission-mode', String(mcp.permission_mode));
  }
  if (Array.isArray(mcp.allowed_tools) && mcp.allowed_tools.length) {
    out.push('--allowedTools', mcp.allowed_tools.join(','));
  }
  return out;
}

// ---- メイン処理 ----
function main() {
  const args = parseArgs(process.argv);
  const seedPath = path.resolve(SEEDS_ROOT, `${args.seed}.md`);
  if (!fs.existsSync(seedPath)) {
    console.error(`seed file not found: ${seedPath}`);
    process.exit(2);
  }

  const raw = fs.readFileSync(seedPath, 'utf8');
  const { fm } = extractFrontmatter(raw);

  let seed;
  try {
    seed = parseYaml(fm);
  } catch (e) {
    console.error(`yaml parse error: ${e.message}`);
    process.exit(2);
  }

  // 検証
  if (seed.type !== 'seed') {
    console.error(`not a seed file: type=${seed.type}`);
    process.exit(2);
  }
  const triggerType = seed.trigger?.type;
  if (triggerType !== 'cron') {
    console.error(`launcher supports only cron triggers (got: ${triggerType}). event seeds use watcher daemon.`);
    process.exit(2);
  }
  if (seed.status === 'paused' || seed.status === 'deprecated') {
    console.error(`seed status is ${seed.status} — skipping`);
    process.exit(0);
  }

  const seedKey = `${seed.plot}/${seed.name}`;

  // ロック取得
  const lock = acquireLock(seedKey);
  if (!lock.acquired) {
    console.error(`another instance is running (lock: ${lock.lockFile})`);
    process.exit(3);
  }
  // process.exit() は finally を実行しないため、exit フックでも必ず解放する
  // (S43: 失敗パス exit(143) で lock が残った実障害の再発防止)
  process.on('exit', () => releaseLock(lock));

  const state = loadState();

  try {
    // 変数評価
    const baseVars = {
      seed_name: seed.name,
      seed_key: seedKey,
      today: execSync('date +%Y-%m-%d', { encoding: 'utf8' }).trim(),
    };
    const vars = evaluateComputedInputs(seed.execute?.computed_inputs, baseVars);

    // prompt 構築
    const promptTemplate = seed.execute?.prompt || '';
    const prompt = substituteVars(promptTemplate, vars);

    // ログパス
    const logPath = path.join(LOG_ROOT, `${vars.today}-${seed.name}.log`);
    ensureLogDir(logPath);

    const model = seed.execute?.model || null;
    // 種ごとの timeout(分)。重い種(invoice の Gemini 解析等)が既定 10 分で
    // SIGTERM(exit 143)されるのを防ぐ(S43)。未指定は CLAUDE_TIMEOUT_MS。
    const timeoutMs = seed.execute?.timeout_minutes
      ? parseInt(seed.execute.timeout_minutes, 10) * 60 * 1000
      : CLAUDE_TIMEOUT_MS;

    // MCP 種(scribe の Plaud 等)。frontmatter `execute.mcp` があれば claude -p に
    // --mcp-config / --strict-mcp-config / --permission-mode / --allowedTools を渡す。
    // ★Plaud MCP は OAuth トークンが ~/.plaud/tokens-mcp.json で自動更新されるため、
    //   認証済みホスト(=トークンを持つローカル WSL)での headless 実行に限り到達できる(S54 実証)。
    const mcpArgs = buildMcpArgs(seed.execute?.mcp);

    const header = [
      '',
      `========================================`,
      `seed: ${seedKey}`,
      `started_at: ${new Date().toISOString()}`,
      `host: ${execSync('hostname', { encoding: 'utf8' }).trim()}`,
      `launcher_version: 1.0.1 (session30)`,
      `working_dir: ${seed.execute?.working_dir || process.cwd()}`,
      `claude_bin: ${CLAUDE_BIN}`,
      `model: ${model || '(default)'}`,
      `timeout_ms: ${timeoutMs}`,
      `mcp: ${mcpArgs.length ? mcpArgs.join(' ') : '(none)'}`,
      `dry_run: ${args.dryRun}`,
      `---- vars ----`,
      JSON.stringify(vars, null, 2),
      `---- prompt ----`,
      prompt,
      `---- claude -p output ----`,
      ''
    ].join('\n');
    appendLog(logPath, header);

    if (args.dryRun) {
      appendLog(logPath, '\n[dry-run: claude -p not invoked]\n');
      updateAudit(state, seedKey, 'dry_run', { last_log: logPath });
      console.log(`[dry-run] ${seedKey} → ${logPath}`);
      return;
    }

    // working_dir
    const cwd = seed.execute?.working_dir || process.cwd();
    if (!fs.existsSync(cwd)) {
      appendLog(logPath, `\n[error] working_dir does not exist: ${cwd}\n`);
      updateAudit(state, seedKey, 'failed', { reason: 'working_dir missing' });
      process.exit(4);
    }

    // claude -p 起動(model 指定があれば --model で渡す)
    // ★prompt は positional として -p の直後に置く。--allowedTools は可変長オプションで、
    //   末尾に置くと直後の positional prompt を許可ツール名として飲み込み
    //   「Input must be provided」で落ちる(S54 実証)。prompt 先頭ならフラグに飲まれない。
    const cliArgs = ['-p', prompt];
    if (model) {
      cliArgs.push('--model', model);
    }
    cliArgs.push(...mcpArgs);
    const ret = spawnSync(CLAUDE_BIN, cliArgs, {
      cwd,
      encoding: 'utf8',
      timeout: timeoutMs,
      maxBuffer: 50 * 1024 * 1024, // 50MB
      env: { ...process.env },
    });

    appendLog(logPath, ret.stdout || '');
    if (ret.stderr) {
      appendLog(logPath, `\n---- stderr ----\n${ret.stderr}`);
    }
    const exitCode = ret.status;
    const finishedAt = new Date().toISOString();
    appendLog(logPath, `\n---- end ----\nexit_code: ${exitCode}\nfinished_at: ${finishedAt}\n`);

    if (exitCode === 0) {
      updateAudit(state, seedKey, 'success', { last_log: logPath, exit_code: 0 });
      console.log(`[ok] ${seedKey} → ${logPath}`);
    } else {
      updateAudit(state, seedKey, 'failed', { last_log: logPath, exit_code: exitCode });
      console.error(`[fail] ${seedKey} exit=${exitCode} → ${logPath}`);
      // on_failure.fallback の自動発火は未実装 — 後追い
      process.exit(exitCode || 1);
    }
  } catch (e) {
    console.error(`[error] ${e.message}`);
    updateAudit(state, seedKey, 'error', { reason: e.message });
    process.exit(1);
  } finally {
    releaseLock(lock);
  }
}

main();
