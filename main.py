import flask
from flask import Flask, render_template, request, redirect, session
from flask import send_from_directory
import json
import os
from flask_socketio import SocketIO, send
from pymongo import MongoClient
from flask import flash

app = Flask(__name__)
app.secret_key = "pyc"  # Moved this line up
socketio = SocketIO(app, cors_allowed_origins="*")

mongo = os.getenv("mongodb")

mongodb = mongo

# Initialize MongoDB client and connect to the database
client = MongoClient(mongodb)
db = client["anonium"]
messages_collection = db["messages"]
users_collection = db["users"]


@socketio.on('message')
def handle_message(message):
  print("Message: " + message)
  if message != "User Connected!":
    message_obj = json.loads(message)
    messages_collection.insert_one({
      "username": session['username'],
      "message": message_obj["message"],
      "color": message_obj["color"]
    })
    if messages_collection.count_documents({}) >= 50:
      messages_collection.delete_many({})
    send(message, broadcast=True)

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
      existing_user = users_collection.find_one({"username": username})
      if existing_user:
        error = "Username already taken. Please choose a different one."
        return render_template("signup.html", error=error)
      else:
        post = {'username': username, 'password': password}
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
      if username == "admin":
        if password == "zu1G5ew5MlD68ijY":
          session['admin'] = "valid"
          session['username'] = "admin"
          return redirect("/panel")
      query = {
        'username' : username,
        'password' : password
      }
      existing_user = users_collection.find_one(query)
      if existing_user:
        session['username'] = username
        return redirect('/chat')
      else:
        error = "Account does not exist. Please create a new account first."
        return render_template("signup.html", error=error)
  return render_template("login.html")


@app.route('/del', methods=["POST"])
def delchat():
  if request.method == "POST":
    messages_collection.delete_many({})
    return redirect('/panel')


@app.route('/ban', methods=["POST"])
def ban():
  if request.method == "POST":
    username = request.form.get("banuser")
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
      users_collection.delete_one({'username': username})
      msg = f"Successfully banned {username}."
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


if __name__ == "__main__":
  socketio.run(app, host="0.0.0.0", port=8080)
