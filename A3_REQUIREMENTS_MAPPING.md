# Assignment A3 Requirements Mapping

This file maps the A3 specification to this repository implementation.

## Design and Architecture

- 5 microservices are present:
  - `web_bff`
  - `mobile_bff`
  - `customer_service`
  - `book_service`
  - `crm_service`
- Kubernetes manifests are under `k8s/` and use namespace `bookstore-ns`.
- Web and Mobile BFFs are exposed with `Service` type `LoadBalancer`.
- Internal service routing is handled by `k8s/backend-router.yaml`.

## EKS / K8S Deployment Requirements

- Namespace:
  - `k8s/namespace.yaml` creates `bookstore-ns`.
- Replicas:
  - Web BFF: 2 (`k8s/web-bff.yaml`)
  - Mobile BFF: 2 (`k8s/mobile-bff.yaml`)
  - Customer service: 2 (`k8s/customer-service.yaml`)
  - Book service: 1 (`k8s/book-service.yaml`)
  - CRM service: 1 (`k8s/crm-service.yaml`)
- Liveness probes to `GET /status` configured for all REST services.
- CRM deployment intentionally has no liveness probe (per assignment note).
- `imagePullPolicy: Always` is set in all application deployment manifests.

## Task 2: Related Books Endpoint

- Added endpoint:
  - `GET /books/<isbn>/related-books` in `book_service/app.py`
- Return semantics implemented:
  - `200` with list
  - `204` for empty list
  - `504` on timeout from recommendation service (when circuit was closed)
  - `503` when circuit is open

## Task 3: Circuit Breaker

- Circuit state is persisted in a file:
  - path from env `CIRCUIT_STATE_FILE` (defaults to `/tmp/related_books_circuit_state.json`)
- Book pod mounts an `emptyDir` volume in `k8s/book-service.yaml`.
- Behavior implemented:
  - timeout threshold: `3` seconds via `RELATED_BOOKS_TIMEOUT_SECONDS`
  - open circuit on first timeout
  - keep open for `60` seconds via `RELATED_BOOKS_CIRCUIT_OPEN_SECONDS`
  - fail-fast `503` while still inside open window
  - first request after window attempts external call:
    - success closes circuit
    - timeout returns `503` and re-opens window

## Task 4: Kafka + CRM Async Service

- Customer service publishes `Customer Registered` event on successful `POST /customers`.
  - topic format: `<andrew_id>.customer.evt`
  - configured by env `ANDREW_ID` and `KAFKA_BROKERS`
  - implemented in `customer_service/app.py`
- CRM service consumes that topic and sends activation emails:
  - implemented in `crm_service/app.py`
  - subject: `Activate your book store account`
  - body includes customer name and Andrew ID text from assignment

## Task 5: DB Per Microservice

- Customer service default DB changed to `customers_db`.
- Book service default DB changed to `books_db`.
- SQL bootstrap updated:
  - `scripts/init_db.sql` creates `customers_db` and `books_db` and respective tables.
- truncate/seed scripts updated to target service-specific DBs.

## Required Runtime Inputs

Set these before deployment:

- `ANDREW_ID`
- `KAFKA_BROKERS`
- `RECOMMENDATION_SERVICE_URL`
- `RECOMMENDATION_PATH_TEMPLATE` (default in manifests: `/api/recommendations/{isbn}`)
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`
- SMTP settings for CRM:
  - `SMTP_HOST`
  - `SMTP_PORT`
  - `SMTP_USERNAME`
  - `SMTP_PASSWORD`
  - `SMTP_SENDER_EMAIL`
