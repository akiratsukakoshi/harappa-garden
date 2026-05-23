# 2026-05-23 GOG keyring パスフレーズ漏洩・ローテーション

## 概要

`~/.bashrc` および両リポ (`harappa-cockpit` / `harappa-garden`) の `.agent/skills/email_organizer/SKILL.md` に gog cli の keyring 復号パスフレーズが**平文で記載されていた**ことが発覚。同日中に当該パスフレーズの失効・新パスフレーズへのローテーションを完了。

## 発覚経緯

harappa-garden 側のエージェントが tmux 環境整備中、`tail -10 ~/.bashrc` で末尾の体裁確認を行った際に偶然このパス行が見え、cockpit 側へ通知。

## 漏洩経路

| 経路 | 露出形態 | 対応 |
|---|---|---|
| `~/.bashrc:122` | 平文 `export GOG_KEYRING_PASSWORD=<password>` | ✅ sed で削除（バックアップ取得） |
| `~/.bash_history` | 52行に出現（直接実行・連結実行） | ✅ sed で削除（バックアップ取得） |
| cockpit `.agent/skills/email_organizer/SKILL.md:62` | 平文ハードコード（commit `e38f3ae`） | ✅ commit `af2c5e7` で placeholder 化、push |
| garden `.agent/skills/email_organizer/SKILL.md:62` | 平文ハードコード（commit `654a3b0`） | ✅ commit `71b68a8` で placeholder 化、push |
| 両 GitHub リポ | 上記 commit が `origin/main` へ push 済み | ⏸️ filter-repo 書き換え見送り（private + ローテートで旧パス無効化のため） |

## リスク評価

- gog cli は **GOG_KEYRING_BACKEND=file + GOG_KEYRING_PASSWORD** の組合せで `~/.config/gogcli/keyring/` を暗号化。パスフレーズ + keyring ファイルの両方が揃えば、保存された OAuth refresh token から Gmail/Drive スコープへのアクセスが可能。
- パスフレーズが平文の `~/.bashrc` と `SKILL.md`、`.bash_history` に存在し、keyring ファイルも同 uid からアクセス可能だったため、**漏洩リスクは中〜高**と判断。即時 rotation を実施。
- リポは両方 private なので外部公開リスクは限定的だが、collaborator 追加経路や GitHub トークン漏洩時の二次被害を考慮。

## 対応内容

### 1. ソースコードの修正（自動）

- cockpit / garden 両リポの `SKILL.md:62` の平文を `your_password` placeholder に置換。両リポで commit + push（`af2c5e7` / `71b68a8`）。
- git 履歴の filter-repo 書き換えは見送り（private + 旧パスを無効化することで実害ゼロのため）。

### 2. ローカル環境のクリーンアップ（自動）

- `~/.bashrc:122` の `export GOG_KEYRING_PASSWORD=...` 行を削除。バックアップ: `~/.bashrc.bak.security.20260523_213943`。
- `~/.bash_history` から該当 52 行を sed で削除。バックアップ: `~/.bash_history.bak.security.20260523_213943` および `.bak.security2.*`。

### 3. 新パスフレーズの生成と保管（手動）

- 32文字ランダム英数字を `openssl rand -base64 48 | tr -d '\n/+=' | head -c 32` で生成。
- `~/.config/gogcli/env` (パーミッション 600) に格納。
- `~/.bashrc` 末尾で `[ -f ~/.config/gogcli/env ] && source ~/.config/gogcli/env` により自動読み込み。

### 4. keyring の再生成（手動）

```bash
# 旧 keyring を退避
mv ~/.config/gogcli/keyring ~/.config/gogcli/keyring.OLD.20260523_221152

# 新パスを source した状態で再認証
~/.local/bin/gog auth add tukapontas@gmail.com --manual --services gmail,drive --drive-scope file
```

### 5. Google OAuth refresh token の revoke（手動）

- https://myaccount.google.com/permissions で当該 OAuth クライアントを「アクセス権を削除」
- → 旧 refresh token を Google 側で完全無効化
- 再認証で新 refresh token を取得し、新パスフレーズで暗号化された新 keyring に保存

### 6. bash 履歴汚染防止（自動）

- `~/.bashrc` 末尾に `HISTCONTROL=ignorespace:ignoredups` を追記。
- 以後、行頭にスペースを付けたコマンドは履歴に残らない。

### 7. 動作確認

- `gog gmail labels list` でラベル一覧取得 → 成功
- `gog gmail messages search 'has:attachment -label:処理済 -label:Invoice_Fetched' --account me` で invoice_processor 用の検索クエリも疎通確認 → 成功

## 残作業

### 2026-05-30 以降のクリーンアップ

新環境で1週間運用して問題ないことを確認後、古いバックアップを安全消去:

```bash
shred -u ~/.bashrc.bak.security.20260523_213943
shred -u ~/.bash_history.bak.security.20260523_213943
shred -u ~/.bash_history.bak.security2.*
rm -rf ~/.config/gogcli/keyring.OLD.20260523_221152
```

### 任意（後回し可）

- https://myaccount.google.com/security で「最近のセキュリティアクティビティ」を確認し、不審なアクセスがないか監査
- https://myaccount.google.com/permissions で承認済み OAuth クライアントの一覧を確認

### 見送った対応

- **OAuth client_id / client_secret の rotation**: 漏洩したのは keyring パスフレーズであり、client_secret 単独での悪用は困難（OAuth 同意フローが別途必要）なため、塚越さん判断で client は使い回し。徹底するなら Google Cloud Console で新 OAuth client を作成し `gog auth credentials <new.json>` で登録し直す。
- **git history の filter-repo 書き換え**: private リポ + パスローテートで旧パスは無効化されているため、書き換えのコスト（force push、collaborator 周知）が割に合わないと判断。

## 副次的に発生した事故と再発防止

対応作業中、AI 側の確認コマンドのミスにより**新パスフレーズが 2 回連続で AI チャットログに出力される**事故が発生（即時再生成で実害ゼロ化）。原因と対策:

- 原因: `echo "VAR: ${VAR:+SET (length=${#VAR})}${VAR:-UNSET}"` という構文を使用した。`${VAR:-UNSET}` は「VAR が unset なら UNSET、set なら **VAR の値そのもの**」を返すため、値が連結出力されてしまった。
- 対策: 確認コマンドのテンプレートを「**length 比較**」または「**set/unset 判定**」の2形式に限定する運用ルールを `docs/security/README.md` に明文化（[§1.4](../README.md#14-secret-の値を画面ログに出力しない)）。
- 加えて、`HISTCONTROL=ignorespace:ignoredups` 設定により、上矢印で過去の危険なコマンドが再実行される事故も緩和。

## 再認証手順（参考）

将来 keyring を再生成する必要が出た時の標準手順:

```bash
# 1. 旧 keyring 退避（消さずに退避）
mv ~/.config/gogcli/keyring ~/.config/gogcli/keyring.OLD.$(date +%Y%m%d_%H%M%S)

# 2. 新パス生成 → env に直書き（値を画面に出さない）
install -m 600 /dev/null ~/.config/gogcli/env
{
  printf '# Generated %s\n' "$(date -Iseconds)"
  printf 'export GOG_KEYRING_PASSWORD=%q\n' "$(openssl rand -base64 48 | tr -d '\n/+=' | head -c 32)"
} > ~/.config/gogcli/env

# 3. 現シェルに反映
source ~/.config/gogcli/env
test ${#GOG_KEYRING_PASSWORD} -eq 32 && echo "OK"

# 4. Google 側で旧 OAuth を revoke
# (https://myaccount.google.com/permissions で「アクセス権を削除」)

# 5. 新 keyring 作成（対話モード）
~/.local/bin/gog auth add tukapontas@gmail.com --manual --services gmail,drive --drive-scope file

# 6. 動作確認
~/.local/bin/gog gmail labels list --plain | head
```

## 関連

- 運用ルール本体: [`../README.md`](../README.md)
- gog cli 認証構成: [steipete/gogcli](https://github.com/steipete/gogcli)
- 通知元: harappa-garden 側エージェント（tmux-workspace 環境整備時に発見）
