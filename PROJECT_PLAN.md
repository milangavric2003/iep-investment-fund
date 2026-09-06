# Investment Fund Project Plan

## Project Scope

Implement the investment fund system described in `IEP_Projekat_2026.pdf` using Python, Flask, SQLAlchemy, PyMongo, Redis, JWT, Docker Compose, and later Kubernetes. The optional Ethereum blockchain voting extension is intentionally excluded.

All source code, comments, configuration keys, API messages, database names, and commit messages will be written in English.

The implementation will stay close to the structure and techniques used in:

- `flask-vezbe1`
- `sql-alchemy-vezbe2`
- `jwt-vezbe3`
- `mongodb-vezbe4`
- `Docker-vezbe5`
- `V5/kod`, used only as a Docker and Compose reference because it targets an older Python version

## Decisions Confirmed So Far

- Start with the user-account management service.
- Use MySQL from the beginning, running locally through Docker Compose.
- Do not add Kubernetes yet.
- Use a simple Dockerfile for the Flask service and a simple Compose YAML file, following the faculty exercises.
- Use a persistent MySQL volume so data survives container restarts.
- Use Adminer as the browser-based database administration tool.
- Use Flask-Migrate/Alembic for schema migrations instead of relying only on `database.create_all()`.
- Keep seed data in an SQL file. The director may also be created or edited manually through Adminer.
- Do not allow public registration to choose a role.
- The two roles required by the specification are `EMPLOYEE` and `DIRECTOR`.
- Every public registration creates an employee account.
- The initial director account is defined by the specification:
  - forename: `Scrooge`
  - surname: `McDuck`
  - email: `onlymoney@gmail.com`
  - password: `evenmoremoney`
- Passwords must be stored as secure password hashes, never as plain text.
- Access tokens are valid for one hour, as required by the specification.

## Target Structure

The first implementation phase should establish a small structure compatible with the exercises:

```text
iep-investment-fund/
    main.py
    configuration.py
    models.py
    decorators.py
    requirements.txt
    seed.sql
    authentication.dockerfile
    development.yaml
    migrations/
        ...
```

The structure may be split into services later when the employee and director services are introduced. Until then, the account-management service remains the first executable service.

## Phase 1: Account Management

### Database model

Create the SQLAlchemy model for users with:

- integer primary key;
- email, maximum 256 characters, unique and required;
- password hash, maximum 256 characters, required;
- forename, maximum 256 characters, required;
- surname, maximum 256 characters, required;
- role represented by `EMPLOYEE` or `DIRECTOR`.

A single role column is sufficient because the specification states that a user can have the role of director or employee. A many-to-many role model from the JWT exercise should not be introduced unless a later requirement needs it.

### `POST /register`

Implement the exact validation order and response messages from the specification:

1. Check `forename`.
2. Check `surname`.
3. Check `email`.
4. Check `password`.
5. Validate the email format.
6. Validate the password length.
7. Check whether the email already exists.
8. Create the user with role `EMPLOYEE`.

Successful response: HTTP 200 with no body.

Error response: HTTP 400 with a JSON object containing `message`.

### `POST /login`

Implement the exact validation order from the specification:

1. Check `email`.
2. Check `password`.
3. Validate the email format.
4. Validate the credentials using the stored password hash.

Successful response:


```json
{
  "accessToken": "..."
}
```

The JWT identity will be the user's email. The token claims will contain the user's forename, surname, and role, without the password.

### `POST /delete`

Protect the endpoint with a Bearer access token. Read the user's email from the token and delete that user from MySQL.

Required behavior:

- missing authorization header: HTTP 401 with `{"msg": "Missing Authorization Header"}`;
- unknown user: HTTP 400 with `{"message": "Unknown user."}`;
- success: HTTP 200 with no body.

## Database and Migration Strategy

- MySQL is the development database from the first implementation.
- The database URL must be configurable through environment variables.
- The Compose service name, not `localhost`, must be used as the database host from inside the Flask container.
- Use `mysql+pymysql` as the SQLAlchemy driver, matching the Docker exercise configuration.
- Flask-Migrate/Alembic owns table creation and schema changes.
- The first migration creates the users table and all required constraints.
- Do not use `database.create_all()` as the main schema-management mechanism.
- The migration commands and startup order must be documented in the README after implementation.

## Seed Data

Create a small English-language `seed.sql` file with:

- one director account;
- several employee accounts;
- role values matching the application model.

Because passwords are hashed by the application, the seed file must contain generated password hashes rather than plain-text passwords. The test credentials used by the seed file will be documented separately for local development.

The seed process must be idempotent or clearly documented as a one-time operation. The initial director may alternatively be inserted or modified manually through Adminer.

The seed file must be applied only after the migration has created the table. It must not become a second, conflicting definition of the schema.

## Docker Compose Development Setup
- `mysql` service;
- `adminer` service;
- Flask authentication service;
- named persistent volume for MySQL data;
- shared network where the Flask service can reach MySQL by service name;
- environment variables for database host, username, password, database name, and JWT secret;
- MySQL initialization settings such as root password and database name;
- exposed ports for local development only.

The Flask image should follow the style of `Docker-vezbe5` and `V5/kod`:

- use a Python base image compatible with Python 3.13 where possible;
- copy the application files and `requirements.txt`;
- install dependencies;
- start the Flask application with an explicit host of `0.0.0.0`.

The first Docker iteration should remain intentionally small. Kubernetes, replicas, Secrets, ConfigMaps, Redis, and MongoDB belong to later phases.

The Compose setup must account for the fact that a MySQL container can be running before MySQL is ready to accept connections. The application or startup command must handle this without requiring manual race-condition fixes.

## Later Project Phases

### Phase 2: MongoDB and Redis foundation

Add the investment-fund data model and services:

- MongoDB asset documents with flexible `info` fields;
- Redis pending buy and sell orders;
- employee service;
- director service;
- JWT role checks shared with the account service.

Implement:

- `POST /search`;
- `POST /create_buy_order`;
- `POST /create_sell_order`;
- `GET /pending_orders`;
- the non-blockchain version of `POST /decision`;
- `GET /report`.

MongoDB queries should perform filtering in the database wherever possible, including nested `info` fields and the requested date/category filters.

### Phase 3: Docker service split

Split the application into the authentication, employee, and director containers. Add MongoDB and Redis services to Compose, keeping all connection details in environment variables.

Use the MongoDB and Redis patterns from `mongodb-vezbe4` and `Docker-vezbe5` rather than inventing new project-wide abstractions.


### Phase 4: Kubernetes

Only after the complete Compose system works:

- add ConfigMaps for non-sensitive configuration;
- add Secrets for passwords and JWT secrets;
- add persistent volumes for databases;
- add the required three employee-service replicas;
- add service discovery and startup configuration;
- provide the Kubernetes configuration needed for the defense demonstration.

## Validation Checklist

Before moving to the next phase, verify:

- migrations create a fresh MySQL database successfully;
- the seed SQL can populate the migrated schema;
- Adminer can connect to MySQL;
- registration follows the exact validation order and messages;
- duplicate email registration is rejected;
- login issues a one-hour JWT;
- the JWT does not contain the password;
- `/delete` rejects missing authorization and deletes the authenticated user;
- the Flask container can resolve MySQL by its Compose service name;
- MySQL data survives a container restart;
- the account endpoints work both from the host and through the container network.

## Current Implementation Status

Phase 1 is implemented in the project. The next coding step is Phase 2: the MongoDB asset model, Redis order storage, and employee/director services. The Ethereum voting extension will not be implemented.
