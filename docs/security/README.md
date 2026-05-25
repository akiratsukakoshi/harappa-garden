# セキュリティ運用ルール

HARAPPA Management Cockpit (HMC) における secret 管理・認証情報の取り扱いの基本ルール。

過去のインシデント記録は [`incidents/`](./incidents/) を参照。

---

## 1. secret 管理の原則

### 1.1 平文を bashrc・ソースコード・git に置かない

- パスフレーズ、API キー、OAuth client_secret、refresh token などは **`~/.bashrc` に直書きしない**。
- ソースコードにも書かない。
- git にコミットしない。`.env`, credentials 系のファイルは `.gitignore` に必ず含める。

### 1.2 専用 env ファイルに分離する

secret は専用のファイルに分離し、bashrc は source 行のみ持つ。

```bash
# ~/.bashrc 末尾
[ -f ~/.config/gogcli/env ] && source ~/.config/gogcli/env
```

env ファイルは:
- パーミッション `600`（`install -m 600 /dev/null <path>` で作成）
- 親ディレクトリも `700` 推奨
- git 管理外（`.gitignore` 必須）

### 1.3 bash 履歴汚染を防ぐ

`~/.bashrc` 末尾に以下を入れる:

```bash
HISTCONTROL=ignorespace:ignoredups
```

これにより:
- **行頭スペース付きのコマンドは履歴に残らない** → `  export SECRET=...` のような ad-hoc 実行が安全になる
- 同一コマンドの連続実行は重複登録されない

### 1.4 secret の値を画面・ログに出力しない

機密情報が環境変数に入っているか確認したい時、**値そのものを出力する構文は使わない**:

| ❌ 使ってはいけない | 理由 |
|---|---|
| `echo "$VAR"` | 値が画面に出る |
| `echo "${VAR:-x}"` | VAR が set ならその値が出る |
| `cat ~/.config/foo/secret` | ファイル内容が全部出る |

| ✅ 使ってよい | 何を出すか |
|---|---|
| `test ${#VAR} -eq 32 && echo "OK"` | 長さが期待値か (OK/NG) のみ |
| `if [ -n "$VAR" ]; then echo "SET"; else echo "UNSET"; fi` | set/unset の判定のみ |
| `wc -c ~/.config/foo/secret` | ファイルサイズのみ |
| `head -1 ~/.config/foo/env` | env ファイルなら先頭の `# Generated ...` コメント行のみ確認 |

**理由**: 2026-05-23 のインシデント（[詳細](./incidents/2026-05-23_gog_keyring_rotation.md)）で、`echo "${VAR:+SET (length=${#VAR})}${VAR:-UNSET}"` という確認コマンドにより新パスフレーズを 2 回連続で AI チャットログに漏洩させる事故が発生。確認コマンドのテンプレは上記2形式に限定する。

#### 補足: env の読み込み確認は interactive シェルで実施

`~/.bashrc` 冒頭の `case $- in *i*) ;; *) return;; esac` により、**non-interactive シェルでは bashrc が early return し、`source ~/.config/gogcli/env` まで到達しない**。

動作確認は必ず下記いずれかの方法で:

```bash
# 方法1: 塚越さん自身の対話ターミナルで実行
exec bash -l
test ${#GOG_KEYRING_PASSWORD} -eq 32 && echo "OK"

# 方法2: AI / スクリプトから login+interactive で起動
bash -lic 'test ${#GOG_KEYRING_PASSWORD} -eq 32 && echo "OK"'

# 方法3: bashrc を経由せず env を明示 source
bash -c 'source ~/.config/gogcli/env && test ${#GOG_KEYRING_PASSWORD} -eq 32 && echo "OK"'
```

業務スクリプトを cron / systemd / 非対話ラッパーから呼ぶ時も、起動側で明示的に `source ~/.config/gogcli/env` してから実行すること（[詳細](./incidents/2026-05-23_gog_keyring_rotation.md#動作確認時の注意点garden-側で判明した知見)）。

### 1.5 secret を含むコマンドが履歴に残ったら即削除

```bash
# 一時的に履歴記録を止める
set +o history
# 機密を扱うコマンド実行
...
set -o history

# あるいは事後的に履歴から特定行を削除
history -d <line_number>
history -w  # ファイルに反映
```

## 2. パスフレーズの生成

ランダム32文字の英数字パスフレーズ生成 + ファイル直書き（値は画面に出さない）:

```bash
install -m 600 /dev/null ~/.config/gogcli/env
{
  printf '# Generated %s\n' "$(date -Iseconds)"
  printf 'export GOG_KEYRING_PASSWORD=%q\n' "$(openssl rand -base64 48 | tr -d '\n/+=' | head -c 32)"
} > ~/.config/gogcli/env
source ~/.config/gogcli/env
test ${#GOG_KEYRING_PASSWORD} -eq 32 && echo "OK"
```

`openssl rand -base64 48 | tr -d '\n/+='` で「英数字のみ」が確定（記号 `'` `"` `\` `$` `` ` `` は混入しない）。

## 3. 認証情報の再生成手順

各サービス別の具体的な再認証手順:

- gog cli (Gmail/Drive): [`incidents/2026-05-23_gog_keyring_rotation.md`](./incidents/2026-05-23_gog_keyring_rotation.md#再認証手順) の手順を参照
- Freee OAuth: TBD（今後追加）
- Google API key: TBD

## 4. 緊急時の対応原則

機密情報の漏洩が疑われた時:

1. **発覚した経路を即時遮断**（bashrc 編集、history 削除、ファイル退避）
2. **当該 secret を rotate**（パスフレーズ変更、OAuth revoke + 再認証、API キー再発行）
3. **漏洩元の二次経路を確認**（git history、コードベース、リモート push 履歴）
4. **インシデントレポートを `docs/security/incidents/YYYY-MM-DD_<topic>.md` として記録**
5. 必要に応じて関連サービスの監査（Google アカウント / Freee 管理画面 等）

## 5. ファイル一覧（参考）

| パス | 内容 | パーミッション |
|---|---|---|
| `~/.config/gogcli/env` | gog cli の keyring パスフレーズ | 600 |
| `~/.config/gogcli/keyring/` | gog cli の暗号化 refresh token | 700 |
| `~/harappa-cockpit/.env` | アプリ用 API キー類 | 600（推奨） |

`~/.bashrc` には source 行のみを書き、secret 本体は環境変数として埋め込まない。

---

## 6. VPS 環境での追加考慮（Garden Phase 3b 以降）

**§1〜§5 は WSL（ローカル）前提**。Garden が業務 secret を VPS に配置する Phase 3b 以降では、以下を追加で考慮する。

詳細は [VPS secret 管理方針 ADR](../decisions/2026-05-25-vps-secret-management-direction.md) 参照。

### 6.1 保管方式

- 初期: **平文 env + 600**（§1.1〜1.5 を VPS にもそのまま延長）
- 発展余地: 後追いで **age 暗号化 + master key** に移行
- 採用しない: クラウド secret manager（ベンダー中立性のため）

### 6.2 サービス隔離

- gaku-co5.0 / hmc-on-vps / garden-seed-launcher / CouchDB は **各々別 Docker コンテナ**
- 各コンテナ内で **root 不使用**
- secret は **必要コンテナのみマウント**（共通マウント禁止）
- Docker network はサービス間通信に必要なものだけ

### 6.3 OAuth scope 最小化

- **scope を最小に**（write 不要なら read のみ・特定リソース限定）
- **人事労務 freee は最も厳重**：独立 OAuth client、アクセスする種を限定
- **読取り専用と書込みでトークン分離**（可能な場合は別 OAuth client）
- Google Drive は **file scope** のみ（gog cli の既存方式踏襲）

### 6.4 ローテーション

- **発覚時**: 即時ローテ（§4 緊急時対応原則 + [2026-05-23 インシデント手順](incidents/2026-05-23_gog_keyring_rotation.md)）
- **年1強制ローテ**: 全 token を1年に1度ローテ（漏えい発覚なしでも）
- **手順**: 初期はチェックリスト、後追いでスクリプト化
- **記録**: ローテ実施都度 `incidents/` に YYYY-MM-DD 形式で記録

### 6.5 VPS 自体のハードニング（別セッションで監査・強化）

未確定の項目（Phase 3b で監査する）:

- SSH 鍵認証のみ・パスワード認証無効
- SSH ポート変更や fail2ban
- ファイアウォール（必要ポートのみ open）
- OS / Docker / 各 daemon の自動更新
- root 直接ログイン無効化

### 6.6 CLAUDE.md 由来のルール（VPS でも厳守）

- secret 確認コマンドは **length 比較 か set/unset 判定のみ**（§1.4）
- ベンダー中立性: 特定 secret manager に強く依存しない
