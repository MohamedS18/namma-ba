import json
import os

DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"projects": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_transcript_to_db(project_name: str, file_url: str):
    db = load_db()
    if project_name not in db["projects"]:
        db["projects"][project_name] = {"features": {}, "transcript_urls": []}
    
    # Check if the URL is already there to avoid duplicates
    if file_url not in db["projects"][project_name]["transcript_urls"]:
        db["projects"][project_name]["transcript_urls"].append(file_url)
        save_db(db)
        print(f"💾 Saved {file_url} to project {project_name}")
