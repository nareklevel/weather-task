# Weather Data Pipeline

A real-time weather data pipeline that polls [WeatherAPI](https://www.weatherapi.com/) every 60 seconds, streams data through Kafka, and persists it to PostgreSQL — all running on AWS EKS, managed via GitOps with ArgoCD.

## Architecture

```
WeatherAPI
    │
    ▼
┌─────────┐       ┌───────────────┐       ┌──────────────────┐
│Producer │──────▶│  Kafka Topic  │──────▶│ Consumer Short   │──▶ weather_short table
│(Python) │       │ (weather-raw) │       └──────────────────┘
└─────────┘       │               │       ┌──────────────────┐
                  │               │──────▶│ Consumer Long    │──▶ weather_long table
                  └───────────────┘       └──────────────────┘
                                                   │
                                           ┌───────┴───────┐
                                           │  PostgreSQL   │
                                           └───────────────┘
```

| Component        | Technology                  | Namespace    |
|------------------|-----------------------------|--------------|
| Message broker   | Kafka (Strimzi Operator)    | `kafka`      |
| Database         | PostgreSQL (CloudNativePG)  | `postgres`   |
| Applications     | Python 3.11                 | `weather-app`|
| Infrastructure   | AWS EKS + VPC (Terraform)   | —            |
| GitOps           | ArgoCD (app-of-apps)        | `argocd`     |
| CI/CD            | GitHub Actions              | —            |

### Services

- **Producer** — fetches current weather for Yerevan from WeatherAPI, publishes raw JSON to the `weather-raw` Kafka topic every 60 seconds.
- **Consumer Short** — reads from `weather-raw`, writes `city`, `time`, `temp_c`, `temp_f` to the `weather_short` table.
- **Consumer Long** — reads from `weather-raw`, writes the full 39-field weather record to the `weather_long` table.

## Prerequisites

- AWS account (profile `playground` configured locally)
- Terraform >= 1.14.7
- `kubectl`, `helm`
- A [WeatherAPI](https://www.weatherapi.com/) free-tier API key
- GitHub repository with the following **Actions secrets** set:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`

## Infrastructure Provisioning

```bash
cd terraform
terraform init
terraform apply
```

This creates:
- VPC (`10.77.0.0/16`) with public/private subnets across 2 AZs
- EKS cluster (`weather-eks`, Kubernetes 1.34) with t3.medium nodes (1–3)
- NAT Gateway for private subnet egress

After the cluster is up, update your kubeconfig:

```bash
aws eks update-kubeconfig --region us-east-1 --name weather-eks
```

## Operator Installation

Install the required cluster operators before applying ArgoCD apps:

```bash
# Strimzi (Kafka)
kubectl create namespace kafka
kubectl apply -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka

# CloudNativePG (PostgreSQL)
kubectl apply --server-side -f \
  https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.24/releases/cnpg-1.24.0.yaml

# ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

## GitOps Deployment

1. Set your WeatherAPI key:

```bash
kubectl create namespace weather-app
kubectl apply -f k8s/app/secret.yaml
# Edit the secret with your actual key:
kubectl -n weather-app edit secret weather-api-secret
```

2. Apply the ArgoCD app-of-apps — this deploys everything else automatically:

```bash
kubectl apply -f k8s/argocd/app-of-apps.yaml
```

ArgoCD will reconcile and deploy:
- Kafka cluster + topic
- PostgreSQL cluster + tables
- Producer, consumer-short, consumer-long

Monitor sync status:

```bash
kubectl -n argocd get applications
```

## CI/CD

### On pull request → `main`

`.github/workflows/ci.yml` runs:
- Terraform format check
- Python syntax validation for all three services

### On merge to `main` (services changes only)

`.github/workflows/build-push.yml` runs:
1. Builds Docker images for all three services
2. Pushes to ECR with both `:<git-sha>` and `:latest` tags
3. Updates image tags in `k8s/app/*.yaml` with the commit SHA
4. Commits the manifest changes back (`[skip ci]`)
5. ArgoCD detects the manifest change and redeploys

### ECR Repositories

Create the three ECR repositories once before the first CI run:

```bash
for repo in weather/producer weather/consumer-short weather/consumer-long; do
  aws ecr create-repository --repository-name $repo --region us-east-1
done
```

## Database Schema

**`weather_short`**

| Column        | Type          |
|---------------|---------------|
| id            | SERIAL PK     |
| city          | VARCHAR(100)  |
| time          | TIMESTAMP     |
| temperature_c | NUMERIC(5,2)  |
| temperature_f | NUMERIC(5,2)  |

**`weather_long`** — 39 columns covering full location metadata, temperature, wind, pressure, precipitation, humidity, visibility, UV, solar radiation, and more. See `k8s/postgres/cluster.yaml` for the full DDL.

## Secrets

| Secret name           | Namespace     | Keys                   | Purpose                      |
|-----------------------|---------------|------------------------|------------------------------|
| `weather-api-secret`  | `weather-app` | `api_key`              | WeatherAPI key (set manually)|
| `db-credentials`      | `weather-app` | `username`, `password` | PostgreSQL app credentials   |
| `postgres-credentials`| `postgres`    | `username`, `password` | CloudNativePG cluster init   |

> **Note:** Secrets are stored in-cluster only. The values in this repo are defaults — replace them before deploying to any non-dev environment.
