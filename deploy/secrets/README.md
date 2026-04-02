Create these files on the server before starting `docker compose -f docker-compose.hetzner.yml up -d --build`:

- `database_password`
- `storage_access_key`
- `storage_secret_key`
- `jwt_signing_key`
- `redis_password`

Recommended:

- keep this directory out of Git
- use long random values for every file
- set file permissions to the deploy user only, for example `chmod 600 deploy/secrets/*`

Example secret generation on Ubuntu:

```bash
mkdir -p deploy/secrets
openssl rand -hex 24 > deploy/secrets/database_password
openssl rand -hex 24 > deploy/secrets/storage_access_key
openssl rand -hex 32 > deploy/secrets/storage_secret_key
openssl rand -hex 32 > deploy/secrets/jwt_signing_key
openssl rand -hex 24 > deploy/secrets/redis_password
chmod 600 deploy/secrets/*
```
