import json
import ollama
from app.services.database import load_db, save_db

# ==========================================
# 1. AGENT TOOLS (Direct Database Storage)
# ==========================================
def read_feature_knowledge(project_name: str, feature_name: str) -> str:
    """Reads feature data directly from the JSON database."""
    db = load_db()
    project = db.get("projects", {}).get(project_name, {})
    features = project.get("features", {})
    
    if feature_name in features:
        return json.dumps(features[feature_name])
        
    return "No existing knowledge found for this feature. You are creating it for the first time."

def save_feature_knowledge(project_name: str, feature_name: str, title: str, description: str, conflicts: str = "") -> str:
    """Saves the feature data directly into the JSON database (no physical files)."""
    db = load_db()
    
    if project_name not in db.get("projects", {}):
        if "projects" not in db:
            db["projects"] = {}
        db["projects"][project_name] = {"features": {}, "transcript_urls": []}
        
    if "features" not in db["projects"][project_name]:
        db["projects"][project_name]["features"] = {}
    
    feature_data = {
        "Title": title,
        "Description": description
    }
    if conflicts:
        feature_data["Conflicts"] = conflicts
        
    db["projects"][project_name]["features"][feature_name] = feature_data
    save_db(db)
    
    return f"Success! Saved feature {feature_name} directly to database.json."

def read_project_details(project_name: str) -> str:
    """Reads the entire project object from the database."""
    db = load_db()
    project = db.get("projects", {}).get(project_name)
    if project:
        return json.dumps(project, indent=2)
    return f"Project '{project_name}' not found in the database."

# -- NEW TOOL --
def read_entire_database() -> str:
    """Reads the entire database containing all projects."""
    db = load_db()
    return json.dumps(db, indent=2)

# Mapping for the LLM
tools_dict = {
    'read_feature_knowledge': read_feature_knowledge,
    'save_feature_knowledge': save_feature_knowledge,
    'read_project_details': read_project_details,
    'read_entire_database': read_entire_database
}

tools_schema = [
    {
        'type': 'function',
        'function': {
            'name': 'read_feature_knowledge',
            'description': 'Read the existing state of a specific project feature from the database.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'project_name': {'type': 'string'},
                    'feature_name': {'type': 'string', 'description': 'The name of the feature (e.g., auth, database, ui)'}
                },
                'required': ['project_name', 'feature_name']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'save_feature_knowledge',
            'description': 'Save the updated knowledge for a feature directly into the database. MUST include Title and Description.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'project_name': {'type': 'string'},
                    'feature_name': {'type': 'string'},
                    'title': {'type': 'string'},
                    'description': {'type': 'string'},
                    'conflicts': {'type': 'string', 'description': 'OPTIONAL: Any contradictions between old and new knowledge.'}
                },
                'required': ['project_name', 'feature_name', 'title', 'description']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'read_project_details',
            'description': 'Read the entire project object from the database to see a birds-eye view of all its features and metadata.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'project_name': {'type': 'string'}
                },
                'required': ['project_name']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'read_entire_database',
            'description': 'Read the entire database to see a list of all projects and all high-level data. Use this when the user asks what projects exist.',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    }
]

from typing import Callable

# ==========================================
# 2. THE MODULAR AGENT ENGINE
# ==========================================
def run_knowledge_agent(project_name: str, transcript_json: dict, log_callback: Callable = None) -> list:
    print(f"🤖 Agent starting analysis for {project_name}...")
    
    system_prompt = """
    You are a modular Knowledge Synthesizer. You receive JSON transcripts.
    1. Analyze the JSON to determine which feature it belongs to.
    2. Use `read_feature_knowledge` to check existing state in the database.
    3. Use `save_feature_knowledge` to write the updated knowledge back to the database.
    You MUST adhere strictly to the Title and Description structure. Only include Conflicts if there is a direct contradiction.
    """
    
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f"Project: {project_name}\nIncoming JSON Transcript:\n{json.dumps(transcript_json)}"}
    ]

    updated_features = []

    for step in range(5): 
        response = ollama.chat(model='qwen2.5:3b', messages=messages, tools=tools_schema)
        msg = response['message']
        messages.append(msg)
        
        if not msg.get('tool_calls'):
            break
            
        for tool in msg['tool_calls']:
            func_name = tool['function']['name']
            args = tool['function']['arguments']
            
            # Broadcast the tool call back to Slack!
            if log_callback:
                args_preview = json.dumps(args)
                log_callback(f"🔧 *Agent Action:* Calling tool `{func_name}` with args `{args_preview}`")
            
            try:
                result = tools_dict[func_name](**args)
                if func_name == 'save_feature_knowledge':
                    updated_features.append(args)
            except Exception as e:
                result = f"Error: {e}"
                
            messages.append({'role': 'tool', 'name': func_name, 'content': result})

    return updated_features

# ==========================================
# 3. CONVERSATIONAL AGENT (Chat & Query with Memory)
# ==========================================
# This dictionary stores the history of conversations, grouped by their Slack thread ID!
THREAD_MEMORY = {}

def run_chat_agent(prompt: str, thread_ts: str, log_callback: Callable = None) -> str:
    print(f"🤖 Chat Agent answering raw message in thread {thread_ts}...")
    
    system_prompt = """
    You are a helpful AI project assistant (name: NAMMA-BA) in a Slack channel.
    Users will ask you general questions or ask for project details.
    - You can use `read_entire_database` to see a list of all projects we are tracking.
    - You can use `read_project_details` to get a bird's-eye view of an entire project and list its features.
    - You can use `read_feature_knowledge` to look up specific information about a single feature.
    If you don't need to look anything up, just reply conversationally.
    
    FORMATTING RULES FOR SLACK:
    - Never use `#` or `###` for headers. Use bold text like `*Header*` instead.
    - Never use `**` for bold. Use a single asterisk `*` (e.g. `*bold text*`).
    - Use standard `-` for bullet points.
    """
    
    # If this is a brand new thread, initialize it with the system prompt!
    if thread_ts not in THREAD_MEMORY:
        THREAD_MEMORY[thread_ts] = [{'role': 'system', 'content': system_prompt}]
        
    # Append the user's new message to this specific thread's memory
    THREAD_MEMORY[thread_ts].append({'role': 'user', 'content': prompt})
    
    # Give the LLM the entire history of this thread
    messages = THREAD_MEMORY[thread_ts]

    for step in range(3): 
        response = ollama.chat(model='qwen2.5:3b', messages=messages, tools=tools_schema)
        msg = response['message']
        
        # Append the AI's response (or tool call) to the memory
        messages.append(msg)
        
        if not msg.get('tool_calls'):
            return msg.get('content', 'Sorry, I do not have a response.')
            
        for tool in msg['tool_calls']:
            func_name = tool['function']['name']
            args = tool['function']['arguments']
            
            # Broadcast the tool call back to Slack!
            if log_callback:
                args_preview = json.dumps(args)
                log_callback(f"🔧 *Agent Action:* Calling tool `{func_name}` with args `{args_preview}`")
                
            try:
                result = tools_dict[func_name](**args)
            except Exception as e:
                result = f"Error: {e}"
                
            # Append the tool's result to the memory
            messages.append({'role': 'tool', 'name': func_name, 'content': result})

    return messages[-1].get('content', 'Finished processing request.')
