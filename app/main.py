from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import os
import time
import requests
import openai

import json

try:
    with open("/data/options.json") as f:
        addon_config = json.load(f)
        openai.api_key = addon_config.get("openai_api_key")
        OPENAI_ADMIN_KEY = addon_config.get("openai_admin_api_key")
except Exception as e:
    print(f"❌ Failed to load add-on config: {e}")
    openai.api_key = None
    OPENAI_ADMIN_KEY = None

app = FastAPI()

# Ensure /data folder exists and db is ready
DB_PATH = "/data/gmail.sqlite"
Path("/data").mkdir(exist_ok=True)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    sender TEXT,
    subject TEXT
)
""")
conn.commit()
conn.close()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")


def get_gmail_service():
    creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/gmail.readonly"])
    return build("gmail", "v1", credentials=creds)


@app.get("/api/gmail/unread")
def get_unread_today():
    try:
        service = get_gmail_service()

        unread_today_query = f"is:unread after:{datetime.now().strftime('%Y-%m-%d')}"
        today_response = service.users().messages().list(userId="me", q=unread_today_query).execute()
        unread_today = today_response.get("resultSizeEstimate", 0)

        return JSONResponse({
            "unread_today": unread_today
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/hello")
def hello():
    return JSONResponse({"message": "Hello from FastAPI!"})

from googleapiclient.errors import HttpError

@app.get("/api/gmail/fetch")
def fetch_and_store_gmail():
    try:
        service = get_gmail_service()
        query = f"after:{datetime.now().strftime('%Y-%m-%d')}"

        messages = []
        response = service.users().messages().list(userId='me', q=query).execute()
        messages.extend(response.get('messages', []))

        while 'nextPageToken' in response:
            response = service.users().messages().list(userId='me', q=query, pageToken=response['nextPageToken']).execute()
            messages.extend(response.get('messages', []))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        count = 0
        for msg in messages:
            try:
                msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject']).execute()
                headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
                sender = headers.get('From', 'Unknown')
                subject = headers.get('Subject', '(No Subject)')

                cursor.execute("INSERT OR REPLACE INTO emails (id, sender, subject) VALUES (?, ?, ?)",
                               (msg['id'], sender, subject))
                count += 1
            except HttpError as e:
                print(f"Error fetching message {msg['id']}: {e}")

        conn.commit()
        conn.close()

        return JSONResponse({"fetched": count})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/gmail/list")
def list_stored_emails():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, sender, subject FROM emails ORDER BY rowid DESC LIMIT 100")
        rows = cursor.fetchall()
        conn.close()

        emails = [{"id": r[0], "sender": r[1], "subject": r[2]} for r in rows]
        return JSONResponse(content={"emails": emails})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

from fastapi import Request

@app.post("/api/openai/chat")
async def openai_chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    assistant_id = "asst_HCLbiRcnBGBuK40Ax5jxkRcB"

    try:
        print("🔧 Entered /api/openai/chat")

        # Check if key is loaded
        print("OpenAI Key:", openai.api_key[:10], "..." if openai.api_key else "MISSING")

        # Assistant ID check
        assistant_id = "asst_HCLbiRcnBGBuK40Ax5jxkRcB"
        print("Assistant ID:", assistant_id)
        # 1. Create a thread
        thread = openai.beta.threads.create()

        # 2. Add user's message to thread
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # 3. Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )

        # 4. Poll until it's complete
        import time
        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Run failed: {run_status.status}")
            time.sleep(1)

        # 5. Get messages (last is the assistant's reply)
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        reply = next((m.content[0].text.value for m in messages.data if m.role == "assistant"), "No reply")

        return JSONResponse({"reply": reply})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

import requests

@app.get("/api/openai/cost")
def get_openai_monthly_cost():
    admin_key = os.getenv("OPENAI_ADMIN_API_KEY")
    if not admin_key:
        return JSONResponse(status_code=500, content={"error": "Admin API key not set"})

    headers = {
        "Authorization": f"Bearer {admin_key}"
    }

    from datetime import datetime
    now = datetime.utcnow()
    start_date = now.replace(day=1).strftime('%Y-%m-%d')
    end_date = now.strftime('%Y-%m-%d')

    usage_url = f"https://api.openai.com/v1/dashboard/billing/usage?start_date={start_date}&end_date={end_date}"
    subscription_url = "https://api.openai.com/v1/dashboard/billing/subscription"

    try:
        usage_response = requests.get(usage_url, headers=headers).json()
        sub_response = requests.get(subscription_url, headers=headers).json()

        total_usage = usage_response.get("total_usage", 0) / 100.0  # convert from cents
        limit = sub_response.get("hard_limit_usd", 0)

        return JSONResponse({
            "used": round(total_usage, 2),
            "limit": round(limit, 2)
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
