import pytest
from nasha_lab import knowledge, tools as T, world as W


@pytest.fixture(scope="session")
def kb():
    return knowledge.default_kb()


@pytest.fixture()
def world():
    return W.build_world(1)[0]


@pytest.fixture()
def ctx(kb):
    return T.ToolContext(kb=kb)
