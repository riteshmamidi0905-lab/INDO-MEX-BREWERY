# NASHA lab: reproducible local commands. SYNTHETIC data only.  `make help`
PY ?= python3
.PHONY: help test eval repro dashboards pg lock skip-report
help:            ## list targets
	@grep -E '^[a-z-]+:.*##' Makefile | sed 's/:.*##/ -/'
test:            ## full test suite with a JUnit file and skip report
	$(PY) -m pytest -q -p no:cacheprovider -rs --junitxml=/tmp/junit.xml tests; $(PY) tools/skip_report.py /tmp/junit.xml
eval:            ## Ops AI evaluation on a fresh dev warehouse (fails on any wrong answer / false allow)
	$(PY) -c "import tempfile,pathlib;from nasha_lab import enterprise_sim as es;from nasha_lab.warehouse import pipeline,ops_ai_eval as E;d=pathlib.Path(tempfile.mkdtemp());es.generate(es.PROFILES['dev'],d/'s');pipeline.run(d/'s',d/'w.db');from nasha_lab.warehouse import scenario;scenario.build(d/'w.db');import sys;sys.exit(E.main(['--db',str(d/'w.db'),'--check','--out','results/ops_ai_eval_dev.json']))"
repro:           ## build twice from scratch and compare every table hash
	$(PY) -m nasha_lab.warehouse.repro --profile dev --out results/warehouse_repro_dev.json
dashboards:      ## build the static dashboards from a fresh dev warehouse into /tmp/nasha-dashboards
	$(PY) -c "import tempfile,pathlib;from nasha_lab import enterprise_sim as es;from nasha_lab.warehouse import pipeline,dashboards;d=pathlib.Path(tempfile.mkdtemp());es.generate(es.PROFILES['dev'],d/'s');pipeline.run(d/'s',d/'w.db');print(dashboards.build_all(d/'w.db','/tmp/nasha-dashboards'))"
pg:              ## PostgreSQL variant tests (needs NASHA_PG_DSN or `pip install pixeltable-pgserver sqlglot`)
	$(PY) -m pytest -q -p no:cacheprovider -rs tests/test_warehouse_pg.py
lock:            ## record installed direct-dependency versions
	$(PY) tools/make_lock.py
