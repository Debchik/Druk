"""Download all workspace files and write manifest.json using a user access token."""
import json, os
from pathlib import Path
import httpx

url=os.environ['SUPABASE_URL'].rstrip('/')
key=os.environ['SUPABASE_ANON_KEY']
token=os.environ['USER_ACCESS_TOKEN']
workspace=os.environ['WORKSPACE_ID']
out=Path(os.getenv('OUTPUT_DIR','storage-backup'));out.mkdir(parents=True,exist_ok=True)
h={'apikey':key,'Authorization':f'Bearer {token}'}
with httpx.Client(timeout=60) as c:
    r=c.get(f'{url}/rest/v1/files',params={'workspace_id':f'eq.{workspace}','select':'id,display_name,original_name,storage_path,mime_type,size_bytes,created_at'},headers=h);r.raise_for_status();files=r.json()
    for f in files:
        target=out/f['id']; target.mkdir(exist_ok=True)
        rr=c.get(f"{url}/storage/v1/object/authenticated/workspace-files/{f['storage_path']}",headers=h);rr.raise_for_status()
        (target/f['original_name']).write_bytes(rr.content)
(out/'manifest.json').write_text(json.dumps({'workspace_id':workspace,'files':files},ensure_ascii=False,indent=2),encoding='utf-8')
print(out)
