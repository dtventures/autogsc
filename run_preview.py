from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("home_v2.html")

if __name__ == "__main__":
    print("Running preview on http://localhost:5001")
    app.run(debug=True, port=5001)
