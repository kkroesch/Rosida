from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QTextBrowser, QVBoxLayout

from .base import RosidaAction

APP_VERSION = "0.2.0"

_FIRST_RUN_SETTINGS_KEY = "help/manual_shown_on_first_run"


def _find_quickstart_path() -> Path | None:
  """Sucht docs/quickstart.md sowohl im Entwicklungs-Checkout als auch im gebauten App-Bundle."""
  src_dir = Path(__file__).resolve().parent.parent
  candidates = [
    src_dir / "docs" / "quickstart.md",          # gebündeltes App-Bundle (Resources/docs/...)
    src_dir.parent / "docs" / "quickstart.md",   # Entwicklungs-Checkout (repo_root/docs/...)
  ]
  for candidate in candidates:
    if candidate.exists():
      return candidate
  return None


def show_manual_dialog(parent):
  """Zeigt das Handbuch (docs/quickstart.md) in einem einfachen, schreibgeschützten Dialog."""
  dialog = QDialog(parent)
  dialog.setWindowTitle("Rosida – Handbuch")
  dialog.resize(760, 680)

  layout = QVBoxLayout(dialog)
  layout.setContentsMargins(0, 0, 0, 0)

  browser = QTextBrowser(dialog)
  browser.setOpenExternalLinks(True)
  browser.setStyleSheet("QTextBrowser { border: none; padding: 16px; font-size: 13px; }")

  path = _find_quickstart_path()
  if path is not None:
    browser.setMarkdown(path.read_text(encoding="utf-8"))
  else:
    browser.setPlainText(
      "Das Handbuch (docs/quickstart.md) wurde nicht gefunden.\n\n"
      "Im Entwicklungs-Checkout liegt es unter docs/quickstart.md."
    )
  layout.addWidget(browser)

  dialog.exec()


def maybe_show_manual_on_first_run(main_window):
  """Öffnet das Handbuch automatisch beim allerersten Start von Rosida."""
  settings = QSettings()
  if settings.value(_FIRST_RUN_SETTINGS_KEY, False, type=bool):
    return
  settings.setValue(_FIRST_RUN_SETTINGS_KEY, True)
  show_manual_dialog(main_window)


class ManualAction(RosidaAction):

  def __init__(self, main_window, parent=None):
    super().__init__("&Handbuch...", parent)
    self.win = main_window

    self.setShortcut(QKeySequence.StandardKey.HelpContents)
    self.setToolTip("Kurzanleitung mit Beispielen anzeigen (F1)")
    self.set_icon_name("fa5s.book")

    self.triggered.connect(self._execute)

  def _execute(self):
    show_manual_dialog(self.win)


class AboutAction(RosidaAction):

  def __init__(self, main_window, parent=None):
    super().__init__("&Über Rosida", parent)
    self.win = main_window

    self.setMenuRole(QAction.MenuRole.AboutRole)
    self.setToolTip("Über Rosida")
    self.set_icon_name("fa5s.info-circle")

    self.triggered.connect(self._execute)

  def _execute(self):
    QMessageBox.about(
      self.win,
      "Über Rosida",
      "<h3>Rosida</h3>"
      f"<p>Version {APP_VERSION}</p>"
      "<p>Natives, rechenfähiges Notizbuch für macOS &amp; Linux – Python, SymPy, NumPy, "
      "Matplotlib und Polars direkt im Dokument, gespeichert als reines Markdown.</p>"
      "<p>MIT-Lizenz.</p>",
    )


class SettingsAction(RosidaAction):

  def __init__(self, main_window, parent=None):
    super().__init__("&Einstellungen...", parent)
    self.win = main_window

    self.setShortcut(QKeySequence.StandardKey.Preferences)
    self.setMenuRole(QAction.MenuRole.PreferencesRole)
    self.setToolTip("Einstellungen (Cmd+, / Ctrl+,)")
    self.set_icon_name("fa5s.cog")

    self.triggered.connect(self._execute)

  def _execute(self):
    dialog = QDialog(self.win)
    dialog.setWindowTitle("Einstellungen")
    dialog.resize(420, 260)

    layout = QVBoxLayout(dialog)
    hint = QLabel("Noch keine Einstellungen verfügbar.")
    hint.setStyleSheet("color: #94a3b8; padding: 24px; font-size: 13px;")
    hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(hint)

    dialog.exec()
