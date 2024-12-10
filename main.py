import json
import google.generativeai as genai
from flask import Flask, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz'

# Your API key setup for Google Gemini
genai.configure(api_key="AIzaSyD7cZ-H5GYzrQQ70-bMM_shl-HGs3Eyrhk")

USERS_FILE = "./users.json"
CHAT_HISTORY_DIR = "./chat_histories"


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as file:
            return json.load(file)
    return {}


# Save users to a file
def save_users(users):
    with open(USERS_FILE, "w") as file:
        json.dump(users, file)

# Check if logged in route
@app.route('/check_login', methods=['GET'])
def check_login():
    if 'username' in session:
        return jsonify({'logged_in': True})
    return jsonify({'logged_in': False})


# Signup route
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    users = load_users()

    if username in users:
        return jsonify({'error': 'Username already exists.'}), 400

    # Save the new user with a hashed password
    users[username] = generate_password_hash(password)
    save_users(users)

    # Create chat history file for the new user
    history_file = f"{CHAT_HISTORY_DIR}/{username}.json"
    with open(history_file, 'w') as f:
        json.dump([], f)  # Initialize with an empty list

    return jsonify({'message': 'User registered successfully!'}), 200


# Login route
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    users = load_users()

    if username not in users or not check_password_hash(
            users[username], password):
        return jsonify({'error': 'Invalid username or password.'}), 401

    # Store the username in the session
    session['username'] = username

    return jsonify({'message': 'Login successful!'}), 200


@app.route('/history', methods=['GET'])
def history():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"}), 401

    username = session['username']
    history_file = f"{CHAT_HISTORY_DIR}/{username}.json"

    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            chat_history = json.load(f)
    else:
        chat_history = []

    return jsonify(chat_history)


@app.route('/save_message', methods=['POST'])
def save_message(bot, user):
    if 'username' not in session:
        return jsonify({"error": "User not logged in"}), 401

    username = session['username']
    history_file = f"{CHAT_HISTORY_DIR}/{username}.json"

    # Load existing history
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            chat_history = json.load(f)

    # Append the new message-response pair
    chat_history.append({"role": "user", "content": user})
    chat_history.append({"role": "bot", "content": bot})

    # Save the updated history
    with open(history_file, 'w') as f:
        json.dump(chat_history, f)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        user_prompt = data.get('prompt')

        # Retrieve the user's chat history from the file system
        username = session.get('username')

        if not username:
            return jsonify({"error": "User not logged in"}), 401

        # Define the path to the user's chat history file
        history_file = f"chat_histories/{username}.json"

        # Load the chat history if the file exists
        if os.path.exists(history_file):
            with open(history_file, 'r') as file:
                chat_history = json.load(file)

        # Generate conversation string
        conversation = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}"
            for msg in chat_history
        ])
        conversation += f"\nUser: {user_prompt}\nAssistant:"

        # Append user's message to chat history

        # Call your AI model with the conversation
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(conversation)
        bot_message = response.text

        # Append AI's response to chat history
        ai_response = bot_message
        human_message = user_prompt

        # Save
        data = request.json
        message = data.get('message')
        response = data.get('response')

        if 'username' not in session:
            return jsonify({"error": "User not logged in"}), 401

        username = session['username']
        history_file = f"{CHAT_HISTORY_DIR}/{username}.json"

        # Load existing history
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                chat_history = json.load(f)

        # Append the new message-response pair
        chat_history.append({"role": "user", "content": human_message})
        chat_history.append({"role": "bot", "content": ai_response})

        # Save the updated history
        with open(history_file, 'w') as f:
            json.dump(chat_history, f)

        return jsonify({"response": bot_message})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/clear-history', methods=['POST'])
def clear_history():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"}), 401

    username = session['username']
    history_file = f"{CHAT_HISTORY_DIR}/{username}.json"

    if os.path.exists(history_file):
        os.remove(history_file)

    return jsonify({"success": True, "message": "History cleared"})

# Logout route
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({"ok": True})


if __name__ == '__main__':
    app.run(debug=True)
