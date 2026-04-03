# A3 EKS Deploy Order and Value Checklist

This is the exact deployment order for this repository after the A3 refactor.

## 1) Fill runtime values once

1. Copy env template:

```bash
cp k8s/deploy.env.example k8s/deploy.env
```

2. Edit `k8s/deploy.env` with your real values.

Required fields:
- `IMAGE_REGISTRY`, `IMAGE_TAG`
- `RDS_ENDPOINT`, `DB_USER`, `DB_PASSWORD`
- `KAFKA_BROKERS`
- `ANDREW_ID`, `EMAIL_ADDRESS`
- `RECOMMENDATION_SERVICE_URL`, `RECOMMENDATION_PATH_TEMPLATE` (see Canvas; typical values: testing `http://52.73.13.84`, Gradescope `http://100.51.187.149`, path `/recommended-titles/isbn/{isbn}`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_STARTTLS`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SENDER_EMAIL`
- `AWS_REGION`, `EKS_CLUSTER_NAME`

## 2) Discover AWS values correctly

Use these commands to avoid guessing:

```bash
# RDS endpoint (Aurora writer endpoint)
aws rds describe-db-clusters \
  --query "DBClusters[?DBClusterIdentifier=='bookstore-db-dev'].Endpoint" \
  --output text

# EKS cluster names, then set EKS_CLUSTER_NAME in k8s/deploy.env
aws eks list-clusters --region us-east-1 --output table

# Kafka brokers: from your Canvas announcement (paste into KAFKA_BROKERS)
# Recommendation URL: testing http://52.73.13.84 | Gradescope http://100.51.187.149
# Path template: /recommended-titles/isbn/{isbn}
```

If you prefer CloudFormation queries, use:

```bash
aws cloudformation describe-stacks --stack-name <your-stack-name> --region us-east-1
```

## 3) Build and push all images

From repo root:

```bash
export DH=<your_registry_user_or_prefix>
export TAG=<image_tag>
./scripts/build-push-dockerhub-amd64.sh
```

Then set in `k8s/deploy.env`:
- `IMAGE_REGISTRY=<same registry prefix>`
- `IMAGE_TAG=<same tag>`

## 4) Render Kubernetes manifests with your values

```bash
./scripts/render_k8s_from_env.sh
```

Rendered files are written to `k8s/rendered/`.

## 5) Configure kubectl for EKS

```bash
source k8s/deploy.env
aws eks update-kubeconfig --region "$AWS_REGION" --name "$EKS_CLUSTER_NAME"
kubectl get nodes
```

## 6) Apply manifests in this exact order

```bash
kubectl apply -f k8s/rendered/namespace.yaml
kubectl apply -f k8s/rendered/backend-router.yaml
kubectl apply -f k8s/rendered/customer-service.yaml
kubectl apply -f k8s/rendered/book-service.yaml
kubectl apply -f k8s/rendered/crm-service.yaml
kubectl apply -f k8s/rendered/web-bff.yaml
kubectl apply -f k8s/rendered/mobile-bff.yaml
```

Why this order:
- namespace first
- internal routing and backend services first
- BFFs last (they depend on backend-router/book/customer services)

## 7) Wait for healthy rollout

```bash
kubectl -n bookstore-ns get pods
kubectl -n bookstore-ns rollout status deploy/backend-router
kubectl -n bookstore-ns rollout status deploy/customer-service
kubectl -n bookstore-ns rollout status deploy/book-service
kubectl -n bookstore-ns rollout status deploy/crm-service
kubectl -n bookstore-ns rollout status deploy/web-bff
kubectl -n bookstore-ns rollout status deploy/mobile-bff
```

## 8) Get the two BFF base URLs for `url.txt`

```bash
WEB_URL="http://$(kubectl -n bookstore-ns get svc web-bff -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
MOBILE_URL="http://$(kubectl -n bookstore-ns get svc mobile-bff -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
echo "$WEB_URL"
echo "$MOBILE_URL"
```

Set `url.txt` exactly:
1. web BFF URL
2. mobile BFF URL
3. Andrew ID
4. email address used by CRM sender

## 9) Verify assignment-critical behavior

- `GET /status` on both BFF URLs returns `200`
- `POST /customers` publishes Kafka event
- CRM consumes event and sends activation email
- `GET /books/{isbn}/related-books`:
  - `200/204` when recommendation service responds in <= 3s
  - `504` on timeout while circuit closed
  - `503` while circuit open (<60s)
  - retry after 60s behaves as specified
