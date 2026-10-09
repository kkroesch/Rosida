import re

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import QPlainTextEdit


class CellHighlighter(QSyntaxHighlighter):
    def __init__(self, document, cell_type="python"):
        super().__init__(document)
        self.cell_type = cell_type

        # 1. PySide6-konforme Formate
        self.fmt_keyword = QTextCharFormat()
        self.fmt_keyword.setForeground(QColor("#D33682"))
        self.fmt_keyword.setFontWeight(QFont.Weight.Bold)

        self.fmt_string = QTextCharFormat()
        self.fmt_string.setForeground(QColor("#2AA198"))

        self.fmt_comment = QTextCharFormat()
        self.fmt_comment.setForeground(QColor("#93A1A1"))
        self.fmt_comment.setFontItalic(True)

        # 2. Regeln vorab kompilieren
        self.python_rules = []
        keywords = [
            "def",
            "class",
            "import",
            "from",
            "return",
            "if",
            "else",
            "elif",
            "for",
            "while",
            "pass",
            "break",
            "continue",
            "print",
        ]

        for kw in keywords:
            self.python_rules.append(
                (QRegularExpression(rf"\b{kw}\b"), self.fmt_keyword)
            )

        self.python_rules.append((QRegularExpression(r'".*?"'), self.fmt_string))
        self.python_rules.append((QRegularExpression(r"'.*?'"), self.fmt_string))
        self.python_rules.append((QRegularExpression(r"#.*"), self.fmt_comment))

        self._init_markdown_formats()

    # Markdown: Der Quelltext soll aussehen wie die gerenderte Zelle (CMU-Schriften
    # wie in DEFAULT_MARKDOWN_CSS), die Markierungszeichen treten grau zurück.
    _MD_MARKER = "#94a3b8"
    _MD_CODE_BG = "#f1f5f9"
    _MD_MATH = "#7c3aed"

    def _md_format(self, color=None, bold=False, italic=False, size=None, family=None, bg=None):
        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        if size:
            fmt.setFontPointSize(size)
        if family:
            fmt.setFontFamilies([family])
        if bg:
            fmt.setBackground(QColor(bg))
        return fmt

    def _init_markdown_formats(self):
        mono = "CMU Typewriter Text"
        self.md_marker = self._md_format(self._MD_MARKER)
        self.md_heading = {
            1: self._md_format("#0f172a", bold=True, size=22, family="CMU Sans Serif"),
            2: self._md_format("#0f172a", bold=True, size=18, family="CMU Sans Serif"),
            3: self._md_format("#334155", bold=True, size=16, family="CMU Sans Serif"),
        }
        self.md_quote = self._md_format("#64748b", italic=True)
        self.md_bold = self._md_format(bold=True)
        self.md_italic = self._md_format(italic=True)
        self.md_code = self._md_format("#0f172a", size=13, family=mono, bg=self._MD_CODE_BG)
        self.md_math = self._md_format(self._MD_MATH, size=13, family=mono)
        self.md_cite = self._md_format("#2563eb")

        self.md_inline_rules = [
            (re.compile(r"(?<!\\)\*\*[^*\n]+\*\*"), self.md_bold),
            (re.compile(r"(?<![*\\])\*[^*\s][^*\n]*\*(?!\*)"), self.md_italic),
            (re.compile(r"`[^`\n]+`"), self.md_code),
            (re.compile(r"(?<![\\$])\$[^$\n]+\$(?!\$)"), self.md_math),
            (re.compile(r"\[@[^\]\n]+\]"), self.md_cite),
        ]
        self.md_marker_rules = [
            re.compile(r"\*\*|(?<!\*)\*(?!\*)|`"),
            re.compile(r"^\s*(?:[-*+]|\d+\.)\s"),
        ]

    def _highlight_markdown(self, text: str):
        # Zustand 1: innerhalb eines $$-Blocks (Formel über mehrere Zeilen)
        in_math = self.previousBlockState() == 1
        stripped = text.strip()
        if stripped.startswith("$$") and not (len(stripped) > 2 and stripped.endswith("$$")):
            in_math = not in_math
            self.setCurrentBlockState(1 if in_math else 0)
            self.setFormat(0, len(text), self.md_math)
            return
        if in_math:
            self.setCurrentBlockState(1)
            self.setFormat(0, len(text), self.md_math)
            return
        self.setCurrentBlockState(0)

        heading = re.match(r"^(#{1,6})(\s+)", text)
        if heading:
            level = min(len(heading.group(1)), 3)
            self.setFormat(0, len(text), self.md_heading[level])
            self.setFormat(0, heading.end(), self.md_marker)
            return
        if text.startswith(">"):
            self.setFormat(0, len(text), self.md_quote)
            self.setFormat(0, 1, self.md_marker)
            return

        for pattern, fmt in self.md_inline_rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)
        for pattern in self.md_marker_rules:
            for m in pattern.finditer(text):
                # nur die Farbe grau setzen, der Schriftschnitt bleibt erhalten
                marker = QTextCharFormat(self.format(m.start()))
                marker.setForeground(QColor(self._MD_MARKER))
                self.setFormat(m.start(), m.end() - m.start(), marker)

    def set_mode(self, mode):
        """Schaltet den Modus um und triggert das sofortige Neuzeichnen."""
        if self.cell_type != mode:
            self.cell_type = mode
            self.rehighlight()  # Das ist der magische Qt-Befehl!

    def highlightBlock(self, text):
        if self.cell_type == "markdown":
            self._highlight_markdown(text)
            return
        if self.cell_type != "python":
            return

        for pattern, fmt in self.python_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
