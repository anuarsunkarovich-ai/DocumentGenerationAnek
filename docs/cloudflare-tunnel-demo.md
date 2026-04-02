# Cloudflare Tunnel Demo

This guide is the cheapest way to get the backend publicly reachable today without renting a server.

It runs the existing Docker Compose stack on your Windows machine and exposes:

- the API on local port `8000`
- MinIO on local port `9000`

through free Cloudflare Tunnel URLs.

Use this for:

- live demos
- pilot calls
- showing the engine to local agencies, brokers, notaries, or admin-heavy businesses

Do not treat this as production. Your machine must stay on, connected, and awake.

## What Works Well

- API demos
- template upload
- document generation
- presigned artifact downloads
- short sales calls and proof-of-value sessions

## What Is Temporary

- Quick Tunnel URLs are random and change every time you restart them
- your PC becomes the origin
- if your laptop sleeps, the demo dies

Cloudflare officially documents both Quick Tunnels and named published applications:

- Quick Tunnels: [Cloudflare Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/)
- Published applications / hostnames: [Cloudflare published applications](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/routing-to-tunnel/)

## Option 1: Fastest Path With Quick Tunnels

Quick Tunnels are free, anonymous, and temporary. Cloudflare says they generate a random `*.trycloudflare.com` URL and proxy traffic to your localhost service.

### Prerequisites

1. Docker Desktop is running
2. `cloudflared` is installed
3. There is no conflicting `.cloudflared/config.yml` or `config.yaml` if you want to use Quick Tunnels

Cloudflare notes that Quick Tunnels are not supported when a `config.yaml` is present in the `.cloudflared` directory.

### Step 1: Prepare Tunnel Override Env

Copy [.env.tunnel.example](/C:/Users/Anek/DocumentGenerationAnek/.env.tunnel.example) to `.env.tunnel`.

Leave `STORAGE__PUBLIC_ENDPOINT` blank for now.

### Step 2: Start The Local Stack

From the repo root:

```powershell
docker-compose.exe --env-file .env.tunnel -f docker-compose.yml -f docker-compose.tunnel.yml up -d --build
```

Check health:

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/health/ready
```

### Step 3: Start A Tunnel For The API

In a separate terminal:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Cloudflare will print a `https://...trycloudflare.com` URL.

### Step 4: Start A Tunnel For Storage

In another terminal:

```powershell
cloudflared tunnel --url http://localhost:9000
```

Copy only the hostname from the storage URL into `.env.tunnel`, for example:

```env
STORAGE__PUBLIC_ENDPOINT=quiet-wave-123.trycloudflare.com
STORAGE__PUBLIC_SECURE=true
```

Then restart the app services so presigned download URLs use the public storage hostname:

```powershell
docker-compose.exe --env-file .env.tunnel -f docker-compose.yml -f docker-compose.tunnel.yml up -d --build api worker scheduler
```

### Step 5: Seed Your Demo Admin

```powershell
docker-compose.exe --env-file .env.tunnel -f docker-compose.yml -f docker-compose.tunnel.yml exec api uv run python scripts/seed_stack_admin.py
```

Use those credentials to log in and run the demo.

## Option 2: Better Demo With A Named Tunnel

If you already have a domain on Cloudflare, use a named tunnel instead of Quick Tunnels.

That gives you stable hostnames like:

- `api.yourdomain.com`
- `storage.yourdomain.com`

This is better because:

- links do not change on every restart
- your `STORAGE__PUBLIC_ENDPOINT` stays stable
- you can reuse the same demo URL across meetings

Cloudflare documents mapping public hostnames to local services in its published-applications docs.

## Browser Frontend Note

If you use a browser UI hosted somewhere else, add that hostname to `APP__CORS_ORIGINS` in `.env.tunnel`.

Example:

```env
APP__CORS_ORIGINS=["http://localhost:5173","https://your-demo-ui.example.com"]
```

If you are only demoing with Swagger, curl, Postman, or direct API calls, you can ignore this.

## Demo-Day Checklist

Before a client call:

1. Start Docker Desktop
2. Start the stack
3. Start the API tunnel
4. Start the storage tunnel
5. Confirm `/health/ready`
6. Confirm generated file downloads open through the public storage URL
7. Disable sleep mode for the session
8. Keep your charger plugged in

## Useful Commands

Start stack:

```powershell
docker-compose.exe --env-file .env.tunnel -f docker-compose.yml -f docker-compose.tunnel.yml up -d --build
```

View API logs:

```powershell
docker-compose.exe --env-file .env.tunnel -f docker-compose.yml -f docker-compose.tunnel.yml logs api --tail=100
```

View worker logs:

```powershell
docker-compose.exe --env-file .env.tunnel -f docker-compose.yml -f docker-compose.tunnel.yml logs worker --tail=100
```

Stop stack:

```powershell
docker-compose.exe --env-file .env.tunnel -f docker-compose.yml -f docker-compose.tunnel.yml down
```

## Recommendation

Use Quick Tunnels for today.

Use a named tunnel as soon as you have a stable domain you can put on Cloudflare.
