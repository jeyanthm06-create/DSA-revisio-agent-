import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib
import hmac
import hashlib
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from analyzer import analyze_solution
from datetime import datetime, timezone, timedelta

load_dotenv()
app = FastAPI()

app.mount("/static", StaticFiles(directory=str(pathlib.Path(__file__).parent.parent / "frontend")), name="static")

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


@app.get("/")
async def dashboard():
    return FileResponse(str(pathlib.Path(__file__).parent.parent / "frontend" / "index.html"))


def verify_github_signature(payload: bytes, signature: str) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    expected = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def fetch_file_content(repo: str, file_path: str) -> str:
    url = f"https://raw.githubusercontent.com/{repo}/main/{file_path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        print(f"Fetch status: {response.status_code} for {file_path}")
        if response.status_code == 200:
            return response.text
        return ""


@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    data = await request.json()
    repo = data.get("repository", {}).get("full_name", "")
    commits = data.get("commits", [])
    for commit in commits:
        all_files = commit.get("added", []) + commit.get("modified", [])
        c_files = [f for f in all_files if f.endswith(".c")]
        for file_path in c_files:
            print(f"New solution detected: {file_path}")
            code = await fetch_file_content(repo, file_path)
            print(f"Fetched: {len(code)} chars")
            if code:
                result = analyze_solution(file_path, code)
                print(f"Result: {result}")
    return {"status": "received"}


@app.get("/solutions")
async def get_solutions():
    from supabase import create_client
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))
    response = supabase.table("solutions").select("*").order("created_at", desc=True).execute()
    return {"solutions": response.data}


@app.get("/due-today")
async def get_due_today():
    from supabase import create_client
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))
    response = supabase.table("solutions").select("*").execute()
    all_solutions = response.data
    due = []
    now = datetime.now(timezone.utc)
    for s in all_solutions:
        created = datetime.fromisoformat(s["created_at"])
        days = s.get("next_revision_days") or 7
        due_date = created + timedelta(days=days)
        if due_date <= now:
            due.append(s)
    return {"due": due}


@app.get("/health")
async def health():
    return {"status": "ok"}