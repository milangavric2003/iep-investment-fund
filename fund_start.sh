#!/bin/sh

set -e

until python -c "from fund_helpers import mongo_client, redis_client; mongo_client.admin.command('ping'); redis_client.ping()"; do
    echo "Waiting for MongoDB and Redis to become available..."
    sleep 2
done

if [ "${RUN_MONGO_SEED:-0}" = "1" ]; then
    python mongo_seed.py
fi

exec python "${SERVICE_MODULE}"