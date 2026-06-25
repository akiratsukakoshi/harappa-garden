// launcher.mjs の unit test(S39 レビュー指摘 O4 → S40 実装)
//
// 方針: launcher.mjs は import 時に main() が走る構造のため、本体を無改修のまま
// サブプロセス起動 + env 差し替え(GARDEN_SEEDS_ROOT 等)+ --dry-run で検証する。
// --dry-run は claude -p を呼ばない一方、frontmatter パース / YAML / computed_inputs
// 評価 / {var} 置換 / lock / state 永続化 / ログ書き込みまで本物の経路を通る。
//
// 実行: cd garden/services/launcher && npm test
//
// 注意: VPS にはこの test/ を rsync しない(launcher.mjs 単体で動く構造は不変)。

import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LAUNCHER = path.resolve(__dirname, '../launcher.mjs');

let workdir;

before(() => {
  workdir = fs.mkdtempSync(path.join(os.tmpdir(), 'garden-launcher-test-'));
  fs.mkdirSync(path.join(workdir, 'seeds', 'test_plot'), { recursive: true });
  fs.mkdirSync(path.join(workdir, 'log'), { recursive: true });
  fs.mkdirSync(path.join(workdir, 'locks'), { recursive: true });
});

after(() => {
  fs.rmSync(workdir, { recursive: true, force: true });
});

function writeSeed(name, content) {
  const p = path.join(workdir, 'seeds', 'test_plot', `${name}.md`);
  fs.writeFileSync(p, content);
  return p;
}

function runLauncher(seedRef, { dryRun = true, extraEnv = {} } = {}) {
  const args = [LAUNCHER, '--seed', seedRef];
  if (dryRun) args.push('--dry-run');
  return spawnSync('node', args, {
    encoding: 'utf8',
    timeout: 30000,
    env: {
      ...process.env,
      GARDEN_SEEDS_ROOT: path.join(workdir, 'seeds'),
      GARDEN_LOG_ROOT: path.join(workdir, 'log'),
      GARDEN_STATE_FILE: path.join(workdir, 'state.json'),
      GARDEN_LOCK_DIR: path.join(workdir, 'locks'),
      ...extraEnv,
    },
  });
}

function readState() {
  return JSON.parse(fs.readFileSync(path.join(workdir, 'state.json'), 'utf8'));
}

function todayLog(seedName) {
  // launcher のログ名は `$(date +%Y-%m-%d)`(ローカル = JST)由来。
  // toISOString()(UTC)だと JST 00:00〜09:00 にズレて ENOENT になる(S43 で実検出)。
  const d = new Date();
  const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  return path.join(workdir, 'log', `${today}-${seedName}.log`);
}

// 実運用の種 frontmatter と同じ構造の最小 cron 種
const VALID_SEED = `---
type: seed
name: unit-valid
plot: test_plot
description: launcher unit test 用の最小 cron 種
status: draft
trigger:
  type: cron
  schedule: "0 8 * * *"
  timezone: Asia/Tokyo
engine: claude-code
execute:
  working_dir: /tmp
  computed_inputs:
    target_month: "$(echo 2026-07)"
    greeting: "hello-{target_month}"
  prompt: |
    あなたは種「unit-valid」です。
    target_month: {target_month}
    greeting: {greeting}
    seed_key: {seed_key}
---

# unit-valid
`;

test('正常系: dry-run が exit 0 で完走し、state.json に dry_run が記録される', () => {
  writeSeed('unit-valid', VALID_SEED);
  const ret = runLauncher('test_plot/unit-valid');
  assert.equal(ret.status, 0, `stderr: ${ret.stderr}`);
  assert.match(ret.stdout, /\[dry-run\] test_plot\/unit-valid/);
  const state = readState();
  assert.equal(state.seeds['test_plot/unit-valid'].last_outcome, 'dry_run');
  assert.ok(state.seeds['test_plot/unit-valid'].last_fired);
});

test('computed_inputs: $() シェル展開と {var} 内部参照がログの prompt に解決される', () => {
  writeSeed('unit-valid', VALID_SEED);
  const ret = runLauncher('test_plot/unit-valid');
  assert.equal(ret.status, 0);
  const log = fs.readFileSync(todayLog('unit-valid'), 'utf8');
  assert.match(log, /target_month: 2026-07/);          // $() 展開
  assert.match(log, /greeting: hello-2026-07/);        // {var} 内部参照(2nd pass)
  assert.match(log, /seed_key: test_plot\/unit-valid/); // baseVars 注入
});

test('YAML: ブロックスカラー(|)の prompt が複数行で保持される', () => {
  writeSeed('unit-valid', VALID_SEED);
  runLauncher('test_plot/unit-valid');
  const log = fs.readFileSync(todayLog('unit-valid'), 'utf8');
  assert.match(log, /あなたは種「unit-valid」です。\ntarget_month:/);
});

test('未解決の {var} はそのまま残す(壊さない)', () => {
  writeSeed('unit-unresolved', VALID_SEED
    .replaceAll('unit-valid', 'unit-unresolved')
    .replace('seed_key: {seed_key}', 'missing: {no_such_var}'));
  const ret = runLauncher('test_plot/unit-unresolved');
  assert.equal(ret.status, 0);
  const log = fs.readFileSync(todayLog('unit-unresolved'), 'utf8');
  assert.match(log, /missing: \{no_such_var\}/);
});

test('MCP: execute.mcp ブロックが claude -p フラグに変換されログに出る(scribe/Plaud 型)', () => {
  const mcpSeed = `---
type: seed
name: unit-mcp
plot: test_plot
description: MCP 種(Plaud)の launcher 配線 unit test
status: draft
trigger:
  type: cron
  schedule: "30 7 * * *"
  timezone: Asia/Tokyo
engine: claude-code
execute:
  working_dir: /tmp
  mcp:
    config: ".mcp.json"
    strict: true
    permission_mode: "acceptEdits"
    allowed_tools:
      - "mcp__plaud__list_files"
      - "mcp__plaud__get_note"
  prompt: |
    あなたは種「unit-mcp」です。
---

# unit-mcp
`;
  writeSeed('unit-mcp', mcpSeed);
  const ret = runLauncher('test_plot/unit-mcp');
  assert.equal(ret.status, 0, `stderr: ${ret.stderr}`);
  const log = fs.readFileSync(todayLog('unit-mcp'), 'utf8');
  // ヘッダ mcp 行に全フラグが組み立てられている(allowed_tools はカンマ結合)
  assert.match(log, /mcp: --mcp-config \.mcp\.json --strict-mcp-config --permission-mode acceptEdits --allowedTools mcp__plaud__list_files,mcp__plaud__get_note/);
});

test('MCP: mcp ブロックの無い種は従来どおり mcp:(none)(後方互換)', () => {
  writeSeed('unit-valid', VALID_SEED);
  runLauncher('test_plot/unit-valid');
  const log = fs.readFileSync(todayLog('unit-valid'), 'utf8');
  assert.match(log, /mcp: \(none\)/);
});

test('検証: type が seed でないファイルは exit 2', () => {
  writeSeed('unit-not-seed', VALID_SEED.replace('type: seed', 'type: note'));
  const ret = runLauncher('test_plot/unit-not-seed');
  assert.equal(ret.status, 2);
  assert.match(ret.stderr, /not a seed file/);
});

test('検証: trigger.type が cron 以外(event)は exit 2', () => {
  writeSeed('unit-event', VALID_SEED
    .replaceAll('unit-valid', 'unit-event')
    .replace('type: cron', 'type: event'));
  const ret = runLauncher('test_plot/unit-event');
  assert.equal(ret.status, 2);
  assert.match(ret.stderr, /only cron triggers/);
});

test('engine: 未対応 engine(codex 等)は exit 2 で明示エラー(黙って claude にフォールバックしない)', () => {
  writeSeed('unit-codex', VALID_SEED
    .replaceAll('unit-valid', 'unit-codex')
    .replace('engine: claude-code', 'engine: codex'));
  const ret = runLauncher('test_plot/unit-codex');
  assert.equal(ret.status, 2);
  assert.match(ret.stderr, /engine 'codex' is not supported/);
});

test('engine: 省略時は claude-code にフォールバックして完走(後方互換)', () => {
  writeSeed('unit-no-engine', VALID_SEED
    .replaceAll('unit-valid', 'unit-no-engine')
    .replace('engine: claude-code\n', ''));
  const ret = runLauncher('test_plot/unit-no-engine');
  assert.equal(ret.status, 0);
  const log = fs.readFileSync(todayLog('unit-no-engine'), 'utf8');
  assert.match(log, /engine: claude-code/);
});

test('検証: status: paused は exit 0 で skip(cron を汚さない)', () => {
  writeSeed('unit-paused', VALID_SEED
    .replaceAll('unit-valid', 'unit-paused')
    .replace('status: draft', 'status: paused'));
  const ret = runLauncher('test_plot/unit-paused');
  assert.equal(ret.status, 0);
  assert.match(ret.stderr, /paused/);
});

test('検証: 種ファイルが無い場合は exit 2', () => {
  const ret = runLauncher('test_plot/no-such-seed');
  assert.equal(ret.status, 2);
  assert.match(ret.stderr, /seed file not found/);
});

test('検証: frontmatter が無いファイルは異常終了(0 以外)', () => {
  writeSeed('unit-no-fm', '# ただの markdown\n本文のみ。\n');
  const ret = runLauncher('test_plot/unit-no-fm');
  assert.notEqual(ret.status, 0);
});

test('並行制御: 生きている pid の lock があると exit 3、lock 解放後は再実行できる', () => {
  writeSeed('unit-valid', VALID_SEED);
  const lockFile = path.join(workdir, 'locks', 'garden-launcher-test_plot_unit-valid.lock');
  fs.writeFileSync(lockFile, `pid=${process.pid}\n`); // テストランナー自身 = 確実に生存
  const blocked = runLauncher('test_plot/unit-valid');
  assert.equal(blocked.status, 3);
  assert.match(blocked.stderr, /another instance is running/);
  fs.unlinkSync(lockFile);
  const retry = runLauncher('test_plot/unit-valid');
  assert.equal(retry.status, 0);
});

test('並行制御: 死んだ pid の stale lock は乗っ取って実行し、終了後に lock が残らない(S43)', () => {
  writeSeed('unit-valid', VALID_SEED);
  const lockFile = path.join(workdir, 'locks', 'garden-launcher-test_plot_unit-valid.lock');
  // 確実に死んでいる pid: 自分で spawn して終了済みの子プロセス
  const dead = spawnSync('node', ['-e', 'process.exit(0)'], { encoding: 'utf8' });
  fs.writeFileSync(lockFile, `pid=${dead.pid}\nstarted=2026-01-01T00:00:00Z\n`);
  const ret = runLauncher('test_plot/unit-valid');
  assert.equal(ret.status, 0);
  assert.match(ret.stderr, /stale lock/);
  assert.equal(fs.existsSync(lockFile), false);
});

test('並行制御: 失敗パス(working_dir 不在)でも lock が残らない(S43 exit143 障害の再発防止)', () => {
  const seed = VALID_SEED
    .replace('working_dir: /tmp', 'working_dir: /nonexistent-dir-for-test')
    .replace('name: unit-valid', 'name: unit-faildir');
  writeSeed('unit-faildir', seed);
  const lockFile = path.join(workdir, 'locks', 'garden-launcher-test_plot_unit-faildir.lock');
  const ret = runLauncher('test_plot/unit-faildir', { dryRun: false });
  assert.equal(ret.status, 4);
  assert.equal(fs.existsSync(lockFile), false);
});

test('CLI: --seed 無しは exit 2 / --help は exit 0', () => {
  const noSeed = spawnSync('node', [LAUNCHER], { encoding: 'utf8', timeout: 10000 });
  assert.equal(noSeed.status, 2);
  const help = spawnSync('node', [LAUNCHER, '--help'], { encoding: 'utf8', timeout: 10000 });
  assert.equal(help.status, 0);
  assert.match(help.stdout, /Usage:/);
});

test('実運用の種 frontmatter がパース可能(repo の active 種で dry-run)', () => {
  // 実際の seeds/ を読ませて、本物の frontmatter(ネスト・シーケンス・ブロック)が
  // launcher の最小 YAML パーサで通ることを退行検査する。
  const repoSeeds = path.resolve(__dirname, '../../../seeds');
  for (const ref of [
    'daily-pilot/morning-briefing',
    'shift_manager/monthly-shift-survey',
    'expense_processor/monthly-expense-draft',
  ]) {
    if (!fs.existsSync(path.join(repoSeeds, `${ref}.md`))) continue;
    const ret = runLauncher(ref, { extraEnv: { GARDEN_SEEDS_ROOT: repoSeeds } });
    assert.equal(ret.status, 0, `${ref} failed: ${ret.stderr}`);
  }
});
