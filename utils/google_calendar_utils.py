import os.path
import pickle

import datetime

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('config/google_calendar_credentials.json', SCOPES)
            creds = flow.run_local_server(port=8765)
        with open('config/token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    service = build('calendar', 'v3', credentials=creds)
    return service

def create_recurring_event(summary, start_time, end_time, recurrence_rule, attendees_emails=None):
    service = get_calendar_service()
    event = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': 'UTC'},
        'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        'recurrence': [recurrence_rule],
        'conferenceData': {
            'createRequest': {
                'requestId': 'meet-' + summary.replace(' ', '-'),
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }

    if attendees_emails:
        event['attendees'] = [{'email': email} for email in attendees_emails]
    
    event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
    return event.get('htmlLink')
