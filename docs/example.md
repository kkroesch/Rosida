---
author: Karsten
date: 2026-09-29
status: draft
---

# Dämpfung und Resonanz

```python
a=23
b=42
```

Es sei a={{a}} und b={{b}}. Addiert gibt das {{a+b}}.

---

Untersuchung der Signalübertragungsfunktion $f(x) = \sin(x) \cdot e^x$.

Das unbestimmte Integral lautet:

$$\int \sin(x) e^x \, dx = \frac{e^x}{2} (\sin(x) - \cos(x)) + C$$

## Symbolische Ableitung mit SymPy

Hier berechnen wir die erste Ableitung $f'(x)$:

---

::: {.callout-tip}
Klicke auf eine Formel oder Grafik, um Code oder Text direkt zu bearbeiten. Mit Escape kehrst du in die Ansicht zurück.
:::

```python
x = sp.symbols('x')
f = sp.sin(x) * sp.exp(x)
sp.diff(f, x)
```

## Grafischer Verlauf

Visualisierung des Funktionsgraphen über das Intervall $[0, 3]$:

```python
fig, ax = plt.subplots(figsize=(7.0, 2.8), dpi=100)
x_vals = np.linspace(0, 3, 200)
y_vals = np.sin(x_vals) * np.exp(x_vals)
ax.plot(x_vals, y_vals, color='#2563eb', lw=2.2, label=r'$f(x) = \sin(x) e^x$')
ax.set_title('Funktionsverlauf', fontsize=11, color='#1e293b', pad=8)
ax.set_facecolor('#ffffff')
fig.patch.set_facecolor('#f8fafc')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(True, linestyle=':', alpha=0.6)
ax.legend(frameon=False, loc='upper left')
fig
```

Auch weitere Abbildungen können eingefügt werden, müssen aber ein einem separaten Block stehen.

---

![Screenshot der Abbildung](screenshot.png){#fig-screenshot}

```python
def fn(x):
    """ Syntax Highlighting Test """
    print(f"Die Antwort ist {x}.")

fn(42)
```
