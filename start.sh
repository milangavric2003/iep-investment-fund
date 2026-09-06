#!/bin/sh

set -e

until flask --app migrate:application db upgrade; do
    echo "Waiting for MySQL to become available..."
    sleep 2
done

python seed.py
exec python main.py