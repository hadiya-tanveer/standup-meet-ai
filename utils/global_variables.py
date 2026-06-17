import os
from crewai import LLM
from datetime import date
from dotenv import load_dotenv

load_dotenv()

DATE_NOW = date.today().strftime('%d-%m-%Y')

TTS_MODEL = os.getenv("TTS_MODEL")
LLM_MODEL = os.getenv("LLM_MODEL")
MODEL_TEMPERATURE = os.getenv("MODEL_TEMPERATURE")

CREWAI_LLM = LLM(model=f"groq/{LLM_MODEL}", temperature=MODEL_TEMPERATURE)

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")

GOOGLE_EMAIL = os.getenv("GOOGLE_EMAIL")
GOOGLE_PASSWORD = os.getenv("GOOGLE_PASSWORD")
GOOGLE_MEET_LINK = os.getenv("GOOGLE_MEET_LINK")

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
RECALL_API_KEY = os.getenv("RECALL_API")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

TRANSCRIPTS_FILE = "test/output/transcripts.json"
ACTIVE_PARTICIPANTS_FILE = "test/output/active_participants.json"

ISSUE_HISTORY_FILE = "test/output/issue_history.json"
SPRINT_BACKLOG_FILE = "test/output/sprint_backlog.json"
PRODUCT_BACKLOG_FILE = "test/output/sprint_backlog.json"
MEETING_CONVERSATIONS_FILE = "test/output/meeting_conversations.json"

# Time (in seconds)
TIME_TO_WAIT = 45
AGENT_REMINDER_TIME = 15