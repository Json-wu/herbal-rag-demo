#!/bin/sh
# 在服务器上拉取新镜像并重启。由 GitHub Actions 调用。
set -eu

DEPLOY_PATH="${DEPLOY_PATH:-/opt/herbal-rag}"
cd "$DEPLOY_PATH"

if ! docker compose version >/dev/null 2>&1; then
  echo "服务器需要 Docker Compose v2（命令是 docker compose）"
  exit 1
fi

touch .env
echo "$ALIYUN_REGISTRY_PASSWORD" | docker login \
  --username "$ALIYUN_REGISTRY_USER" \
  --password-stdin \
  "$ALIYUN_REGISTRY"

export HERBAL_IMAGE="$IMAGE"
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker logout "$ALIYUN_REGISTRY" >/dev/null 2>&1 || true

check_health() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS http://127.0.0.1:8000/api/health
    return
  fi
  docker compose -f docker-compose.prod.yml exec -T herbal-rag \
    python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read().decode())"
}

i=0
while [ "$i" -lt 20 ]; do
  if check_health; then
    echo
    docker image prune -f >/dev/null 2>&1 || true
    exit 0
  fi
  i=$((i + 1))
  sleep 3
done

echo "健康检查失败"
docker compose -f docker-compose.prod.yml logs --tail 80
exit 1
