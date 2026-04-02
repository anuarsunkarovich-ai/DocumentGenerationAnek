# Operations

## Production Secrets

The production configuration supports file-backed secrets for deployment platforms that mount credentials as files.

Required in production:

- `DATABASE__PASSWORD_FILE`
- `STORAGE__ACCESS_KEY_FILE`
- `STORAGE__SECRET_KEY_FILE`
- `AUTH__JWT_SECRET_KEY_FILE`

Optional file-backed secrets:

- `REDIS__PASSWORD_FILE`
- `OBSERVABILITY__SENTRY_DSN_FILE`

The application rejects production startup when required secrets are still configured as plaintext environment values.

## Scheduled Maintenance

The Docker stack now includes a Celery beat scheduler service that runs:

- stale-job recovery
- retention cleanup for expired artifacts
- failed-job cleanup
- audit-log cleanup
- temporary-file cleanup

Key settings:

- `WORKER__MAINTENANCE_CLEANUP_INTERVAL_MINUTES`
- `RETENTION__GENERATED_ARTIFACT_RETENTION_DAYS`
- `RETENTION__FAILED_JOB_RETENTION_DAYS`
- `RETENTION__AUDIT_LOG_RETENTION_DAYS`
- `RETENTION__TEMP_DATA_RETENTION_HOURS`
- `RETENTION__CLEANUP_BATCH_SIZE`

## Backup Scripts

Operational scripts live under `/scripts`:

- `python scripts/backup_postgres.py <output.dump>`
- `python scripts/restore_postgres.py <input.dump>`
- `python scripts/backup_minio.py <output_dir>`
- `python scripts/restore_minio.py <input_dir>`
- `python scripts/run_restore_drill.py <backup_dir>`

`run_restore_drill.py` expects:

- `postgres.dump`
- `minio/`

under the supplied backup directory.

## Support Endpoints

Admin support tooling is available under `/api/v1/admin/support`:

- `GET /audit-history`
- `POST /jobs/{job_id}/replay`
- `POST /jobs/{job_id}/invalidate-cache`
- `POST /users/{user_id}/disable`
- `POST /api-keys/{api_key_id}/disable`
- `POST /maintenance/cleanup`

All support routes require authenticated admin membership for the selected organization.

## Retention Behavior

- generated artifacts are retained according to `RETENTION__GENERATED_ARTIFACT_RETENTION_DAYS`
- failed jobs are removed after `RETENTION__FAILED_JOB_RETENTION_DAYS`
- audit logs are hard-pruned after `RETENTION__AUDIT_LOG_RETENTION_DAYS`
- temporary files under `data/tmp` are removed after `RETENTION__TEMP_DATA_RETENTION_HOURS`

Plan-based audit visibility still applies at read time, so support users only see audit history inside the organization's allowed window even before global retention cleanup removes older rows.
