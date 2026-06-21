# Deploy to Cloud Run (Terraform / OpenTofu)

Minimal module that runs the `latamfx-mcp` container on Google Cloud Run. It is
intentionally small — a reference, not a turnkey platform.

> Note: MCP's default transport is **stdio** (the client spawns the process).
> A hosted Cloud Run deployment is meant for the **streamable HTTP** transport;
> put authentication (IAP or an API gateway) in front of it. `allow_unauthenticated`
> defaults to `false` on purpose.

## Usage

```bash
# 1. Build and push the image (example with Artifact Registry)
REGION=southamerica-east1
REPO=mcp
PROJECT=your-project
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/latamfx-mcp:0.1.0"

docker build -t "$IMAGE" .
docker push "$IMAGE"

# 2. Apply (works with terraform or tofu)
tofu init
tofu apply \
  -var="project_id=${PROJECT}" \
  -var="image=${IMAGE}"
```

## Inputs

| Variable | Default | Description |
| --- | --- | --- |
| `project_id` | — | GCP project (required). |
| `image` | — | Container image (required). |
| `region` | `southamerica-east1` | Cloud Run region. |
| `service_name` | `latamfx-mcp` | Service name. |
| `max_instances` | `3` | Autoscaling ceiling. |
| `cache_ttl_seconds` | `60` | FX cache TTL passed as env var. |
| `allow_unauthenticated` | `false` | Grant public invoker (keep false). |

## Outputs

| Output | Description |
| --- | --- |
| `service_uri` | Deployed Cloud Run URL. |
