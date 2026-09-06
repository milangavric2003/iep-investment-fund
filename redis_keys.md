# Redis Order Storage

Redis stores pending orders temporarily. MongoDB is the permanent source of asset data.

## Keys

The pending UUID index is a Redis set:

```text
fund:orders:pending
```

Each order is stored as a JSON string under:

```text
fund:orders:<uuid>
```

The index allows the director to list orders without scanning the whole Redis keyspace. The order key contains the complete API order, including `order_type`.

## Inspect Redis

From the project directory:

```powershell
docker compose -f development.yaml exec redis redis-cli
SMEMBERS fund:orders:pending
GET fund:orders:<uuid>
```

The Redis container uses append-only persistence and the Compose file mounts the `redis_volume` named volume at `/data`. Removing the volume deletes the pending orders:

```powershell
docker compose -f development.yaml down -v
```

Do not use `down -v` during a normal restart or demonstration when the data should remain.
