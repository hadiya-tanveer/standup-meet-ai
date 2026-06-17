import os
import json
import time
import asyncio
import requests
import threading

from crewai import Agent

from meeting.meet_controller import MeetController

from agents.summary_agent import SummaryAgent
from agents.facilitator_agent import FacilitatorAgent
from agents.issuehistory_agent import IssueHistoryAgent
from agents.issueanalyzer_agent import IssueAnalyzerAgent
from agents.absencemanager_agent import AbsenceManagerAgent
from agents.contextaggregator_agent import ContextAggregatorAgent

from utils.global_variables import SLACK_CHANNEL, SLACK_TOKEN, DATE_NOW, CREWAI_LLM
from utils.global_variables import MEETING_CONVERSATIONS_FILE, ISSUE_HISTORY_FILE
from utils.global_variables import TIME_TO_WAIT, AGENT_REMINDER_TIME


class OrchestratorAgent:
    def __init__(self, name="Orchestrator"):
        self.agent = Agent(
            name=name,
            role="Orchestrator Agent",
            goal="Connect all the agents and manage the standup meeting.",
            backstory="This agent coordinates the standup meeting, ensuring all agents perform their roles effectively."
        )

        self.llm = CREWAI_LLM
        self.meet_controller = MeetController()

        self.facilitator_agent =        FacilitatorAgent(name="FacilitatorAgent")
        self.issue_analyzer_agent =     IssueAnalyzerAgent(name="IssueAnalyzerAgent")
        self.context_aggregator_agent = ContextAggregatorAgent(name="ContextAggregatorAgent")
        self.summary_agent =            SummaryAgent(name="SummaryAgent", token=SLACK_TOKEN, channel=SLACK_CHANNEL)
        self.issue_history_agent =      IssueHistoryAgent(name="IssueHistoryAgent", history_file=ISSUE_HISTORY_FILE)
        self.absence_manager_agent =    AbsenceManagerAgent(token=SLACK_TOKEN, slack_channel=SLACK_CHANNEL, date_now=DATE_NOW)

        self.transcripts = {}

    def open_file(self, file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
        
    def write_json_output(self, data, filename):
        path = os.path.join("test/output", filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def participants(self):
        return [
            {"name": "Hadiya Tanveer"},
            {"name": "Arshik Javed"},
            {"name": "Alia Malik"}
        ]
    
    def get_current_participants(self):
        return self.meet_controller.get_current_participants()
        
    def get_transcript(self, name):
        return self.meet_controller.get_transcript(name)
    
    def agent_speak(self, message):
        return self.meet_controller.speak_into_meet(message)
        
    def wait_for_silence(self, name, silence_timeout=9.0, check_interval=2.5):
        last_transcript = self.get_transcript(name)
        last_change_time = time.time()

        while True:
            time.sleep(check_interval)

            current_transcript = self.get_transcript(name)

            # If transcript changed, reset the timer
            if current_transcript != last_transcript:
                last_transcript = current_transcript
                last_change_time = time.time()

            # If no change for silence_timeout seconds, break
            if time.time() - last_change_time >= silence_timeout:
                break

    def prepare_meeting(self, agent_reminder_time, time_to_wait, participants):
        # Thread 01: Login, join meet, wait for participants.
        def run_pre_meeting():
            self.meet_controller.pre_meeting_phase(agent_reminder_time=agent_reminder_time, time_to_wait=time_to_wait)

        # Thread 02: Facilitator and Context Aggregator
        def run_facilitator_and_aggregator():
            self.facilitator_agent.set_participants(participants)
            # self.context_aggregator_agent.run()

        # Create threads
        thread1 = threading.Thread(target=run_pre_meeting)
        thread2 = threading.Thread(target=run_facilitator_and_aggregator)

        # Start threads
        thread1.start();    thread2.start()

        # Wait for both to complete before moving on
        thread1.join();     thread2.join()

    def get_meeting_lines(self, step, participant=None, notes=None):
        messages = [
        {
            "role": "system",
            "content": (
                "You are a professional standup meeting facilitator."
                "Your tone should be polite, confident, and neutral — neither overly enthusiastic nor dull."
                "Respond in plain, concise language."
                "You will be given:"
                "- The current agenda step"
                "- The participant’s name (if relevant)"
                "- Any notes or issues"
                "Your job is to respond with ONE short, conversational sentence appropriate for that step."
                "The sentence must sound natural, professional, and aligned with the context."
                "Do not add new topics or change the meeting flow."
                "Avoid repetition in phrasing by varying expressions when possible."
                "Limit the response to a maximum of 2 sentences if necessary."
            )
        },
        {
            "role": "user",
            "content": (
                f"Current step: {step}\n"
                f"Participant: {participant}\n"
                f"Notes: {notes}\n\n"
                "Examples:\n"
                "GREETING:\n"
                "- Good morning, everyone.\n"
                "- Hi team, I hope you’re doing well.\n"
                "- Hello all, let’s get started.\n\n"
                "PICK_PARTICIPANT:\n"
                f"- Next up is {participant}.\n"
                f"- {participant}, you’re up.\n\n"
                "GOODBYE:\n"
                "- Alright, that’s all for today. Have a great day.\n"
                "- Thanks, everyone. See you tomorrow.\n"
                "- That wraps it up — enjoy the rest of your day.\n\n"
                "Now, generate ONE new professional variation for this step."
            )
        }
    ]

        return self.llm.call(messages=messages)
    
    def meeting_pointers(self, status_message):
        requests.post("http://127.0.0.1:3000/status", json={"status": status_message})

    def run(self):  
        all_participants = self.participants()

        self.prepare_meeting(agent_reminder_time=AGENT_REMINDER_TIME, time_to_wait=TIME_TO_WAIT, participants=all_participants)

        response, duration = self.agent_speak("Hello, this is the agent speaking. I am testing the Voice Animation feature as well as the way the style looks like.")  
        self.meeting_pointers("Agent is speaking.")
        time.sleep(duration + 1)

        self.meeting_pointers("Agent is listening.")

        