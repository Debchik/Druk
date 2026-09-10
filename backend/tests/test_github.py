import json
import pytest
import app.main as main


class FakeResponse:
    status_code = 200
    def json(self):
        return [
            {'id':1,'number':1,'title':'Issue','state':'open','html_url':'x','labels':[],'updated_at':'2026-01-01T00:00:00Z'},
            {'id':2,'number':2,'title':'PR','state':'open','html_url':'y','labels':[],'updated_at':'2026-01-01T00:00:00Z','pull_request':{}},
        ]


class FakeClient:
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def get(self, *args, **kwargs): return FakeResponse()


@pytest.mark.asyncio
async def test_github_issue_fetch_excludes_pr(monkeypatch):
    monkeypatch.setattr(main.settings, 'github_token', 'token')
    monkeypatch.setattr(main.httpx, 'AsyncClient', FakeClient)
    rows = await main.fetch_github_issues('owner/repo')
    assert [x['title'] for x in rows] == ['Issue']
