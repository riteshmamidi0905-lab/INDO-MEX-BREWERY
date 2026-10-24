import pytest
from nasha_lab.growth import agent_research as AR


def test_default_is_unchanged_when_unset(monkeypatch):
    monkeypatch.delenv("X_T", raising=False)
    assert AR.env_seconds("X_T", 60.0) == 60.0
    monkeypatch.setenv("X_T", "  ")
    assert AR.env_seconds("X_T", 60.0) == 60.0


def test_valid_value_is_used(monkeypatch):
    monkeypatch.setenv("X_T", "600")
    assert AR.env_seconds("X_T", 60.0) == 600.0


@pytest.mark.parametrize("bad", ["abc", "0", "-5", "99999", "nan"])
def test_bad_value_is_refused_not_ignored(monkeypatch, bad):
    monkeypatch.setenv("X_T", bad)
    with pytest.raises(AR.AgentUnavailable) as e:
        AR.env_seconds("X_T", 60.0)
    assert e.value.failure_class == "bad_configuration"


def test_workflow_default_run_timeout_unchanged(monkeypatch):
    monkeypatch.delenv("NASHA_AGENT_RUN_TIMEOUT_S", raising=False)
    from nasha_lab.growth import launch_workflow as LW
    assert AR.env_seconds("NASHA_AGENT_RUN_TIMEOUT_S", LW.AGENT_TIMEOUT_S, hi=7200.0) == LW.AGENT_TIMEOUT_S == 120
