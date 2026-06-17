from slack_sdk import WebClient

class SlackService:
    def __init__(self, token):
        self.token = token      
        self.client = WebClient(token=self.token)
    
    # Send a text message to a channel
    def send_message(self, channel, message, thread_ts=None):
        response = self.client.chat_postMessage(
            channel=channel,
            text=message,
            thread_ts=thread_ts
        )

        return response