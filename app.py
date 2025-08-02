import os
import json
from flask import Flask, request, jsonify, send_from_directory

# --- Initialization ---
app = Flask(__name__, static_folder='.', static_url_path='')
NOTICES_FILE = os.path.join(app.root_path, 'notices.json')

# --- Helper Functions ---
def read_notices():
    """Reads the notices from the JSON file."""
    try:
        with open(NOTICES_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is empty/corrupt, return an empty list
        return []

def write_notices(notices):
    """Writes the notices list back to the JSON file."""
    with open(NOTICES_FILE, 'w') as f:
        json.dump(notices, f, indent=2)

# --- API Endpoints ---

@app.route('/api/notices', methods=['GET'])
def get_notices():
    """Reads all notices from the JSON file and sends them to the client."""
    print('GET /api/notices - Fetching all notices')
    notices = read_notices()
    return jsonify(notices)

@app.route('/api/notices/add', methods=['POST'])
def add_notice():
    """Adds a new notice to the JSON file."""
    print('POST /api/notices/add - Adding a new notice')
    new_notice = request.get_json()
    notices = read_notices()
    
    # Assign a unique ID on the server-side (using timestamp)
    import time
    new_notice['id'] = int(time.time() * 1000)
    
    notices.append(new_notice)
    write_notices(notices)
    
    return jsonify(new_notice), 201 # 201 Created

@app.route('/api/notices/delete', methods=['POST'])
def delete_notice():
    """Deletes a notice by its ID."""
    print('POST /api/notices/delete - Deleting a notice')
    data = request.get_json()
    notice_id_to_delete = data.get('id')
    
    notices = read_notices()
    initial_length = len(notices)
    
    notices = [notice for notice in notices if notice.get('id') != notice_id_to_delete]
    
    if len(notices) < initial_length:
        write_notices(notices)
        return jsonify({'message': 'Notice deleted successfully.'}), 200
    else:
        return jsonify({'message': 'Notice not found.'}), 404

# --- Static File Serving ---

@app.route('/<path:filename>')
def serve_static(filename):
    """Serves static files from the root directory."""
    return send_from_directory(app.root_path, filename)

@app.route('/')
def serve_index():
    """Serves the main HTML file by default."""
    return send_from_directory(app.root_path, 'notice-board.html')

# --- Start the Server ---
if __name__ == '__main__':
    # Use 0.0.0.0 to make it accessible on your network
    app.run(host='0.0.0.0', port=3000, debug=True)
