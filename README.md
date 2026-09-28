# NAMMA-BA: AI Project Management Slack Bot

NAMMA-BA is an enterprise-grade Slack bot powered by a local AI (Qwen 2.5 via Ollama). It acts as an autonomous project manager that can ingest transcripts, update a central knowledge base, and answer conversational queries about your projects in real-time.

## 🚀 Features

* **File Ingestion:** Upload a JSON transcript to Slack, type `transcripts [ProjectName]`, and the AI will autonomously extract the features and update the database.
* **Conversational Agent:** Ask the bot questions in Slack (e.g., *"What features do we have in DemoProject?"*), and it will intelligently use tools to query the database and answer you.
* **Thread Memory:** The bot remembers the context of your conversation within specific Slack threads.
* **Real-Time Action Logging:** The bot "thinks out loud" by logging exactly which tools it is using directly into the Slack thread so you can monitor its process.
* **100% Local AI & Storage:** All knowledge is safely stored in a local `database.json` file, and AI inference runs completely locally via Ollama.

---

## 🛠 Prerequisites

Before running the server, ensure you have the following installed:
1. **Python 3.8+**
2. **Ollama:** Installed and running on your machine.
3. **Ngrok:** For exposing your local server to Slack.
4. **Slack App:** A configured Slack App in your workspace.

---

## ⚙️ Setup Instructions

### 1. Environment Setup
Navigate to the project directory and activate the virtual environment:
```bash
cd /Users/user/projects/AGENT/NAMMA-BA
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
Install the required Python packages:
```bash
pip install fastapi uvicorn python-multipart ollama requests python-dotenv
```

### 3. Pull the Local AI Model
Ensure Ollama has the Qwen model downloaded:
```bash
ollama pull qwen2.5:3b
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory (this file is ignored by Git for security):
```bash
touch .env
```
Add your Slack Bot Token to the `.env` file:
```text
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
```

### 5. Start the Services
You need three terminal windows running simultaneously to power the bot:

**Terminal 1 (Ollama):**
```bash
ollama serve
```

**Terminal 2 (Ngrok):**
```bash
ngrok http 8000
```

**Terminal 3 (The Python Server):**
```bash
source venv/bin/activate
python -m app.main
```

---

## 🔌 Slack Dashboard Configuration

To connect Slack to your local server, configure your app at [api.slack.com](https://api.slack.com/):

1. **OAuth & Permissions (Scopes):**
   Ensure your Bot Token has the following scopes:
   * `chat:write` (To send messages)
   * `files:read` (To download uploaded transcripts)
   * `app_mentions:read` (To hear when users tag the bot)

2. **Event Subscriptions:**
   * Toggle **Enable Events** to **On**.
   * Paste your Ngrok URL followed by the endpoint: `https://<your-ngrok-url>.ngrok-free.app/slack/events`
   * Subscribe to the following bot events:
     * `app_mention` (or `message.channels` if you want it to read every message)

*(Don't forget to click "Reinstall to Workspace" whenever you change scopes!)*

---

## 💬 Usage

**Updating a Project:**
1. Invite the bot to your channel (`/invite @YourBot`).
2. Upload a `.json` transcript file to the channel.
3. In the message box attached to the file, type: `transcripts YourProjectName`.
4. The bot will download the file, process it, update `database.json`, and reply in a thread with a beautifully formatted summary.

**Chatting with the Bot:**
1. Simply tag the bot or send a message in the channel.
2. Ask a question like: *"Give me an overview of the features in YourProjectName."*
3. The bot will reply in a thread. You can reply back in that same thread, and the bot will remember the context of the conversation!
