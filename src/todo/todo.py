import json
import os

DATA_FILE = "todos.json"

DEFAULTS = {
    "category": "",
    "priority": "Medium",
    "deadline": "",
    "attachment": "",
    "todoist_id": "",
}


class TodoManager:
    def __init__(self):
        self.todos = []
        self._load()

    def _load(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.todos = json.load(f)
            for todo in self.todos:
                for key, default in DEFAULTS.items():
                    if key not in todo:
                        todo[key] = default

    def _save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.todos, f, ensure_ascii=False, indent=2)

    def _next_id(self):
        if not self.todos:
            return 1
        return max(t["id"] for t in self.todos) + 1

    def add(self, text, category="", priority="Medium", deadline="", attachment="", todoist_id=""):
        todo = {
            "id": self._next_id(),
            "text": text,
            "done": False,
            "category": category,
            "priority": priority,
            "deadline": deadline,
            "attachment": attachment,
            "todoist_id": todoist_id,
        }
        self.todos.append(todo)
        self._save()
        return todo

    def toggle_done(self, todo_id):
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["done"] = not todo["done"]
                self._save()
                return todo
        return None

    def complete(self, todo_id):
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["done"] = True
                self._save()
                return todo
        return None

    def edit(self, todo_id, new_text=None, category=None, priority=None, deadline=None, attachment=None, todoist_id=None):
        for todo in self.todos:
            if todo["id"] == todo_id:
                if new_text is not None:
                    todo["text"] = new_text
                if category is not None:
                    todo["category"] = category
                if priority is not None:
                    todo["priority"] = priority
                if deadline is not None:
                    todo["deadline"] = deadline
                if attachment is not None:
                    todo["attachment"] = attachment
                if todoist_id is not None:
                    todo["todoist_id"] = todoist_id
                self._save()
                return todo
        return None

    def delete(self, todo_id):
        for i, todo in enumerate(self.todos):
            if todo["id"] == todo_id:
                removed = self.todos.pop(i)
                self._save()
                return removed
        return None

    def list(self):
        return self.todos
