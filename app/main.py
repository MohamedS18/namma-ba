from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env BEFORE importing routes

from fastapi import FastAPI
import uvicorn
from app.routes import slack_commands, slack_events

# This is our main application container
app = FastAPI(title="Agentic Slack Bot")

# We register our endpoints from the routes folder
app.include_router(slack_commands.router)
app.include_router(slack_events.router)

@app.get("/")
def home():
    return {"message": "Agentic Slack Bot is running!"}

if __name__ == "__main__":
    print("🌐 Starting Structured Enterprise Server on port 8000...")
    # By pointing uvicorn to "app.main:app", we tell it to look in the app folder
    # We also turn on "reload=True" so the server automatically restarts when you edit a file!
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
