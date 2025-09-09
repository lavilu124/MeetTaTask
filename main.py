#imports
from flask import Flask, render_template, request, redirect, url_for

#app creation
app = Flask(__name__)
app.secret_key = "supersecretkey"

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
            email = request.form.get("email")
            password = request.form.get("password")
            return redirect(url_for("home"))
        
        #if there is a username in the form then it's a sign up request
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        return redirect(url_for("home"))
    
    return render_template("register.html")


#hoem route
@app.route('/home')
def home():
    return render_template("home.html")


# checking if this file is the main file
if(__name__ == "__main__"):
    #running the app on local host on port 80 (all adresses) and in debug mode
    app.run(host="0.0.0.0", port=80, debug=True)