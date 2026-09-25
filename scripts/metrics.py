"""Erzeugt einen Code-Metriken-Report für src/ (Aufruf über `just metrics`).

Deckt ab:
- Lines of Code (SLOC/LOC/Kommentare) via radon
- Zyklomatische Komplexität (McCabe) via radon, inkl. Top-Ausreißer
- Wartbarkeitsindex (Maintainability Index) via radon
- Anzahl Klassen/Funktionen/Methoden via ast
- Lint-Findings via ruff (Default-Regelsatz)
- Möglicher toter Code via vulture

Absichtlich NICHT dabei: Docstring-Abdeckung. Der Projektstil verzichtet bewusst auf
Kommentare/Docstrings außer bei nicht-offensichtlichem WHY (siehe CLAUDE.md-Konvention),
so eine Metrik würde also die falsche Sache belohnen.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from radon.complexity import cc_visit, cc_rank
from radon.metrics import mi_visit, mi_rank
from radon.raw import analyze as raw_analyze
from radon.visitors import Class as RadonClass

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
REPORT_PATH = REPO_ROOT / "metrics-report.md"

TOP_N_COMPLEXITY = 10


@dataclass
class FunctionComplexity:
  qualname: str
  complexity: int
  lineno: int


@dataclass
class ModuleMetrics:
  path: Path
  sloc: int = 0
  loc: int = 0
  comments: int = 0
  blank: int = 0
  classes: int = 0
  functions: int = 0
  complexities: list[FunctionComplexity] = field(default_factory=list)
  mi: float | None = None

  @property
  def relpath(self) -> str:
    return str(self.path.relative_to(REPO_ROOT))

  @property
  def avg_complexity(self) -> float:
    if not self.complexities:
      return 0.0
    return sum(c.complexity for c in self.complexities) / len(self.complexities)


def discover_files() -> list[Path]:
  return sorted(p for p in SRC_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def analyze_file(path: Path) -> ModuleMetrics:
  source = path.read_text(encoding="utf-8")
  metrics = ModuleMetrics(path=path)

  raw = raw_analyze(source)
  metrics.sloc, metrics.loc = raw.sloc, raw.loc
  metrics.comments, metrics.blank = raw.comments, raw.blank

  try:
    tree = ast.parse(source, filename=str(path))
    metrics.classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    metrics.functions = sum(
      1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
  except SyntaxError:
    pass

  for block in cc_visit(source):
    if isinstance(block, RadonClass):
      continue
    qualname = f"{block.classname}.{block.name}" if getattr(block, "classname", None) else block.name
    metrics.complexities.append(FunctionComplexity(qualname, block.complexity, block.lineno))

  try:
    metrics.mi = mi_visit(source, True)
  except Exception:
    metrics.mi = None

  return metrics


def run_ruff() -> list[dict]:
  try:
    result = subprocess.run(
      ["ruff", "check", str(SRC_DIR), "--output-format=json"],
      capture_output=True,
      text=True,
    )
  except FileNotFoundError:
    return []
  try:
    return json.loads(result.stdout or "[]")
  except json.JSONDecodeError:
    return []


def run_vulture() -> list[str]:
  try:
    result = subprocess.run(
      ["vulture", str(SRC_DIR), "--min-confidence", "60"],
      capture_output=True,
      text=True,
    )
  except FileNotFoundError:
    return []
  return [line for line in result.stdout.splitlines() if line.strip()]


def _fmt_mi(mi: float | None) -> str:
  if mi is None:
    return "–"
  return f"{mi:.1f} ({mi_rank(mi)})"


# Notenbasierte Fortschrittsbalken, damit man "wie gut sind wir" auf einen Blick sieht.
# Die Balkenlänge folgt der Note (A-F), nicht dem Rohwert – so bleibt sie konsistent mit
# radons eigener Notenskala (z.B. MI ~60 ist Note A, aber nur "60% eines 100er-Balkens" wäre irreführend).
_GRADE_SCORE = {"A": 100, "B": 80, "C": 60, "D": 40, "E": 20, "F": 0}
_GRADE_ANSI = {
  "A": "\033[92m",  # hellgrün
  "B": "\033[32m",  # grün
  "C": "\033[33m",  # gelb
  "D": "\033[93m",  # hellgelb
  "E": "\033[31m",  # rot
  "F": "\033[91m",  # hellrot
}
_ANSI_RESET = "\033[0m"
_BAR_WIDTH = 20


def supports_color() -> bool:
  return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def render_bar(grade: str, width: int = _BAR_WIDTH, colored: bool = False) -> str:
  score = _GRADE_SCORE.get(grade, 0)
  filled = round(width * score / 100)
  bar = "█" * filled + "░" * (width - filled)
  if colored:
    color = _GRADE_ANSI.get(grade, "")
    return f"{color}{bar}{_ANSI_RESET} {grade}"
  return f"{bar} {grade}"


def rate_grade(count: int, sloc: int) -> str:
  """Bewertet eine Fundstellen-Zahl relativ zur Codegröße (Funde je 1000 SLOC).

  Heuristische Schwellwerte, keine offizielle Norm - dient nur der groben Einordnung."""
  rate = (count / sloc * 1000) if sloc else 0.0
  for limit, grade in [(5, "A"), (15, "B"), (30, "C"), (50, "D"), (80, "E")]:
    if rate < limit:
      return grade
  return "F"


def build_report(modules: list[ModuleMetrics], ruff_findings: list[dict], vulture_findings: list[str]) -> str:
  total_sloc = sum(m.sloc for m in modules)
  total_loc = sum(m.loc for m in modules)
  total_comments = sum(m.comments for m in modules)
  total_classes = sum(m.classes for m in modules)
  total_functions = sum(m.functions for m in modules)

  all_complexities = [(m, c) for m in modules for c in m.complexities]
  avg_complexity = (
    sum(c.complexity for _, c in all_complexities) / len(all_complexities) if all_complexities else 0.0
  )
  mi_values = [m.mi for m in modules if m.mi is not None]
  avg_mi = sum(mi_values) / len(mi_values) if mi_values else 0.0

  lines = [
    "# Rosida – Code-Metriken",
    "",
    f"Generiert am {datetime.now():%Y-%m-%d %H:%M} für {len(modules)} Python-Dateien unter `src/`.",
    "",
    "## Überblick",
    "",
    "| Metrik | Wert | Bewertung |",
    "|---|---|---|",
    f"| Dateien | {len(modules)} | |",
    f"| Zeilen (SLOC, ohne Blank/Kommentar) | {total_sloc} | |",
    f"| Zeilen gesamt (LOC) | {total_loc} | |",
    f"| Kommentarzeilen | {total_comments} | |",
    f"| Klassen | {total_classes} | |",
    f"| Funktionen/Methoden | {total_functions} | |",
  ]
  complexity_grade = cc_rank(round(avg_complexity)) if all_complexities else "A"
  mi_grade = mi_rank(avg_mi) if mi_values else "A"
  ruff_grade = rate_grade(len(ruff_findings), total_sloc)
  vulture_grade = rate_grade(len(vulture_findings), total_sloc)
  lines += [
    f"| Ø Zyklomatische Komplexität | {avg_complexity:.2f} ({complexity_grade}) | `{render_bar(complexity_grade)}` |",
    f"| Ø Wartbarkeitsindex (MI) | {avg_mi:.1f} ({mi_grade}) | `{render_bar(mi_grade)}` |",
    f"| Ruff-Findings (Default-Regelsatz) | {len(ruff_findings)} ({ruff_grade}) | `{render_bar(ruff_grade)}` |",
    f"| Vulture-Funde (möglicher toter Code, ≥60% Konfidenz) | {len(vulture_findings)} ({vulture_grade}) | `{render_bar(vulture_grade)}` |",
    "",
    "> Der Wartbarkeitsindex ist trotz Anzeige als Zahl 0–100 **kein Prozentwert** – radons "
    "eigene Notenskala setzt die Grenze zu Note A schon bei ca. 20. Ein MI um 60 mit Note A ist "
    "also gut, nicht mittelmäßig. Die Note in Klammern ist die verlässlichere Angabe. Komplexität "
    "und MI nutzen radons eigene Notenskala; die Noten für Ruff/Vulture sind eine eigene, "
    "heuristische Einordnung (Funde je 1000 SLOC) ohne offiziellen Standard dahinter.",
    "",
    "## Pro Modul",
    "",
    "| Datei | SLOC | Klassen | Funktionen | Ø Komplexität | MI |",
    "|---|---:|---:|---:|---:|---|",
  ]
  for m in sorted(modules, key=lambda m: m.relpath):
    lines.append(
      f"| `{m.relpath}` | {m.sloc} | {m.classes} | {m.functions} | {m.avg_complexity:.1f} | {_fmt_mi(m.mi)} |"
    )

  lines += ["", f"## Komplexeste Funktionen (Top {TOP_N_COMPLEXITY})", "", "| Funktion | Datei:Zeile | Komplexität | Note |", "|---|---|---:|---|"]
  top_complex = sorted(all_complexities, key=lambda mc: mc[1].complexity, reverse=True)[:TOP_N_COMPLEXITY]
  for m, c in top_complex:
    lines.append(f"| `{c.qualname}` | `{m.relpath}:{c.lineno}` | {c.complexity} | {cc_rank(c.complexity)} |")

  outliers = [m for m in modules if m.mi is not None and mi_rank(m.mi) != "A"]
  lines += ["", "## Wartbarkeits-Ausreißer", "", "Module mit MI-Note B oder schlechter (radons eigene Notenskala, nicht der Rohwert):"]
  if outliers:
    lines.append("")
    for m in sorted(outliers, key=lambda m: m.mi):
      lines.append(f"- `{m.relpath}` – MI {m.mi:.1f} ({mi_rank(m.mi)})")
  else:
    lines.append("")
    lines.append("Keine – alle Module liegen über der Schwelle.")

  lines += ["", "## Ruff-Findings", ""]
  if ruff_findings:
    by_code: dict[str, int] = {}
    for finding in ruff_findings:
      by_code[finding["code"]] = by_code.get(finding["code"], 0) + 1
    lines.append("| Regel | Anzahl | Beispiel |")
    lines.append("|---|---:|---|")
    examples = {f["code"]: f["message"] for f in ruff_findings}
    for code, count in sorted(by_code.items(), key=lambda kv: kv[1], reverse=True):
      lines.append(f"| `{code}` | {count} | {examples[code]} |")
  else:
    lines.append("Keine Findings (oder `ruff` war nicht installiert/erreichbar).")

  lines += [
    "",
    "## Möglicher toter Code (vulture)",
    "",
    "> **Vorsicht:** Vulture erkennt Qt-Callback-Methoden (`paintEvent`, `mouseMoveEvent`, "
    "Model-Methoden wie `rowCount`/`columnCount`/`headerData`, ...) fälschlich als \"unbenutzt\", "
    "da diese vom Qt-Framework aufgerufen werden, nicht aus sichtbarem Python-Code heraus. "
    "Vor dem Löschen jeden Fund einzeln prüfen.",
    "",
  ]
  if vulture_findings:
    for line in vulture_findings:
      relline = line.replace(str(SRC_DIR) + "/", "src/")
      lines.append(f"- `{relline}`")
  else:
    lines.append("Keine Funde (oder `vulture` war nicht installiert/erreichbar).")

  lines.append("")
  return "\n".join(lines)


def print_summary(modules: list[ModuleMetrics], ruff_findings: list[dict], vulture_findings: list[str]) -> None:
  total_sloc = sum(m.sloc for m in modules)
  total_classes = sum(m.classes for m in modules)
  total_functions = sum(m.functions for m in modules)
  all_complexities = [c for m in modules for c in m.complexities]
  avg_complexity = (
    sum(c.complexity for c in all_complexities) / len(all_complexities) if all_complexities else 0.0
  )
  mi_values = [m.mi for m in modules if m.mi is not None]
  avg_mi = sum(mi_values) / len(mi_values) if mi_values else 0.0

  colored = supports_color()
  complexity_grade = cc_rank(round(avg_complexity)) if all_complexities else "A"
  mi_grade = mi_rank(avg_mi) if mi_values else "A"
  ruff_grade = rate_grade(len(ruff_findings), total_sloc)
  vulture_grade = rate_grade(len(vulture_findings), total_sloc)

  print(f"Dateien:              {len(modules)}")
  print(f"SLOC gesamt:          {total_sloc}")
  print(f"Klassen:              {total_classes}")
  print(f"Funktionen/Methoden:  {total_functions}")
  print(f"Ø Komplexität:        {avg_complexity:5.2f}  {render_bar(complexity_grade, colored=colored)}")
  print(f"Ø Wartbarkeitsindex:  {avg_mi:5.1f}  {render_bar(mi_grade, colored=colored)}")
  print(f"Ruff-Findings:        {len(ruff_findings):5d}  {render_bar(ruff_grade, colored=colored)}")
  print(f"Vulture-Funde:        {len(vulture_findings):5d}  {render_bar(vulture_grade, colored=colored)}")
  print()
  print(f"Vollständiger Report: {REPORT_PATH.relative_to(REPO_ROOT)}")


def main() -> None:
  modules = [analyze_file(p) for p in discover_files()]
  ruff_findings = run_ruff()
  vulture_findings = run_vulture()

  report = build_report(modules, ruff_findings, vulture_findings)
  REPORT_PATH.write_text(report, encoding="utf-8")

  print_summary(modules, ruff_findings, vulture_findings)


if __name__ == "__main__":
  main()
