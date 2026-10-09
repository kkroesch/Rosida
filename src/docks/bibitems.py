from html import escape
from pathlib import Path

from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QStackedWidget,
    QFileDialog,
    QLineEdit,
)
from PySide6.QtCore import QCoreApplication, QSize, QTimer, QUrl, Signal, Qt
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from exporters import zotero
from exporters.bibtex import load_bibliography


class BibItemWidget(QWidget):
    """Fehlertolerantes UI-Element für einen einzelnen Zettelkasten-Eintrag."""

    def __init__(self, key, author="", title="", parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        # Fallbacks für unsaubere BibTeX-Daten
        display_author = author if author else self.tr("Unknown author")
        display_title = title if title else self.tr("No title")

        layout.addWidget(QLabel(f"<b>[{key}]</b>"))
        layout.addWidget(QLabel(f"<i>{display_author}</i>"))

        lbl_title = QLabel(display_title)
        lbl_title.setWordWrap(True)
        layout.addWidget(lbl_title)


class ZoteroItemWidget(QLabel):
    """Title, 'Author Year' and the citation key as a link."""

    link_clicked = Signal(str)

    def __init__(self, entry: "zotero.ZoteroEntry", parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setContentsMargins(8, 6, 8, 6)

        title = escape(entry.title) or self.tr("No title")
        who = " ".join(p for p in (escape(entry.authors), escape(entry.year)) if p)
        who = who or self.tr("Unknown author")
        self.setText(
            f"<b>{title}</b><br><i>{who}</i><br>"
            f'<a href="{escape(entry.key, quote=True)}">[@{escape(entry.key)}]</a>'
        )
        self.linkActivated.connect(self.link_clicked)


class BibDock(QDockWidget):
    """Dock-Widget mit integriertem Stack für nahtloses Umschalten zwischen Button und Liste."""

    # Sendet ausschließlich den fertigen Quarto-String nach außen (z.B. "[@Asimov1956]")
    citation_selected = Signal(str)
    # Vom Benutzer gewählte .bib-Datei (absoluter Pfad); das Hauptfenster
    # trägt sie als bibliography in die Frontmatter ein.
    bib_file_chosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__(QCoreApplication.translate("BibDock", "References"), parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.stack = QStackedWidget()
        self.setWidget(self.stack)

        # Seite 0: Initialer Lade-Button
        self.btn_load = QPushButton(self.tr("Load references (.bib)"))
        self.btn_load.clicked.connect(self.choose_bib_file)
        self.lbl_hint = QLabel()
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("color: #64748b; font-size: 11px;")

        page_load = QWidget()
        page_load_layout = QVBoxLayout(page_load)
        page_load_layout.addWidget(self.btn_load)
        page_load_layout.addWidget(self.lbl_hint)
        page_load_layout.addStretch()

        # Seite 1: Die scrollbare Literatur-Liste mit Dateiname und Wechsel-Button
        self.lbl_source = QLabel()
        self.lbl_source.setStyleSheet("color: #64748b; font-size: 11px;")
        btn_change = QPushButton(self.tr("Change …"))
        btn_change.setToolTip(self.tr("Choose another bibliography file"))
        btn_change.clicked.connect(self.choose_bib_file)
        header = QHBoxLayout()
        header.setContentsMargins(4, 4, 4, 0)
        header.addWidget(self.lbl_source, 1)
        header.addWidget(btn_change)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        page_list = QWidget()
        page_list_layout = QVBoxLayout(page_list)
        page_list_layout.setContentsMargins(0, 0, 0, 0)
        page_list_layout.addLayout(header)
        page_list_layout.addWidget(self.list_widget)

        # Seite 2: Zotero-Suche (Better BibTeX)
        self.btn_zotero = QPushButton(self.tr("Zotero"))
        self.btn_zotero.setToolTip(self.tr("Search the Zotero library"))
        self.btn_zotero.clicked.connect(lambda: self._choose_view("zotero"))
        header.addWidget(self.btn_zotero)
        self.btn_zotero.hide()

        lbl_zotero = QLabel(self.tr("Zotero library"))
        lbl_zotero.setStyleSheet("color: #64748b; font-size: 11px;")
        btn_bib = QPushButton(self.tr("Use .bib …"))
        btn_bib.setToolTip(self.tr("Use a BibTeX file instead of Zotero"))
        btn_bib.clicked.connect(lambda: self._choose_view("bib"))
        zotero_header = QHBoxLayout()
        zotero_header.setContentsMargins(4, 4, 4, 0)
        zotero_header.addWidget(lbl_zotero, 1)
        zotero_header.addWidget(btn_bib)

        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(self.tr("Author, title or citation key"))
        self.search_edit.textChanged.connect(self._search_timer_restart)

        self.lbl_zotero_hint = QLabel()
        self.lbl_zotero_hint.setWordWrap(True)
        self.lbl_zotero_hint.setStyleSheet("color: #64748b; font-size: 11px;")

        self.zotero_list = QListWidget()
        self.zotero_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        page_zotero = QWidget()
        page_zotero_layout = QVBoxLayout(page_zotero)
        page_zotero_layout.setContentsMargins(4, 0, 4, 4)
        page_zotero_layout.addLayout(zotero_header)
        page_zotero_layout.addWidget(self.search_edit)
        page_zotero_layout.addWidget(self.lbl_zotero_hint)
        page_zotero_layout.addWidget(self.zotero_list, 1)

        self.stack.addWidget(page_load)
        self.stack.addWidget(page_list)
        self.stack.addWidget(page_zotero)
        self._start_dir = ""

        # Zotero-Anbindung: Verfügbarkeit regelmäßig prüfen, Suche entprellt
        self._net = QNetworkAccessManager(self)
        self._zotero_ok = False
        self._has_bib = False
        self._view: str | None = None  # explizite Wahl des Benutzers: "zotero" | "bib"
        self._ping_reply: QNetworkReply | None = None
        self._search_reply: QNetworkReply | None = None
        self._search_timer = QTimer(self, singleShot=True, interval=300)
        self._search_timer.timeout.connect(self._run_search)
        self._ping_timer = QTimer(self, interval=10_000)
        self._ping_timer.timeout.connect(self._check_zotero)
        self._ping_timer.start()
        QTimer.singleShot(0, self._check_zotero)

    def choose_bib_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Choose BibTeX file"),
            self._start_dir,
            self.tr("BibTeX (*.bib)") + ";;" + self.tr("All files (*)"),
        )
        if file_path:
            self.bib_file_chosen.emit(file_path)

    def show_bibliography(self, files: list[Path], start_dir: str = ""):
        """Loads the given .bib files, or shows the load button if there are none.

        Missing files are named in a hint below the button.
        """
        self._start_dir = start_dir
        existing = [f for f in files if f.is_file()]
        missing = [f.name for f in files if not f.is_file()]

        entries = []
        for f in existing:
            entries.extend(self._parse_bibtex_lightweight(f))
        self.populate_list(entries)

        self._has_bib = bool(existing)
        if existing:
            self.lbl_source.setText(", ".join(f.name for f in existing))
            self.lbl_source.setToolTip("\n".join(str(f) for f in existing))
        else:
            self.lbl_hint.setText(
                self.tr("Not found: {0}").format(", ".join(missing)) if missing else ""
            )
        self._update_page()

    # --- Zotero ---------------------------------------------------------

    def _choose_view(self, view: str):
        if view == "bib" and not self._has_bib:
            self.choose_bib_file()
            return
        self._view = view
        self._update_page()

    def _update_page(self):
        """Zotero search if Zotero is running and no .bib is set (or chosen explicitly)."""
        self.btn_zotero.setVisible(self._zotero_ok)
        use_zotero = self._zotero_ok and (
            self._view == "zotero" or (self._view is None and not self._has_bib)
        )
        if use_zotero:
            self.stack.setCurrentIndex(2)
        else:
            self.stack.setCurrentIndex(1 if self._has_bib else 0)

    def _post(self, method: str, params: list | None = None) -> QNetworkReply:
        request = QNetworkRequest(QUrl(zotero.ZOTERO_RPC_URL))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        # Zotero weist Browser-User-Agents ("Mozilla/…", Qt-Standard) ab.
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "Rosida")
        request.setTransferTimeout(2000)
        return self._net.post(request, zotero.rpc_payload(method, params))

    def _check_zotero(self):
        if self._ping_reply is not None:
            return
        reply = self._ping_reply = self._post("api.ready")
        reply.finished.connect(lambda: self._on_ping_finished(reply))

    def _on_ping_finished(self, reply: QNetworkReply):
        self._ping_reply = None
        ok = reply.error() == QNetworkReply.NetworkError.NoError and zotero.is_ready_response(
            bytes(reply.readAll())
        )
        reply.deleteLater()
        if ok != self._zotero_ok:
            self._zotero_ok = ok
            self._update_page()

    def _search_timer_restart(self):
        self._search_timer.start()

    def _run_search(self):
        term = self.search_edit.text().strip()
        if self._search_reply is not None:
            self._search_reply.abort()
        if not term:
            self.zotero_list.clear()
            self.lbl_zotero_hint.setText("")
            return
        reply = self._search_reply = self._post("item.search", [term])
        reply.finished.connect(lambda: self._on_search_finished(reply))

    def _on_search_finished(self, reply: QNetworkReply):
        if reply is not self._search_reply:  # überholt oder abgebrochen
            reply.deleteLater()
            return
        self._search_reply = None
        failed = reply.error() != QNetworkReply.NetworkError.NoError
        data = bytes(reply.readAll())
        reply.deleteLater()

        if failed:
            self.lbl_zotero_hint.setText(self.tr("Zotero is not reachable."))
            return
        entries = zotero.parse_entries(data)
        self.lbl_zotero_hint.setText("" if entries else self.tr("No results."))
        self.populate_zotero(entries)

    def populate_zotero(self, entries):
        self.zotero_list.clear()
        for entry in entries:
            widget = ZoteroItemWidget(entry)
            widget.link_clicked.connect(lambda key: self.citation_selected.emit(f"[@{key}]"))
            item = QListWidgetItem(self.zotero_list)
            self.zotero_list.setItemWidget(item, widget)
        self._fit_zotero_items()

    def _fit_zotero_items(self):
        """Item heights depend on the wrapped text, i.e. on the current width."""
        width = self.zotero_list.viewport().width()
        for i in range(self.zotero_list.count()):
            item = self.zotero_list.item(i)
            widget = self.zotero_list.itemWidget(item)
            item.setSizeHint(QSize(width, widget.heightForWidth(width)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_zotero_items()

    def _parse_bibtex_lightweight(self, file_path):
        """Einträge als dicts (key, author, title) für die Liste."""
        return [
            {
                "key": entry.key,
                "author": "; ".join(entry.authors),
                "title": entry.get("title"),
            }
            for entry in load_bibliography([Path(file_path)]).values()
        ]

    def populate_list(self, entries):
        self.list_widget.clear()

        for entry in entries:
            item = QListWidgetItem(self.list_widget)

            # Widget mit Fallbacks initialisieren
            custom_widget = BibItemWidget(
                key=entry.get("key", "Unknown"),
                author=entry.get("author", ""),
                title=entry.get("title", ""),
            )

            # Größe anpassen und den Key unsichtbar im Item hinterlegen
            item.setSizeHint(custom_widget.sizeHint())
            item.setData(Qt.UserRole, entry.get("key", ""))

            self.list_widget.setItemWidget(item, custom_widget)

    def on_item_double_clicked(self, item):
        bib_key = item.data(Qt.UserRole)
        if bib_key:
            self.citation_selected.emit(f"[@{bib_key}]")
