import importlib
import requests

try:
    import config as _config_module
except ImportError:
    _config_module = None


class TodoistSyncError(Exception):
    """Raised on Todoist API errors."""
    pass


class TodoistSync:
    # Mapping mellem Todoist projekt-navne og lokale kategorier
    PROJECT_TO_CATEGORY = {
        "work": "Arbejde",
        "arbejde": "Arbejde",
        "personal": "Privat",
        "privat": "Privat",
        "shopping": "Indkøb",
        "indkøb": "Indkøb",
        "groceries": "Indkøb",
    }

    CATEGORY_TO_PROJECT = {
        "Arbejde": "Arbejde",
        "Privat": "Privat",
        "Indkøb": "Indkøb",
    }

    def __init__(self, manager):
        self.manager = manager
        self._project_cache = {}  # name -> id
        self._project_id_cache = {}  # id -> name

    def _read_config(self):
        """Re-read config.py every time so token changes are picked up."""
        if _config_module is None:
            return "", "https://api.todoist.com/rest/v2"
        importlib.reload(_config_module)
        token = getattr(_config_module, "TODOIST_API_TOKEN", "")
        base = getattr(_config_module, "TODOIST_API_BASE", "https://api.todoist.com/rest/v2")
        return token, base

    def _get_headers(self):
        token, _ = self._read_config()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _get_base(self):
        _, base = self._read_config()
        return base

    def is_configured(self):
        token, _ = self._read_config()
        return bool(token and token.strip())

    # ── HTTP helpers ─────────────────────────────────────────────────────────

    def _get(self, path):
        url = f"{self._get_base()}{path}"
        resp = requests.get(url, headers=self._get_headers(), timeout=15)
        self._check_response(resp)
        return resp.json()

    def _post(self, path, data=None):
        url = f"{self._get_base()}{path}"
        resp = requests.post(url, headers=self._get_headers(), json=data or {}, timeout=15)
        self._check_response(resp)
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def _delete(self, path):
        url = f"{self._get_base()}{path}"
        resp = requests.delete(url, headers=self._get_headers(), timeout=15)
        self._check_response(resp)
        return {}

    def _check_response(self, resp):
        if resp.status_code == 401:
            raise TodoistSyncError("Ugyldigt API token. Tjek din config.py.")
        if resp.status_code == 429:
            retry = resp.headers.get("Retry-After", "ukendt")
            raise TodoistSyncError(f"Rate limit nået. Prøv igen om {retry} sekunder.")
        if resp.status_code >= 500:
            raise TodoistSyncError(f"Todoist server fejl ({resp.status_code}). Prøv igen senere.")
        if resp.status_code >= 400:
            msg = resp.text[:200] if resp.text else str(resp.status_code)
            raise TodoistSyncError(f"Todoist API fejl: {msg}")

    # ── Project mapping ──────────────────────────────────────────────────────

    def _load_projects(self):
        projects = self._get("/projects")
        self._project_cache = {}
        self._project_id_cache = {}
        for p in projects:
            self._project_cache[p["name"]] = p["id"]
            self._project_id_cache[p["id"]] = p["name"]

    def _ensure_project(self, category):
        if not category:
            return None
        if category in self._project_cache:
            return self._project_cache[category]
        project = self._post("/projects", {"name": category})
        self._project_cache[project["name"]] = project["id"]
        self._project_id_cache[project["id"]] = project["name"]
        return project["id"]

    def _project_id_to_category(self, project_id):
        if not project_id:
            return ""
        name = self._project_id_cache.get(project_id, "")
        # Ignorer Inbox - det er Todoist's default og matcher ikke en lokal kategori
        if name.lower() == "inbox":
            return ""
        # Tjek om projektet mapper til en lokal kategori
        mapped = self.PROJECT_TO_CATEGORY.get(name.lower())
        if mapped:
            return mapped
        # Ellers brug projekt-navnet direkte hvis det matcher en kategori
        if name in self.CATEGORY_TO_PROJECT:
            return name
        return ""

    # ── Priority mapping ─────────────────────────────────────────────────────

    @staticmethod
    def _local_to_api_priority(priority):
        mapping = {"Høj": 4, "Medium": 2, "Lav": 1}
        return mapping.get(priority, 1)

    @staticmethod
    def _api_to_local_priority(api_priority):
        mapping = {4: "Høj", 3: "Høj", 2: "Medium", 1: "Lav"}
        return mapping.get(api_priority, "Medium")

    # ── Task CRUD on Todoist ─────────────────────────────────────────────────

    def _create_todoist_task(self, local_todo):
        content = local_todo["text"]
        # Tilføj note om vedhæftet fil
        if local_todo.get("attachment"):
            filename = local_todo["attachment"].split("_", 1)[-1] if "_" in local_todo["attachment"] else local_todo["attachment"]
            content += f" 📎 Har lokal fil: {filename}"

        data = {
            "content": content,
            "priority": self._local_to_api_priority(local_todo.get("priority", "Medium")),
        }
        project_id = self._ensure_project(local_todo.get("category", ""))
        if project_id:
            data["project_id"] = project_id
        deadline = local_todo.get("deadline", "")
        if deadline:
            data["due_date"] = deadline
        return self._post("/tasks", data)

    def _update_todoist_task(self, todoist_id, local_todo):
        content = local_todo["text"]
        # Tilføj note om vedhæftet fil
        if local_todo.get("attachment"):
            filename = local_todo["attachment"].split("_", 1)[-1] if "_" in local_todo["attachment"] else local_todo["attachment"]
            if "📎" not in content:
                content += f" 📎 Har lokal fil: {filename}"

        data = {
            "content": content,
            "priority": self._local_to_api_priority(local_todo.get("priority", "Medium")),
        }

        # Opdater projekt hvis der er en kategori
        category = local_todo.get("category", "")
        if category:
            project_id = self._ensure_project(category)
            if project_id:
                data["project_id"] = project_id

        deadline = local_todo.get("deadline", "")
        if deadline:
            data["due_date"] = deadline
        else:
            data["due_string"] = "no date"
        self._post(f"/tasks/{todoist_id}", data)

    def _close_todoist_task(self, todoist_id):
        self._post(f"/tasks/{todoist_id}/close")

    def _reopen_todoist_task(self, todoist_id):
        self._post(f"/tasks/{todoist_id}/reopen")

    # ── Full sync algorithm ──────────────────────────────────────────────────

    def full_sync(self):
        if not self.is_configured():
            raise TodoistSyncError("Todoist API token er ikke konfigureret i config.py.")

        result = {
            "success": True,
            "pulled": 0,
            "pushed": 0,
            "updated": 0,
            "completed": 0,
            "errors": [],
        }

        # 1. Load projects
        self._load_projects()

        # 2. Fetch all active Todoist tasks
        todoist_tasks = self._get("/tasks")

        # 3. Build lookup maps
        todoist_by_id = {str(t["id"]): t for t in todoist_tasks}

        # Gem en kopi af lokale todos med deres done-status FØR vi ændrer noget
        local_todos_snapshot = []
        for todo in self.manager.todos:
            local_todos_snapshot.append({
                "id": todo["id"],
                "todoist_id": todo.get("todoist_id", ""),
                "done": todo["done"],
                "text": todo["text"],
                "category": todo.get("category", ""),
                "priority": todo.get("priority", "Medium"),
                "deadline": todo.get("deadline", ""),
                "attachment": todo.get("attachment", ""),
            })

        local_by_todoist_id = {}
        local_without_link = []

        for todo in local_todos_snapshot:
            tid = todo.get("todoist_id", "")
            if tid:
                local_by_todoist_id[tid] = todo
            else:
                local_without_link.append(todo)

        # 4. Håndter linkede tasks - tjek done status FØRST
        for tid, local_todo in list(local_by_todoist_id.items()):
            # Hvis lokal er done -> luk på Todoist og unlink
            if local_todo["done"]:
                if tid in todoist_by_id:
                    try:
                        self._close_todoist_task(tid)
                        self.manager.edit(local_todo["id"], todoist_id="")
                        result["completed"] += 1
                    except Exception as e:
                        result["errors"].append(f"Close todoist #{tid}: {e}")
                else:
                    # Allerede væk fra Todoist, bare unlink
                    self.manager.edit(local_todo["id"], todoist_id="")
            elif tid in todoist_by_id:
                # Begge aktive - opdater Todoist med lokale data (fil-note, etc)
                remote = todoist_by_id[tid]
                try:
                    self._update_todoist_task(tid, local_todo)
                    # Opdater også lokalt fra Todoist (prioritet, etc fra Todoist)
                    self._update_local_from_remote_keep_local(local_todo, remote)
                    result["updated"] += 1
                except Exception as e:
                    result["errors"].append(f"Update #{local_todo['id']}: {e}")
            else:
                # Task forsvundet fra Todoist -> marker som done lokalt, unlink
                try:
                    self.manager.edit(local_todo["id"], todoist_id="")
                    self.manager.complete(local_todo["id"])
                    result["completed"] += 1
                except Exception as e:
                    result["errors"].append(f"Complete lokal #{local_todo['id']}: {e}")

        # 5. New Todoist tasks (not linked to any local task)
        linked_todoist_ids = set(local_by_todoist_id.keys())
        for tid, remote in todoist_by_id.items():
            if tid not in linked_todoist_ids:
                try:
                    self._create_local_from_remote(remote)
                    result["pulled"] += 1
                except Exception as e:
                    result["errors"].append(f"Pull todoist #{tid}: {e}")

        # 6. New local tasks (no todoist_id, not done) -> push to Todoist
        for local_todo in local_without_link:
            if local_todo["done"]:
                continue
            try:
                created = self._create_todoist_task(local_todo)
                self.manager.edit(local_todo["id"], todoist_id=str(created["id"]))
                result["pushed"] += 1
            except Exception as e:
                result["errors"].append(f"Push lokal #{local_todo['id']}: {e}")

        if result["errors"]:
            result["success"] = False

        return result

    def _update_local_from_remote_keep_local(self, local_todo, remote):
        """Opdater lokalt fra Todoist, men behold lokale værdier for attachment."""
        # Vi beholder lokal attachment og sender den til Todoist
        # Men henter text/priority/deadline fra Todoist hvis de er ændret der
        pass  # For nu gør vi ingenting - lokal vinder for linkede tasks

    def _strip_attachment_note(self, text):
        """Fjern fil-note fra tekst så den ikke akkumulerer."""
        import re
        return re.sub(r'\s*📎 Har lokal fil:.*$', '', text).strip()

    def _update_local_from_remote(self, local_todo, remote):
        """Update local task from Todoist data (Todoist wins)."""
        new_text = self._strip_attachment_note(remote.get("content", local_todo["text"]))
        new_priority = self._api_to_local_priority(remote.get("priority", 1))
        new_category = self._project_id_to_category(remote.get("project_id"))

        # Samme logik som _create_local_from_remote for deadline
        due = remote.get("due")
        new_deadline = ""
        if due:
            due_string = due.get("string", "")
            due_date = due.get("date", "")
            has_time = due.get("datetime") is not None
            if due_string or has_time or due.get("is_recurring"):
                new_deadline = due_date

        self.manager.edit(
            local_todo["id"],
            new_text=new_text,
            category=new_category,
            priority=new_priority,
            deadline=new_deadline,
        )

    def _create_local_from_remote(self, remote):
        """Create a new local task from a Todoist task."""
        text = self._strip_attachment_note(remote.get("content", ""))
        priority = self._api_to_local_priority(remote.get("priority", 1))
        category = self._project_id_to_category(remote.get("project_id"))

        # Kun brug deadline hvis det er en eksplicit sat dato (ikke bare oprettelsesdato)
        # Todoist's "due" objekt har "is_recurring" og "string" der indikerer om det er bevidst sat
        due = remote.get("due")
        deadline = ""
        if due:
            # Hvis der er en "string" (f.eks. "tomorrow", "every monday") er det bevidst sat
            # Ellers tjek om datoen er i fremtiden eller har tid specificeret
            due_string = due.get("string", "")
            due_date = due.get("date", "")
            has_time = due.get("datetime") is not None

            # Behold deadline hvis: har due_string, har tid, eller er recurring
            if due_string or has_time or due.get("is_recurring"):
                deadline = due_date

        todoist_id = str(remote["id"])

        self.manager.add(
            text=text,
            category=category,
            priority=priority,
            deadline=deadline,
            todoist_id=todoist_id,
        )
