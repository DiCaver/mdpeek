# MDPeek Markdown Showcase

This document exercises Qt's built-in Markdown renderer and MDPeek's reading style. It includes **bold**, *italic*, ~~strikethrough~~, and an [external link to Qt](https://www.qt.io/).

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

## Syntax highlighting

The palette is intentionally quiet, and every code panel remains selectable.

```javascript
const greeting = "Hello from MDPeek";
console.log(greeting);
```

```css
.document {
  color: #e6edf3;
  background: #202428;
}
```

```csharp
public sealed class Preview
{
    public string Title { get; init; } = "MDPeek";
}
```

```json
{
  "application": "MDPeek",
  "readOnly": true,
  "features": ["Markdown", "syntax highlighting"]
}
```

```sql
SELECT language, COUNT(*) AS examples
FROM code_blocks
WHERE highlighted = TRUE
GROUP BY language;
```

Unknown languages fall back to ordinary monospace code without guessing:

```made-up-language
widget := preserve(<this & that>)
```

An unlabeled fence has the same safe fallback:

```
exact text: <tag> & "quotes"
```

| Feature | Example | Expected |
| :-- | :--: | --: |
| Unicode | č, š, ž | Preserved |
| Alignment | left / center / right | Qt-dependent |
| Code | `inline` | Monospace |

---

## Relative image

The image below is loaded relative to this Markdown file:

![A simple MDPeek document illustration](mdpeek-mark.svg)

![JRS_3.gif (200×200)](https://www.jamarska-zveza.si/images/JRS_3.gif)

End of showcase.
