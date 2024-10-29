import sys, os, logging
import argparse
import requests
from configparser import ConfigParser
from flask import request, jsonify, Flask

class Subscriber:
    def __init__(self, own_port, webhook_url, critic_url, events) -> None:
        self.own_port = own_port
        self.webhook_url = webhook_url
        self.critic_url = critic_url
        self.events = events
        self.app = Flask(__name__)
        self.setup_routes()
        self.subscribe()
        self.app.run(port=own_port)

    def subscribe(self):
        url = f'{self.critic_url}/subscribe'
        data = {'webhook_url': self.webhook_url, 'events': self.events}
        try:
            response = requests.post(url, json=data)
        except Exception as e:
            print(f"Failed to subscribe to Critic:\n{e}")
            exit()
        return response.json()
    
    def setup_routes(self):
        # override this method to actually do something with the events
        @self.app.route('/', methods=['POST'])
        def receive():
            event = request.json
            print(event)
            return jsonify({'status': 'success'})

if __name__ == '__main__':
    config_path = os.path.join(os.path.dirname(__file__), 'config.txt')
    cfg = ConfigParser()
    cfg.read(config_path)
    cfg = cfg['DEFAULT']
    critic_port = cfg.getint('CRITIC_PORT')
    
    subscriber_port = 5101
    subscriber = Subscriber(own_port=subscriber_port, webhook_url=f'http://localhost:{subscriber_port}', critic_url=f'http://localhost:{critic_port}', events=['crash'])