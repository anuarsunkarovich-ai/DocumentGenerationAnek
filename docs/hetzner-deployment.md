# Hetzner Deployment

This guide is the shortest practical path from this repository to a live backend on one Ubuntu VPS.

It assumes:

- one Hetzner Cloud VPS running Ubuntu
- two public subdomains:
  - `api.example.com` for the FastAPI backend
  - `storage.example.com` for MinIO downloads and presigned artifact URLs
- one operator-managed deployment, not a self-serve SaaS checkout flow

## What This Deploys

Use [docker-compose.hetzner.yml](/C:/Users/Anek/DocumentGenerationAnek/docker-compose.hetzner.yml) for the VPS deployment. It intentionally keeps:

- the API on `127.0.0.1:8000`
- MinIO API on `127.0.0.1:9000`
- MinIO console on `127.0.0.1:9001`
- PostgreSQL and Redis private inside Docker only

Public traffic should go through Nginx, not directly to Docker container ports.

## Local Prep

Before you copy the repo to the server:

1. Copy [.env.prod.example](/C:/Users/Anek/DocumentGenerationAnek/.env.prod.example) to `.env.prod`
2. Edit these values in `.env.prod`:

```env
APP__CORS_ORIGINS=["https://dashboard.example.com"]
STORAGE__PUBLIC_ENDPOINT=storage.example.com
STORAGE__PUBLIC_SECURE=true
OBSERVABILITY__SENTRY_DSN_FILE=/run/secrets/sentry_dsn
```

3. If you are not using Sentry yet, remove or comment out `OBSERVABILITY__SENTRY_DSN_FILE`
4. Keep these internal service values unchanged:

```env
DATABASE__HOST=db
STORAGE__ENDPOINT=minio:9000
REDIS__HOST=redis
```

5. Prepare the secret files listed in [deploy/secrets/README.md](/C:/Users/Anek/DocumentGenerationAnek/deploy/secrets/README.md)

## Ubuntu Server Bootstrap

SSH into the VPS and run:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg nginx certbot python3-certbot-nginx ufw
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

Log out and back in once after adding your user to the `docker` group.

## Copy And Start The Stack

On the VPS:

```bash
git clone <your-repo-url> document-generation
cd document-generation
mkdir -p deploy/secrets
```

Add your real `.env.prod` and secret files, then start the stack:

```bash
docker compose -f docker-compose.hetzner.yml up -d --build
docker compose -f docker-compose.hetzner.yml ps
```

Health checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
```

## Nginx Reverse Proxy

Copy [deploy/nginx/docgen.conf.example](/C:/Users/Anek/DocumentGenerationAnek/deploy/nginx/docgen.conf.example) to the server config path:

```bash
sudo cp deploy/nginx/docgen.conf.example /etc/nginx/sites-available/docgen.conf
sudo nano /etc/nginx/sites-available/docgen.conf
```

Replace:

- `api.example.com` with your API hostname
- `storage.example.com` with your storage hostname

Enable and reload:

```bash
sudo ln -sf /etc/nginx/sites-available/docgen.conf /etc/nginx/sites-enabled/docgen.conf
sudo nginx -t
sudo systemctl reload nginx
```

Issue TLS certificates:

```bash
sudo certbot --nginx -d api.example.com -d storage.example.com
```

After TLS is live, verify:

```bash
curl https://api.example.com/health
curl -I https://storage.example.com/
```

## First Admin User

Seed your first admin account from inside the running API container:

```bash
docker compose -f docker-compose.hetzner.yml exec api uv run python scripts/seed_stack_admin.py
```

That prints JSON with:

- `organization_id`
- `organization_code`
- `email`
- `password`
- `user_id`

Use those credentials to log in and start uploading templates.

## Concierge Operations

This backend is already suited to a managed B2B workflow:

1. Create one tenant/admin identity
2. Upload and configure the client's templates
3. Hand over either:
   - API credentials and scoped API keys
   - a simple low-code dashboard that calls this API
4. Collect payment manually through Kaspi, invoice, or bank transfer
5. Disable or revoke access on non-payment

Useful routes for managed client operations are documented in:

- [docs/api-contract.md](/C:/Users/Anek/DocumentGenerationAnek/docs/api-contract.md)
- [docs/operations.md](/C:/Users/Anek/DocumentGenerationAnek/docs/operations.md)

## Useful Commands

Start or rebuild:

```bash
docker compose -f docker-compose.hetzner.yml up -d --build
```

Logs:

```bash
docker compose -f docker-compose.hetzner.yml logs api --tail=100
docker compose -f docker-compose.hetzner.yml logs worker --tail=100
docker compose -f docker-compose.hetzner.yml logs scheduler --tail=100
```

Restart one service:

```bash
docker compose -f docker-compose.hetzner.yml restart api
```

Stop the stack:

```bash
docker compose -f docker-compose.hetzner.yml down
```

## Recommended First Sale Workflow

For the first revenue, keep the operating model boring:

1. Deploy one shared instance
2. Use one organization per paying client
3. Seed the client admin yourself
4. Upload and templateize their documents yourself
5. Charge a setup fee and a monthly maintenance fee
6. Add a better client-facing dashboard only after clients are paying
