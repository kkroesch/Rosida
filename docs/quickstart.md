# Rosida – Schnellstart

Rosida ist ein natives, rechenfähiges Notizbuch: Du schreibst Text und Python-Code in Zellen,
Rosida wertet sie aus und zeigt Formeln, Grafiken und Tabellen direkt im Dokument an. Gespeichert
wird als ganz normale `.md`-Datei – kein proprietäres Format, kein Web-Browser im Hintergrund.

## Starten

```bash
just run
```

Das startet die App über `uv run` mit allen benötigten Paketen (PySide6, SymPy, NumPy, Matplotlib,
Polars, qtawesome). Optional kann eine vorhandene `.md`-Datei direkt mitgegeben werden:

```bash
uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy --with qtawesome \
  src/app.py mein_dokument.md
```

## Grundprinzip: Zellen

Ein Dokument besteht aus einer Folge von **Zellen**. Jede Zelle ist entweder:

- **Python** – wird ausgeführt, letzter Ausdruck bzw. `print()`-Ausgabe wird angezeigt,
- **Text (Markdown)** – wird als formatierter Text gerendert (Überschriften, Formeln, `{{ }}`-Ausdrücke, ...),
- **Auto** – Rosida rät anhand des Inhalts, was gemeint ist (Standardmodus für neue Zellen).

| Aktion | Tastenkürzel |
|---|---|
| Zelle ausführen / rendern | `Shift+Enter` |
| Zurück in den Editor (aus der Ansicht) | Klick auf die Zelle, dann `Escape` zum Schließen |
| Modus umschalten (Auto → Python → Text) | `Ctrl+M` oder Klick auf die Modus-Pille |
| Zelle darüber / darunter einfügen | `Ctrl+Shift+A` / `Ctrl+Shift+B` |
| Aktive Zelle löschen | `Ctrl+Shift+D` |
| Alle Zellen ausführen | `Ctrl+Shift+Return` |
| Rückgängig / Wiederholen | `Cmd+Z` / `Cmd+Shift+Z` |

Eine Zelle klickst du jederzeit an, um sie zu bearbeiten – die Ausgabe verschwindet dabei nicht,
sie wird nur durch den Editor ersetzt, bis du mit `Shift+Enter` neu auswertest oder mit `Escape`
abbrichst.

**Zellen ohne sichtbare Ausgabe** (z. B. reine `import`- oder Variablendefinitionen) nehmen keinen
Platz weg – statt einer leeren Box erscheint links nur ein kleiner, gedämpfter „+"-Kreis. Klick
darauf öffnet den Editor wieder in voller Höhe.

Rosida führt allen Python-Code in einem **gemeinsamen Namespace** aus – Variablen aus einer Zelle
sind in allen folgenden Zellen sichtbar, ganz wie in einem Jupyter-Notebook. Vorbelegt sind:

```python
sp   # sympy
np   # numpy
plt  # matplotlib.pyplot
pl   # polars
```

## Beispiele

### Einfaches Python

```python
radius = 4
umfang = 2 * 3.14159 * radius
umfang
```

Zeigt `25.13272` als Ergebnis an (letzter Ausdruck der Zelle).

### NumPy

```python
werte = np.linspace(0, 10, 5)
np.mean(werte), np.std(werte)
```

### Matplotlib

Eine `Figure` als letzter Ausdruck einer Zelle wird direkt als Grafik eingebettet:

```python
fig, ax = plt.subplots(figsize=(6, 2.5))
x = np.linspace(0, 3, 200)
ax.plot(x, np.sin(x) * np.exp(x), color="#2563eb", lw=2)
ax.set_title("f(x) = sin(x)·eˣ")
fig
```

### SymPy

Symbolische Ausdrücke werden automatisch als LaTeX-Formel gerendert:

```python
x = sp.symbols("x")
f = sp.sin(x) * sp.exp(x)
sp.diff(f, x)
```

### Polars

```python
df = pl.DataFrame({"stadt": ["Zürich", "Bern", "Genf"], "einwohner": [434000, 134000, 203000]})
df
```

Polars-`DataFrame`s werden als interaktive Tabelle angezeigt (sortierbar, scrollbar).

## Text-Zellen: Formeln und Live-Ausdrücke

In einer Text-Zelle kannst du normales Markdown schreiben (`#`, `##`, `> Zitat`, `**fett**`,
`*kursiv*`, `` `code` ``), dazu:

- **LaTeX-Formeln**: `$ f(x) = x^2 $` (inline) oder `$$ \int_0^1 x^2\,dx $$` (Block), gerendert über
  Matplotlibs Mathtext-Engine.
- **`{{ ausdruck }}`**: wird live im gemeinsamen Namespace ausgewertet. Ein SymPy-Ergebnis wird
  automatisch zu LaTeX; alles andere wird als Text eingesetzt.

```markdown
Die Ableitung ist $ f'(x) = $ {{ sp.diff(f, x) }}

Der Umfang beträgt {{ umfang }} cm.
```

Steht `{{ ... }}` allein auf einer Zeile, wird das Ergebnis als zentrierte Blockformel gerendert
statt inline.

## Speichern & Laden

- `Cmd+S` speichert als `.md` – Python-Zellen werden als ` ```python `-Codeblöcke geschrieben,
  Text-Zellen bleiben rohes Markdown, mehrere Text-Zellen werden durch `---` getrennt.
- Der **Speichern**-Button ist nur aktiv, wenn seit dem letzten Speichern/Laden wirklich etwas
  geändert wurde. Bei einem neuen, noch nie gespeicherten Dokument öffnet `Cmd+S` automatisch den
  „Speichern unter…“-Dialog.
- `Cmd+O` öffnet eine bestehende `.md`-Datei und baut daraus wieder interaktive Zellen auf.
- **Datei → Zuletzt geöffnet** listet die letzten Dateien, die geöffnet oder gespeichert wurden.

Weil das Format reines Markdown ist, funktionieren normale Git-Diffs und Merges ohne Reibung.

## Export

Über **Datei → Exportieren** (oder Toolbar):

- **PDF** (`Ctrl+Shift+P`) – Vektor-Druck des gesamten Dokuments inkl. gerenderter Formeln, Plots
  und Tabellen.
- **Quarto** (`Ctrl+Shift+Q`) – schreibt eine `.qmd`-Datei. `{{ }}`-Ausdrücke in Text-Zellen werden
  dabei ebenfalls ausgewertet (SymPy → LaTeX, Polars → Quarto-Tabelle, Matplotlib-Figur → SVG-Datei
  neben dem `.qmd`), Python-Zellen landen als Codeblock samt letztem Ergebnis. Ideal, um ein
  Rosida-Dokument zu einem hübschen HTML/PDF/Typst-Report über Quarto weiterzuverarbeiten.

## Seitenleisten (Docks)

- **Dokumentstruktur** (`F3`, links): zeigt eine Gliederung aus den `#`/`##`/`###`-Überschriften
  deiner Text-Zellen sowie den Python-Zellen; Klick springt direkt zur Zelle.
- **LaTeX-Palette** (`F4`, rechts): anklickbare Kürzel für Kalkül (Bruch, Integral, Summe, ...),
  griechische Buchstaben, Symbole und Matrizen – fügt den Code an der Cursorposition der aktiven
  Zelle ein. Der eingeklappte Abschnitt **„Quarto (.qmd)"** enthält zusätzlich Callout-Boxen
  (`::: {.callout-note}` usw.), Fußnoten- und Cross-Reference-Bausteine für den Quarto-Export –
  diese werden in Rosidas eigener Live-Vorschau nur als Text angezeigt, erst ein echtes
  `quarto render` macht daraus die formatierten Boxen.

## Kleines Gesamtbeispiel

````markdown
# Gedämpfte Schwingung

Wir untersuchen $f(t) = e^{-\gamma t} \cos(\omega t)$.

---

```python
t, gamma, omega = sp.symbols("t gamma omega", positive=True)
f = sp.exp(-gamma * t) * sp.cos(omega * t)
f
```

Die erste Ableitung lautet {{ sp.diff(f, t) }}.

---

```python
werte = np.linspace(0, 10, 300)
fig, ax = plt.subplots(figsize=(6, 2.5))
ax.plot(werte, np.exp(-0.3 * werte) * np.cos(2 * werte), color="#2563eb")
ax.set_title("Numerischer Verlauf")
fig
```
````

Das ist im Kern schon alles, was du für den Einstieg brauchst – der Rest ergibt sich beim
Ausprobieren.

## Hilfe-Menü

- **Handbuch...** (`F1`) zeigt genau diese Anleitung in einem Dialog – nützlich, wenn kein
  Terminal/Browser griffbereit ist. Direkt nach der allerersten Installation öffnet sich dieser
  Dialog automatisch einmalig.
- **Über Rosida** zeigt Versionsnummer und Lizenz.
- **Einstellungen...** (`Cmd+,`) ist aktuell ein Platzhalter ohne Inhalt.
