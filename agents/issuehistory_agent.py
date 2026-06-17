import os
import re
import json
from datetime import datetime

from crewai import Agent
from typing import List, Any, Optional
from utils.global_variables import CREWAI_LLM, DATE_NOW


class IssueHistoryAgent(Agent):
    issues: List[Any] = []  
    history_file: Optional[str] = None

    def __init__(self, name="Issue History Agent", history_file=None, *args, **kwargs):
        super().__init__(
            name=name,
            role="Issue History Agent",
            goal="Track and manage unresolved issues from standup meetings, updating their status based on participant responses.",
            backstory="This agent maintains a history of issues raised during standup meetings and determines when issues have been addressed based on participant transcripts."
        )
        
        object.__setattr__(self, "date", DATE_NOW)
        object.__setattr__(self, "llm", CREWAI_LLM)
        
        self.issues = []
        self.history_file = history_file

    # Format the issue text to string.
    def _format_issue_text(self, issue_text):
            task_id = issue_text[0]
            task_summary = issue_text[1]
            llm_response = issue_text[2]
            return f"{task_id}: {task_summary} - {llm_response}"

    # Add new issues for a person to the issue history, if not already present.
    def add_issues_for_person(self, person, issues_list):
        for issue in issues_list:
            issue_text = issue
            
            # Check if this issue is already in history.
            if not any(history.get('person') == person and history.get('issue_text') == issue_text for history in self.issues):
                self.issues.append({
                    'person': person,
                    'issue_text': issue_text,
                    'date': self.date,
                    'responded': False
                })
        
        return self.issues

    # Update the status of unresolved issues for a person based on their transcript.
    def update_responded_status(self, person, transcript):
        # Gather all unresolved issues for this person.
        unresolved_issues = [
            issue for issue in self.issues 
            if issue.get('person') == person and not issue.get('responded')
        ]
        
        if not unresolved_issues:
            return self.issues
            
        # Create a numbered list string of issues
        issues_list_str = "\n".join([
            f"{i+1}. {self._format_issue_text(issue['issue_text'])}" 
            for i, issue in enumerate(unresolved_issues)
        ])
        
        prompt = (
            "You are an assistant for a standup meeting.\n"
            "Here is a participant's transcript and a list of their unresolved issues.\n\n"
            f"Transcript:\n{transcript}\n\n"
            f"Issues:\n{issues_list_str}\n\n"
            "Which of these issues does the transcript address, mention, or resolve?\n"
            "Respond with a JSON array of the numbers of the addressed issues (e.g., [1, 3]).\n"
            "Do not include any explanation or extra text."
        )
        
        response = self.llm.call(prompt)
        
        # Parse the response to find addressed issues
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            indices = json.loads(match.group(0))
            for idx in indices:
                if 1 <= idx <= len(unresolved_issues):
                    unresolved_issues[idx-1]['responded'] = True
        
        return unresolved_issues

    # Main method to process issues for a person.
    def run(self, name, transcript, issues):
        # Load or initialize issue history
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as f:
                self.issues = json.load(f)

        self.issues = self.add_issues_for_person(name, issues)
        self.issues = self.update_responded_status(name, transcript)
        return self.issues