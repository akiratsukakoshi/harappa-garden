# VPS secret 管理方針(Phase 3b の入口)

- **日付**: 2026-05-25
- **記録**: セッション7
- **決定者**: 塚越さん (庭師) / Claude (壁打ち相手)
- **ステータス**: 方針合意・大枠のみ。実雅詳細(VPS ハードニング監査・OAuth scope 棚卸し・age 移行)は Phase 3b の別セッションで確定

## 背景

セッション7 で「cron 種実行ホスト = VPS」と確定([別 ADR](2026-05-25-seed-schema-and-execution-host.md))した結果、HMC 依存種を active 化するには **HMC を VPS に移す or 必要部分を切り出す** ことが必要となり、その前提として **VPS に business secret(Freee / Google OAuth / 人事労務 freee)を載せる** ことになる。

塚越さんから「OK だがセキュリティについては議論したい」と提起 → 本 ADR で方針の入口を確定する。

既存ルール: [docs/security/README.md](../security/README.md) は **WSL(ローカル)前提**。VPS 環境(常時ネットワーク露出・複数サービス相乗り・侵害確率高)で追加考慮すべき項目は未記載。

## 決定 1: secret 保管 = 平文 env + 600 で開始、age 暗号化への発展余地を残す

### 初期スタート(Phase 3b の入口)

- `~/.config/{service}/env` 形式のファイルに secret を平文で配置
- パーミッション `600`(親ディレクトリ `700`)
- VPS 上の運用は **既存 WSL ルール([docs/security/README.md §1.1〜1.5](../security/README.md))をそのまま延長**
- 環境変数は systemd Unit or Docker Compose `env_file` 経由で注入(ファイル経路を起動側に固定)

### 発展余地(Phase 3b 後半 or Phase 4)

- secret 量が増えてきたら **age 暗号化 + master key** へ移行
- master key の保管設計(VPS 内 / 別経路)も同時に決める

### 採用しなかった案

| 案 | 却下理由 |
|---|---|
| 初期から age 暗号化 | master key 保管設計が必要になり、初期実装の足を引っ張る。WSL ルールとの段差も大きい |
| sops + age | 1人運用ではバージョン管理のメリットが学習コストに見合わない。チーム拡大時に再評価 |
| クラウド secret manager(Vault / GCP Secret Manager 等) | 月額コスト + ベンダー依存 + 新規依存追加。CLAUDE.md のベンダー中立方針とも整合性悪い |

## 決定 2: 隔離 = サービス単位 Docker 分離 + コンテナ内 root 不使用

### 構成

```
[VPS]
  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
  │ gaku-co5.0      │  │ hmc-on-vps      │  │ garden-seed-     │
  │ (LINE Bot)      │  │ (HMC SKILL 群)  │  │ launcher         │
  │ 既存            │  │ Phase 3b 移植   │  │ Phase 3a 実装    │
  └────────┬────────┘  └────────┬────────┘  └────────┬─────────┘
           │                    │                    │
           ▼                    ▼                    ▼
       (LINE webhook)      (Freee/Google API)    (cron + Claude Code)
  ┌─────────────────┐  ┌─────────────────────────────────────────┐
  │ CouchDB         │  │ /opt/garden/                            │
  │ (LiveSync DB)   │  │   tasks/*.md(平文 MD ミラー)             │
  │                 │  │   board/{pending,processed}/             │
  │                 │  │   seeds/.log/                            │
  └─────────────────┘  └─────────────────────────────────────────┘
```

### ルール

- **各サービスは別 Docker コンテナ**(gaku-co5.0 / hmc-on-vps / garden-seed-launcher / CouchDB)
- **コンテナ内では root 不使用**(non-root user で起動)
- **secret は必要コンテナのみマウント**(全コンテナ共通の secret マウントは禁止)
- ホスト側のファイルパーミッション(600 / 700)は維持
- Docker network はサービス間通信に必要なものだけ通す(全コンテナ同一ネットワークは避ける)

### 侵害時の Blast radius

- 1 コンテナ侵害 → そのコンテナにマウントされた secret + network 接続先まで
- gaku-co5.0 侵害 → LINE Bot トークンのみ(財務データへ届かない)
- hmc-on-vps 侵害 → Freee / Google credentials(財務・業務データ全部)
- 種ランチャー侵害 → CouchDB + board ファイル(business data + 議論ログ)

### 採用しなかった案

| 案 | 却下理由 |
|---|---|
| ホスト上で uid だけ分離(Docker 不使用) | 侵害時の隔離が弱い。サービス間ファイルアクセスを制御しきれない |
| 全部同一 uid(従来型) | 1つ侵害されれば全部抜かれる。 |

## 決定 3: OAuth scope 最小化(大枠合意のみ)

### 原則

- **scope を最小に絞る**(write が要らないなら read のみ、特定リソースのみアクセス可能なら全体権限を取らない)
- **人事労務 freee は最も厳重に扱う**(給与・個人情報)。独立 OAuth client を作成し、 **アクセスする種を限定**
- **読取り専用と書込みでトークン分離**(可能な場合は別 OAuth client)
- Google Drive は **file scope** のみ(現状 gog cli が既にこの方式)

### 実雅詳細は別セッション

- HMC 現行 OAuth scope の棚卸し
- 削減可能 scope の特定
- 新規 OAuth client 作成計画(人事労務 freee / 読取専用クライアント)
- 種ごとの必要 scope マップ

→ Phase 3b の HMC 移植作業と同時並行で進める。

## 決定 4: rotation = 発覚時 + 年1強制ローテ

### 運用

- **漏えい発覚時**: 即時ローテ([docs/security/README.md §4 緊急時対応原則](../security/README.md) + [2026-05-23 gog インシデント](../security/incidents/2026-05-23_gog_keyring_rotation.md) の手順を踏襲)
- **年1強制ローテ**: 全 token を1年に1度ローテ(漏えい発覚していなくても)
- **手順**: スクリプト化に動くが、初期は **チェックリスト**(各サービスの再認証ステップを docs/security/ に追記)
- **記録**: ローテ実施は都度 [docs/security/incidents/](../security/incidents/) に YYYY-MM-DD 形式で記録(発覚時もルーチンも同様)

### スクリプト化の方向性

- `~/.config/garden/rotate.sh {service}` で各サービスのローテ手順を半自動化
- Phase 3b 後半 or 必要が出たら実装

## 決定 5: docs/security/README.md を VPS 環境向けに拡張(本セッション内で着手)

現状の docs/security/README.md は WSL 前提。本 ADR の決定 1〜4 を反映するため、追記する。

### 本セッションで追記する範囲

- 「§6. VPS 環境での追加考慮」セクション(本 ADR の決定 1〜4 を要約)

### 別セッションで詳細化する範囲

- VPS ハードニング監査(SSH 鍵認証のみ・fail2ban・firewall・OS/Docker 自動更新の現状確認と強化)
- Docker secret マウント手順
- ローテスクリプト

## 横断: 監査・ログ

- 種実行ログは `garden/seeds/.log/` に蓄積([別 ADR](2026-05-25-seed-schema-and-execution-host.md) で確定済)
- Freee / Google API 呼び出しログは Phase 3b の HMC 移植時に設計(現状は HMC 内部のログに依存)
- 異常検知(短時間に大量送信など)は Phase 4 watcher 候補

## CLAUDE.md / 既存ルールとの整合性

- **CLAUDE.md ベンダー中立性**: クラウド secret manager を採用しないことで整合
- **CLAUDE.md secret 確認コマンドルール**: 「length比較 か set/unset判定のみ」は VPS でも厳守
- **docs/security/README.md §1.4 同上ルール**: 過去インシデント(2026-05-23 GOG keyring 漏えい)の教訓を VPS 運用にも適用

## Phase 3b 別セッションへの宿題

- VPS ハードニング監査(SSH / firewall / fail2ban / 自動更新の現状)
- HMC OAuth scope 棚卸し
- 人事労務 freee 独立 OAuth client 作成計画
- 読取/書込トークン分離計画
- Docker Compose スケルトン(gaku-co5.0 / hmc-on-vps / garden-seed-launcher / CouchDB)
- ローテスクリプトの設計
- age 暗号化への移行条件(secret 数の閾値・運用継続期間)

## 関連

- [セッション7 サマリ](../sessions/2026-05-25-session7.md)
- [種スキーマ + 実行ホスト ADR](2026-05-25-seed-schema-and-execution-host.md)
- [docs/security/README.md](../security/README.md)(本 ADR で §6 追記)
- [2026-05-23 GOG keyring 漏えいインシデント](../security/incidents/2026-05-23_gog_keyring_rotation.md)
- [CLAUDE.md](../../CLAUDE.md)
- [gaku-co5.0 INTERFACE](file:///home/tukapontas/gaku-co5.0/INTERFACE.md)
