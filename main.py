#imports
from flask import Flask, render_template, redirect, url_for

#main app
app = Flask(__name__)

#main route that sends the user to home
@app.route('/')
def index():
    return redirect(url_for("home"))

#hoem route
@app.route('/home')
def home():
    return render_template("home.html")


# checking if this file is the main file
if(__name__ == "__main__"):
    #running the app on local host on port 80 (all adresses) and in debug mode
    app.run(host="0.0.0.0", port=80, debug=True)