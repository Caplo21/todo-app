import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, jsonify, request, render_template, send_from_directory
from werkzeug.utils import secure_filename
from todo import TodoManager
from todoist_sync import TodoistSync, TodoistSyncError
import requests

app = Flask(__name__)
manager = TodoManager()
syncer = TodoistSync(manager)
last_sync_time = None

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "pdf", "docx", "txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


# ── REST API ──────────────────────────────────────────────────────────────────

@app.route("/api/todos")
def get_todos():
    return jsonify(manager.list())


@app.route("/api/todos", methods=["POST"])
def add_todo():
    data = request.get_json(force=True)
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    todo = manager.add(
        text,
        category=data.get("category", ""),
        priority=data.get("priority", "Medium"),
        deadline=data.get("deadline", ""),
    )
    return jsonify(todo), 201


@app.route("/api/todos/<int:todo_id>", methods=["PUT"])
def update_todo(todo_id):
    data = request.get_json(force=True)
    todo = manager.edit(
        todo_id,
        new_text=data.get("text"),
        category=data.get("category"),
        priority=data.get("priority"),
        deadline=data.get("deadline"),
    )
    if todo is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(todo)


@app.route("/api/todos/<int:todo_id>/toggle", methods=["PATCH"])
def toggle_todo(todo_id):
    todo = manager.toggle_done(todo_id)
    if todo is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(todo)


@app.route("/api/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id):
    todo = manager.delete(todo_id)
    if todo is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(todo)


# ── File uploads ─────────────────────────────────────────────────────────────


@app.route("/api/todos/<int:todo_id>/upload", methods=["POST"])
def upload_file(todo_id):
    todo = next((t for t in manager.todos if t["id"] == todo_id), None)
    if todo is None:
        return jsonify({"error": "not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "no file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "file type not allowed"}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({"error": "file too large (max 10 MB)"}), 400

    # Remove old attachment if exists
    if todo.get("attachment"):
        old_path = os.path.join(UPLOAD_FOLDER, todo["attachment"])
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save with unique prefix to avoid collisions
    original = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{original}"
    file.save(os.path.join(UPLOAD_FOLDER, unique_name))

    updated = manager.edit(todo_id, attachment=unique_name)
    return jsonify(updated)


@app.route("/uploads/<filename>")
def serve_upload(filename):
    safe = secure_filename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe)


@app.route("/api/todos/<int:todo_id>/attachment", methods=["DELETE"])
def remove_attachment(todo_id):
    todo = next((t for t in manager.todos if t["id"] == todo_id), None)
    if todo is None:
        return jsonify({"error": "not found"}), 404

    if todo.get("attachment"):
        old_path = os.path.join(UPLOAD_FOLDER, todo["attachment"])
        if os.path.exists(old_path):
            os.remove(old_path)

    updated = manager.edit(todo_id, attachment="")
    return jsonify(updated)


# ── Todoist Sync ────────────────────────────────────────────────────────────


@app.route("/api/sync", methods=["POST"])
def trigger_sync():
    global last_sync_time

    if not syncer.is_configured():
        return jsonify({"error": "Todoist API token er ikke konfigureret i config.py."}), 400

    try:
        result = syncer.full_sync()
        last_sync_time = datetime.now().isoformat()
        return jsonify(result)
    except TodoistSyncError as e:
        return jsonify({"error": str(e)}), 502
    except requests.ConnectionError:
        return jsonify({"error": "Kunne ikke forbinde til Todoist. Tjek din internetforbindelse."}), 503
    except Exception as e:
        return jsonify({"error": f"Uventet fejl: {e}"}), 500


@app.route("/api/sync/status")
def sync_status():
    return jsonify({
        "configured": syncer.is_configured(),
        "last_sync": last_sync_time,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
