from types import SimpleNamespace

import pytest
from fastapi import HTTPException


@pytest.mark.parametrize('value', [False, True])
def test_matched_priority_toggle_is_rejected_without_mutating_worlds(monkeypatch, value):
    import app
    logs=[]
    matched=[SimpleNamespace(enabled=True,log=logs.append),SimpleNamespace(enabled=False,log=logs.append)]
    monkeypatch.setattr(app,'worlds',matched)
    with pytest.raises(HTTPException) as exc:
        app.control(app.Control(action='enabled',value=value))
    assert exc.value.status_code==400
    assert 'matched comparisons' in exc.value.detail
    assert [world.enabled for world in matched]==[True,False]
    assert logs==[]


def test_single_world_priority_toggle_remains_available(monkeypatch):
    import app
    logs=[]
    world=SimpleNamespace(enabled=True,log=logs.append)
    monkeypatch.setattr(app,'worlds',[world])
    assert app.control(app.Control(action='enabled',value=False))=={'ok':True}
    assert world.enabled is False
    assert logs
