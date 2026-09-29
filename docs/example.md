---
title: "Pendel"
date: 2024-04-25
math: true
authors:
    - name: "Karsten"
    - image: "/avatar.jpg"
tags: ["physik"]
summary: "Am Beispiel eines einfachen Pendels zeige ich die Anwendung der theoretischen Mechanik zur Aufstellung und Lösung von Differentialgleichungen. Neben der analytischen Lösung und der numerischen Lösung mit dem Runge-Kutta-Verfahren zeige ich auch die Modellierung mit analogen Schaltkreisen als Alternative."
categories:
  - "Science"
cover: pendulum.png
---

# Das Pendel

Eines der einfachsten Experimente, anhand dessen man
Bewegungsgleichungen erklären kann, ist das Pendel, das sich im
Schwerefeld bewegt. Wie immer in solchen Fällen nehmen wir zunächst an,
dass das Schwerefeld homogen, die Masse punktförmig und der
Luftwiderstand zu vernachlässigen sei.

---

## Der Hamilton-Formalismus

Um die Bewegungsgleichung eines einfachen Pendels mit Hilfe des
*Hamilton-Formalismus* herzuleiten, folgen wir diesen
Schritten:

**Ausdruck für die kinetische Energie $T$:** Die kinetische Energie
eines Pendels ist gegeben durch die Bewegung der Masse an seinem Ende.
Bei einem Pendel der Länge $l$ und einer Masse $m$, das um einen Winkel
$\theta$ ausgelenkt wird, ist die Geschwindigkeit des Pendelendes
$v = l\dot{\theta}$ (wobei $\dot{\theta}$ die zeitliche Ableitung von
$\theta$ ist). Daher ist die kinetische Energie
$$T = \frac{1}{2} m v^2 = \frac{1}{2} m (l\dot{\theta})^2.$$

---

**Ausdruck für die potenzielle Energie $V$:** Die potenzielle Energie
wird durch die Höhe des Pendelendes über seinem tiefsten Punkt bestimmt.
Wenn das Pendel um den Winkel $\theta$ ausgelenkt wird, ist die Höhe
$h = l(1 - \cos\theta)$. Die potenzielle Energie ist dann
$$V = mgh = mg l(1 - \cos\theta),$$
wobei $g$ die Erdbeschleunigung ist.

---

**Hamilton-Funktion $H$):** Die Hamilton-Funktion $H$ ist die Summe aus
kinetischer und potenzieller Energie, aber ausgedrückt in
generalisierten Koordinaten und Impulsen. Im Falle des Pendels gibt es nur eine abhängige Koordniate: Den Auslenkungswinkel $\theta$. Es ist viel praktischer, nur diese Koordinate zu betrachten, als kompliziert zu kartesischen Koordinaten umzurechnen. Ein weiterer praktischer Umstand ist, dass die Ebene, in der das Pendel schwingt, immer gleich bleibt. Dass dem so ist, sieht man am [Foucaultschen Pendel](https://de.wikipedia.org/wiki/Foucaultsches_Pendel). Eine formalere Betrachtung findet sich in der Infobox.

---

Der generalisierte Impuls $p$
bezogen auf $\theta$ ist
$$p = \frac{\partial T}{\partial \dot{\theta}} = m l^2 \dot{\theta}$$
Dann drücken wir $\dot{\theta}$ in $p$ aus und setzen es in den Ausdruck
für $T$ ein. Die Hamilton-Funktion ist
$$H = T + V = \frac{p^2}{2ml^2} + mg l(1 - \cos\theta).$$

---

**Hamiltonsche Bewegungsgleichungen:** Die Hamiltonschen Gleichungen
lauten
$$\dot{\theta} = \frac{\partial H}{\partial p}, \quad \dot{p} = -\frac{\partial H}{\partial \theta}.$$

Aus der ersten Gleichung erhalten wir $$\dot{\theta} = \frac{p}{ml^2}.$$
Die zweite Gleichung liefert
$$\dot{p} = -\frac{\partial H}{\partial \theta} = -mg l \sin\theta.$$

---

**Bewegungsgleichung:** Ersetzen wir $p$ in der zweiten Hamiltonschen
Gleichung durch $m l^2 \dot{\theta}$, erhalten wir die
Bewegungsgleichung: $$ml^2 \ddot{\theta} = -mg l \sin\theta.$$
Vereinfacht ergibt sich: $$\ddot{\theta} = -\frac{g}{l} \sin\theta.$$

---

Diese Gleichung beschreibt die Bewegung eines einfachen Pendels im
Rahmen des Hamilton-Formalismus. Sie gilt für kleine
Winkelapproximationen, wobei $\sin\theta \approx \theta$ angenommen
wird. Für größere Winkel muss man die volle Sinusfunktion
berücksichtigen. Die Lösung der Bewegungsgleichung für ein einfaches
Pendel, insbesondere im Falle kleiner Winkelauslenkungen, kann mit einer
Approximation erreicht werden. Die Differentialgleichung, die wir zuvor
hergeleitet haben, ist:

$$\ddot{\theta} = -\frac{g}{l} \sin\theta.$$

Für kleine Winkel kann man $\sin\theta$ durch $\theta$ annähern, was die
Gleichung zu einer linearen Differentialgleichung macht:

$$\ddot{\theta} = -\frac{g}{l} \theta.$$

---

Diese Gleichung ist eine Standardform der harmonischen Bewegung. Ihre
allgemeine Lösung ist:

$$\theta(t) = A \cos(\omega t + \phi),$$

dabei ist $A$ die Amplitude der Schwingung ist (maximaler
Winkelausschlag), $\omega = \sqrt{\frac{g}{l}}$ die Winkelfrequenz der
Schwingung, $\phi$ die Phasenverschiebung, abhängig von den
Anfangsbedingungen (z.B. Anfangsauslenkung und Anfangsgeschwindigkeit)
und $t$ die Zeit.

---

## Numerische Lösung

Für größere Winkel ist die Lösung der Bewegungsgleichung deutlich
komplexer und kann elliptische Funktionen involvieren, da die Näherung
$\sin\theta \approx \theta$ nicht mehr gültig ist. In diesem Fall ist
eine numerische Lösung oft der praktikabelste Weg.

---

Das *Runge-Kutta-Verfahren der vierten Ordnung (RK4)* ist ein weit
verbreitetes und effektives numerisches Verfahren zur Lösung von
Differentialgleichungen. Es bietet eine gute Balance zwischen
Genauigkeit und Rechenaufwand. Um RK4 auf die Bewegungsgleichung des
Pendels anzuwenden, verwenden wir erneut die beiden Gleichungen, die das
System beschreiben:

$$\begin{aligned}   \dot{\theta} &= \omega \\   \dot{\omega} &= -\frac{g}{l} \sin\theta \end{aligned}$$

---

Das RK4-Verfahren verwendet vier Approximationen ($k1$, $k2$, $k3$,
$k4$) für die Steigung der Funktion und nimmt deren gewichteten
Durchschnitt, um eine präzisere Schätzung des nächsten Werts zu
erhalten.

Für jeden Schritt berechnen wir:

Für $\theta$:

$$k1 = \Delta t \cdot \omega$$
$$k2 = \Delta t \cdot (\omega + \frac{k1}{2})$$
$$k3 = \Delta t \cdot (\omega + \frac{k2}{2})$$
$$k4 = \Delta t \cdot (\omega + k3)$$
$$\theta_{\text{nächste}} = \theta + \frac{1}{6}(k1 + 2k2 + 2k3 + k4)$$

Für $\omega$:

$$l1 = \Delta t \cdot (-\frac{g}{l} \sin\theta)$$
$$l2 = \Delta t \cdot (-\frac{g}{l} \sin(\theta + \frac{l1}{2}))$$
$$l3 = \Delta t \cdot (-\frac{g}{l} \sin(\theta + \frac{l2}{2}))$$
$$l4 = \Delta t \cdot (-\frac{g}{l} \sin(\theta + l3))$$
$$\omega_{\text{nächste}} = \omega + \frac{1}{6}(l1 + 2l2 + 2l3 + l4)$$

Man beginnt mit Anfangswerten für $\theta$ und $\omega$ und wiederholt
diesen Prozess mit einer festgelegten Schrittgröße $\Delta t$ über den
gewünschten Zeitraum.

---

Im Vergleich zum Euler-Verfahren ist RK4 deutlich genauer, insbesondere
bei komplexeren Differentialgleichungen oder wenn eine höhere
Genauigkeit erforderlich ist. Allerdings ist es auch rechenintensiver.
Listing [5](#lst:rk4.py){reference-type="ref" reference="lst:rk4.py"}
zeigt eine Beispielimplementierung mit *SciPy*.

---

## Gedämpfte Schwingung

Die Bewegungsgleichung für ein gedämpftes Pendel, bei dem die Dämpfung
durch Luftwiderstand oder Reibung im Aufhängungspunkt berücksichtigt
wird, kann durch eine lineare Differentialgleichung zweiter Ordnung
beschrieben werden, wenn die Auslenkung klein ist. Die allgemeine Form
dieser Gleichung lautet:

$$\ddot{\theta} + 2\gamma\dot{\theta} + \omega_0^2\theta = 0$$
Dabei ist
$\gamma$ der Dämpfungskoeffizient, der die Stärke der Dämpfung bestimmt,
und $\omega_0 = \sqrt{g / L}$ die ungedämpfte Eigenkreisfrequenz des
Pendels. Die Lösung dieser Differentialgleichung hängt von den
Anfangsbedingungen und dem Wert des Dämpfungskoeffizienten $\gamma$ ab.
Für unterkritische Dämpfung ($\gamma < \omega_0$) beispielsweise hat die
Lösung die Form:

$$\theta(t) = \Theta e^{-\gamma t} \cos(\omega_d t + \phi)$$

wobei:

-   $\Theta$ die Amplitude der Anfangsauslenkung ist,
-   $\omega_d = \sqrt{\omega_0^2 - \gamma^2}$ die gedämpfte
    Eigenfrequenz des Pendels
-   $\phi$ die Phasenverschiebung ist, die von den Anfangsbedingungen
    abhängt.

---

Diese Lösung beschreibt eine Schwingung, deren Amplitude exponentiell
mit der Zeit abnimmt, was charakteristisch für ein gedämpftes System
ist.

```python
import numpy as np
import matplotlib.pyplot as plt

# Pendelparameter
g = 9.81  # Erdbeschleunigung in m/s^2
l = 1.0   # Länge in Metern

# RK4 Setup
t_max = 4.0
dt = 0.04
n_steps = int(t_max / dt)

t = np.linspace(0, t_max, n_steps)
theta = np.zeros(n_steps)
omega = np.zeros(n_steps)

# Anfangsbedingungen
theta[0] = 0.5
omega[0] = 0.0

# Der explizite RK4-Loop (Pure NumPy)
for i in range(n_steps - 1):
    th = theta[i]
    om = omega[i]
    
    k1_th = om
    k1_om = -(g / l) * np.sin(th)
    
    k2_th = om + 0.5 * dt * k1_om
    k2_om = -(g / l) * np.sin(th + 0.5 * dt * k1_th)
    
    k3_th = om + 0.5 * dt * k2_om
    k3_om = -(g / l) * np.sin(th + 0.5 * dt * k2_th)
    
    k4_th = om + dt * k3_om
    k4_om = -(g / l) * np.sin(th + dt * k3_th)
    
    theta[i+1] = th + (dt / 6.0) * (k1_th + 2*k2_th + 2*k3_th + k4_th)
    omega[i+1] = om + (dt / 6.0) * (k1_om + 2*k2_om + 2*k3_om + k4_om)

# Plot aufbauen
fig, ax = plt.subplots(figsize=(7.0, 2.8), dpi=100)
ax.plot(t, theta, color='#2563eb', lw=2.2, label=r'$f(x) = \sin(x)$')
ax.plot(t, omega, color='#ff63ef', lw=2.2, label=r'$f(x) = \sin(x)$')
ax.set_title('Funktionsverlauf', fontsize=11, color='#1e293b', pad=8)
ax.set_facecolor('#ffffff')
fig.patch.set_facecolor('#f8fafc')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(True, linestyle=':', alpha=0.6)
ax.legend(frameon=False, loc='upper left')
fig
```
