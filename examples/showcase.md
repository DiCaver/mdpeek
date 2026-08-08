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

The next two blocks deliberately contain identical code so each copy control can be checked independently:

```text
identical block
```

```text
identical block
```

Whitespace, blank lines, special characters, and Unicode should copy exactly:

```
first line

    four spaces
	and a tab: < > & "quotes" \\ č š ž
```

| Feature | Example | Expected |
| :-- | :--: | --: |
| Unicode | č, š, ž | Preserved |
| Alignment | left / center / right | Qt-dependent |
| Code | `inline` | Monospace |

---

## Consecutive section
### Empty nested section
### Following nested section

The headings above exercise empty and consecutive section boundaries.

## Images

The image below is loaded relative to this Markdown file:

![A simple MDPeek document illustration](mdpeek-mark.svg)

The image below is loaded from a subfolder relative to this Markdown file:

![JRS_3.gif](img/JRS_3.gif)

The image below is loaded from a web:

![A mushroom-head robot drinking bubble tea](https://raw.githubusercontent.com/Codecademy/docs/main/media/codey.jpg)

End of showcase.

## Final section

This final section continues to the end of the document because no same-level or higher-level heading follows it.
