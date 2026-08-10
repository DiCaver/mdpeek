# Navigation Journal

A third document for longer Back and Forward chains.

## Entry one

MDPeek history belongs to one window and lasts only for the current application session. Closing and reopening the application starts with an empty history.

### Things to observe

- Back is disabled on the first entry.
- Forward becomes available after going Back.
- Opening a new file after going Back replaces the Forward branch.

## Entry two

Scroll positions are associated with history entries rather than file paths. This matters when the same file appears more than once in the sequence.

```json
{
  "path": "navigation-journal.md",
  "vertical_position": 420
}
```

### Layout changes

Resize the window or toggle the outline before returning here. The restored position is clamped to the scrollbar's current range.

## Entry three

Selecting text is deliberately not history state. Make a selection, navigate away, and return; the document should reopen without restoring that selection.

> Navigation should not modify the clipboard, either.

## Entry four

Try opening this file by both a relative and an absolute path. Equivalent normalized paths refresh the current history entry instead of creating a consecutive duplicate.

## Final entry

This is the bottom marker. Leave the page here, navigate through the other examples, and return with Forward.
