from utils.google_calendar_utils import create_recurring_event

class SchedulerAgent:
    def schedule_event(self, summary, start_time, end_time, recurrence_rule, attendees_emails=None):
        event_link = create_recurring_event(
            summary,
            start_time,
            end_time,
            recurrence_rule,
            attendees_emails=attendees_emails
        )
        
        return event_link