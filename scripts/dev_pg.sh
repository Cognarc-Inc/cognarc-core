#!/usr/bin/env bash
# 起一個只聽 127.0.0.1 的臨時 PostgreSQL 16 供整合測試；認證為本機 trust，只供測試。
#   scripts/dev_pg.sh up    # 啟動（已在跑則略過），並印出 CORE_TEST_ADMIN_URL
#   scripts/dev_pg.sh down  # 停止
# 優先用本機的 postgres 伺服器二進位（brew install postgresql@16；資料放 .pgdata/，不進版控）；
# 只有 libpq 時改用 Docker 的公開映像 postgres:16（容器名 cognarc-core-pg）。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PGDATA="${PGDATA:-$ROOT/.pgdata}"
PORT="${CORE_PG_PORT:-55434}"
CONTAINER="cognarc-core-pg"
URL="postgresql+psycopg://$USER@127.0.0.1:$PORT/postgres"

have_server() { command -v pg_ctl >/dev/null 2>&1 && [ -x "$(dirname "$(command -v pg_ctl)")/postgres" ]; }

wait_ready() {
  for _ in $(seq 1 60); do
    pg_isready -h 127.0.0.1 -p "$PORT" -U "$USER" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "Postgres 沒有在 60 秒內就緒" >&2
  return 1
}

case "${1:-}" in
  up)
    if have_server; then
      if [ ! -f "$PGDATA/PG_VERSION" ]; then
        initdb -D "$PGDATA" -A trust -U "$USER" --encoding=UTF8 --locale=C >/dev/null
      fi
      if pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
        echo "already running on 127.0.0.1:$PORT"
      else
        pg_ctl -D "$PGDATA" -l "$PGDATA/server.log" -o "-p $PORT -k '' -c listen_addresses=127.0.0.1" -w start >/dev/null
        echo "started on 127.0.0.1:$PORT (log: $PGDATA/server.log)"
      fi
    else
      # 只拉公開映像；把容器工具的憑證設定指向空檔，避免觸發全域 credential helper（例如 gcloud）。
      export DOCKER_CONFIG="${DOCKER_CONFIG:-$ROOT/.pgdata/docker-config}"
      mkdir -p "$DOCKER_CONFIG" && [ -f "$DOCKER_CONFIG/config.json" ] || echo '{}' > "$DOCKER_CONFIG/config.json"
      if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
        echo "container $CONTAINER already running on 127.0.0.1:$PORT"
      else
        docker run -d --rm --name "$CONTAINER" -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER="$USER" \
          -p "127.0.0.1:$PORT:5432" postgres:16 >/dev/null
        echo "started container $CONTAINER on 127.0.0.1:$PORT"
      fi
    fi
    wait_ready
    echo "export CORE_TEST_ADMIN_URL=$URL"
    ;;
  down)
    if have_server && pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
      pg_ctl -D "$PGDATA" -m fast stop >/dev/null && echo "stopped"
    elif docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
      docker stop "$CONTAINER" >/dev/null && echo "stopped container $CONTAINER"
    else
      echo "nothing running"
    fi
    ;;
  *)
    echo "usage: $0 up|down" >&2
    exit 2
    ;;
esac
