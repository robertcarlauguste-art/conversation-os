# Railway staging deployment

ConversationOS uses one Railway project with five services and Cloudflare R2
for private audio storage:

- `frontend`: Next.js, root directory `/frontend`, config `/frontend/railway.json`
- `backend`: FastAPI, root directory `/backend`, config `/backend/railway-api.json`
- `worker`: ARQ, root directory `/backend`, config `/backend/railway-worker.json`
- Railway PostgreSQL
- Railway Redis

The backend and worker deploy from the same Git commit and Dockerfile. Only the
backend runs Alembic as a pre-deploy release step. The worker does not receive a
public domain.

## Required variables

Never paste secret values into source control. Configure them in Railway's
service variable UI. Use Railway reference variables for PostgreSQL and Redis.

### Shared backend and worker

```text
APP_ENV=production
AUTH_ENABLED=true
PROCESSING_MODE=queue
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=<Cloudflare R2 S3 endpoint>
S3_REGION=auto
S3_BUCKET=conversation-os-staging
S3_ACCESS_KEY_ID=<bucket-scoped access key>
S3_SECRET_ACCESS_KEY=<bucket-scoped secret key>
CLERK_SECRET_KEY=<Clerk staging secret>
OPENAI_API_KEY=<OpenAI key>
ANTHROPIC_API_KEY=<Anthropic key>
```

The backend additionally receives exact JSON arrays after both public Railway
domains are known:

```text
CORS_ORIGINS=["https://<frontend-domain>"]
CLERK_AUTHORIZED_PARTIES=["https://<frontend-domain>"]
```

### Frontend

```text
NEXT_PUBLIC_API_URL=https://<backend-domain>
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<Clerk staging publishable key>
CLERK_SECRET_KEY=<Clerk staging secret>
```

`NEXT_PUBLIC_*` values are compiled into the browser bundle and are not
secrets. Changing either requires a frontend rebuild.

## Deployment order

1. Create the project and a `staging` environment.
2. Add PostgreSQL and Redis in the same Railway region.
3. Add backend and worker from the same GitHub repository and commit.
4. Add the frontend and generate public domains for frontend and backend only.
5. Configure exact Clerk authorized parties and backend CORS.
6. Deploy backend first, then worker, then frontend.
7. Require `/ready` to report PostgreSQL, Redis, and worker as healthy.
8. Run the staging smoke checker and authenticated two-user isolation checks.

## Cost and rollback controls

- Set compute email alerts and a hard usage limit before deployment.
- Keep all services in one region to use private networking.
- Roll back application services to the last successful deployment together.
- Never roll back application code across an incompatible database migration.
- Revoke the R2 token and rotate Railway secrets if credentials are exposed.
