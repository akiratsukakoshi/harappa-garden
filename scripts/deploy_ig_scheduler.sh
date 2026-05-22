#!/bin/bash
# IGスケジューラーをXserverにデプロイする
# 使い方: bash scripts/deploy_ig_scheduler.sh
set -e

REMOTE="harappa"
REMOTE_DIR="/home/vps-harappa/ig_scheduler"
LOCAL_DIR="deploy/ig_scheduler"

echo "=== IGスケジューラー デプロイ ==="
echo "転送先: $REMOTE:$REMOTE_DIR"
echo ""

# リモートにディレクトリ作成
ssh "$REMOTE" "mkdir -p $REMOTE_DIR"

# ファイル転送（.envは除外）
rsync -avz --exclude='.env' --exclude='__pycache__' --exclude='*.pyc' \
  "$LOCAL_DIR/" "$REMOTE:$REMOTE_DIR/"

# .envの存在確認
ENV_EXISTS=$(ssh "$REMOTE" "[ -f $REMOTE_DIR/.env ] && echo yes || echo no")
if [ "$ENV_EXISTS" = "no" ]; then
  echo ""
  echo "⚠️  初回セットアップ: .env を作成してください"
  echo "  ssh harappa"
  echo "  cp $REMOTE_DIR/.env.example $REMOTE_DIR/.env"
  echo "  nano $REMOTE_DIR/.env"
  echo ""
  echo "設定後に再度このスクリプトを実行してください。"
  exit 1
fi

# ビルド・起動
echo "--- Docker ビルド・起動 ---"
ssh "$REMOTE" "cd $REMOTE_DIR && docker-compose up -d --build 2>&1"

# ヘルスチェック
echo "--- ヘルスチェック (3秒待機) ---"
sleep 3
ssh "$REMOTE" "curl -s http://localhost:8100/health"
echo ""
echo "=== デプロイ完了 ==="
