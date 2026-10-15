"""ASGI factory for uvicorn: `uvicorn --factory nasha_lab.serve:app`. Builds the synthetic world and knowledge base at start-up (about 10 s)."""
import logging
import os

from . import agent, api, knowledge, trace, world


def app():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data = os.environ.get("NASHA_LAB_DATA", "/tmp/nasha_lab")
    os.makedirs(data, exist_ok=True)
    w, _, _ = world.build_world(int(os.environ.get("NASHA_LAB_SEED", "1")))
    svc = agent.AgentService(w, knowledge.default_kb(), store=trace.Store(os.path.join(data, "runs.db")), checkpoint_path=os.path.join(data, "checkpoints.db"))
    return api.create_app(service=svc)
