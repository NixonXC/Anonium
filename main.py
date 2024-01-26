import flask
from flask import Flask, render_template, request, redirect, session
from flask import send_from_directory
import json
import os
from flask_socketio import SocketIO, send, emit
from pymongo import MongoClient
from flask import flash
import bcrypt

app = Flask(__name__)
app.secret_key = "pyc"  # Moved this line up
socketio = SocketIO(app, cors_allowed_origins="*")

mongodb = os.getenv("mongodb")
# Initialize MongoDB client and connect to the database
client = MongoClient(mongodb)
db = client["anonium"]
messages_collection = db["messages"]
users_collection = db["users"]
coding_messages_collection = db["coding"]
media_messages = db["media"]

@socketio.on('general-message')
def handle_general_message(message):
    print("Message: " + message)
    if message != "User Connected!":
        message_obj = json.loads(message)
        messages_collection.insert_one({
            "username": session['username'],
            "message": message_obj["message"],
            "color": message_obj["color"]
        })
        if messages_collection.count_documents({}) >= 1000:
            messages_collection.delete_many({})
        emit('general-message', message, broadcast=True)

@socketio.on('coding-message')
def handle_coding_message(message):
    print("Message: " + message)
    if message != "User Connected!":
        message_obj = json.loads(message)
        coding_messages_collection.insert_one({
            "username": session['username'],
            "message": message_obj["message"],
            "color": message_obj["color"]
        })
        if coding_messages_collection.count_documents({}) >= 1000:
            coding_messages_collection.delete_many({})
        emit('coding-message', message, broadcast=True)

@socketio.on('media-message')
def handle_media_messages(message):
    print("Message: " + message)
    if message != "User Connected!":
        message_obj = json.loads(message)
        media_messages.insert_one({
            "username": session['username'],
            "message": message_obj["message"],
            "color": message_obj["color"]
        })
        if media_messages.count_documents({}) >= 1000:
            media_messages.delete_many({})
        emit('media-message', message, broadcast=True)

@app.route('/logout')
def logout():
  if 'username' in session:
    session.pop('username', None)
    return redirect('/login')
  else:
    return


@app.route('/favicon.ico')
def favicon():
  return send_from_directory(os.path.join(app.root_path, 'static'),
                             'logo.ico',
                             mimetype='image/vnd.microsoft.icon')


@app.route('/', methods=["GET"])
def root():
  if 'username' in session:
    return redirect('/chat')
  else:
    return redirect('/signup')


@app.route('/signup', methods=["GET", "POST"])
def signup():
    if 'username' in session:
        return redirect('/chat')
    else:
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            existing_user = users_collection.find_one({"username": username})
            if existing_user:
                error = "Username already taken. Please choose a different one."
                return render_template("signup.html", error=error)
            else:
                post = {'username': username, 'password': hashed_password}
                users_collection.insert_one(post)
                session['username'] = username
                return redirect('/chat')
        return render_template("signup.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    if 'username' in session:
        return redirect('/chat')
    else:
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            
            # Check if the user is admin
            if username == "admin":
                admin_user = users_collection.find_one({"username": "admin"})
                if admin_user and bcrypt.checkpw(password.encode('utf-8'), admin_user['password']):
                    session['admin'] = "valid"
                    session['username'] = "admin"
                    return redirect("/panel")
                else:
                    error = "Invalid admin credentials. Please try again."
                    return render_template("login.html", error=error)

            query = {'username': username}
            existing_user = users_collection.find_one(query)
            if existing_user:
                # Compare the hashed password with the provided password
                if bcrypt.checkpw(password.encode('utf-8'), existing_user['password']):
                    session['username'] = username
                    return redirect('/chat')
                else:
                    error = "Invalid password. Please try again."
                    return render_template("login.html", error=error)
            else:
                error = "Account does not exist. Please create a new account first."
                return render_template("signup.html", error=error)
        return render_template("login.html")



@app.route('/del', methods=["POST"])
def delchat():
  if request.method == "POST":
    room = request.form.get('room')
    if room == "general":
        messages_collection.delete_many({})
    elif room == "coding":
        coding_messages_collection.delete_many({})
    elif room == "media":
        media_messages.delete_many({})
    return redirect('/panel')


@app.route('/ban', methods=["POST"])
def ban():
  if request.method == "POST":
    username = request.form.get("banuser")
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
      users_collection.delete_one({'username': username})
      msg = f"Successfully banned {username}"
      return render_template("panel.html", ms=msg)
    else:
      error = "Account does not exist."
      return render_template("panel.html", error=error)

@app.route('/delone', methods=["POST"])
def delone():
  if request.method == "POST":
    msg = request.form.get("msg")
    existing_msg = messages_collection.find_one({"message": msg})
    if existing_msg:
      messages_collection.delete_one({"message": msg})
      return redirect('/panel')
  else:
    return

@app.route('/adminlogout', methods=["POST"])
def adminlogout():
  if 'username' and 'admin' in session:
    session.pop('username', None)
    session.pop('admin', None)
    return redirect('/login')
  else:
    return


@app.route('/panel')
def panel():
  if 'admin' in session:
    return render_template("panel.html")
  else:
    return redirect('/login')


@app.route('/chat')
def chat():
  if 'username' in session:
    messages = list(messages_collection.find().sort("_id", -1))
    messages.reverse()
    return render_template("chat.html", messages=messages)
  else:
    return redirect('/signup')

@app.route('/coding')
def coding():
  if 'username' in session:
    messages = list(coding_messages_collection.find().sort("_id", -1))
    messages.reverse()
    return render_template("coding.html", messages=messages)
  else:
    return redirect('/signup')

@app.route('/media')
def media():
  if 'username' in session:
    messages = list(media_messages.find().sort("_id", -1))
    messages.reverse()
    return render_template("media.html", messages=messages)
  else:
    return redirect('/signup')

if __name__ == "__main__":
  socketio.run(app, host="0.0.0.0", port=8080, debug=True)
