# Navigation Notes

A lightweight document for testing Back and Forward navigation in MDPeek.

## Morning checklist

- Review the document outline
- Scroll to the middle of the page
- Open another example
- Navigate back and confirm the reading position

## Project update

The viewer should reload this file from disk whenever it is reached through history. Edit this paragraph while MDPeek is displaying another file, then navigate back to see the change.

> A successful history navigation preserves the current session while showing the latest contents from disk.

### Current status

| Area | Status | Notes |
| --- | --- | --- |
| Rendering | Ready | Markdown and highlighting remain unchanged |
| Navigation | Ready | Back and Forward are session-only |
| Position | Ready | Vertical scrolling is restored per entry |

## Implementation sketch

```python
def visit(path):
    markdown = path.read_text(encoding="utf-8")
    render(markdown)
    history.append(path)
```

The real implementation commits history only after loading succeeds.

## Afternoon checklist

1. Scroll to this section.
2. Open `navigation-reference.md`.
3. Press `Alt+Left`.
4. Confirm this section is visible again.

## Closing notes

This final section makes the document long enough to provide several distinct reading positions in a small window.
