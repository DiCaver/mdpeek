# MDPeek Markdown Showcase

This document exercises Qt's built-in Markdown renderer and MDPeek's Phase 2 reading style. It includes **bold**, *italic*, ~~strikethrough~~, and an [external link to Qt](https://www.qt.io/).

## Heading level two

Readable paragraphs should have comfortable line spacing and separation. Unicode remains intact: Slovenian **č, š, ž**, plus café, naïve, Ελληνικά, 日本語, and an em dash —.

### Heading level three

Inline code such as `mdpeek examples/showcase.md` uses a monospace face and a quiet background.

#### Heading level four

- An unordered item
- Another item with nested content
  - A nested item
  - A second nested item

##### Heading level five

1. First ordered step
2. Second ordered step
3. Third ordered step

###### Heading level six

Task-list syntax is included for comparison:

- [x] Open the document
- [ ] Observe whether checkboxes are rendered

> A blockquote should be distinct but restrained.
>
> It may contain more than one paragraph and **formatted text**.

```python
from pathlib import Path

showcase = Path("examples/showcase.md")
print(f"Viewing {showcase.name}")
```

| Feature | Example | Expected |
|:--|:--:|--:|
| Unicode | č, š, ž | Preserved |
| Alignment | left / center / right | Qt-dependent |
| Code | `inline` | Monospace |

---

## Relative image

The image below is loaded relative to this Markdown file:

![A simple MDPeek document illustration](mdpeek-mark.svg)

End of showcase.
