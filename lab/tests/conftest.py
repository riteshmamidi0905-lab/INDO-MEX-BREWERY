import pytest
from nasha_lab import knowledge, tools as T, world as W

knowledge.use_version("block3")      # the Block 1-3 test suite pins the frozen Block 3 corpus; Block 4 tests ask for version='current' explicitly


@pytest.fixture(scope="session")
def kb():
    return knowledge.default_kb()


@pytest.fixture()
def world():
    return W.build_world(1)[0]


@pytest.fixture()
def ctx(kb):
    return T.ToolContext(kb=kb)
