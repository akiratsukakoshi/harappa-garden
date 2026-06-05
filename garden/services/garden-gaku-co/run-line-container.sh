#!/usr/bin/env bash
# garden-gaku-co — 社内(core_team)LINE Webhook サーバ コンテナの (再)起動スクリプト。
#
# なぜ docker-compose を使わないか(S34):
#   VPS の docker-compose は v1 で、buildkit 製イメージの image config に
#   'ContainerConfig' キーが無いと recreate 経路で KeyError で落ちる既知バグがある。
#   そのため compose ではなく `docker run` で直接起動する(docker-compose.line.yml は参考用)。
#
# キープアライブ:
#   --restart unless-stopped により docker daemon 再起動/クラッシュ後も自動復帰。
#   cron は不要(ホストプロセス方式の run-line-server.sh は廃止)。
#
# 配線:
#   NPM(proxy-manager_default 上のコンテナ)→ garden-gaku-core:8011(同ネットワーク)。
#   ポートは publish しない = 公開 IP には一切出ない(エアギャップの一部)。
#
# 使い方:
#   ./run-line-container.sh          # イメージがあれば起動、無ければ build してから
#   ./run-line-container.sh --build  # 依存更新時など、必ず rebuild してから起動
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=garden-gaku-core:latest
NAME=garden-gaku-core
NETWORK=proxy-manager_default

if [ "${1:-}" = "--build" ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "[build] $IMAGE"
  docker build -f Dockerfile.line -t "$IMAGE" .
fi

# env_file はコンテナ作成時にしか読まれないため、設定変更時は作り直しが必要。
docker rm -f "$NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$NAME" \
  --restart unless-stopped \
  --network "$NETWORK" \
  --user "1000:1000" \
  -w /home/vps-harappa/garden/services/garden-gaku-co \
  --env-file .env \
  -e HOME=/tmp \
  -v /home/vps-harappa/garden:/home/vps-harappa/garden \
  -v /home/vps-harappa/garden-mirror:/home/vps-harappa/garden-mirror \
  "$IMAGE" >/dev/null

echo "[run] $NAME started on $NETWORK (container-internal :8011)"
echo "[hint] health: docker exec proxy-manager_nginx-proxy-manager_1 curl -s http://garden-gaku-core:8011/health"
