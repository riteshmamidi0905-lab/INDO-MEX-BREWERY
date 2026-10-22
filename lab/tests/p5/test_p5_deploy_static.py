"""Static checks of the deployment files. Docker is NOT runnable in the authoring sandbox, so this is a manual-lint-as-code: it proves properties of the TEXT of the Dockerfile and compose file,
not that they build or run. The only evidence that they do is the GitHub Actions run of .github/workflows/p5-service-ci.yml."""
from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest
import yaml

LAB = os.path.join(os.path.dirname(__file__), "..", "..")
REPO = os.path.join(LAB, "..")
DOCKERFILE = open(os.path.join(LAB, "Dockerfile.service"), encoding="utf-8").read()
COMPOSE = yaml.safe_load(open(os.path.join(LAB, "docker-compose.service.yml"), encoding="utf-8"))
COMPOSE_TEXT = open(os.path.join(LAB, "docker-compose.service.yml"), encoding="utf-8").read()
IGNORE = open(os.path.join(LAB, "Dockerfile.service.dockerignore"), encoding="utf-8").read()


def lines(): return [x.strip() for x in DOCKERFILE.splitlines() if x.strip() and not x.strip().startswith("#")]


def test_dockerfile_is_multistage_pinned_nonroot_with_healthcheck():
    froms = [x for x in lines() if x.startswith("FROM ")]
    assert len(froms) == 2 and all(re.match(r"FROM python:\d+\.\d+\.\d+-slim-bookworm AS \w+$", f) for f in froms), froms        # pinned by full tag, never :latest
    assert not any(":latest" in f for f in froms)
    assert "USER 10001:10001" in DOCKERFILE and DOCKERFILE.index("USER 10001:10001") > DOCKERFILE.index("COPY . .")
    assert re.search(r"^HEALTHCHECK ", DOCKERFILE, re.M) and "/healthz" in DOCKERFILE
    assert "COPY --from=builder /opt/venv /opt/venv" in DOCKERFILE and "apt-get install" in DOCKERFILE.split("AS runtime")[0] and "apt-get" not in DOCKERFILE.split("AS runtime")[1]    # tooling only in the build stage
    assert "--no-server-header" in DOCKERFILE and "--timeout-graceful-shutdown" in DOCKERFILE and "STOPSIGNAL SIGTERM" in DOCKERFILE
    assert "PYTHONDONTWRITEBYTECODE=1" in DOCKERFILE


def test_dockerfile_has_no_secrets_no_build_args_for_secrets_and_no_privileged_patterns():
    low = DOCKERFILE.lower()
    for bad in ("password", "secret", "api_key", "token=", "sudo", "chmod 777", "--privileged", "curl | sh", "wget -O- | sh", "add http", "ssh-"):
        assert bad not in low.replace("secrets", "").replace("secret", "") or bad == "secret", bad
    assert not re.search(r"^(ARG|ENV)\s+\w*(PASS|SECRET|KEY|TOKEN)\w*", DOCKERFILE, re.M | re.I)
    assert "pip install --no-cache-dir" in DOCKERFILE or "PIP_NO_CACHE_DIR=1" in DOCKERFILE


def test_dockerignore_excludes_vcs_env_files_and_key_material():
    for must in (".git", "**/.env", "**/*.pem", "**/*.key", "lab/secrets/*", "lab/tests", "**/__pycache__"): assert must in IGNORE.splitlines(), must
    assert "!**/.env.example" in IGNORE.splitlines()


def test_compose_services_are_hardened():
    svc = COMPOSE["services"]; assert set(svc) == {"db", "migrate", "api"}
    for name in ("migrate", "api"):
        s = svc[name]
        assert s["read_only"] is True and "no-new-privileges:true" in s["security_opt"] and s["cap_drop"] == ["ALL"] and s["init"] is True and s["tmpfs"], name
        assert s["mem_limit"] and s["cpus"] and s["pids_limit"], name
    assert svc["db"]["mem_limit"] and svc["db"]["cpus"] and svc["db"]["pids_limit"] and "ports" not in svc["db"]              # the database is not published
    assert svc["api"]["ports"] == ["127.0.0.1:${P5_API_PORT:-8000}:8000"]                                                     # loopback only
    for name in ("db", "api"): assert svc[name]["healthcheck"]["test"], name
    assert svc["db"]["healthcheck"]["retries"] >= 10 and svc["api"]["stop_grace_period"]
    assert svc["api"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully" and svc["api"]["depends_on"]["db"]["condition"] == "service_healthy"
    assert svc["migrate"]["restart"] == "no" and svc["migrate"]["command"][-1] == "up"


def test_compose_carries_no_secret_literals_and_requires_variables_loudly():
    env_all = {}
    for s in COMPOSE["services"].values(): env_all.update(s.get("environment", {}))
    for k, v in env_all.items():
        assert not re.search(r"(?i)(pass|secret|key|token)", k) or k.endswith("_FILE") or k in ("NASHA_SVC_JWT_ACTIVE_KID",), k
        assert not re.search(r"(?i)^(nasha|password|changeme|secret|test|admin)$", str(v)), k
    assert "POSTGRES_PASSWORD_FILE" in env_all and "POSTGRES_PASSWORD:" not in COMPOSE_TEXT and set(COMPOSE["secrets"]) == {"db_password", "database_url", "jwt_keys"}
    assert "${POSTGRES_USER:?" in COMPOSE_TEXT and "${POSTGRES_DB:?" in COMPOSE_TEXT
    assert all(set(v) == {"file"} for v in COMPOSE["secrets"].values())


def test_every_nasha_svc_variable_in_compose_is_a_real_setting():
    from nasha_lab.service.config import SECRET_FIELDS, Settings
    names = set(Settings.model_fields)
    for s in COMPOSE["services"].values():
        for k in s.get("environment", {}):
            if not k.startswith("NASHA_SVC_"): continue
            base = k[len("NASHA_SVC_"):].lower(); base = base[:-5] if base.endswith("_file") and base[:-5] in SECRET_FIELDS else base
            assert base in names, f"{k} is not a setting: the service would refuse to start"


def test_env_example_has_no_secrets_and_secret_dir_is_ignored():
    t = open(os.path.join(LAB, ".env.example"), encoding="utf-8").read()
    assert not re.search(r"(?i)(PASSWORD|SECRET|TOKEN|KEY)\s*=\s*\S+", t.replace("NASHA_SVC_JWT_ACTIVE_KID=k1", "")), "no secret-looking assignment in .env.example"
    assert open(os.path.join(LAB, "secrets", ".gitignore"), encoding="utf-8").read().split() == ["*", "!.gitignore", "!README.md"]
    assert "lab/.env" in open(os.path.join(REPO, ".gitignore"), encoding="utf-8").read()


def test_requirements_include_the_service_dependencies():
    t = open(os.path.join(LAB, "requirements-service.txt"), encoding="utf-8").read()
    for dep in ("psycopg[binary,pool]", "pydantic-settings", "PyJWT"): assert dep in t


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not installed here (expected in the authoring sandbox); CI runs `docker compose config -q`")
def test_docker_compose_config_validates():
    r = subprocess.run(["docker", "compose", "-f", os.path.join(LAB, "docker-compose.service.yml"), "config", "-q"], capture_output=True, text=True, env={**os.environ, "POSTGRES_USER": "u", "POSTGRES_DB": "d"})
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(shutil.which("hadolint") is None, reason="hadolint not installed here; CI runs hadolint")
def test_hadolint_clean():
    assert subprocess.run(["hadolint", os.path.join(LAB, "Dockerfile.service")], capture_output=True).returncode == 0
