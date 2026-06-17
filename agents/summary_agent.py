import json
from mdutils.mdutils import MdUtils

from crewai import Agent

from utils.slack_service import SlackService
from utils.global_variables import CREWAI_LLM, DATE_NOW

class SummaryAgent(Agent):
    def __init__(self, name, token, channel, *args, **kwargs):
        super().__init__(
            name=name,
            role="Summary Agent",
            goal="Summarize each participant's standup transcript, highlighting work planned, work done, and blockers.",
            backstory="This agent receives all participant transcripts and produces a readable summary for each, suitable for later review."
        )

        object.__setattr__(self, "llm", CREWAI_LLM)
        object.__setattr__(self, "date", DATE_NOW)
        
        object.__setattr__(self, "slack_token", token)
        object.__setattr__(self, "slack_channel", channel)
        object.__setattr__(self, "slack_service", SlackService(token))

        object.__setattr__(self, "md", MdUtils(file_name="standup_summary"))

    def summarize_transcript(self, name, transcript):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant summarizing individual updates from a standup meeting.\n"
                    "You will receive a transcript from one participant.\n\n"
                    "Your task is to extract only the meaningful work-related content and organize it into the following JSON format:\n\n"
                    "{\n"
                    '  "name": "[Speaker Name]",\n'
                    '  "done": ["Task 1", "Task 2", ...],\n'
                    '  "plan_to_do": ["Task 1", "Task 2", ...],\n'
                    '  "issues": ["Issue 1", "Issue 2", ...]\n'
                    "}\n\n"
                    "**Each list item must be grammatically correct (first letter captialized) but does not need to be a full sentence.**\n"
                    "**Ignore any unrelated chatter, greetings, or small talk. Focus only on work-related updates.**\n"
                    "Do not include markdown, explanations, or any text, examples from your own outside the JSON object."
                )
            },

            {
                "role": "user",
                "content": (
                    f"Here is the transcript for {name}:\n\n{transcript}\n\n"
                    "Summarize it as instructed."
                )
            }
        ]

        raw_response = self.llm.call(messages=messages)
        return json.loads(raw_response)
    
    def combine_summaries(self, summaries):
        participant_blocks = []
        for summary in summaries.values():
            name = summary.get("name")
            done = summary.get("done");     plan = summary.get("plan_to_do");       issues = summary.get("issues")

            block = f"{name}:\n"
            if done:
                block += "  Done:\n" + "".join(f"    - {item}\n" for item in done)
            if plan:
                block += "  Plan to Do:\n" + "".join(f"    - {item}\n" for item in plan)
            if issues:
                block += "  Issues:\n" + "".join(f"    - {item}\n" for item in issues)
            
            participant_blocks.append(block)

        combined_input = "\n\n".join(participant_blocks)
        return combined_input

    def summarize_overall_meeting(self, combined_input):       
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert meeting assistant. Based on structured standup summaries from each team member, "
                    "generate a professional meeting summary in bullet point format (•). The summary should:\n"
                    "Be concise and informative (5–6 bullet points max)\n"
                    "Use proper full sentences\n"
                    "Mention the person's name when describing what they did, plan to do, or are blocked by\n"
                    "Cover completed work, upcoming plans, and issues from across the team\n"
                    "Avoid any extra commentary or introductory/closing lines."
                )
            },

            {
                "role": "user",
                "content": (
                    "Here are the summaries from each participant:\n\n"
                    f"{combined_input}\n\n"
                    "Write a bullet point summary as instructed."
                )
            }
        ]

        return self.llm.call(messages=messages)

    
    def construct_summary(self, summaries, overall_summary):
        self.md.new_paragraph(f":clipboard: *Meeting Summary*")
        self.md.new_paragraph(f"*Date:* [{DATE_NOW}]")

        attendees_str = ", ".join(sorted(summaries.keys()))
        self.md.new_paragraph(f"*Attendees:* [{attendees_str}]")
        self.md.new_line()

        self.md.new_paragraph(":pushpin: *Meeting Recap: *")
        self.md.new_paragraph(overall_summary.strip())
        self.md.new_line()

        self.md.new_paragraph("*Attendees Recap: *")
        for i, summary in enumerate(summaries.values(), start=1):
            name = summary.get("name", "Unknown")
            done = summary.get("done", [])
            plan = summary.get("plan_to_do", [])
            issues = summary.get("issues", [])

            done_str = ", ".join(done) if done else "No items"
            plan_str = ", ".join(plan) if plan else "No items"
            issues_str = ", ".join(issues) if issues else "No items"

            # Add the participant's name and updates
            self.md.new_paragraph(f"{i}. *{name}*  ")
            self.md.new_paragraph(f"   _Did:_ {done_str} ")
            self.md.new_paragraph(f"   _Plans to Do:_ {plan_str}  ")
            self.md.new_paragraph(f"   _Issues:_ {issues_str}  ")
            
            self.md.new_line()

        return self.md.get_md_text()

    def run(self, transcripts_dict):
        summaries = {}

        for name, info in transcripts_dict.items():
            transcript = info.get('transcript', '')
            
            summary = self.summarize_transcript(name, transcript)
            summaries[name] = summary
        
        combined_input = self.combine_summaries(summaries)
        overall_summary = self.summarize_overall_meeting(combined_input)

        slack_summary = self.construct_summary(summaries, overall_summary)
        
        # Send to Slack if token and channel provided
        if self.slack_token and self.slack_channel:
            self.slack_service.send_message(channel=self.slack_channel, message=slack_summary)