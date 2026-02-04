import json
import os

DATA_FILE = "todos.json"


class TodoManager:
    def __init__(self):
        self.todos = []
        self._load()

    def _load(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.todos = json.load(f)

    def _save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.todos, f, ensure_ascii=False, indent=2)

    def add(self, text):
        todo = {"id": len(self.todos) + 1, "text": text, "done": False}
        self.todos.append(todo)
        self._save()
        return todo

    def complete(self, todo_id):
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["done"] = True
                self._save()
                return todo
        return None

    def edit(self, todo_id, new_text):
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["text"] = new_text
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
