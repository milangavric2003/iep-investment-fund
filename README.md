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

The employee and director containers wait for MongoDB and Redis before starting. Demo assets are not loaded automatically, so a clean Compose start is also suitable for the integration grader. MongoDB data is stored in `mongodb_volume`; Redis data is stored in `redis_volume`.

To load the two idempotent demo assets for a manual presentation, run this after the services are healthy:

```powershell
docker compose -f development.yaml exec director python mongo_seed.py
```

Phase 2 service URLs:

- Employee API: `http://localhost:5001`
- Director API: `http://localhost:5003` (container port `5002`)
- MongoDB: `mongodb://root:example@localhost:27018/?authSource=admin`
- Redis: `localhost:6379`

The director host port is `5003` because port `5002` was occupied on the development machine. Only the host mapping is changed; the director listens on port `5002` inside its container.

The MongoDB host port is `27018` because port `27017` is already used by another MongoDB process on the development machine. Only the host mapping is changed. Application containers continue to use `mongodb:27017` inside the Compose network.

To connect from MongoDB Compass, open the desktop application on the host machine and use:

```text
mongodb://root:example@localhost:27018/?authSource=admin
```

After connecting, open the `investment_fund` database and its `assets` collection. If Compass still shows databases from an older exercise, edit the saved connection and verify that it uses port `27018`, not `27017`.

To recreate the services after this port change:

```powershell
docker compose -f development.yaml down
docker compose -f development.yaml up --build -d
docker compose -f development.yaml ps
```

Do not use `docker compose down -v` during a normal restart because the `mongodb_volume` contains the persistent MongoDB data.

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

## Run the Grader

Install the grader dependencies into the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r tests\iep_grader\requirements-pytest.txt
```

The grader is stateful, so start from clean database volumes when a completely fresh run is needed:

```powershell
docker compose -f development.yaml down -v
docker compose -f development.yaml up --build -d
```

Run the authentication and non-blockchain grader with the Compose host mappings:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\iep_grader --type all `
  --authentication-url http://127.0.0.1:5000 `
  --jwt-secret development-secret-key-with-at-least-32-bytes `
  --roles-field role --employee-role EMPLOYEE --director-role DIRECTOR `
  --with-authentication --employee-url http://127.0.0.1:5001 `
  --director-url http://127.0.0.1:5003 --wait-for-services `
  --grade-report-file grade_report.json
```

## Kubernetes Runbook

The Kubernetes configuration is in the `k8s` directory. The documented target is Docker Desktop Kubernetes. The Compose setup remains available and is not replaced by Kubernetes.

### 1. Check prerequisites

Enable Kubernetes in Docker Desktop, then verify the cluster:

```powershell
kubectl config current-context
kubectl get nodes
```

The expected context is usually `docker-desktop`, and the node should be `Ready`.

### 2. Build local images

Run these commands from the project directory. Docker Desktop Kubernetes can use images built by the local Docker engine:

```powershell
docker build -t iep-authentication:k8s-20260908 -f authentication.dockerfile .
docker build -t iep-employee:k8s-20260908 -f employee.dockerfile .
docker build -t iep-director:k8s-20260908 -f director.dockerfile .
```

The manifests use `imagePullPolicy: IfNotPresent`, so Kubernetes will use these local images. The date-stamped tag prevents Kubernetes from silently reusing an older cached image with the same generic tag. When application code changes, use a new tag in the three Docker build commands and in the four application image references under `k8s/`.

### 3. Apply configuration and storage

```powershell
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/mysql-storage.yaml
kubectl apply -f k8s/mysql.yaml
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/redis.yaml
```

Wait for the three databases:

```powershell
kubectl wait --for=condition=available deployment/mysql -n iep-investment-fund --timeout=180s
kubectl wait --for=condition=available deployment/mongodb -n iep-investment-fund --timeout=180s
kubectl wait --for=condition=available deployment/redis -n iep-investment-fund --timeout=180s
kubectl get pods,pvc,services -n iep-investment-fund
```

If a previous local installation left one of these PVCs in `Pending` and its
PV in `Released`, the old PVC-to-PV binding must be removed before retrying.
This is a local-cluster recovery step; it does not remove the hostPath
directories or their data. Run it only when the affected database Pods are
not being used:

```powershell
kubectl delete pvc mysql-pvc mongodb-pvc redis-pvc -n iep-investment-fund
kubectl delete pv mysql-pv mongodb-pv redis-pv
kubectl apply -f k8s/mysql-storage.yaml
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/redis.yaml
```

The storage manifests intentionally use `persistentVolumeReclaimPolicy: Retain`.
This preserves the PV and its data if a PVC is deleted accidentally. A retained
PV becomes `Released` after its PVC is deleted, so the manual recovery above is
required before reusing the same static PV name. Do not delete PVCs during the
normal restart or persistence test.

### 4. Run the relational migration Job

```powershell
kubectl apply -f k8s/authentication-migration.yaml
kubectl wait --for=condition=complete job/authentication-migration -n iep-investment-fund --timeout=180s
kubectl logs job/authentication-migration -n iep-investment-fund
```

The Job creates the MySQL tables. The authentication Deployment also runs the existing retryable startup script and idempotent relational seed.

### 5. Start application services

```powershell
kubectl apply -f k8s/authentication.yaml
kubectl apply -f k8s/employee.yaml
kubectl apply -f k8s/director.yaml
kubectl apply -f k8s/adminer.yaml

kubectl rollout status deployment/authentication -n iep-investment-fund --timeout=180s
kubectl rollout status deployment/employee -n iep-investment-fund --timeout=180s
kubectl rollout status deployment/director -n iep-investment-fund --timeout=180s
kubectl get pods -n iep-investment-fund -l app=employee
```

The employee Deployment must have exactly three ready Pods.

### 6. Access MySQL through Adminer

MySQL is intentionally exposed only as an internal `ClusterIP` Service. Open
Adminer through a local port-forward in a separate PowerShell terminal and
leave that command running:

```powershell
kubectl port-forward service/adminer 18080:8080 -n iep-investment-fund
```

Open `http://localhost:18080` in a browser and use these login values:

- System: `MySQL`
- Server: `mysql`
- Username: `root`
- Password: `root`
- Database: `investment_fund`

The Server value must be `mysql`, because Adminer connects to MySQL from
inside the Kubernetes network. Do not use `localhost` there. The database
tables are available after the `authentication-migration` Job has completed.

Adminer also has a NodePort Service on `30080`, so Docker Desktop may expose it
at `http://localhost:30080`. Port-forwarding is recommended because it works
consistently across local Kubernetes installations and avoids host port
conflicts.

### 7. Access APIs with port-forward

NodePort Services are defined on ports `30050`-`30052`, but port-forward is more portable across local Kubernetes installations and avoids Windows host port behavior differences. Use separate terminals for these commands AND LEFT THAT PROCESSES RUNNING IN TERMINAL:

```powershell
kubectl port-forward service/authentication 31050:5000 -n iep-investment-fund
kubectl port-forward service/employee 31051:5001 -n iep-investment-fund
kubectl port-forward service/director 31052:5002 -n iep-investment-fund
```

Then use the same API examples as Compose with these Kubernetes URLs:

- authentication: `http://localhost:31050`;
- employee: `http://localhost:31051`;
- director: `http://localhost:31052`.

The grader is deployment-agnostic. It sends HTTP requests to the URLs supplied on the command line, so it can test Docker Compose or Kubernetes without any test-code changes. For Kubernetes, keep the three port-forward commands running in separate terminals and use this command from a fourth terminal:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\iep_grader --type all `
  --authentication-url http://127.0.0.1:31050 `
  --jwt-secret development-secret-key-with-at-least-32-bytes `
  --roles-field role --employee-role EMPLOYEE --director-role DIRECTOR `
  --with-authentication --employee-url http://127.0.0.1:31051 `
  --director-url http://127.0.0.1:31052 --wait-for-services `
  --grade-report-file grade_report_kubernetes.json
```

!!!IF RUNNING TEST TWO TIMES - run this command to delete previously left state in databases: 
```powershell
kubectl exec -n iep-investment-fund deployment/authentication -- python -c "from main import application; from models import User, database; application.app_context().push(); user=User.query.filter_by(email='john@gmail.com').first(); print('deleted', user.email if user else None); database.session.delete(user) if user else None; database.session.commit()"; kubectl exec -n iep-investment-fund deployment/mongodb -- mongosh --quiet --username root --password example --authenticationDatabase admin --eval "db.getSiblingDB('investment_fund').assets.deleteMany({})"; kubectl exec -n iep-investment-fund deployment/redis -- redis-cli FLUSHDB
```

Kubernetes uses port `5002` for the director Service internally. The Compose host mapping uses `5003` only because another host process occupied port `5002`; this difference does not affect the application or the grader. NodePort values `30050`-`30052` are also defined, but port-forward is the recommended access method because Docker Desktop and other local clusters can expose NodePorts differently on Windows.

The Kubernetes manifests intentionally do not load demo MongoDB assets automatically, so a clean cluster can be tested without extra data. For a manual presentation, load the idempotent demo assets with:

```powershell
kubectl exec -n iep-investment-fund deployment/director -- python mongo_seed.py
```

### 8. Inspect MongoDB with Compass

Forward MongoDB to a free host port:

```powershell
kubectl port-forward service/mongodb 27018:27017 -n iep-investment-fund
```

In MongoDB Compass, connect with:

```text
mongodb://root:example@localhost:27018/?authSource=admin
```

Open database `investment_fund` and collection `assets`. The port-forward command must remain running while Compass is connected.

### 9. Inspect Redis

Redis is intentionally an internal ClusterIP service. Inspect it through the Redis Pod:

```powershell
kubectl get pods -n iep-investment-fund -l app=redis
kubectl exec -n iep-investment-fund deployment/redis -- redis-cli ping
kubectl exec -n iep-investment-fund deployment/redis -- redis-cli SMEMBERS fund:orders:pending
kubectl exec -n iep-investment-fund deployment/redis -- redis-cli KEYS 'fund:orders:*'
```

For a particular order:

```powershell
kubectl exec -n iep-investment-fund deployment/redis -- redis-cli GET fund:orders:<uuid>
```

!!!OR JUST FROM CONTAINER LIKE THIS:
```powershell
kubectl exec -it deployment/redis -n iep-investment-fund -- /bin/sh
redis-cli
```

### 10. Useful Kubernetes commands

```powershell
kubectl get all -n iep-investment-fund
kubectl get pvc -n iep-investment-fund
kubectl get endpoints -n iep-investment-fund
kubectl describe pod <pod-name> -n iep-investment-fund
kubectl logs deployment/employee -n iep-investment-fund
kubectl logs deployment/director -n iep-investment-fund
kubectl exec -it deployment/employee -n iep-investment-fund -- /bin/sh
```

If a Pod is not ready, check `kubectl describe pod` events first, then inspect its logs. `CreateContainerConfigError` usually means a ConfigMap or Secret key is missing. `ImagePullBackOff` usually means the image was not built with the exact tag used by the manifest.

### 11. Persistence test

Do not delete PVCs. Recreate database Pods and verify that data remains:

```powershell
kubectl delete pod -l app=mongodb -n iep-investment-fund
kubectl delete pod -l app=redis -n iep-investment-fund
kubectl wait --for=condition=available deployment/mongodb -n iep-investment-fund --timeout=180s
kubectl wait --for=condition=available deployment/redis -n iep-investment-fund --timeout=180s
kubectl get pvc -n iep-investment-fund
```

MongoDB assets and Redis pending orders should still exist because the PVCs were retained.

### 12. Cleanup

To stop the project while retaining persistent data, delete Deployments and Services or leave the namespace running. To remove the complete local project, including PVCs and data, use this only deliberately:

```powershell
kubectl delete namespace iep-investment-fund
!!!verovatno i kubectl delete all --all
```

Deleting the namespace removes the project resources. Treat this as destructive for the local Kubernetes data.

## Project Plan

The implementation plan and later MongoDB, Redis, Docker service split, and Kubernetes phases are documented in [PROJECT_PLAN.md](PROJECT_PLAN.md). The optional Ethereum blockchain voting extension is not part of this implementation.

# Testiranje kad radis modifikaciju

- netstat -ano | findstr LISTENING => komanda za listanje portova koji slusaju

- na primer menjamo nesto u main.py i koristimo `kubernetes za testiranje`: 
  1) docker build -t iep-authentication:k8s-v2 -f authentication.dockerfile . => novi image sa novim tagom
  2) promeni u authentication.yaml, novi tag stavi
  3) kubectl apply -f k8s/authentication.yaml
  
- ili mozda moze i ovako ali `docker compose` da se primenjuje:
  1) dodas ovo u yaml: 
    environment:
      ...
        FLASK_ENV: development     # <--- DODAO
      FLASK_DEBUG: "1"
    ports: ...
    volumes:
      - .:/app (ili sta god je putanja do foldera koji ocemo da mountujemo u kontejner u app folder
  2) pokreces docker compose i gasis ga da bi mogo kubernetes:
    docker compose -f development.yaml up --build -d (-d oslobadja terminal)
    docker compose -f development.yaml down (bez -v koje brise volumene da ne bi izgubio podatke u bazama)

