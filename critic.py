# Sage Santomenna 2024

import sys, os, logging
import queue, threading
import json, requests, socket
from flask import request, jsonify, Flask
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from configparser import ConfigParser
from threading import Thread, Event

config_path = os.path.join(os.path.dirname(__file__), 'config.txt')
cfg = ConfigParser()
cfg.read(config_path)
cfg = cfg['DEFAULT']

app = Flask(__name__)
crash_event_queue = queue.Queue()
subscribers = {}
subscribed_to = {}
lock = threading.Lock()

queues = [crash_event_queue]

class CrashEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        crash_event_queue.put({"event_type": "crash", 'src_path': event.src_path})

@app.route('/subscribe', methods=['POST'])
def subscribe():
    subscriber = request.json["webhook_url"]
    subscribed_events = request.json["events"]
    with lock:
        for subscribed_event in subscribed_events:
            if subscribed_event not in subscribers:
                subscribers[subscribed_event] = []
            subscribers[subscribed_event].append(subscriber)
            subscribers[subscribed_event] = list(set(subscribers[subscribed_event]))
        if subscriber not in subscribed_to:
            subscribed_to[subscriber] = []
        subscribed_to[subscriber].extend(subscribed_events)
        subscribed_to[subscriber] = list(set(subscribed_to[subscriber]))
    print(f"Got subscription request from {subscriber} for events {subscribed_events}")
    print(f"Subscribers: {subscribers}")
    return jsonify({'status': 'success'})

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    subscriber = request.json["webhook_url"]
    with lock:
        for subscribed_event in subscribed_to[subscriber]:
            del subscribers[subscribed_event]
        del subscribed_to[subscriber]
    return jsonify({'status': 'success'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

def publish(stop_event):
    while True:
        if stop_event.is_set():
            return
        for event_queue in queues:
            try:
                event = event_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            event_type = event["event_type"]
            event_src_path = event["src_path"]
            event = {'event_type': event_type, 'event_src_path': event_src_path}
            notify(event)

def format_msg(event):
    event_type = event['event_type']
    event_src_path = event['event_src_path']
    msg = f'Event type: {event_type}, Event source path: {event_src_path}'
    return msg

def notify(event):
    msg = format_msg(event)
    event["payload"] = msg
    print(f"Notifying subscribers of event: {event}")
    with lock:
        for subscriber in subscribers.get(event['event_type'], []):
            try:
                requests.post(subscriber, json=event)
            except:
                logging.error('Failed to notify subscriber %s', subscriber['url'])

def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def find_available_port(start_port, end_port):
    for port in range(start_port, end_port):
        if is_port_available(port):
            return port
    return None

if __name__ == "__main__":
    port = cfg.getint('CRITIC_PORT')

    # parser = argparse.ArgumentParser()
    # parser.add_argument('watch_dir', help='Directory to watch for file events')
    # args = parser.parse_args()

    watch_dir = cfg['WATCH_DIR']

    if not os.path.isdir(watch_dir):
        logging.error('Invalid directory: %s', watch_dir)
        sys.exit(1)

    logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    observer = Observer()
    observer.schedule(CrashEventHandler(), path=watch_dir, recursive=True)
    observer.start()
    logger.info('Watching directory: %s', watch_dir)

    logger.info('Starting publisher thread')
    stop_event = Event()        
    publish_thread = Thread(target=publish, args=(stop_event,))
    publish_thread.start()
    logger.info('Starting critic server on port %d', port)
    app.run(port=port)
    logger.info('Shutting down...')
    observer.stop()
    observer.join()
    logger.info('Observer stopped')
    stop_event.set()
    publish_thread.join()
    logger.info('Publisher stopped')
    logger.info('All done!')