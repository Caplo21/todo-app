import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import todo.todo as todo_module
from todo import TodoManager

TEST_DATA_FILE = "test_todos.json"


class TestTodoManager(unittest.TestCase):
    def setUp(self):
        todo_module.DATA_FILE = TEST_DATA_FILE
        if os.path.exists(TEST_DATA_FILE):
            os.remove(TEST_DATA_FILE)
        self.manager = TodoManager()

    def tearDown(self):
        if os.path.exists(TEST_DATA_FILE):
            os.remove(TEST_DATA_FILE)

    def test_add(self):
        todo = self.manager.add("Køb mælk")
        self.assertEqual(todo["id"], 1)
        self.assertEqual(todo["text"], "Køb mælk")
        self.assertFalse(todo["done"])

    def test_add_multiple(self):
        self.manager.add("Første")
        second = self.manager.add("Anden")
        self.assertEqual(second["id"], 2)
        self.assertEqual(len(self.manager.list()), 2)

    def test_list_empty(self):
        self.assertEqual(self.manager.list(), [])

    def test_list_returns_all(self):
        self.manager.add("A")
        self.manager.add("B")
        self.manager.add("C")
        self.assertEqual(len(self.manager.list()), 3)

    def test_complete(self):
        self.manager.add("Test")
        todo = self.manager.complete(1)
        self.assertTrue(todo["done"])

    def test_complete_nonexistent(self):
        result = self.manager.complete(99)
        self.assertIsNone(result)

    def test_edit(self):
        self.manager.add("Gammel tekst")
        todo = self.manager.edit(1, "Ny tekst")
        self.assertEqual(todo["text"], "Ny tekst")

    def test_edit_nonexistent(self):
        result = self.manager.edit(99, "Tekst")
        self.assertIsNone(result)

    def test_delete(self):
        self.manager.add("Slet mig")
        removed = self.manager.delete(1)
        self.assertEqual(removed["text"], "Slet mig")
        self.assertEqual(len(self.manager.list()), 0)

    def test_delete_nonexistent(self):
        result = self.manager.delete(99)
        self.assertIsNone(result)

    def test_persistence(self):
        self.manager.add("Persistens test")
        new_manager = TodoManager()
        self.assertEqual(len(new_manager.list()), 1)
        self.assertEqual(new_manager.list()[0]["text"], "Persistens test")


if __name__ == "__main__":
    unittest.main()
