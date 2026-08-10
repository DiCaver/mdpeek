"""Session-only, widget-independent file navigation history."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def normalize_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


@dataclass
class HistoryEntry:
    path: Path
    vertical_position: int = 0


class NavigationHistory:
    """Ordered browser-style history with per-visit reading positions."""

    def __init__(self) -> None:
        self.entries: list[HistoryEntry] = []
        self.current_index = -1

    @property
    def current(self) -> HistoryEntry | None:
        return self.entries[self.current_index] if 0 <= self.current_index < len(self.entries) else None

    @property
    def can_go_back(self) -> bool:
        return self.current_index > 0

    @property
    def can_go_forward(self) -> bool:
        return 0 <= self.current_index < len(self.entries) - 1

    def target_index(self, offset: int) -> int | None:
        index = self.current_index + offset
        return index if 0 <= index < len(self.entries) else None

    def record_current_position(self, position: int) -> None:
        if self.current is not None:
            self.current.vertical_position = max(0, int(position))

    def add(self, path: str | Path) -> bool:
        """Commit a successful user open; return False for a refresh."""
        normalized = normalize_path(path)
        if self.current is not None and self.current.path == normalized:
            return False
        del self.entries[self.current_index + 1 :]
        self.entries.append(HistoryEntry(normalized))
        self.current_index = len(self.entries) - 1
        return True

    def move_to(self, index: int) -> bool:
        """Commit an already-successful history load."""
        if not 0 <= index < len(self.entries):
            return False
        self.current_index = index
        return True

    def back(self) -> bool:
        target = self.target_index(-1)
        return target is not None and self.move_to(target)

    def forward(self) -> bool:
        target = self.target_index(1)
        return target is not None and self.move_to(target)
