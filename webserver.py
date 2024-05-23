import base64
import json
import os
import uuid

from flask import Flask, render_template, request, url_for, send_from_directory, session

app = Flask(__name__, static_folder="./static", template_folder="./templates")
app.config['host'] = '0.0.0.0'
app.config['IGNORE_RELOADER'] = "posts.json"
app.secret_key = "asdkhaskjdhkajsdh213"
#app.add_url_rule('/favicon.ico',
#                 redirect_to=url_for('static', filename='favicon.ico'))

db = None
post_function = None
post_response_function = None
get_all_messages = None
get_public_messages = None
get_response = None
delete_function = None
increase_viewcount = None
config = None
logged_in_uuid = ""

@app.route('/')
def index():
    global db
    count = 0
    if callable(increase_viewcount):
        count = increase_viewcount(db)
    username = config["username"]
    # set first character of username to upper case
    username = username[0].upper() + username[1:]
    return render_template('index.html', username=username, viewcount=count)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/get_messages")
def get_messages():
    global get_all_messages
    global get_public_messages
    global db
    uuid = request.args.get("uuid")
    if uuid == logged_in_uuid and uuid != "":
        msgs = get_all_messages(db)
        return json.dumps(msgs)
    else:
        msgs = get_public_messages(db)
        return json.dumps(msgs)

# get logged in sesison
@app.route("/get_logged_in")
def get_logged_in():
    if session.get("logged_in"):
        # return json string { "success": true, "session_token": a random uuid }
        return json.dumps({"success": True, "session_token": session.get("logged_in_user")})
    else:
        return json.dumps({"success": False})


# flask /login with username and password fields
@app.route('/login', methods=['GET', 'POST'])
def login():
    global logged_in_uuid
    error = None
    if request.method == 'POST':
        if request.form['username'] != config["username"] or request.form['password'] != config["password"]:
            error = 'Invalid Credentials. Please try again.'
            return json.dumps({"success": False})
        else:
            logged_in_uuid = str(uuid.uuid4())
            session["logged_in_user"] = request.form["username"]
            session["logged_in_uuid"] = logged_in_uuid
            return json.dumps({"success": True, "session_token": logged_in_uuid})
    return json.dumps({"success": False})

# logout
@app.route("/logout")
def logout():
    global logged_in_uuid
    session.pop("logged_in", None)
    session.pop("logged_in_user", None)
    logged_in_uuid = ""
    return "success"

@app.route("/check_uuid")
def check_uuid():
    global logged_in_uuid
    print(logged_in_uuid)
    uuid = request.args.get("uuid")
    if uuid == "":
        return json.dumps({"success": False})
    if uuid == logged_in_uuid:
        return json.dumps({"success": True})
    else:
        return json.dumps({"success": False})

@app.route("/post_message")
def post_message():
    global db
    global post_function
    message_b64 = request.args.get("message")
    response_enabled = request.args.get("response")
    visibility = request.args.get("public")
    message_str = base64.b64decode(message_b64).decode('utf-8')
    response = ""
    print(response_enabled)
    # ChatGPT
    if response_enabled == "true":
        response = get_response(message_str)
    print("Received: " + str(message_str))
    # Is a message
    if message_str != b'undefined':
        post_function(db, message_str, visibility)
        if response_enabled == "true":
            post_response_function(db, response, visibility)
        return "success"
    else:
        return "fail"


@app.route("/delete_timestamp")
def delete_timestamp():
    timestamp_str = request.args.get("timestamp")
    print("Deleting: " + timestamp_str)
    delete_function(timestamp_str)
    return "success"


def run():
    app.run(debug=True, port=20452, host="0.0.0.0")