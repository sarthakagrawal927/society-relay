from concurrent.futures import ThreadPoolExecutor

import pytest

from relay.limits import take


def test_shared_limit_is_atomic_and_survives_reopening(tmp_path, monkeypatch):
    monkeypatch.setenv("RELAY_PUBLIC_DEMO", "1")
    monkeypatch.setenv("RELAY_LIMIT_DB", str(tmp_path / "limits.db"))

    def attempt(_):
        try:
            take("inference", 5)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(20))) == 5
    with pytest.raises(ValueError, match="shared usage limit"):
        take("inference", 5)
    take("new_workspaces", 1)


def test_limit_resets_at_next_utc_bucket(tmp_path, monkeypatch):
    monkeypatch.setenv("RELAY_PUBLIC_DEMO", "1")
    monkeypatch.setenv("RELAY_LIMIT_DB", str(tmp_path / "limits.db"))
    monkeypatch.setattr("relay.limits.time.time", lambda: 86400)
    take("inference", 1)
    monkeypatch.setattr("relay.limits.time.time", lambda: 172800)
    take("inference", 1)
