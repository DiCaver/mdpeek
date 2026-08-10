# Navigation Reference

Use this page as the second stop in a navigation sequence.

## Keyboard shortcuts

| Command | Shortcut |
| --- | --- |
| Open | `Ctrl+O` |
| Back | `Alt+Left` |
| Forward | `Alt+Right` |
| Document Outline | `Ctrl+H` |

## Browser-style branching

Start with this sequence:

```text
navigation-notes.md → navigation-reference.md → navigation-journal.md
```

Navigate Back once, then open another file. The old Forward destination should be replaced by the newly opened file.

## Duplicate visits

Non-consecutive visits are separate entries:

```text
notes.md at position 100
→ reference.md at position 250
→ notes.md at position 700
```

Each visit to `notes.md` should restore its own position.

## Failure exercise

To test retry behavior:

1. Open this file, then another Markdown file.
2. Temporarily rename this file outside MDPeek.
3. Navigate Back and acknowledge the error.
4. Restore the original filename.
5. Navigate Back again.

The failed attempt should not remove or skip the history entry.

## Useful links

- [MDPeek README](../README.md)
- [Navigation Notes](navigation-notes.md)
- [Navigation Journal](navigation-journal.md)

## End marker

Scroll here before navigating away to test restoration near the bottom of a document.
