import json
from crewai import Agent
from utils.global_variables import CREWAI_LLM

class IssueAnalyzerAgent(Agent):
    def __init__(self, name, *args, **kwargs):
        super().__init__(
            name=name,
            role="Issue Analyzer",
            goal="Analyze issues from team updates, classify them, and take action or record accountability as needed.",
            backstory="This agent receives issues from the Update Collector, determines if they are personal or dependent on others, and responds or records accountability accordingly."
        )

        self.llm = CREWAI_LLM

    def analyze_transcript_issue(self, transcript):
        messages = [
            {
                "role": "system",
                "content": (
                    "You're a helpful assistant for standup meetings.\n"
                    "You will be given a transcript from a team member.\n"
                    "Your task is to identify if the speaker mentioned any issue, and if so, provide a helpful suggestion.\n\n"
                    "Follow these steps:\n"
                    "1. Ignore any irrelevant information or chit-chat.\n"
                    "2. Identify one clear issue from the transcript.\n"
                    "3. Classify it as either:\n"
                    "   - \"personal\" (the speaker can resolve it)\n"
                    "   - \"dependent\" (requires help from someone else)\n"
                    "4. If it's personal, start your response with: \"Regarding your issue about...\", then suggest something helpful.\n"
                    "5. If it's dependent, mention who it's about if possible, and write a helpful message that starts with: \"Regarding your issue about...\".\n\n"
                    "6. If you cannot find any issue, give the person response by commending them minimally.\n\n"
                    "Return ONLY valid JSON. No markdown, no extra text, no commentary.\n"
                    "Use **double quotes** for all keys and values.\n\n"
                    "Example formats:\n"
                    "{\n"
                    "  \"type\": \"personal\",\n"
                    "  \"about\": \"-\",\n"
                    "  \"response\": \"Regarding your issue about connecting to the database, try checking if any background process is using the same port.\"\n"
                    "}\n\n"
                    "{\n"
                    "  \"type\": \"dependent\",\n"
                    "  \"about\": \"Sarah\",\n"
                    "  \"response\": \"Regarding your issue about the API spec, I’ll check with Sarah to see if she can send it today.\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": transcript
            }
        ]
        
        output = self.llm.call(messages=messages)
        return json.loads(output) if output else {}


    def run(self, transcript):
        return self.analyze_transcript_issue(transcript)



