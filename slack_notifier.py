import sys, os, logging
import argparse
import requests
from configparser import ConfigParser
from flask import request, jsonify, Flask
from subscriber import Subscriber
import dotenv, os, sys
from datetime import datetime

from slack_sdk.models.attachments import Attachment
from slack_sdk import WebClient

config_path = os.path.join(os.path.dirname(__file__), 'config.txt')
cfg = ConfigParser()
cfg.read(config_path)
cfg = cfg['DEFAULT']
critic_port = cfg.getint("CRITIC_PORT")


class SlackNotifier(Subscriber):
    def __init__(self, own_port, webhook_url, critic_url, events) -> None:
        dotenv.load_dotenv()
        self.slack_token = os.getenv('SLACK_TOKEN')
        self.slack_channel = os.getenv('SLACK_CHANNEL')
        self.slack_client = WebClient(token=self.slack_token)
        super().__init__(own_port, webhook_url, critic_url, events)

    def send(self, message, **kwargs):
        # send message to slack channel
        return self.slack_client.chat_postMessage(channel=self.slack_channel, text=message, **kwargs)
    
    def whisper(self,message,**kwargs):
        user = os.getenv('WHISPER_TO')
        return self.slack_client.chat_postEphemeral(channel=self.slack_channel, text=message, user=user, **kwargs)
    
    def dm(self,message,uid=None,**kwargs):
        user = uid if uid else os.getenv('WHISPER_TO')
        return self.slack_client.chat_postMessage(channel=user, text=message, **kwargs)

    def setup_routes(self):
        @self.app.route('/', methods=['POST'])
        def receive():
            event = request.json
            print(f"Received event: {event}")
            if event['event_type'] == 'crash':
                self.notify_crash(event)
            return jsonify({'status': 'success'})

    def notify_crash(self, event):        
        block = self.make_msg_block(event)
        print("Message success?",self.dm(message=f"*Critic Crash Alert* <@{os.getenv('WHISPER_TO')}>",attachments=block)["ok"])
        # print("Message success?",self.whisper(message=f"*Critic Crash Alert* <@{os.getenv('WHISPER_TO')}>",attachments=block)["ok"])
    
    def make_msg_block(self, event):
        filename = os.path.basename(event['event_src_path'])
        timestamp = datetime.strptime(filename.strip(".txt"),'%Y_%m_%d_%H_%M_%S').strftime('%Y-%m-%d %H:%M:%S UTC')
        dirname = os.path.basename(os.path.dirname(event['event_src_path']))
        message = f"{timestamp}"
        with open(event['event_src_path'], 'r') as f:
            msg = f"{f.read()}"
        message_parts = msg.split("Traceback:")
        message+=f"\n{message_parts[0]}"
        traceback = message_parts[1]
        # return Attachment(text=traceback, pretext=message, color="#36a64f",title="Traceback").to_dict()
        return [
            {"color": "#E01E5A",
             "blocks":[{
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Crash Alert: {dirname}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{message}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Traceback*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{traceback}"
                }
            }]}
        ]


if __name__ == '__main__':
    subscriber_port = 5101
    subscriber = SlackNotifier(own_port=subscriber_port, webhook_url=f'http://localhost:{subscriber_port}', critic_url=f'http://localhost:{critic_port}', events=['crash'])