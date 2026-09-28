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

        # 2. Regeln vorab kompilieren (nur wenn es eine Python-Zelle ist)
        self.python_rules = []
        if self.cell_type == "python":
            keywords = ["def", "class", "import", "from", "return", "if", "else",
                        "elif", "for", "while", "pass", "break", "continue", "print"]

            for kw in keywords:
                self.python_rules.append((QRegularExpression(rf"\b{kw}\b"), self.fmt_keyword))

            self.python_rules.append((QRegularExpression(r'".*?"'), self.fmt_string))
            self.python_rules.append((QRegularExpression(r"'.*?'"), self.fmt_string))
            self.python_rules.append((QRegularExpression(r"#.*"), self.fmt_comment))


    def set_mode(self, mode):
            """Schaltet den Modus um und triggert das sofortige Neuzeichnen."""
            if self.cell_type != mode:
                self.cell_type = mode
                self.rehighlight()  # Das ist der magische Qt-Befehl!

    def highlightBlock(self, text):
        # Wenn wir nicht im Python-Modus sind, mach gar nichts (spart CPU)
        if self.cell_type != "python":
            return

        for pattern, fmt in self.python_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
