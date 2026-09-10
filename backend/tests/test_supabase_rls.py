import os
import httpx
import pytest

pytestmark = pytest.mark.integration


def test_user_without_membership_cannot_read_workspace():
    url=os.getenv('RLS_SUPABASE_URL'); key=os.getenv('RLS_SUPABASE_ANON_KEY'); token=os.getenv('RLS_NON_MEMBER_TOKEN'); workspace=os.getenv('RLS_WORKSPACE_ID')
    if not all([url,key,token,workspace]):
        pytest.skip('RLS integration credentials are not configured')
    r=httpx.get(f"{url.rstrip('/')}/rest/v1/tasks",params={'workspace_id':f'eq.{workspace}','select':'id'},headers={'apikey':key,'Authorization':f'Bearer {token}'},timeout=20)
    assert r.status_code == 200
    assert r.json() == []
