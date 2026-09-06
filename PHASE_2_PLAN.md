# Phase 2 Plan: Investment Fund Management

## Scope

Implement the non-blockchain investment-fund part from `IEP_Projekat_2026.pdf`.

This phase adds:

- MongoDB storage for assets;
- Redis storage for pending buy and sell orders;
- an employee service;
- a director service;
- JWT role checks using tokens issued by the existing authentication service;
- Docker Compose services with persistent MongoDB and Redis storage.

Kubernetes and the optional Ethereum voting extension remain excluded from this phase.

The existing authentication service, MySQL database, migrations, seed data, and account endpoints remain unchanged unless a small shared configuration change is required.

## Python Environment Convention

- Use only the existing project `.venv` for Phase 2 development, dependency installation, migrations, scripts, and validation.
- The environment must use Python 3.13. Do not run project commands with the Windows global Python directly.
- Keep every runtime dependency in `requirements.txt`, including `pymongo` and `redis`, so the same environment can be recreated on the defense machine.
- Docker images install dependencies from `requirements.txt` and do not copy the host `.venv`.
- Windows commands in the runbook must use the activated `.venv` or explicit paths such as `.venv\\Scripts\\python.exe` and `.venv\\Scripts\\flask.exe`.

## Existing Examples Used

The implementation will follow the local exercises as closely as possible:

- `mongodb-vezbe4/main.py` for `MongoClient`, `ObjectId`, JSON conversion, MongoDB queries, and aggregation pipelines;
- `mongodb-vezbe4/mongo.yaml` for the basic MongoDB container;
- `Docker-vezbe5/Synchronization/producer_consumer.py` for Redis lists and blocking queue behavior;
- `Docker-vezbe5/Synchronization/publish_subscribe.py` for Redis connection configuration;
- `Docker-vezbe5/JWT_ban/admin.py` for Redis usage inside a Flask service and configuration through environment variables;
- `Docker-vezbe5` Dockerfiles and Compose files for service separation.
- `Kubernetes-vezbe6` for maybe some coding, but no kubernetes implementation still.
- `Other files from IEP folder if needed`

The project will improve the exercise examples where needed for this specification: no hardcoded `localhost` inside containers, persistent volumes, environment-based configuration, UUID order identifiers, explicit validation, and clear startup instructions.

## Proposed Structure

The phase should introduce the following files while keeping the current project layout simple:

```text
iep-investment-fund/
    employee.py
    director.py
    fund_configuration.py
    fund_helpers.py
    employee.dockerfile
    director.dockerfile
    development.yaml                 # extended with MongoDB, Redis, employee, director
    mongo_seed.py                     # optional local/demo asset seed
    mongo_seed.json                   # optional demo assets
    redis_keys.md                     # short explanation of the Redis order format
```
!!! maybe organize structure from above in some folders - so it be better organized

The exact module names may be adjusted during implementation if an existing local pattern makes a better fit. The two HTTP services should be separate processes because the assignment explicitly describes employee and director containers.

Shared MongoDB and Redis connection helpers should be small and explicit. They should not introduce a large framework or hide the database queries that are useful for the course defense.

## Phase 2.1: Shared Configuration and Authentication

Add environment-driven configuration for the fund services:

- `MONGO_URL`, defaulting to `mongodb://root:example@localhost:27017/?authSource=admin` for host-side development;
- `MONGO_DATABASE`, defaulting to `investment_fund`;
- `REDIS_HOST`, defaulting to `localhost`;
- `REDIS_PORT`, defaulting to `6379`;
- `REDIS_DB`, defaulting to `0`;
- `JWT_SECRET_KEY`, equal to the authentication service secret in Compose.

Inside Compose, the values must point to service names such as `mongodb` and `redis`, not `localhost`.

Both services will initialize `JWTManager` with the same secret and use the existing JWT claims:

- identity: user email;
- `forename`;
- `surname`;
- `role`.

Role checks:

- employee endpoints require `EMPLOYEE`;
- director endpoints require `DIRECTOR`.

The missing authorization behavior must stay compatible with the assignment: HTTP 401 and `{"msg": "Missing Authorization Header"}`.

A role decorator may be shared with the existing `decorators.py`, but the existing authentication endpoints must not be broken.

## Phase 2.2: MongoDB Asset Document

Store every asset in an `assets` collection with this document shape:

```json
{
  "name": "Government Bond",
  "categories": ["fixed-income", "government"],
  "buying_price": 10000,
  "buying_date": "2026-09-06T12:00:00Z",
  "selling_price": 12000,
  "selling_date": "2026-10-06T12:00:00Z",
  "info": {
    "issuer": "Example State",
    "rating": {
      "value": "AAA"
    }
  }
}
```

Implementation notes:

- MongoDB supplies the `_id` ObjectId. API responses expose it as the string field `id`.
- `selling_price` and `selling_date` are absent for assets that have not been sold.
- Dates should be stored as BSON datetimes, not only strings, so comparison queries work correctly.
- `info` remains an unrestricted nested document.
- Buying and selling prices should be numeric values greater than zero.
- Categories are a non-empty list of strings.

Add a small optional demo seed containing both sold and unsold assets, multiple categories, and nested `info` fields. The seed must be safe to run more than once, for example by checking a stable demo marker or using deterministic IDs.

## Phase 2.3: Employee Service

Create the employee HTTP service with these JWT-protected endpoints.

### `POST /search`

Implement all filters in the MongoDB query rather than loading all assets and filtering in Python.

Supported filters:

- `name`: case-insensitive substring search;
- `category`: membership in `categories`;
- `buying_date`: assets bought after the supplied ISO 8601 datetime;
- `selling_date`: sold assets with selling date before the supplied ISO 8601 datetime; unsold assets must be excluded;
- `info_filters`: all filters must match, using a safe allowlist of MongoDB comparison operators.

Allowed comparison operators should correspond to the specification values, for example:

- `eq` -> `$eq`;
- `ne` -> `$ne`;
- `gt` -> `$gt`;
- `gte` -> `$gte`;
- `lt` -> `$lt`;
- `lte` -> `$lte`.

The operator must never be copied directly from user input into a MongoDB query. The dotted `field` path must be prefixed with `info.` and validated so a caller cannot escape the `info` document.

All requested filters are combined with logical AND.

Return HTTP 200 and:

```json
{
  "assets": [
    {
      "id": "...",
      "name": "...",
      "categories": [],
      "buying_date": "...",
      "buying_price": 10000,
      "selling_date": "...",
      "selling_price": 12000,
      "info": {}
    }
  ]
}
```

Optional selling fields must not be added to unsold asset responses.

### `POST /create_buy_order`

Validation order:

1. Check `name`.
2. Check `categories`.
3. Check `buying_price`.
4. Check `info`.
5. Reject an empty categories list with `Categories list is empty.`.
6. Reject a non-numeric or non-positive buying price with `Invalid buying price.`.

On success, create a UUID and store a BUY order in Redis. Return HTTP 200 with no body.

### `POST /create_sell_order`

Validation order:

1. Check `id`.
2. Check `selling_price`.
3. Validate the ObjectId format.
4. Check that the asset exists in MongoDB.
5. Validate that the selling price is numeric and positive.

Errors must use the specification messages, including `Invalid id.` and `Invalid selling price.`.

On success, create a UUID and store a SELL order in Redis. Return HTTP 200 with no body.

## Phase 2.4: Redis Order Design

Use Redis as a temporary pending-order store, not as the permanent asset database.

Proposed key format:

```text
fund:orders:{uuid}
```

Each key stores one JSON order document:

BUY:

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "order_type": "BUY",
  "name": "Government Bond",
  "categories": ["fixed-income"],
  "info": {"issuer": "Example State"},
  "buying_price": 10000
}
```

SELL:

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440001",
  "order_type": "SELL",
  "id": "66688f0f4b6f2d6a2f7c9a11",
  "selling_price": 12000
}
```

Maintain a Redis set or list of pending UUIDs so `/pending_orders` can retrieve all pending requests without scanning the entire Redis keyspace. The implementation should use atomic Redis commands where practical:

- `SET` for the order document;
- `SADD` for the pending UUID index;
- `GET` and `SREM` when reading/removing an order.

The order is temporary until a director processes it. Rejected orders are removed from Redis. Approved orders are removed from Redis only after the MongoDB operation succeeds.

This is different from the exercise's producer-consumer queue: the director must be able to list and choose a specific UUID, so a FIFO-only list is not enough.

`/pending_orders` must return the same order fields required by the PDF and must not expose internal Redis key names.

## Phase 2.5: Director Service

### `GET /pending_orders`

Require a director token. Return HTTP 200 with:

```json
{
  "orders": []
}
```

The order list may be sorted by UUID or insertion timestamp, but the choice must be deterministic and documented.

### `POST /decision`

Request body:

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "approved": true
}
```

Validation order:

1. `uuid` is present and non-empty;
2. `uuid` is a valid UUID and exists in Redis;
3. `approved` is present;
4. `approved` is a JSON boolean.

Use the exact messages:

- `Field uuid is missing.`;
- `Invalid uuid.`;
- `Field approved is missing.`;
- `Invalid decision.`.

When `approved` is false, remove the order from Redis and return HTTP 200.

When `approved` is true:

- BUY: insert a new MongoDB asset with the current approval time as `buying_date`;
- SELL: update the existing asset with `selling_price` and the current approval time as `selling_date`;
- remove the Redis order only after the MongoDB operation succeeds;
- return HTTP 200 with no body.

The operation should use an atomic or carefully ordered Redis removal strategy so a failed MongoDB operation does not silently lose an order. This behavior should be explained in a short code comment because it is an important distributed-storage boundary.

## Phase 2.6: Report

### `GET /report`

Require a director token.

Use a MongoDB aggregation pipeline rather than calculating the complete report in Python:

1. unwind `categories`;
2. group by category;
3. sum `buying_price` as `spent`;
4. sum `selling_price` only for sold assets as `earned`;
5. sort by:
   - `earned` descending;
   - `spent` ascending;
   - category name ascending;
6. project the requested response shape.

Return:

```json
{
  "statistics": [
    {
      "category": "fixed-income",
      "spent": 10000,
      "earned": 12000
    }
  ]
}
```

An unsold asset contributes to `spent`, but not to `earned`.

## Phase 2.7: Docker Compose and Persistence

Extend `development.yaml` with:

- `mongodb` using a named volume mounted at `/data/db`;
- `redis` using a named volume mounted at `/data`;
- `employee` service;
- `director` service;
- environment variables for MongoDB, Redis, and JWT configuration;
- health checks or startup retry behavior for MongoDB and Redis;
- ports for host-side development.

Keep the existing MySQL, Adminer, and authentication services working.

Suggested host ports, subject to conflicts:

- employee API: `5001`;
- director API: `5003` (mapped to container port `5002`; change if unavailable);
- MongoDB: `27017`;
- Redis: `6379`.

The host ports are only for development and Compass/debugging. Containers must use Compose service names and internal ports:

- MongoDB: `mongodb:27017`;
- Redis: `redis:6379`.

MongoDB Compass connection for the Compose setup:

```text
mongodb://root:example@localhost:27017/?authSource=admin
```

Compass is useful for inspecting documents and collections, but the application remains responsible for all writes used in the demonstration. MongoDB persistence comes from the named Docker volume, not from Compass.

Redis has no equivalent document browser requirement. We will inspect it with `redis-cli` inside the Redis container when needed:

```powershell
docker compose -f development.yaml exec redis redis-cli
KEYS fund:orders:*
SMEMBERS fund:orders:pending
GET fund:orders:<uuid>
```

The exact inspection commands will be documented after implementation.

## Phase 2.8: Demonstration and Defense Runbook

Update `README.md` with a reproducible sequence and don't shorten already existing useful readme passuses:

1. Start Docker Desktop.
2. Run `docker compose -f development.yaml up --build`.
3. Confirm all services are healthy with `docker compose ps`.
4. Open Compass and connect to MongoDB using the documented URI.
5. Obtain an employee JWT from the authentication API.
6. Create a BUY order and a SELL order.
7. Obtain a director JWT.
8. List pending orders.
9. Approve or reject an order.
10. Confirm the MongoDB asset and Redis order state.
11. Request the report.
12. Restart the database services and confirm that MongoDB assets remain.

Keep all API examples in English, matching the project's coding-language rule. Explain the Serbian PDF requirement in the README where exact endpoint error messages are reproduced.

## Validation Checklist

Before Phase 2 is considered complete:

- employee endpoints reject missing, expired, and director/employee-incompatible tokens as appropriate;
- director endpoints reject employee tokens;
- MongoDB assets survive container restart;
- Redis pending orders survive a Redis container restart while the named volume remains;
- MongoDB Compass can inspect the `investment_fund.assets` collection;
- `/search` performs filtering in MongoDB and handles nested `info` paths;
- all search filters are combined with AND;
- unsold assets are excluded from selling-date searches;
- BUY and SELL validation messages match the PDF;
- pending orders expose UUIDs and the correct BUY/SELL fields;
- approving a BUY creates an asset with the approval timestamp;
- approving a SELL updates the requested asset;
- rejecting an order removes it without changing MongoDB;
- failed approval does not silently lose the Redis order;
- `/report` sorting exactly matches the specification;
- Compose can start from a clean state;
- the README is sufficient to demonstrate the complete phase without assistance.

## Implementation Boundary

Do not modify application code until this plan is reviewed and approved. After approval, implement the phase in small slices:

1. shared configuration and Mongo/Redis connection checks;
2. Mongo asset representation and seed data;
3. employee search;
4. Redis BUY/SELL order creation;
5. director pending orders and decisions;
6. report aggregation;
7. Compose persistence, runbook, and end-to-end tests.

## Current Implementation Status

Phase 2 is implemented and running through Docker Compose. The current host endpoints are:

- authentication: `http://localhost:5000`;
- employee: `http://localhost:5001`;
- director: `http://localhost:5003` mapped to container port `5002`;
- MongoDB: `localhost:27017`;
- Redis: `localhost:6379`.

Validated behavior includes JWT role separation, MongoDB nested search filters, BUY order creation and approval, report aggregation, MongoDB persistence, and Redis persistence. Kubernetes and blockchain remain excluded.
