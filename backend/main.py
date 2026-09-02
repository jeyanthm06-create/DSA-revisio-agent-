import hmac, hashlib, os
import httpx
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from analyzer import analyze_solution

load_dotenv()
app = FastAPI()
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

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

@app.get("/health")
async def health():
    return {"status": "ok"}