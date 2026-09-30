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

fetch_health() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS http://127.0.0.1:4004/api/health
    return
  fi
  docker compose -f docker-compose.prod.yml exec -T herbal-rag \
    python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:4004/api/health').read().decode())"
}

i=0
while [ "$i" -lt 40 ]; do
  if fetch_health; then
    echo
    break
  fi
  i=$((i + 1))
  sleep 3
done

if [ "$i" -ge 40 ]; then
  echo "健康检查失败"
  docker compose -f docker-compose.prod.yml logs --tail 80
  exit 1
fi

echo "从 GitHub 导入古籍"
if ! docker compose -f docker-compose.prod.yml exec -T herbal-rag \
  python -m app.cli import-tcmoc; then
  echo "古籍导入失败"
  docker compose -f docker-compose.prod.yml logs --tail 120
  exit 1
fi

body=$(fetch_health)
echo "$body"
echo "$body" | grep -q '"tcmoc_documents":3' || {
  echo "古籍没有写入索引"
  docker compose -f docker-compose.prod.yml logs --tail 120
  exit 1
}

docker image prune -f >/dev/null 2>&1 || true
