from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QTextBrowser,
    QVBoxLayout,
)

from config.i18n import (
    LANGUAGES,
    SYSTEM,
    language_setting,
    set_language_setting,
    system_language,
    ui_language,
)

from .base import RosidaAction

APP_VERSION = "0.3.0"

_FIRST_RUN_SETTINGS_KEY = "help/manual_shown_on_first_run"


def _find_quickstart_path() -> Path | None:
    """Sucht das Handbuch in der Oberflächensprache (docs/quickstart.<lang>.md),
    sonst docs/quickstart.md, im App-Bundle (Resources/docs) und im Checkout."""
    src_dir = Path(__file__).resolve().parent.parent
    names = [f"quickstart.{ui_language()}.md", "quickstart.md"]
    for name in names:
        for docs_dir in (src_dir / "docs", src_dir.parent / "docs"):
            if (docs_dir / name).exists():
                return docs_dir / name
    return None


def show_manual_dialog(parent):
    """Zeigt das Handbuch (docs/quickstart.md) in einem einfachen, schreibgeschützten Dialog."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(QCoreApplication.translate("Manual", "Rosida – Manual"))
    dialog.resize(760, 680)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(0, 0, 0, 0)

    browser = QTextBrowser(dialog)
    browser.setOpenExternalLinks(True)
    browser.setStyleSheet(
        "QTextBrowser { border: none; padding: 16px; font-size: 13px; }"
    )

    path = _find_quickstart_path()
    if path is not None:
        browser.setMarkdown(path.read_text(encoding="utf-8"))
    else:
        browser.setPlainText(
            QCoreApplication.translate(
                "Manual",
                "The manual (docs/quickstart.md) was not found.\n\n"
                "In a development checkout it is located at docs/quickstart.md.",
            )
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
        super().__init__(QCoreApplication.translate("ManualAction", "&Manual..."), parent)
        self.win = main_window

        self.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.setToolTip(self.tr("Show the quick start guide with examples (F1)"))
        self.set_icon_name("fa5s.book")

        self.triggered.connect(self._execute)

    def _execute(self):
        show_manual_dialog(self.win)


class AboutAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("AboutAction", "&About Rosida"), parent)
        self.win = main_window

        self.setMenuRole(QAction.MenuRole.AboutRole)
        self.setToolTip(self.tr("About Rosida"))
        self.set_icon_name("fa5s.info-circle")

        self.triggered.connect(self._execute)

    def _execute(self):
        QMessageBox.about(
            self.win,
            self.tr("About Rosida"),
            "<h3>Rosida</h3>"
            + self.tr("<p>Version {0}</p>").format(APP_VERSION)
            + self.tr(
                "<p>Native computational notebook for macOS &amp; Linux – Python, "
                "SymPy, NumPy, Matplotlib and Polars right in the document, "
                "saved as plain Markdown.</p>"
            )
            + self.tr("<p>MIT license.</p>"),
        )


class SettingsAction(RosidaAction):
    def __init__(self, main_window, parent=None):
        super().__init__(QCoreApplication.translate("SettingsAction", "&Settings..."), parent)
        self.win = main_window

        self.setShortcut(QKeySequence.StandardKey.Preferences)
        self.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.setToolTip(self.tr("Settings (Cmd+, / Ctrl+,)"))
        self.set_icon_name("fa5s.cog")

        self.triggered.connect(self._execute)

    def _execute(self):
        dialog = QDialog(self.win)
        dialog.setWindowTitle(self.tr("Settings"))
        dialog.resize(420, 160)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        layout.addLayout(form)

        language = QComboBox()
        system_name = LANGUAGES[system_language()]
        language.addItem(self.tr("System language ({0})").format(system_name), SYSTEM)
        for code, name in LANGUAGES.items():
            language.addItem(name, code)
        language.setCurrentIndex(language.findData(language_setting()))
        form.addRow(self.tr("Language:"), language)

        hint = QLabel(self.tr("Changes to the language take effect after a restart."))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(hint)
        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        choice = language.currentData()
        if choice != language_setting():
            set_language_setting(choice)
            self.win.statusbar.showMessage(
                self.tr("Language will change after restarting Rosida."), 5000
            )
