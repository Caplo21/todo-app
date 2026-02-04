import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from todo import TodoManager


def print_todos(todos):
    if not todos:
        print("Ingen todos endnu.")
        return
    for t in todos:
        status = "x" if t["done"] else " "
        print(f"  [{status}] {t['id']}. {t['text']}")


def main():
    manager = TodoManager()

    while True:
        print("\n--- Todo App ---")
        print("1. Vis todos")
        print("2. Tilføj todo")
        print("3. Færdiggør todo")
        print("4. Rediger todo")
        print("5. Slet todo")
        print("6. Afslut")
        choice = input("Vælg: ").strip()

        if choice == "1":
            print_todos(manager.list())
        elif choice == "2":
            text = input("Beskrivelse: ").strip()
            if text:
                todo = manager.add(text)
                print(f"Tilføjet: {todo['id']}. {todo['text']}")
            else:
                print("Tom beskrivelse - todo ikke tilføjet.")
        elif choice == "3":
            print_todos(manager.list())
            try:
                todo_id = int(input("Indtast todo ID: ").strip())
            except ValueError:
                print("Ugyldigt ID.")
                continue
            todo = manager.complete(todo_id)
            if todo:
                print(f"Færdiggjort: {todo['text']}")
            else:
                print("Todo ikke fundet.")
        elif choice == "4":
            print_todos(manager.list())
            try:
                todo_id = int(input("Indtast todo ID: ").strip())
            except ValueError:
                print("Ugyldigt ID.")
                continue
            new_text = input("Ny beskrivelse: ").strip()
            if not new_text:
                print("Tom beskrivelse - todo ikke ændret.")
                continue
            todo = manager.edit(todo_id, new_text)
            if todo:
                print(f"Opdateret: {todo['id']}. {todo['text']}")
            else:
                print("Todo ikke fundet.")
        elif choice == "5":
            print_todos(manager.list())
            try:
                todo_id = int(input("Indtast todo ID: ").strip())
            except ValueError:
                print("Ugyldigt ID.")
                continue
            todo = manager.delete(todo_id)
            if todo:
                print(f"Slettet: {todo['text']}")
            else:
                print("Todo ikke fundet.")
        elif choice == "6":
            print("Farvel!")
            break
        else:
            print("Ugyldigt valg.")


if __name__ == "__main__":
    main()
