# Rosida – Quick Start

Rosida is a native computational notebook: you write text and Python code in cells, Rosida
evaluates them and shows formulas, plots and tables right in the document. Documents are saved as
plain `.md` files – no proprietary format, no web browser running in the background.

## Starting

```bash
just run
```

This starts the app via `uv run` with all required packages (PySide6, SymPy, NumPy, Matplotlib,
Polars, qtawesome). Optionally, pass an existing `.md` file directly:

```bash
uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy --with qtawesome \
  src/app.py my_document.md
```

## Basic idea: cells

A document is a sequence of **cells**. Each cell is either:

- **Python** – executed; the last expression or the `print()` output is shown,
- **Text (Markdown)** – rendered as formatted text (headings, formulas, `{{ }}` expressions, ...),
- **Auto** – Rosida guesses from the content what you mean (default mode for new cells).

| Action | Shortcut |
|---|---|
| Run / render cell | `Shift+Enter` |
| Back to the editor (from the view) | Click the cell, `Escape` to close |
| Toggle mode (Auto → Python → Text) | `Ctrl+M` or click the mode pill |
| Insert a cell before the active one | `Ctrl+Shift+A` |
| Move cell up / down | `Ctrl+Shift+Up` / `Ctrl+Shift+Down` |
| Delete active cell | `Ctrl+Shift+D` |
| Run all cells | `Ctrl+Shift+Return` |
| Undo / Redo | `Cmd+Z` / `Cmd+Shift+Z` |

Click a cell at any time to edit it – its output doesn't disappear, it is only replaced by the
editor until you re-evaluate with `Shift+Enter` or cancel with `Escape`.

**Cells without visible output** (e.g. plain `import`s or variable definitions) take up no space –
instead of an empty box, only a small, muted “+” circle appears on the left. Clicking it opens the
editor again at full height.

Rosida runs all Python code in a **shared namespace** – variables from one cell are visible in all
following cells, just like in a Jupyter notebook. Preloaded are:

```python
sp   # sympy
np   # numpy
plt  # matplotlib.pyplot
pl   # polars
```

Python cells run in the background: while a cell is computing, it shows a progress indicator and
the rest of the app stays usable.

## Examples

### Plain Python

```python
radius = 4
circumference = 2 * 3.14159 * radius
circumference
```

Shows `25.13272` as the result (the last expression of the cell).

### NumPy

```python
values = np.linspace(0, 10, 5)
np.mean(values), np.std(values)
```

### Matplotlib

A `Figure` as the last expression of a cell is embedded directly as a plot:

```python
fig, ax = plt.subplots(figsize=(6, 2.5))
x = np.linspace(0, 3, 200)
ax.plot(x, np.sin(x) * np.exp(x), color="#2563eb", lw=2)
ax.set_title("f(x) = sin(x)·eˣ")
fig
```

### SymPy

Symbolic expressions are rendered as LaTeX formulas automatically:

```python
x = sp.symbols("x")
f = sp.sin(x) * sp.exp(x)
sp.diff(f, x)
```

### Polars

```python
df = pl.DataFrame({"city": ["Zurich", "Bern", "Geneva"], "population": [434000, 134000, 203000]})
df
```

Polars `DataFrame`s are shown as an interactive table (sortable, scrollable).

## Text cells: formulas and live expressions

In a text cell you write regular Markdown (`#`, `##`, `> quote`, `**bold**`, `*italic*`,
`` `code` ``), plus:

- **LaTeX formulas**: `$ f(x) = x^2 $` (inline) or `$$ \int_0^1 x^2\,dx $$` (block), typeset with
  ziamath in Latin Modern Math (matching the CMU fonts), including matrices, `aligned` and `cases`.
- **`{{ expression }}`**: evaluated live in the shared namespace. A SymPy result becomes LaTeX
  automatically; anything else is inserted as text.

```markdown
The derivative is $ f'(x) = $ {{ sp.diff(f, x) }}

The circumference is {{ circumference }} cm.
```

If `{{ ... }}` stands alone on a line, the result is rendered as a centered block formula instead
of inline.

## Saving & loading

- `Cmd+S` saves as `.md` – Python cells are written as ` ```python ` code blocks, text cells stay
  raw Markdown, consecutive text cells are separated by `---`.
- The **Save** button is only active when something has actually changed since the last save/load.
  For a new document that has never been saved, `Cmd+S` opens the “Save as…” dialog.
- `Cmd+O` opens an existing `.md` file and rebuilds the interactive cells from it.
- **File → Open recent** lists the files that were recently opened or saved.

Because the format is plain Markdown, regular Git diffs and merges work without friction.

## Export

Via **File → Export** (or the toolbar):

- **PDF** (`Ctrl+Shift+P`) – vector print of the whole document including rendered formulas, plots
  and tables.
- **HTML** (`Ctrl+Shift+H`) – standalone web page: KaTeX typesets the formulas in the browser
  (loaded from a CDN); CMU fonts, images and plots (as SVG) are embedded. Without internet access
  the LaTeX source stays readable instead of the formulas.
- **Quarto** (`Ctrl+Shift+Q`) – writes a `.qmd` file. `{{ }}` expressions in text cells are
  evaluated as well (SymPy → LaTeX, Polars → Quarto table, Matplotlib figure → SVG file next to the
  `.qmd`); Python cells end up as code blocks with their last result. Ideal for turning a Rosida
  document into a polished HTML/PDF/Typst report via Quarto.

Citations such as `[@key]` are resolved in the PDF and HTML export against the file named in
`bibliography:` in the document properties, and the cited entries are listed at the end. Exports
use the document language (`lang: en` in the document properties, otherwise the UI language).

## Sidebars (docks)

- **Document outline** (`F3`, left): an outline of the `#`/`##`/`###` headings of your text cells
  and of the Python cells; clicking jumps straight to the cell.
- **LaTeX palette** (`F4`, right): clickable snippets for calculus (fraction, integral, sum, ...),
  Greek letters, symbols and matrices – inserts the code at the cursor position of the active cell.
  The collapsed section **“Quarto (.qmd)”** additionally contains callout boxes
  (`::: {.callout-note}` etc.), footnote and cross-reference building blocks for the Quarto
  export – Rosida's own live preview shows them only roughly, a real `quarto render` turns them
  into the formatted boxes.
- **References**: the entries of the bibliography file; double-click inserts a citation.

## A small complete example

````markdown
# Damped oscillation

We examine $f(t) = e^{-\gamma t} \cos(\omega t)$.

---

```python
t, gamma, omega = sp.symbols("t gamma omega", positive=True)
f = sp.exp(-gamma * t) * sp.cos(omega * t)
f
```

The first derivative is {{ sp.diff(f, t) }}.

---

```python
values = np.linspace(0, 10, 300)
fig, ax = plt.subplots(figsize=(6, 2.5))
ax.plot(values, np.exp(-0.3 * values) * np.cos(2 * values), color="#2563eb")
ax.set_title("Numerical course")
fig
```
````

That's essentially all you need to get started – the rest comes with trying things out.

## Help menu

- **Manual...** (`F1`) shows exactly this guide in a dialog – handy when no terminal/browser is at
  hand. Right after the very first installation, this dialog opens automatically once.
- **About Rosida** shows the version number and license.
- **Settings...** (`Cmd+,`): language of the user interface (system language, English or German),
  takes effect after a restart.
