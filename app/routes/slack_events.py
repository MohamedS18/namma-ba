import os
import requests
from fastapi import APIRouter, Request, BackgroundTasks
from app.services.database import add_transcript_to_db
from app.services.agent import run_knowledge_agent, run_chat_agent

router = APIRouter()

import re

def get_slack_token():
    return os.environ.get("SLACK_BOT_TOKEN")

def slackify_markdown(text: str) -> str:
    """Converts standard GitHub markdown (used by LLMs) into Slack's proprietary 'mrkdwn'."""
    # 1. Convert standard bold (**text**) to Slack bold (*text*)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # 2. Convert standard headers (### Header) to Slack bold (*Header*)
    text = re.sub(r'^(#{1,6})\s+(.+)$', r'*\2*', text, flags=re.MULTILINE)
    # 3. Clean up any weird nested asterisks the LLM might have generated
    text = text.replace('***', '*').replace('**', '*')
    return text

def send_slack_message(channel_id: str, text: str, thread_ts: str = None):
    """Sends a beautifully formatted markdown message back to Slack."""
    token = get_slack_token()
    if not token:
        print(f"⚠️ Mock Slack Reply (No Token): {text}")
        return
        
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Apply our Slack-friendly formatter to the text before sending!
    formatted_text = slackify_markdown(text)
    payload = {"channel": channel_id, "text": formatted_text}
    
    if thread_ts:
        payload["thread_ts"] = thread_ts
        
    try:
        requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)
    except Exception as e:
        print(f"❌ Error connecting to Slack API: {e}")

# ==========================================
# BACKGROUND TASK 1 (Raw Chat)
# ==========================================
def process_raw_message(text: str, channel_id: str, thread_ts: str):
    """Handles normal conversational messages in the background."""
    # Send a quick loading message so the user knows the AI is typing
    send_slack_message(channel_id, "_Thinking..._", thread_ts)
    
    # Define a callback to instantly relay tool calls back to Slack
    def log_to_slack(msg: str):
        send_slack_message(channel_id, msg, thread_ts)
    
    # Run the chat agent, passing the thread ID for memory and the logging callback!
    reply = run_chat_agent(text, thread_ts, log_callback=log_to_slack)
    
    # Send the final response
    send_slack_message(channel_id, reply, thread_ts)

# ==========================================
# BACKGROUND TASK 2 (Heavy AI Processing)
# ==========================================
def process_file_and_run_agent(project_name: str, file_url: str, channel_id: str, thread_ts: str):
    """This runs in the background so we don't keep Slack waiting!"""
    send_slack_message(channel_id, f"⏳ Received file for `{project_name}`. Validating JSON...", thread_ts)
    
    token = get_slack_token()
    if not token:
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(file_url, headers=headers)
    
    try:
        transcript_json = response.json()
    except ValueError:
        send_slack_message(channel_id, "❌ *ERROR*: The uploaded file is NOT a valid JSON file.", thread_ts)
        return
        
    send_slack_message(channel_id, f"🧠 JSON validated! Agent is synthesizing knowledge for `{project_name}`...", thread_ts)
    
    # Define callback for tool logging
    def log_to_slack(msg: str):
        send_slack_message(channel_id, msg, thread_ts)
        
    updated_features = run_knowledge_agent(project_name, transcript_json, log_callback=log_to_slack)
    
    if updated_features:
        reply = f"✅ *Knowledge Updated for {project_name}*\n\n"
        for feat in updated_features:
            reply += f"🔹 *Feature:* {feat.get('feature_name', 'Unknown')}\n"
            reply += f"   *Title:* {feat.get('title', 'Unknown')}\n"
            reply += f"   *Description:* {feat.get('description', 'Unknown')}\n"
            
            conflicts = feat.get('conflicts', '')
            if conflicts:
                reply += f"   *Conflicts:* {conflicts}\n\n"
            else:
                reply += "\n"
        send_slack_message(channel_id, reply, thread_ts)
    else:
        send_slack_message(channel_id, "⚠️ Agent finished but made no updates to the features.", thread_ts)

# ==========================================
# FASTAPI ENDPOINT
# ==========================================
@router.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    if "X-Slack-Retry-Num" in request.headers:
        print(f"⚠️ Ignoring Slack Retry #{request.headers['X-Slack-Retry-Num']}")
        return {"status": "ignored_retry"}
        
    payload = await request.json()
    
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    if payload.get("event"):
        event = payload["event"]
        if event.get("bot_id"):
            return {"status": "ignored"}
            
        text = event.get("text", "")
        channel_id = event.get("channel")
        
        # EXTRACT THE THREAD TIMESTAMP (Use parent thread if it exists, otherwise use its own ts)
        thread_ts = event.get("thread_ts", event.get("ts")) 
        
        # ROUTING LOGIC
        if "transcripts " in text.lower():
            start_idx = text.lower().find("transcripts ") + len("transcripts ")
            remainder = text[start_idx:].strip()
            
            if remainder:
                project_name = remainder.split()[0]
                files = event.get("files", [])
                
                if files:
                    file_url = files[0].get("url_private")
                    add_transcript_to_db(project_name, file_url)
                    background_tasks.add_task(process_file_and_run_agent, project_name, file_url, channel_id, thread_ts)
                else:
                    send_slack_message(channel_id, "❌ No physical file attached. Please attach a JSON file.", thread_ts)
        else:
            # If the user didn't type "transcripts", treat it as a conversational message!
            if text.strip():
                background_tasks.add_task(process_raw_message, text, channel_id, thread_ts)
            
    return {"status": "ok"}
