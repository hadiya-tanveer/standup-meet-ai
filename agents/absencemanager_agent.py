from datetime import datetime
from utils.slack_service import SlackService
from utils.global_variables import GOOGLE_MEET_LINK

class AbsenceManagerAgent():
    def __init__(self, token, slack_channel, date_now):
        self.slack_token = token
        self.slack_channel = slack_channel
        self.slack_service = SlackService(self.slack_token)

        self.today = date_now

    def find_absent_participants(self, current_participants, actual_participants):
        current_emails = {p["name"] for p in current_participants}
        missing_participants = [p for p in actual_participants if p["name"] not in current_emails]
        return missing_participants
    
    def construct_message(self, absent_participants, today):
        message = "📌 *Absence Reminder*\n\n"

        # List all absent participants
        message += "*Absent Participants:*\n"
        for participant in absent_participants:
            message += f"• {participant}\n"

        message += "\n📣 *Notice:*\n"
        message += f"You are kindly requested to join the daily standup meeting scheduled for *{today}*.\n"
        message += f"Meeting Link: [Join Meeting] {GOOGLE_MEET_LINK}\n"

        return message

    def send_reminder(self, absent_participants):
        absent_names = [participant['name'] for participant in absent_participants]
        
        # If no absent participants, return early.
        if not absent_names:    return

        absent_message = self.construct_message(absent_names, self.today)
        
        if self.slack_token and self.slack_channel:
            self.slack_service.send_message(channel=self.slack_channel, message=absent_message)
            
    def run(self, current_participants, actual_participants):
        absent_participants = self.find_absent_participants(current_participants, actual_participants)
        self.send_reminder(absent_participants)