import datetime
import os
import random
import shutil
import threading
from operator import itemgetter

import webserver
from tinydb import TinyDB, Query
from tinydb.operations import increment
import json
import schedule
import time
import configparser

import openai

config = {
    "username": "",
    "password": "",
    "port": 20452
}


# open config.ini with configparser
def load_config():
    global config
    cfgp = configparser.ConfigParser()
    cfgp.read("config.ini")
    openai.organization = cfgp.get("OpenAPI", "organization")
    openai.api_key = cfgp.get("OpenAPI", "api_key")
    config["username"] = cfgp.get("App", "username")
    config["password"] = cfgp.get("App", "password")
    config["port"] = cfgp.get("App", "port")


def init_db():
    db = TinyDB('./posts.csv', sort_keys=True)
    PostCount = Query()
    try:
        result = db.search(PostCount.count > -1)
        if len(result) == 0:
            print("No object for view count")
            db.insert({"count": 0})
        else:
            print("view count exists")
        return db
    except json.decoder.JSONDecodeError as e:
        print(e)
        return None


def generate_ai_response(message):
    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                              messages=[{"role": "user", "content": message}])
    response = completion["choices"][0]["message"]["content"]
    return response


def post_message(db, message, visibility):
    now = datetime.datetime.now()
    likes = 0
    if visibility == "true":
        likes = random.randint(0, 100)
    else:
        likes = random.randint(0, 25)
    message_obj = {
        "type": "message",
        "message": message,
        "sender": "user",
        "time": now.strftime("%d %b %Y, %I:%M:%S %p"),
        "likes": likes,
        "public": visibility
    }
    db.insert(message_obj)


def insert_response(db, response, visibility):
    now = datetime.datetime.now()
    likes = 0
    if visibility == "true":
        likes = random.randint(0, 100)
    else:
        likes = random.randint(0, 25)
    message_obj = {
        "type": "message",
        "message": response,
        "sender": "ai",
        "time": now.strftime("%d %b %Y, %I:%M:%S %p"),
        "likes": likes,
        "public": visibility
    }
    db.insert(message_obj)


def get_all_messages(db):
    Posts = Query()
    messages = db.search(Posts.type == "message")
    messages = sorted(messages, key=lambda obj: datetime.datetime.strptime(obj["time"], "%d %b %Y, %I:%M:%S %p"))
    return messages


def get_public_messages(db):
    Posts = Query()
    messages = db.search((Posts.type == "message") & (Posts.public == "true"))
    messages = sorted(messages, key=lambda obj: datetime.datetime.strptime(obj["time"], "%d %b %Y, %I:%M:%S %p"))
    return messages


def delete_post_by_timestamp(timestamp):
    Posts = Query()
    timestamp = timestamp[1:-1]
    # time_dt = datetime.datetime.strptime(timestamp, "%d %b %Y, %I:%M:%S %p")
    messages = db.search(Posts.time == timestamp)
    el = db.get(Posts.time == timestamp)
    print(el.doc_id)
    db.remove(doc_ids=[el.doc_id])
    # for msg in messages:
    #    if msg["sender"] == "user":
    #        print("Found it!")
    #        db.remove(msg.doc_id)


def increase_viewcount(db):
    ViewCount = Query()
    if (db):
        db.update(increment('count'), ViewCount.count > -1)
        count = db.search(ViewCount.count > -1)[0]
        return count['count']
    else:
        return 0


# Back up "posts.csv" file every day
def backup_db():
    # Current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Source and destination paths
    source_file = 'posts.csv'
    backup_folder = 'backups'
    destination_file = os.path.join(backup_folder, f'posts_backup_{timestamp}.csv')

    # Create backup folder if it doesn't exist
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    # Copy the file
    shutil.copy(source_file, destination_file)
    print(f'Backup created at: {destination_file}')


def delete_old_backups():
    backup_folder = 'backups'

    # Calculate date two weeks ago
    two_weeks_ago = datetime.now() - datetime.timedelta(weeks=2)

    # Walk through the backup folder
    for root, dirs, files in os.walk(backup_folder):
        for file in files:
            file_path = os.path.join(root, file)
            # Check if file creation time is older than two weeks
            if datetime.fromtimestamp(os.path.getctime(file_path)) < two_weeks_ago:
                os.remove(file_path)
                print(f'Deleted old backup: {file_path}')


def schedule_jobs():
    # Schedule backup to run every day at midnight
    schedule.every().day.at("00:00").do(backup_db)
    # Schedule deletion of old backups to run every day at 1 AM
    schedule.every().day.at("01:00").do(delete_old_backups)

    # Loop for scheduling jobs
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == '__main__':
    load_config()
    db = init_db()
    now = datetime.datetime.now().strftime("%d %b %y, %I:%M:%S %p")
    # post_message(db, "Test message " + now + ", a number: " + str(random.randint(0, 10000)))
    # print(get_all_messages(db))
    schedule_thread = threading.Thread(target=schedule_jobs)
    schedule_thread.start()

    webserver.db = db
    webserver.config = config
    webserver.post_response_function = insert_response
    webserver.get_response = generate_ai_response
    webserver.get_all_messages = get_all_messages
    webserver.get_public_messages = get_public_messages
    webserver.post_function = post_message
    webserver.delete_function = delete_post_by_timestamp
    webserver.increase_viewcount = increase_viewcount
    webserver.run()
