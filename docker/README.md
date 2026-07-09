# docker/

Reserved for shared Docker assets that don't belong to a single
service (e.g. a future base image, or Postgres init scripts). The
actual per-service Dockerfiles live next to their code
(`backend/Dockerfile`, `frontend/Dockerfile`), and orchestration is
defined in the root `docker-compose.yml` — that's deliberate so each
service's build context stays scoped to its own folder.
