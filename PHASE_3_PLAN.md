# Phase 3 Plan: Kubernetes System Startup

## Scope

Implement the final planned project phase: running the existing investment-fund system with Kubernetes.

This phase covers the non-blockchain system only:

- authentication service and MySQL;
- Adminer for database inspection;
- MongoDB and persistent asset storage;
- Redis and persistent pending-order storage;
- employee service with exactly three replicas;
- director service;
- migration and initial relational database setup;
- ConfigMap, Secret, Services, health probes, and persistent storage.

The Ethereum/blockchain extension remains excluded. Helm, Ingress, HPA, NetworkPolicy, and a production-grade multi-node database cluster are outside the required scope unless a later review shows that one is necessary for the defense.

## Source Material and Design Choices

The implementation will follow the examples from `Kubernetes-vezbe6`:

- `employees.yaml` for Deployments, Services, and three employee replicas;
- `migration.yaml` for a one-time migration Job;
- `mysql-storage.yaml` for Secret, PersistentVolume, PersistentVolumeClaim, database storage, and Adminer;
- `mysql-probes.yaml` for readiness and liveness probes;
- `k8s.md` for Kubernetes concepts, `kubectl` commands, Services, ConfigMaps, Secrets, storage, and debugging.

The existing Docker Compose services and Dockerfiles remain the source of the application images. Kubernetes manifests should reuse those images rather than introduce a second application implementation.

## Kubernetes Environment

The first target is a local Kubernetes cluster:

- Docker Desktop Kubernetes

The plan should prefer Docker Desktop Kubernetes because the existing Docker images can be built into the Docker Desktop image store and used with `imagePullPolicy: IfNotPresent`.

Before implementation, document the chosen cluster and verify:

```powershell
kubectl version
kubectl cluster-info
kubectl get nodes
```


For Docker Desktop Kubernetes, build the images normally:

```powershell
docker build -t iep-authentication:k8s -f authentication.dockerfile .
docker build -t iep-employee:k8s -f employee.dockerfile .
docker build -t iep-director:k8s -f director.dockerfile .
```

The exact image names and commands will be kept in the final README and manifest files.

## Proposed Kubernetes Files

Keep Kubernetes files in a separate project directory so they do not get mixed with the Compose configuration:

```text
iep-investment-fund/
    k8s/
        namespace.yaml
        configmap.yaml
        secrets.yaml
        mysql.yaml
        mysql-storage.yaml
        mongodb.yaml
        redis.yaml
        authentication.yaml
        authentication-migration.yaml
        adminer.yaml
        employee.yaml
        director.yaml
        README.md
```

A smaller number of combined YAML files is also acceptable if it remains readable. The final choice should stay close to the faculty examples and make the defense commands easy to remember.

## Configuration and Secrets

### ConfigMap

Create a ConfigMap for non-sensitive configuration:

- MySQL database name;
- MySQL Service name;
- MongoDB Service name and internal port;
- MongoDB database name;
- Redis Service name and internal port;
- Redis database number;
- application ports;
- JWT access token expiration if the application reads it from the environment;
- environment name.

Kubernetes service DNS names must be used for internal communication:

- MySQL: `mysql`;
- MongoDB: `mongodb`;
- Redis: `redis`;
- authentication: `authentication` where another service needs it.

The host-side Compose ports such as MongoDB `27018` are irrelevant inside Kubernetes. Kubernetes services use internal ports and their own optional NodePort mappings.

### Secret

Create a Kubernetes Secret for sensitive values:

- MySQL root password;
- MongoDB root username/password if the application image requires authentication;
- JWT secret;
- any other database password.

Use `stringData` in the manifest for readability during development, following the faculty examples. Explain that Kubernetes Secret values are not automatically encrypted merely because they are base64 encoded. Do not put passwords in the ConfigMap or directly in application Deployment environment values.

For a real public repository, consider a local ignored secret file or a documented `kubectl create secret` command. The defense manifest still needs a reproducible local setup, so the chosen approach must be clearly documented.

## Namespace

Use a dedicated namespace, for example `iep-investment-fund`.

Benefits for the defense:

- avoids name collisions with old exercises;
- makes `kubectl get all -n iep-investment-fund` easy to explain;
- makes cleanup a single namespace deletion.

All manifests and commands must consistently use this namespace.

## MySQL and Authentication

### MySQL

Create:

- a PersistentVolume and PersistentVolumeClaim, following `mysql-storage.yaml`;
- a MySQL Pod or Deployment;
- a ClusterIP Service named `mysql`;
- a readiness probe using `mysqladmin ping`;
- a liveness probe where appropriate.

Use the Secret for the root password and the ConfigMap for the database name.

The PV implementation should match the local cluster:

- `hostPath` with `DirectoryOrCreate` for Docker Desktop/local development, or
- the cluster's default dynamic StorageClass if that is more reliable in the selected environment.

Do not delete the PVC during normal restarts. Data must remain after Pods are recreated.

### Authentication service

Create a Deployment and ClusterIP Service for the existing authentication image.

The image must:

- run the existing startup script;
- wait for MySQL;
- execute `flask db upgrade`;
- load the idempotent relational seed;
- start the authentication API.

The migration approach should be made explicit. The preferred Kubernetes design is:

1. a dedicated migration Job runs `flask --app migrate:application db upgrade` and finishes successfully;
2. the authentication Deployment starts after the Job has completed, or its startup script remains able to retry safely;
3. seed initialization remains idempotent.

Kubernetes does not provide a simple native dependency ordering between a Job and Deployment, so the runbook must apply the migration Job first and verify it with `kubectl wait`. A startup retry in the application image remains useful as a defensive measure.

Expose authentication through a NodePort for the defense, or use `kubectl port-forward` if NodePort availability differs between local clusters. The selected method must be documented with one copy-paste command.

## MongoDB

Create:

- a PersistentVolume/PersistentVolumeClaim for `/data/db`;
- a MongoDB Deployment or StatefulSet;
- a ClusterIP Service named `mongodb`;
- root credentials from Secret;
- a readiness probe using `mongosh` and `db.adminCommand('ping')`;
- a liveness probe if supported reliably by the selected Mongo image.

The employee and director Deployments must use the internal URI:

```text
mongodb://<username>:<password>@mongodb:27017/?authSource=admin
```

The application database name is `investment_fund`.

The existing idempotent `mongo_seed.py` should run exactly once as part of the director startup only if that remains safe with multiple service restarts. If a cleaner one-time Kubernetes Job is needed, add a dedicated Mongo seed Job instead. The seed must never create duplicate demo assets.

MongoDB Compass is not required for in-cluster service communication. For local inspection, document either:

- a MongoDB NodePort, or
- `kubectl port-forward service/mongodb 27018:27017` and Compass URI `mongodb://root:example@localhost:27018/?authSource=admin`.

Port-forwarding is preferable because it avoids host port conflicts and keeps the database internal to Kubernetes.

## Redis

Create:

- a PersistentVolume/PersistentVolumeClaim for `/data`;
- a Redis Deployment or StatefulSet;
- a ClusterIP Service named `redis`;
- append-only persistence configuration;
- a readiness probe using `redis-cli ping`;
- a liveness probe where appropriate.

Employee and director services use:

```text
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

Pending order UUIDs and order JSON must survive a Redis Pod restart while the PVC remains. Do not expose Redis through a public NodePort unless it is needed for a specific debugging demonstration. Use:

```powershell
kubectl exec -n iep-investment-fund deploy/redis -- redis-cli SMEMBERS fund:orders:pending
```

or port-forward only when host-side inspection is needed.

## Employee Service

Create:

- a Deployment with exactly `replicas: 3`;
- a ClusterIP Service selecting all employee Pods;
- a NodePort or port-forward access path for the defense;
- ConfigMap and Secret environment references;
- readiness and liveness probes against the existing health endpoint or a new minimal health endpoint if the current service does not expose one.

The Service must distribute requests between the three Pods through labels and selectors. The runbook must demonstrate:

```powershell
kubectl get pods -n iep-investment-fund -l app=employee
```

and show three running replicas.

## Director Service

Create:

- a Deployment with one replica initially;
- a ClusterIP Service;
- ConfigMap and Secret environment references;
- readiness and liveness probes;
- a NodePort or port-forward access path for the defense.

The director service must connect to the Kubernetes `mongodb` and `redis` Services, not to localhost.

## Adminer

Adminer is useful for inspecting MySQL and was already part of the Compose setup. Add it as an optional Deployment and NodePort Service if the final defense flow needs browser access to MySQL.

Its documented database server value must be the Kubernetes Service name `mysql`, not `localhost`.

## Service Types and External Access

Use:

- `ClusterIP` for MySQL, MongoDB, Redis, authentication, employee, and director internal communication;
- `NodePort` only for authentication, employee, director, and optional Adminer demonstration access;
- no Ingress unless the local cluster setup makes it necessary.

NodePort values must be in Kubernetes's valid range `30000-32767` and must not conflict with one another. As an alternative, document `kubectl port-forward` for APIs, which is often more portable across Docker Desktop and Minikube.

## Health and Startup

Add readiness probes so Services do not route traffic to unready Pods:

- MySQL: `mysqladmin ping`;
- MongoDB: `mongosh` ping command;
- Redis: `redis-cli ping`;
- application services: HTTP GET `/` or a dedicated health path.

Add liveness probes only where they do not cause restart loops during normal database startup. Use `startupProbe` or sufficiently conservative initial delays for services that wait for dependencies.

The runbook must distinguish:

- Pod is Running;
- container is Ready;
- Service has Endpoints;
- Job has completed.

## Apply Order

The defense-friendly apply order should be:

1. create namespace;
2. apply Secret and ConfigMap;
3. apply PV/PVC resources;
4. apply MySQL, MongoDB, and Redis Services/Deployments;
5. wait for database readiness;
6. apply the relational migration Job;
7. wait for migration completion;
8. apply authentication, employee, director, and optional Adminer resources;
9. wait for Deployments and verify three employee replicas;
10. test login, employee search/order creation, director decision, and report;
11. inspect persistence and service connectivity;
12. clean up only with a deliberate namespace deletion.

Example verification commands:

```powershell
kubectl get all -n iep-investment-fund
kubectl get pvc -n iep-investment-fund
kubectl get jobs -n iep-investment-fund
kubectl get endpoints -n iep-investment-fund
kubectl rollout status deployment/employee -n iep-investment-fund
kubectl logs job/authentication-migration -n iep-investment-fund
```

## Persistence Test

The final Kubernetes validation must:

1. create or approve an asset;
2. create a pending Redis order;
3. delete/restart the MongoDB and Redis Pods without deleting PVCs;
4. wait for replacement Pods to become Ready;
5. confirm the asset and pending order still exist;
6. recreate an application Pod and confirm it reconnects through Service DNS.

Do not use `kubectl delete namespace` or delete PVCs during this test.

## Secrets and Repository Safety

Before writing manifests, decide how development secrets are handled in Git:

- a clearly documented local development Secret manifest that is not used for production, or
- a template plus `kubectl create secret` commands.

The final repository must not accidentally contain real credentials. The current classroom credentials are development-only values and should be labeled as such in documentation.

## Helm Decision

Do not use Helm in this phase. The assignment asks for a Kubernetes configuration file and the faculty examples use plain YAML manifests. Plain manifests are easier to inspect and defend. Helm can be mentioned as a future packaging option but should not add complexity here.

## Documentation

Update `README.md` with a dedicated Kubernetes runbook:

- prerequisites and cluster choice;
- enabling Docker Desktop Kubernetes or starting Minikube;
- building/tagging local images;
- applying manifests in the correct order;
- waiting for readiness and migration completion;
- accessing APIs with NodePort or port-forward;
- connecting Compass through MongoDB port-forward;
- inspecting Redis with `kubectl exec`;
- verifying three employee replicas;
- testing persistence;
- cleanup and the warning not to delete PVCs accidentally.

Keep the existing Compose runbook intact and clearly label the two startup modes.

## Validation Checklist

Before Phase 3 is complete:

- all manifests pass `kubectl apply --dry-run=client`;
- the selected local cluster starts successfully;
- Secrets and ConfigMaps are mounted through environment references;
- MySQL migration Job completes;
- the initial director and seed data are available;
- MongoDB and Redis use persistent PVCs;
- authentication, employee, and director services resolve databases by Service DNS;
- employee Deployment has exactly three ready replicas;
- employee and director APIs are externally reachable through the documented method;
- MongoDB Compass can inspect the in-cluster database through port-forward;
- Redis pending orders can be inspected with `kubectl exec`;
- asset and pending-order data survive Pod recreation;
- Compose behavior remains unchanged;
- the README is sufficient to run the complete system during the defense without assistance.

## Implementation Boundary

Do not modify application code or create Kubernetes manifests until this plan is reviewed and approved. After approval, implement in small slices:

1. finalize image names and health endpoints;
2. create namespace, ConfigMap, and Secret manifests;
3. create database storage and database Services/Deployments;
4. create and test the migration Job;
5. create authentication, employee, director, and Adminer resources;
6. validate three employee replicas and internal Service DNS;
7. add the complete README runbook;
8. run clean-cluster, API, and persistence validation.

## Detail instructions for user
How to start everything, especially because the project will be defended on other computer. And list and describe usefull comands also. For example how to see mongo db content etc. Also use comments everywhere needed for better understanding of code.

## Current Implementation Status

The Kubernetes phase is implemented for Docker Desktop Kubernetes. The current resources include namespace, ConfigMap, development Secret, persistent storage, MySQL, MongoDB, Redis, relational migration Job, authentication, employee, director, and Adminer resources. The employee Deployment uses exactly three replicas.

The manifests pass `kubectl apply --dry-run=client`, the migration Job completed successfully, and the database Deployments reached Ready. The README contains the defense runbook, including port-forward access because NodePort host access can vary between local Kubernetes installations.
