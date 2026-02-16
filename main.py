from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import uvicorn
import json
import time
from pathlib import Path

app = FastAPI()
RESULTS = {}

# TOP.GG CONFIG

TOPGG_WEBHOOK_AUTH = os.getenv("TOPGG_WEBHOOK_AUTH")
VOTE_FILE = Path("topgg_votes.json")
VOTE_DURATION_SECONDS = 60 * 60 * 12  # 12 hours


def load_votes():
    if not VOTE_FILE.exists():
        return {}
    try:
        with VOTE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_votes(data):
    with VOTE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)

@app.post("/webhook")
async def deapi_webhook(req: Request):
    payload = await req.json()

    event_type = payload.get("event", "unknown")
    data = payload.get("data", {})
    request_id = data.get("job_request_id")

    print(f"[Webhook] 📨 {event_type} | request_id={request_id}")

    if event_type == "job.processing":
        return JSONResponse(status_code=200, content={"status": "ack"})

    if event_type == "job.completed" or "result_url" in data:
        result_url = data.get("result_url")

        if request_id and result_url:
            RESULTS[request_id] = result_url
            print(f"[Webhook] Completed: {request_id}")
            return JSONResponse(status_code=200, content={"status": "ok"})

    return JSONResponse(status_code=200, content={"status": "ack"})

@app.post("/topgg-webhook")
async def topgg_webhook(req: Request):
    auth = req.headers.get("Authorization")

    if not TOPGG_WEBHOOK_AUTH or auth != TOPGG_WEBHOOK_AUTH:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    payload = await req.json()
    user_id = payload.get("user")

    if not user_id:
        return JSONResponse(status_code=400, content={"error": "Missing user"})

    votes = load_votes()
    votes[str(user_id)] = int(time.time() + VOTE_DURATION_SECONDS)
    save_votes(votes)

    print(f"[Top.gg] Vote received for user {user_id}")

    return {"status": "ok"}

@app.get("/result/{request_id}")
async def get_result(request_id: str):
    if request_id in RESULTS:
        return {"status": "done", "result_url": RESULTS[request_id]}

    return {"status": "pending"}


@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
