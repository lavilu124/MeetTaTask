#imports
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase
import requests

import time
from datetime import datetime

#app creation
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- FIREBASE CONFIG ---------------- #
# Firebase Web Config (from project settings → SDK setup → Config)
firebase_config = {
    "apiKey": "AIzaSyDl3RLREdxMj1LiKEqtLhRbp0JMXav_M30",
    "authDomain": "tatask-9393c.firebaseapp.com",
    "projectId": "tatask-9393c",
    "databaseURL": "https://tatask-9393c-default-rtdb.firebaseio.com/",
    "storageBucket": "tatask-9393c.appspot.com",
    "messagingSenderId": "229351048156",
    "appId": "1:229351048156:web:31592247707302fa700519"
}


# NASA API Config
NASA_API_KEY = "WhNJKMuqmZONvYHvdbeLeFTJ8H92mrgEbWnYOM3n"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"

# Initialize Pyrebase (for auth)
pb = pyrebase.initialize_app(firebase_config)
pb_auth = pb.auth()

# Initialize Firebase Admin (for Firestore & token verification)
cred = credentials.Certificate("resources/firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

firebase = pyrebase.initialize_app(firebase_config)
rtdb = firebase.database()

# ---------------- useful functions ---------------- #
# Function to get all users except the current user
def get_users():
    try:
        print("Fetching users from Firestore...")  # Debug start
        users_ref = db.collection('users')
        docs = users_ref.stream()

        users = []
        current_user = session.get('user')
        print("Current user:", current_user)

        for doc in docs:
            data = doc.to_dict()
            print("Fetched user:", data)
            if doc.id != current_user:
                users.append(data)

        print("Final users list:", users)
        return users

    except Exception as e:
        print("Error in get_users:", e)
        return []


# ---------------- ROUTES ---------------- #
#main route that sends the user to home
@app.route('/')
def index():
    return redirect(url_for("home"))

#register route
@app.route('/register', methods=["POST", "GET"])
def register():
    #check if the user submitted the form
    if request.method == "POST":
        #if there is no username in the form then it's a sign in request
        if not request.form.get("username"):
            try:
                email = request.form.get("email")
                password = request.form.get("password")
                user = pb_auth.sign_in_with_email_and_password(email, password)
                
                #save data in session
                session['user'] = user['localId']
                session['email'] = email
                session["name"] = db.collection("users").document(user["localId"]).get().to_dict().get("name", "Unknown")
                session['id_token'] = user['idToken']
                return redirect(url_for("home"))
            except Exception as e:
                flash("Invalid email or password", "error")
                return redirect(url_for("register"))
        
        #if there is a username in the form then it's a sign up request
        try:
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            session["name"] = username
            user = pb_auth.create_user_with_email_and_password(email, password)
            
            # Storing additional user info in Firestore
            db.collection("users").document(user["localId"]).set({
                "name": username,
                "email": email
            })
            
            #save data in session
            session['user'] = user['localId']
            session['email'] = email
            session['id_token'] = user['idToken']
            
            return redirect(url_for("home"))
        except Exception as e:
            flash("Invalid email or password", "error")
            return redirect(url_for("register"))
        

    
    return render_template("register.html")


#home route
@app.route('/home', methods=["POST", "GET"])
def home():
    
    #check if the user is logged in
    if 'user' not in session:
        return redirect(url_for('register'))
    
    session["users"] = get_users()
    
    #handle logout
    if request.method == "POST":
        if request.form.get("action") == "logout":
            session.pop('user', None)
            session.pop('email', None)
            return redirect(url_for('register'))
        elif request.form.get("action") == "chat":
            if request.form.get("user") == "random nasa image":
                return redirect(url_for('nasa'))
            user_id = request.form.get("user")
            return redirect(url_for('chat', friend_id=user_id))
    
    return render_template("home.html" , users=session["users"])

#route to get messages
@app.route("/get_messages/<chat_id>")
def get_messages(chat_id):
    id_token = session.get("id_token")

    # Fetch messages from Firebase Realtime DB
    messages_snapshot = rtdb.child("chats").child(chat_id).child("messages").get(token=id_token)

    messages = []
    if messages_snapshot.each():
        for msg in messages_snapshot.each():
            messages.append(msg.val())

    return jsonify(messages)

#route to send messages
@app.route("/send_message/<chat_id>", methods=["POST"])
def send_message(chat_id):
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"status": "error", "message": "Empty message"}), 400

    current_user_id = session.get("user")
    id_token = session.get("id_token")

    rtdb.child("chats").child(chat_id).child("messages").push({
        "sender": session["name"],
        "message": message
    }, token=id_token)

    return jsonify({"status": "success"})


#chat route
@app.route("/chat/<friend_id>", methods=["GET", "POST"])
def chat(friend_id):
    current_user_id = session["user"]
    id_token = session["id_token"]

    # Search friend by name instead of document ID
    print("DEBUG friend_id =", friend_id)
    docs = db.collection("userData").where("name", "==", friend_id).limit(1).get()
    print("DEBUG docs =", docs)

    if docs:
        friend_doc = docs[0].to_dict()
        friend_name = friend_doc.get("name", "Unknown")
        friend_uid = docs[0].id
    else:
        friend_doc = None
        friend_name = "Unknown"
        friend_uid = None

    # Generate chat ID — safer if we use UIDs if available
    chat_id = "_".join(sorted([current_user_id, friend_uid or friend_id]))

    # Check if chat already exists
    chat_ref = rtdb.child("chats").child(chat_id).get(token=id_token)
    if not chat_ref.val():
        name = session["name"]
        rtdb.child("chats").child(chat_id).set({
            "messages": [],
            "participants": [name, friend_id]
        }, token=id_token)

    # Get all messages
    messages_snapshot = rtdb.child("chats").child(chat_id).child("messages").get(token=id_token)
    messages = []
    if messages_snapshot.each():
        for msg in messages_snapshot.each():
            messages.append(msg.val())

    return render_template(
        "chat.html",
        chat_id=chat_id,
        friend_id=friend_id,
        friend_name=friend_name,
        messages=messages
    )


@app.route('/nasa', methods=["GET", "POST"])
def nasa():
    if request.method == "POST":
        return redirect(url_for('home'))
    
    # Fetch NASA APOD data
    response = requests.get(NASA_APOD_URL, params={"api_key": NASA_API_KEY})
    data = response.json()

    # Extract image URL and title
    image_url = data.get("url", "")
    title = data.get("title", "NASA Image")
    explanation = data.get("explanation", "")
    
    return render_template("nasa.html", image_url=image_url, title=title, explanation=explanation)

# checking if this file is the main file
if(__name__ == "__main__"):
    #running the app on local host on port 80 (all adresses) and in debug mode
    app.run(host="0.0.0.0", port=5000, debug=True)