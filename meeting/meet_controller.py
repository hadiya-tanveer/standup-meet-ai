import os
import time
import json
import base64
import random
import requests
import subprocess
import io

from pydub.utils import mediainfo
import pyttsx3

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.global_variables import ACTIVE_PARTICIPANTS_FILE, TRANSCRIPTS_FILE
from utils.global_variables import GOOGLE_EMAIL, GOOGLE_PASSWORD, GOOGLE_MEET_LINK, RECALL_API_KEY, NGROK_AUTH_TOKEN, WEBHOOK_URL, TTS_MODEL

class MeetController:
    def __init__(self):
        self.driver = self.configure_driver()

        self.bot_id = None
        
        self.google_email = GOOGLE_EMAIL
        self.google_password = GOOGLE_PASSWORD
        
        self.meeting_url = GOOGLE_MEET_LINK
        self.recall_api_key = RECALL_API_KEY
        self.ngrok_auth_token = NGROK_AUTH_TOKEN

        self.webhook_url = WEBHOOK_URL

    def configure_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        # Set preferences to allow microphone and camera permissions
        prefs = {
            "profile.default_content_setting_values.media_stream_camera": 1,  
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.geolocation": 0,     
            "profile.default_content_setting_values.notifications":  0
        }
        options.add_experimental_option("prefs", prefs)

        driver = uc.Chrome(options=options)
        return driver

    def login_to_google(self):
        # Navigate to Google login page
        self.driver.get("https://accounts.google.com/signin")

        # Wait for the email input field to be visible and enter the email
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        ).send_keys(self.google_email + Keys.RETURN)

        # Wait for the password input field to be visible and enter the password
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//input[@type="password"]'))
        ).send_keys(self.google_password + Keys.RETURN)

        # Wait for the login to complete and the URL to change
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("myaccount.google.com")
        )

    def join_google_meet(self):
        # Navigate to the Google Meet link
        self.driver.get(self.meeting_url)

        # Wait for the "Join now" button to be visible and click it
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Join now']"))
        ).click()

        self.toggle_camera()
        self.toggle_microphone()

    def toggle_camera(self):
        body = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body.send_keys(Keys.CONTROL + "e")

    def toggle_microphone(self):
        body = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body.send_keys(Keys.CONTROL + "d")

    def start_transcription_bot(self, webhook_port=3000):
        with open("silence.mp3", "rb") as f:
            silent_audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        headers = {
            "Authorization": f"Token {self.recall_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "meeting_url": self.meeting_url,
            "bot_name": "Bloopin's Buddy",
            "recording_config": {
                "transcript": {
                    "provider": {
                        "assembly_ai_v3_streaming": {
                            "speech_model": "universal-streaming-english"
                        }
                    }
                },
                "realtime_endpoints": [
                    {
                        "type": "webhook",
                        "url": f"{self.webhook_url}/api/webhook/recall/transcript",
                        "events": ["transcript.data", "participant_events.join", "participant_events.leave"]
                    }
                ]
            },
            "automatic_audio_output": {
                "in_call_recording": {
                    "data": {
                        "kind": "mp3",
                        "b64_data": silent_audio_b64
                    }
                }
            },
            "output_media": {
                "camera": {
                    "kind": "webpage",
                    "config": { "url": self.webhook_url  }
                }
            }
        }

        response = requests.post("https://us-west-2.recall.ai/api/v1/bot", headers=headers, json=payload)
        
        if response.status_code == 201:
            bot_id = response.json().get("id")
            self.bot_id = bot_id
            print(f"[INFO] Bot started successfully with ID: {bot_id}")
        else:
            print(f"[ERROR] Failed to start bot: {response.text}")
    
    def send_output_audio(self, audio_file_path):
        headers = {
            "Authorization": f"Token {self.recall_api_key}",
            "Content-Type": "application/json"
        }

        # Read audio and encode to base64
        with open(audio_file_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "kind": "mp3",
            "b64_data": audio_base64
        }

        url = f"https://us-west-2.recall.ai/api/v1/bot/{self.bot_id}/output_audio"
        response = requests.post(url, headers=headers, json=payload)
        return response
    
    # TODO: Generate audios for this part.
    def wait_for_participants(self, agent_reminder_time, time_to_wait):
        last_reminder_time = start_time = time.time()

        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            if elapsed >= time_to_wait:
                print("[INFO] Timeout reached. Proceeding.")
                break

            if current_time - last_reminder_time >= agent_reminder_time:                
                response, duration = self.speak_into_meet('Waiting for participants to join the meeting.')
                time.sleep(duration + 1)  
                last_reminder_time = current_time

            time.sleep(3) 

    def speak_into_meet(self, text=None, output_audio_file="test/audio_files/output.mp3"):
        engine = pyttsx3.init()
        
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        
        # pyttsx3 may create WAV instead of MP3, so use WAV first
        wav_file = output_audio_file.replace('.mp3', '.wav')
        engine.save_to_file(text, wav_file)
        engine.runAndWait()
        
        # Convert WAV to MP3 using ffmpeg
        try:
            subprocess.run([
                'ffmpeg', '-i', wav_file, '-q:a', '9', '-y', output_audio_file
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to convert audio: {e}")
            return None, 0
        
        # Verify file exists and get duration
        if not os.path.exists(output_audio_file):
            print(f"[ERROR] Audio file not created: {output_audio_file}")
            return None, 0
        
        try:
            response = self.send_output_audio(output_audio_file)
            info = mediainfo(output_audio_file)
            duration = float(info['duration'])
            print(f"[INFO] Audio sent successfully. Duration: {duration}s")
            return response, duration
        except Exception as e:
            print(f"[ERROR] Failed to send audio: {e}")
            return None, 0

    def end_meeting(self):
        leave_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Leave call' or @aria-label='Leave meeting']")
            )
        )
        
        leave_button.click()

    def get_current_participants(self):
        if not os.path.exists(ACTIVE_PARTICIPANTS_FILE):
            return {} 
        
        with open(ACTIVE_PARTICIPANTS_FILE, "r") as f:
                return json.load(f)
        
    def get_transcript(self, name):
        if not os.path.exists(TRANSCRIPTS_FILE):    return []
        
        with open(TRANSCRIPTS_FILE, "r") as f:
                transcripts = json.load(f)
                
        return transcripts.get(name, [])
    
    def get_driver(self):
        return self.driver

    def pre_meeting_phase(self, agent_reminder_time, time_to_wait, webhook_port=3000):
        # 1. Log in to Google.
        self.login_to_google()

        # 2. Join the Google Meet.
        self.join_google_meet()

        # 3. Start the transcription bot.
        self.start_transcription_bot(webhook_port)
        time.sleep(8)
        
        # 4. Wait for participants to join.
        self.wait_for_participants(agent_reminder_time=agent_reminder_time, time_to_wait=time_to_wait)