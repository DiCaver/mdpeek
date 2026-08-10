import unittest
from pathlib import Path

from mdpeek.navigation import NavigationHistory


class NavigationHistoryTests(unittest.TestCase):
    def test_empty_and_first_entry(self) -> None:
        history = NavigationHistory()
        self.assertIsNone(history.current)
        self.assertFalse(history.can_go_back)
        self.assertFalse(history.can_go_forward)
        history.add("README.md")
        self.assertEqual(history.current.path, Path("README.md").resolve())
        self.assertEqual(history.current_index, 0)

    def test_duplicates_positions_and_movement(self) -> None:
        history = NavigationHistory()
        history.add("README.md")
        self.assertFalse(history.add(Path(".") / "README.md"))
        history.record_current_position(100)
        history.add("examples/showcase.md")
        history.record_current_position(250)
        history.add("README.md")
        history.record_current_position(700)
        self.assertEqual(len(history.entries), 3)
        self.assertEqual([entry.vertical_position for entry in history.entries], [100, 250, 700])
        self.assertTrue(history.back())
        self.assertEqual(history.current_index, 1)
        self.assertTrue(history.back())
        self.assertEqual(history.current.vertical_position, 100)
        self.assertFalse(history.back())
        self.assertTrue(history.forward())

    def test_branch_is_discarded_only_when_add_is_committed(self) -> None:
        history = NavigationHistory()
        for name in ("a.md", "b.md", "c.md"):
            history.add(name)
        history.back()
        self.assertEqual(len(history.entries), 3)  # merely preparing changes nothing
        history.add("d.md")
        self.assertEqual([entry.path.name for entry in history.entries], ["a.md", "b.md", "d.md"])
        self.assertFalse(history.can_go_forward)


if __name__ == "__main__":
    unittest.main()
