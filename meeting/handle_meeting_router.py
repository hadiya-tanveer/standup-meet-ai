import os
import json

from fastapi import APIRouter, Request
from utils.global_variables import ACTIVE_PARTICIPANTS_FILE, TRANSCRIPTS_FILE

router = APIRouter()

# ---------- Participant Utilities ----------
def load_active_participants():
    if os.path.exists(ACTIVE_PARTICIPANTS_FILE):
        with open(ACTIVE_PARTICIPANTS_FILE, "r") as f:
            data = json.load(f)
            return {p["name"] for p in data}
    return set()

def save_active_participants(participants):
    with open(ACTIVE_PARTICIPANTS_FILE, "w") as f:
        json.dump([{"name": p} for p in participants], f, indent=2)

def handle_participant_join(participant):
    name = participant.get("name", "Unknown")
    participants = load_active_participants()
    participants.add(name)
    save_active_participants(participants)

def handle_participant_leave(participant):
    name = participant.get("name", "Unknown")
    participants = load_active_participants()
    participants.discard(name)
    save_active_participants(participants)

def get_current_participants():
    return [{"name": name} for name in load_active_participants()]

# ---------- Transcript Utilities ----------
def handle_transcript_data(payload):
    speaker = payload["data"]["data"]["participant"]["name"]
    words = payload["data"]["data"]["words"]
    text = " ".join(word["text"] for word in words)
    print(f"Transcript from {speaker}: {text}")

    if os.path.exists(TRANSCRIPTS_FILE):
        with open(TRANSCRIPTS_FILE, "r") as f:
            transcripts = json.load(f)
    else:
        transcripts = {}

    transcripts.setdefault(speaker, []).append(text)

    with open(TRANSCRIPTS_FILE, "w") as f:
        json.dump(transcripts, f, indent=2)


# ---------- Webhook Route ----------
@router.post("/api/webhook/recall/transcript")
async def handle_meeting(request: Request):
    payload = await request.json()
    event_type = payload.get("event")

    if event_type == "transcript.data":
        handle_transcript_data(payload)

    elif event_type == "participant_events.join":
        participant = payload["data"]["data"]["participant"]
        handle_participant_join(participant)

    elif event_type == "participant_events.leave":
        participant = payload["data"]["data"]["participant"]
        handle_participant_leave(participant)