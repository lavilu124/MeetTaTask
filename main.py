#imports
from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase

#app creation
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- FIREBASE CONFIG ---------------- #
# Firebase Web Config (from project settings → SDK setup → Config)
firebase_config = {
    "apiKey": "AIzaSyDl3RLREdxMj1LiKEqtLhRbp0JMXav_M30",
    "authDomain": "tatask-9393c.firebaseapp.com",
    "projectId": "tatask-9393c",
    "databaseURL": "https://tatask-9393c.firebaseio.com",
    "storageBucket": "tatask-9393c.appspot.com",
    "messagingSenderId": "229351048156",
    "appId": "1:229351048156:web:31592247707302fa700519"
}

# Initialize Pyrebase (for auth)
pb = pyrebase.initialize_app(firebase_config)
pb_auth = pb.auth()

# Initialize Firebase Admin (for Firestore & token verification)
cred = credentials.Certificate("resources/firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- useful functions ---------------- #
# Function to get all users except the current user
def get_users():
    users_ref = db.collection('users')
    docs = users_ref.stream()
    users = []
    for doc in docs:
        if doc.id != session.get('user'):  # Exclude current user
            users.append(doc.to_dict())
    return users

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
                return redirect(url_for("home"))
            except Exception as e:
                flash("Invalid email or password", "error")
                return redirect(url_for("register"))
        
        #if there is a username in the form then it's a sign up request
        try:
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            user = pb_auth.create_user_with_email_and_password(email, password)
            
            # Storing additional user info in Firestore
            db.collection("users").document(user["localId"]).set({
                "name": username,
                "email": email
            })
            
            #save data in session
            session['user'] = user['localId']
            session['email'] = email
            
            return redirect(url_for("home"))
        except Exception as e:
            flash("Invalid email or password", "error")
            return redirect(url_for("register"))
        

    
    return render_template("register.html")


#home route
@app.route('/home', methods=["POST", "GET"])
def home():
    
    session["users"] = get_users()
    
    #check if the user is logged in
    if 'user' not in session:
        return redirect(url_for('register'))
    
    #handle logout
    if request.method == "POST":
        if request.form.get("action") == "logout":
            session.pop('user', None)
            session.pop('email', None)
            return redirect(url_for('register'))
        elif request.form.get("action") == "chat":
            user_id = request.form.get("user")
            return redirect(url_for('chat', user_id=user_id))
    
    return render_template("home.html" , users=session["users"])


@app.route('/chat/<user_id>')
def chat(user_id):
    return f"Chat with user {user_id}"

# checking if this file is the main file
if(__name__ == "__main__"):
    #running the app on local host on port 80 (all adresses) and in debug mode
    app.run(host="0.0.0.0", port=5000, debug=True)