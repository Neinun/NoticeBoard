import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_bcrypt import Bcrypt
import jwt # PyJWT library
from functools import wraps

# --- Initialization ---
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = 'a-very-secret-key-that-you-should-change' # CHANGE THIS!
bcrypt = Bcrypt(app)

NOTICES_FILE = os.path.join(app.root_path, 'notices.json')
USERS_FILE = os.path.join(app.root_path, 'users.json')

# --- Helper Functions ---
def read_json_file(filepath):
    """Reads data from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_json_file(filepath, data):
    """Writes data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

# --- Authentication Middleware ---
def token_required(f):
    """A decorator to protect routes that require a valid token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check for token in the 'Authorization' header
        if 'Authorization' in request.headers:
            # Expected format: "Bearer <token>"
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            # Decode the token to get user data
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # We only care about the role for authorization here
            if data.get('role') != 'Admin':
                 return jsonify({'message': 'Admin role required!'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(*args, **kwargs)
    return decorated


# --- API Endpoints ---

# POST /api/login
# Handles user login and returns a JWT on success.
@app.route('/api/login', methods=['POST'])
def login():
    """Authenticates a user and returns a token."""
    print('POST /api/login - Attempting user login')
    auth = request.get_json()
    if not auth or not auth.get('username') or not auth.get('password'):
        return jsonify({'message': 'Could not verify'}), 401

    users = read_json_file(USERS_FILE)
    user = next((u for u in users if u['username'] == auth['username']), None)

    if not user:
        return jsonify({'message': 'User not found!'}), 401

    if bcrypt.check_password_hash(user['passwordHash'], auth['password']):
        # Password is correct, generate a token
        token = jwt.encode({
            'username': user['username'],
            'role': user['role'],
            'exp': time.time() + 86400 # Token expires in 24 hours
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({'token': token, 'role': user['role']})

    return jsonify({'message': 'Could not verify! Wrong password.'}), 401


# GET /api/notices (Public)
# This route is public and does not require a token.
@app.route('/api/notices', methods=['GET'])
def get_notices():
    """Reads all notices from the JSON file and sends them to the client."""
    print('GET /api/notices - Fetching all notices')
    notices = read_json_file(NOTICES_FILE)
    return jsonify(notices)

# POST /api/notices/add (Protected)
# This route now requires a valid admin token.
@app.route('/api/notices/add', methods=['POST'])
@token_required
def add_notice():
    """Adds a new notice to the JSON file."""
    print('POST /api/notices/add - Adding a new notice (Admin Only)')
    new_notice = request.get_json()
    notices = read_json_file(NOTICES_FILE)
    new_notice['id'] = int(time.time() * 1000)
    notices.append(new_notice)
    write_json_file(NOTICES_FILE, notices)
    return jsonify(new_notice), 201

# POST /api/notices/delete (Protected)
# This route now requires a valid admin token.
@app.route('/api/notices/delete', methods=['POST'])
@token_required
def delete_notice():
    """Deletes a notice by its ID."""
    print('POST /api/notices/delete - Deleting a notice (Admin Only)')
    data = request.get_json()
    notice_id_to_delete = data.get('id')
    notices = read_json_file(NOTICES_FILE)
    initial_length = len(notices)
    notices = [n for n in notices if n.get('id') != notice_id_to_delete]
    
    if len(notices) < initial_length:
        write_json_file(NOTICES_FILE, notices)
        return jsonify({'message': 'Notice deleted successfully.'}), 200
    else:
        return jsonify({'message': 'Notice not found.'}), 404

# --- Static File Serving ---
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.root_path, filename)

@app.route('/')
def serve_index():
    return send_from_directory(app.root_path, 'notice-board.html')

# --- Start the Server ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
