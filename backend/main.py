import hmac
import hashlib
import os
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """
    GitHub signs every webhook request with your secret.
    This checks the request actually came from GitHub.
    Without this, anyone could send fake push events to your server.
    """
    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@app.post("/webhook")
async def github_webhook(request: Request):
    """
    Receives push events from GitHub.
    GitHub calls this every time you push to dsa-solutions.
    """
    payload = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()

    commits = data.get("commits", [])
    for commit in commits:
        added_files = commit.get("added", [])
        modified_files = commit.get("modified", [])
        all_files = added_files + modified_files

        c_files = [f for f in all_files if f.endswith(".c")]

        for file_path in c_files:
            print(f"New solution detected: {file_path}")

    return {"status": "received"}


@app.get("/health")
async def health():
    """Simple check to confirm the server is running."""
    return {"status": "ok"}