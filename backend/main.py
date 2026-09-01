import hmac
import hashlib
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from analyzer import analyze_solution

load_dotenv()

app = FastAPI()

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """
    GitHub signs every webhook request with your secret.
    This checks the request actually came from GitHub.
    """
    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def fetch_file_content(repo: str, file_path: str) -> str:
    """
    Fetch the raw file content from GitHub using their API.
    """
    url = f"https://raw.githubusercontent.com/{repo}/main/{file_path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.text
        return ""


@app.post("/webhook")
async def github_webhook(request: Request):
    """
    Receives push events from GitHub.
    Fetches the file, sends it to AI for analysis, prints result.
    """
    payload = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()

    repo = data.get("repository", {}).get("full_name", "")
    commits = data.get("commits", [])

    for commit in commits:
        added_files = commit.get("added", [])
        modified_files = commit.get("modified", [])
        all_files = added_files + modified_files

        c_files = [f for f in all_files if f.endswith(".c")]

        for file_path in c_files:
            print(f"New solution detected: {file_path}")
            code = await fetch_file_content(repo, file_path)
            if code:
                result = analyze_solution(file_path, code)
                print(f"Result: {result}")

    return {"status": "received"}


@app.get("/health")
async def health():
    """Simple check to confirm the server is running."""
    return {"status": "ok"}