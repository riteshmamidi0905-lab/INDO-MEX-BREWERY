# Local secret files (never committed)

This directory holds the secret FILES that `docker-compose.service.yml` mounts into the containers. Everything here except this README and `.gitignore` is ignored by git
and excluded from the image build context. Generate them yourself; there are no defaults and no placeholders to copy.

```sh
umask 077
openssl rand -hex 16 > secrets/db_password
printf '{"k1":"%s"}' "$(openssl rand -hex 32)" > secrets/jwt_keys.json
printf 'postgresql://nasha:%s@db:5432/nasha' "$(cat secrets/db_password)" > secrets/database_url
```

SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED. See `docs/P5-RUNBOOK.md` for key rotation.
