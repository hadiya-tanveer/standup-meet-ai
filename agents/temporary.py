import os
import json
import time
import requests
from threading import Thread

from crewai import Agent

from meeting.meet_controller import MeetController

from agents.summary_agent import SummaryAgent
from agents.facilitator_agent import FacilitatorAgent
from agents.issuehistory_agent import IssueHistoryAgent
from agents.issueanalyzer_agent import IssueAnalyzerAgent
from agents.absencemanager_agent import AbsenceManagerAgent
from agents.contextaggregator_agent import ContextAggregatorAgent

from utils.global_variables import CREWAI_LLM
from utils.global_variables import SLACK_CHANNEL, SLACK_TOKEN, DATE_NOW
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

    def open_file(self, file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
        
    def write_json_output(self, data, filename):
        path = os.path.join("test/output", filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def participants(self):
        return [
            {"name": "Maria"},
            {"name": "Mavra Mehak"}
        ]
    
    def get_current_participants(self):
        return self.meet_controller.get_current_participants()
        
    def get_transcript(self, name):
        return self.meet_controller.get_transcript(name)
    
    def agent_speak(self, message):
        return self.meet_controller.speak_into_meet(message)
        
    def meeting_pointers(self, status_message):
        requests.post("http://127.0.0.1:3000/status", json={"status": status_message})
        
    def wait_for_silence(self, name, silence_timeout=9.0, check_interval=1.0):
        while True:
            transcript = self.get_transcript(name)
            if transcript:  break
            time.sleep(0.5) 

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
            self.context_aggregator_agent.run()

        # Create processes.
        thread1 = Thread(target=run_pre_meeting)
        thread2 = Thread(target=run_facilitator_and_aggregator)

        thread1.start();    thread2.start()
        thread1.join();     thread2.join()

    def run(self): 
        print("[INFO] Orchestrator Agent is starting the standup meeting process...") 
        all_participants = self.participants()

        # ------------ Pre-meeting Phase ------------
        print("[INFO] Starting pre-meeting phase...")
        self.prepare_meeting(AGENT_REMINDER_TIME, TIME_TO_WAIT, all_participants)
        context_aggregator_responses = self.open_file(MEETING_CONVERSATIONS_FILE)

        # ------------ Meeting Phase -----------------
        print("[INFO] Starting meeting phase...")
        self.absence_manager_agent.run(self.get_current_participants(), all_participants)

        response, duration = self.agent_speak(self.get_meeting_lines("GREETING"))  
        self.meeting_pointers("Agent is speaking.")
        time.sleep(duration + 1)  
        
        while self.facilitator_agent.has_participants():
            print("[INFO] Facilitator is picking the next participant...")
            self.meeting_pointers("Picking participant.")
            name = next_participant = self.facilitator_agent.update_queue(self.get_current_participants())
            if not next_participant:    continue
            
            print(f"[INFO] Next participant: {name}")
            self.meeting_pointers("Agent is speaking.")
            response, duration = self.agent_speak(self.get_meeting_lines("PICK_PARTICIPANT", participant=name))
            time.sleep(duration + 1)

            ca_response = next(
                (item['conversation'] for item in context_aggregator_responses if item['name'] == name),
                None
            )

            print(f"[INFO] Context Aggregator response for {name}: {ca_response}")
            response, duration = self.agent_speak(ca_response) 
            time.sleep(duration + 1)
            
            self.meeting_pointers("You may speak now.")
            time.sleep(1.5)  
            self.wait_for_silence(name)

            self.meeting_pointers("Agent is processing transcript.")

            transcript = self.get_transcript(name)
            transcript_text = " ".join(transcript)
            self.transcripts[name] = {  'name': name, 'transcript': transcript_text }

            responses = self.issue_analyzer_agent.run(transcript_text)

            response, duration = self.agent_speak(responses.get('response'))
            self.meeting_pointers("Agent is speaking.")
            time.sleep(duration + 1)


        self.meeting_pointers("Agent is speaking.")
        response, duration = self.agent_speak(self.get_meeting_lines("GOODBYE"))
        time.sleep(duration + 1)
        
        self.meeting_pointers("Meeting ended.")
        self.meet_controller.end_meeting()

        # ----------------------POST-MEETING PHASE----------------------
        # TODO: The Orchestrator Agent will call the Summary Agent.
        summary = self.summary_agent.run(self.transcripts)

        # Integrate IssueHistoryAgent: process Context Aggregator issues and participant transcripts
        context_aggregator_responses = self.open_file(MEETING_CONVERSATIONS_FILE)

        for name, transcript_info in self.transcripts.items():
            name = transcript_info.get('name', name)
            
            # Find Context Aggregator issues for this participant
            ca_entry = next(
                (item for item in context_aggregator_responses if item.get('name') == name),
                None
            )
            issues = ca_entry['issues'] if ca_entry else []
            transcript = transcript_info.get('transcript', None)
            
            if issues:
                issue_history = self.issue_history_agent.run(name, transcript, issues)
            else:
                issue_history = []

        # Write outputs to JSON files in the output directory
        self.write_json_output(issue_history, "issue_history.json")


