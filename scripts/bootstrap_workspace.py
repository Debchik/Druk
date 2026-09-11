"""One-time bootstrap with Supabase's new secret API key. Never commit real IDs or keys."""
import os, sys, httpx

url = os.environ["SUPABASE_URL"].rstrip("/")
key = os.environ["SUPABASE_SECRET_KEY"]
users = [x.strip() for x in os.environ["BOOTSTRAP_USER_IDS"].split(",") if x.strip()]
names = [x.strip() for x in os.getenv("BOOTSTRAP_DISPLAY_NAMES", "Сооснователь 1,Сооснователь 2").split(",")]
if not key.startswith("sb_secret_"):
    sys.exit("SUPABASE_SECRET_KEY must be a new sb_secret_ key, not legacy service_role")
if len(users) != 2:
    sys.exit("BOOTSTRAP_USER_IDS must contain exactly 2 comma-separated UUIDs")
# New sb_secret_ keys are opaque API keys, not JWTs. Send them as apikey only.
headers = {"apikey": key, "Content-Type": "application/json", "Prefer": "return=representation"}
with httpx.Client(timeout=20) as c:
    r = c.post(f"{url}/rest/v1/workspaces", headers=headers, json={"name":"Друк"}); r.raise_for_status(); wid = r.json()[0]["id"]
    payload = [{"workspace_id": wid, "user_id": uid, "display_name": names[i] if i < len(names) else f"Сооснователь {i+1}"} for i, uid in enumerate(users)]
    r = c.post(f"{url}/rest/v1/workspace_members", headers=headers, json=payload); r.raise_for_status()
    r = c.post(f"{url}/rest/v1/project_settings", headers=headers, json={"workspace_id":wid,"project_name":"Друк","created_by":users[0]}); r.raise_for_status()
print(wid)
