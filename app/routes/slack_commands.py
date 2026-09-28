from fastapi import APIRouter, Request
from app.services.database import add_transcript_to_db
import re

router = APIRouter()

@router.post("/slack/commands")
async def slack_commands(request: Request):
    form_data = await request.form()
    print("vandha dtaa", form_data)
    
    command = form_data.get("command", "")
    text = form_data.get("text", "")
    
    print(f"\n⚡ Slash Command {command} received: {text}")

    if command == "/add-knowledge":
        parts = text.split(maxsplit=1)
        if not parts:
            return {"text": "Usage: `/add-knowledge ProjectName`"}
            
        project_name = parts[0]
        
        # If the user pasted a URL manually in the command text
        file_url = parts[1] if len(parts) > 1 else None
        
        if file_url:
            add_transcript_to_db(project_name, file_url)
            return {
                "response_type": "in_channel",
                "text": f"✅ Saved manual URL to `{project_name}`."
            }
        else:
            return {
                "response_type": "ephemeral",
                "text": f"⚠️ Command received for `{project_name}`, but no URL was found. Remember: Slash commands don't support file attachments natively! Use '@YourBot add-knowledge {project_name}' in the channel instead."
            }

    return {"text": f"Unknown command {command}"}
