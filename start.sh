#!/bin/sh

set -e

until flask --app migrate:application db upgrade; do
    echo "Waiting for MySQL to become available..."
    sleep 2
done

python seed.py
exec python main.py

# flask --app migrate:application db init
# flask --app migrate:application db migrate -m "Custom message."
# flask --app migrate:application db upgrade

# to enter already running container:
    # docker compose -f development.yaml exec authentication sh
    # exit