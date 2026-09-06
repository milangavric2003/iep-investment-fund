# Investment Fund

This repository contains the investment fund system for the ETF IEP course project.

## Phase 1: Authentication

The first phase implements:

- `POST /register`
- `POST /login`
- `POST /delete`
- `GET /`

Users have one of two roles: `EMPLOYEE` or `DIRECTOR`. Public registration always creates an employee account.

## Run With Docker Compose

Start Docker Desktop first, then run these commands from this directory:

```powershell
docker compose -f development.yaml up --build
```

The services are available at:

- Authentication API: `http://localhost:5000`
- Adminer: `http://localhost:8080`
- MySQL: `localhost:3307`

The application container waits for MySQL, applies Flask-Migrate migrations, loads `seed.sql`, and starts the API. MySQL data is stored in the `database_volume` named volume.

The employee and director containers wait for MongoDB and Redis before starting. The director container loads two idempotent demo assets into MongoDB. MongoDB data is stored in `mongodb_volume`; Redis data is stored in `redis_volume`.

Phase 2 service URLs:

- Employee API: `http://localhost:5001`
- Director API: `http://localhost:5003` (container port `5002`)
- MongoDB: `mongodb://root:example@localhost:27017/?authSource=admin`
- Redis: `localhost:6379`

The director host port is `5003` because port `5002` was occupied on the development machine. Only the host mapping is changed; the director listens on port `5002` inside its container.

Use these Adminer connection values:

- System: `MySQL`
- Server: `database`
- Username: `root`
- Password: `root`
- Database: `investment_fund`

## Seed Credentials

The seed contains one director and two employees:

| Role | Email | Password |
| --- | --- | --- |
| `DIRECTOR` | `onlymoney@gmail.com` | `evenmoremoney` |
| `EMPLOYEE` | `alice.johnson@example.com` | `employeeone` |
| `EMPLOYEE` | `bob.smith@example.com` | `employeetwo` |

Seed passwords are stored as Werkzeug password hashes.

## Local Migration Commands

The migration entry point is `migrate:application`:

```powershell
flask --app migrate:application db upgrade
flask --app migrate:application db migrate -m "Describe the schema change"
```

The normal development database is MySQL. For migration tooling without a running MySQL instance, set `DATABASE_URI` to a temporary SQLite URL.

## API Examples

Register an employee:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:5000/register `
  -ContentType "application/json" `
  -Body '{"forename":"John","surname":"Doe","email":"john.doe@example.com","password":"password123"}'
```

Login:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:5000/login `
  -ContentType "application/json" `
  -Body '{"email":"onlymoney@gmail.com","password":"evenmoremoney"}'
```

The response contains the `accessToken` required by `/delete` in the Bearer authorization header.

## Phase 2 API Examples

Get an employee token and use it with the employee service:

```powershell
$employeeLogin = Invoke-RestMethod -Method Post -Uri http://localhost:5000/login `
  -ContentType "application/json" `
  -Body '{"email":"alice.johnson@example.com","password":"employeeone"}'
$employeeHeaders = @{ Authorization = "Bearer $($employeeLogin.accessToken)" }

Invoke-RestMethod -Method Post -Uri http://localhost:5001/search `
  -Headers $employeeHeaders -ContentType "application/json" `
  -Body '{"category":"fixed-income"}'
```

Create a BUY order:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:5001/create_buy_order `
  -Headers $employeeHeaders -ContentType "application/json" `
  -Body '{"name":"Corporate Bond","categories":["fixed-income","corporate"],"buying_price":5000,"info":{"issuer":"Demo Corp"}}'
```

Get a director token and inspect pending orders:

```powershell
$directorLogin = Invoke-RestMethod -Method Post -Uri http://localhost:5000/login `
  -ContentType "application/json" `
  -Body '{"email":"onlymoney@gmail.com","password":"evenmoremoney"}'
$directorHeaders = @{ Authorization = "Bearer $($directorLogin.accessToken)" }
Invoke-RestMethod -Method Get -Uri http://localhost:5003/pending_orders -Headers $directorHeaders
Invoke-RestMethod -Method Get -Uri http://localhost:5003/report -Headers $directorHeaders
```

Use MongoDB Compass with the MongoDB URI above. The demo collection is `investment_fund.assets`. Compass is useful for inspection; the services perform all project writes.

Redis inspection commands are documented in [redis_keys.md](redis_keys.md).

## Project Plan

The implementation plan and later MongoDB, Redis, Docker service split, and Kubernetes phases are documented in [PROJECT_PLAN.md](PROJECT_PLAN.md). The optional Ethereum blockchain voting extension is not part of this implementation.
