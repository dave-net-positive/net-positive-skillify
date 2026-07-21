# Branding the report

The report uses a neutral built-in theme by default, so it looks finished with no setup. Branding is optional and entirely driven by a small JSON file passed with `--brand`.

```bash
python3 scripts/generate_analysis_report.py efficiency.json report.html --brand brand.json
```

## brand.json fields

All fields are optional; anything you leave out keeps the default.

| Field | Purpose | Example |
|---|---|---|
| `name` | Organisation name shown in the header band | `"Acme Ltd"` |
| `accent` | Header band and table colour | `"#1f6f78"` |
| `accent_dark` | Slightly darker shade for table headers | `"#16545b"` |
| `logo` | Logo in the header (see below) | `"assets/logo.png"` |
| `footer` | Footer line; set to `""` to omit the footer entirely | `"Generated with the assistance of AI."` |
| `kind_label` | Label in the header band's right corner | `"Net Positive Skillify Review (verified)"` |
| `extra_css` | CSS appended after the theme, for fonts, backgrounds, and pill palettes; `__ACCENT__` and `__ACCENT_DARK__` substitute as in the theme | see `assets/brand.net-positive.json` |

A neutral starting point is in `assets/brand.example.json`.

## The bundled Net Positive brand file

`assets/brand.net-positive.json` is the default brand for this skill and encodes
the Net Positive (Slate & Ember) brand rules: Ember `#e0783a` as the accent
colour with `#b85f28` for darker table headers, the Net Positive typefaces
(Barlow Condensed for headings, Plus Jakarta Sans for body, JetBrains Mono for
code), the Net Positive logo on the accent header band, and WCAG AA contrast
throughout. The footer carries the line "Generated with the assistance of AI."

## Logo handling

The `logo` value can be:

- a **local file path**: the image is read and base64-embedded, so the report stays a single self-contained file with no external dependency. A relative path resolves against the brand file's own folder first, so a brand file shipped inside the skill works from any working directory;
- a **URL** (`https://...`): referenced directly (the report then needs network access to show it);
- a **data URI** (`data:image/png;base64,...`): used as-is.

PNG, JPEG, SVG, GIF, and WebP are recognised for local files. A missing local file is skipped with a warning rather than failing the report.

## Using an existing brand library

If you maintain a richer brand system (for example a Python module that wraps HTML with corporate headers and footers), you do not need this generator's theming: generate the report body with the default theme, or adapt `render_page` to call your own wrapper. The `--brand` route is deliberately dependency-free so the skill stays portable and shareable.
