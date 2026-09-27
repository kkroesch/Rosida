import matplotlib.pyplot as plt
import numpy as np


def f(X, Y):
    """Zu untersuchende Funktion f(x, y).

    Ungültige Bereiche (z. B. Division durch 0 oder negative Wurzeln)
    werden über np.nan maskiert.
    """
    # Beispiel: f(x, y) = 1 / sqrt(16 - x^2 - y^2)
    Z = 16 - X**2 - Y**2
    Z[Z <= 0] = np.nan 
    return 1 / np.sqrt(Z)

def f2(X,Y):
    return 2*X**2 + Y**2


# 1. Gitter definieren
x = np.linspace(-5, 5, 800)
y = np.linspace(-5, 5, 800)
X, Y = np.meshgrid(x, y)
Z = f(X, Y)

# 2. Plot konfigurieren
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": ":",
    }
)

fig, ax = plt.subplots(figsize=(7, 6), dpi=150)

# 3. Diskreter Hintergrund (Filled Contours) für den Verlauf
bg_levels = np.linspace(np.nanmin(Z) if not np.isnan(np.nanmin(Z)) else 0, 6, 50)
cf = ax.contourf(X, Y, Z, levels=bg_levels, cmap="cividis", alpha=0.35, extend="both")
cbar = fig.colorbar(cf, ax=ax, shrink=0.85, pad=0.04)
cbar.set_label("$f(x, y)$", rotation=0, labelpad=15)

# 4. Spezifische Niveaus hervorheben
target_levels = [0, 0.5, 1, 5]
cs = ax.contour(
    X,
    Y,
    Z,
    levels=target_levels,
    colors="#1f2937",
    linewidths=1.8,
    linestyles="solid",
)

# Konturlabels direkt auf die Linien setzen
ax.clabel(
    cs,
    inline=True,
    fontsize=9,
    fmt=lambda val: f"c = {val:g}",
    manual=False,
)

# 5. Geometrie und Beschriftung
ax.set_aspect("equal", adjustable="box")
ax.set_title(r"Niveaumengen $f(x, y) = c$", pad=12, fontweight="medium")
ax.set_xlabel("$x$")
ax.set_ylabel("$y$")

# Achsenkreuz durch den Ursprung
ax.axhline(0, color="gray", lw=0.6, alpha=0.6)
ax.axvline(0, color="gray", lw=0.6, alpha=0.6)

plt.tight_layout()
plt.show()
