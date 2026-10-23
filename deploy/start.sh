#!/bin/sh
set -eu

PGDATA="${PGDATA:-/var/lib/forge-pg}"
PORT="${PORT:-80}"
# Four extra Python processes plus MiniLM plus Postgres do not fit in 512 MB.
export FORGE_TOOL_TRANSPORT=inprocess
export PATH="/usr/lib/postgresql/16/bin:${PATH}"

if [ ! -s "${PGDATA}/PG_VERSION" ]; then
  mkdir -p "${PGDATA}"
  chown postgres:postgres "${PGDATA}"
  chmod 700 "${PGDATA}"
  gosu postgres initdb -D "${PGDATA}" --username=postgres --auth-local=trust --auth-host=trust
fi

gosu postgres pg_ctl -D "${PGDATA}" -w start \
  -o "-c listen_addresses=127.0.0.1 -c shared_buffers=32MB -c max_connections=20"

gosu postgres psql -d postgres -c "CREATE ROLE forge WITH LOGIN SUPERUSER" || true
gosu postgres psql -d postgres -c "CREATE DATABASE forge OWNER forge" || true

sed -i "s/worker_processes auto;/worker_processes 1;/" /etc/nginx/nginx.conf
sed "s/__PORT__/${PORT}/g" /etc/nginx/forge.conf > /etc/nginx/conf.d/forge.conf
rm -f /etc/nginx/sites-enabled/default

cd /app
/opt/forge/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 &
api_pid=$!

ready=0
i=0
while [ "${i}" -lt 90 ]; do
  if /opt/forge/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"; then
    ready=1
    break
  fi
  if ! kill -0 "${api_pid}" 2>/dev/null; then
    echo "api exited before health" >&2
    exit 1
  fi
  i=$((i + 1))
  sleep 2
done

if [ "${ready}" -ne 1 ]; then
  echo "api health did not come up" >&2
  exit 1
fi

exec nginx -g "daemon off;"
