from flask import Flask, request, jsonify, render_template
from main import handle_user_query
import threading
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

def warm_up_chatbot():
    try:
        print("🔄 Warming up chatbot...")
        handle_user_query("warm up", is_voice=True)
    except Exception as e:
        print(f"⚠️ Warm-up failed: {e}")

def run_startup_once():
    if not hasattr(app, "has_run"):
        app.has_run = True
        threading.Thread(target=warm_up_chatbot).start()

@app.before_request
def before_request():
    run_startup_once()

@app.route("/")
def index():
    return render_template("interface.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        user_message = data.get("message", "").strip()
        app.logger.debug(f"Received chat request: {user_message}")

        if not user_message:
            return jsonify({"response": "Please say something!"})

        response = handle_user_query(user_message, is_voice=True)
        app.logger.debug(f"Sending response: {response}")
        return jsonify({"response": response})
    except Exception as e:
        app.logger.error(f"Error in /chat route: {e}", exc_info=True)
        return jsonify({"response": "Sorry, something went wrong. Please try again."})

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    print("✅ Starting Flask server...")
    warm_up_chatbot()
    app.run(debug=True, threaded=True)