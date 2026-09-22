from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QGridLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    """Einklappbarer Abschnitt mit Kopfzeile und kompaktem Inhalts-Container."""

    def __init__(
        self,
        title: str,
        content_widget: QWidget,
        parent=None,
        is_expanded: bool = True,
    ):
        super().__init__(parent)
        self.title = title
        self.is_expanded = is_expanded
        self.content_widget = content_widget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.toggle_btn = QPushButton(self)
        self.toggle_btn.setObjectName("section_header")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(is_expanded)
        self.toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle)

        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content_widget)

        self._update_state()

    def _toggle(self, checked: bool):
        self.is_expanded = checked
        self._update_state()

    def _update_state(self):
        arrow = "▾" if self.is_expanded else "▸"
        self.toggle_btn.setText(f"{arrow}  {self.title}")
        self.content_widget.setVisible(self.is_expanded)


class LatexPaletteDock(QDockWidget):
    """Einklappbares Dock mit mathematischen LaTeX-Kürzeln und fokusfreien Buttons."""

    insert_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__("LaTeX-Kürzel & Formeln", parent)
        self.setObjectName("LatexPaletteDock")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()
        content.setObjectName("palette_content")
        main_layout = QVBoxLayout(content)
        # Bündig nach oben ausrichten
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        content.setStyleSheet("""
            QWidget#palette_content {
                background-color: #f8fafc;
            }
            QPushButton#section_header {
                text-align: left;
                font-size: 11px;
                font-weight: 700;
                color: #475569;
                background-color: #e2e8f0;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 5px 8px;
            }
            QPushButton#section_header:hover {
                background-color: #cbd5e1;
                color: #0f172a;
            }
            QPushButton#snippet_btn {
                min-height: 28px;
                font-size: 13px;
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                color: #0f172a;
                padding: 2px 4px;
            }
            QPushButton#snippet_btn:hover {
                background-color: #f1f5f9;
                border-color: #94a3b8;
            }
            QPushButton#snippet_btn:pressed {
                background-color: #e2e8f0;
            }
        """)

        # Einklappbare Sektionen anlegen
        main_layout.addWidget(
            CollapsibleSection(
                "Kalkül", self._build_calculus_widget(), is_expanded=True
            )
        )
        main_layout.addWidget(
            CollapsibleSection(
                "Griechisch", self._build_greek_widget(), is_expanded=True
            )
        )
        main_layout.addWidget(
            CollapsibleSection(
                "Symbole", self._build_symbols_widget(), is_expanded=True
            )
        )
        main_layout.addWidget(
            CollapsibleSection(
                "Matrizen", self._build_matrices_widget(), is_expanded=True
            )
        )

        # Stretch am Ende drückt alle Sektionen und Buttons nach oben
        main_layout.addStretch()

        scroll.setWidget(content)
        self.setWidget(scroll)
        self.setMinimumWidth(260)

    def _create_btn(self, label: str, code: str, tip: str = "") -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("snippet_btn")
        btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        btn.setToolTip(f"{tip or label}\n{code}")
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda: self.insert_requested.emit(code))
        return btn

    def _build_calculus_widget(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 2, 0, 4)
        grid.setSpacing(4)
        snippets = [
            ("a/b", r"\frac{a}{b}", "Bruch"),
            ("d/dx", r"\frac{d}{dx}", "Ableitung"),
            ("∂/∂x", r"\frac{\partial}{\partial x}", "Partielle Ableitung"),
            ("∫ dx", r"\int f(x) \, dx", "Unbestimmtes Integral"),
            ("∫_a^b", r"\int_{a}^{b} f(x) \, dx", "Bestimmtes Integral"),
            ("∑", r"\sum_{i=1}^{n}", "Summe"),
            ("∏", r"\prod_{i=1}^{n}", "Produkt"),
            ("lim", r"\lim_{x \to \infty}", "Grenzwert"),
            ("√x", r"\sqrt{x}", "Quadratwurzel"),
            ("ⁿ√x", r"\sqrt[n]{x}", "n-te Wurzel"),
            ("xⁿ", r"x^{n}", "Potenz"),
            ("xₙ", r"x_{n}", "Index"),
        ]
        for idx, (lbl, code, tip) in enumerate(snippets):
            grid.addWidget(self._create_btn(lbl, code, tip), idx // 3, idx % 3)
        return container

    def _build_greek_widget(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 2, 0, 4)
        grid.setSpacing(4)
        letters = [
            ("α", r"\alpha"),
            ("β", r"\beta"),
            ("γ", r"\gamma"),
            ("δ", r"\delta"),
            ("ε", r"\varepsilon"),
            ("θ", r"\theta"),
            ("λ", r"\lambda"),
            ("μ", r"\mu"),
            ("π", r"\pi"),
            ("ρ", r"\rho"),
            ("σ", r"\sigma"),
            ("φ", r"\varphi"),
            ("ω", r"\omega"),
            ("Γ", r"\Gamma"),
            ("Δ", r"\Delta"),
            ("Θ", r"\Theta"),
            ("Λ", r"\Lambda"),
            ("Σ", r"\Sigma"),
            ("Φ", r"\Phi"),
            ("Ω", r"\Omega"),
        ]
        for idx, (lbl, code) in enumerate(letters):
            grid.addWidget(
                self._create_btn(lbl, code, f"Symbol {code}"),
                idx // 4,
                idx % 4,
            )
        return container

    def _build_symbols_widget(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 2, 0, 4)
        grid.setSpacing(4)
        syms = [
            ("±", r"\pm"),
            ("·", r"\cdot"),
            ("×", r"\times"),
            ("÷", r"\div"),
            ("∞", r"\infty"),
            ("≤", r"\leq"),
            ("≥", r"\geq"),
            ("≠", r"\neq"),
            ("≈", r"\approx"),
            ("∈", r"\in"),
            ("∀", r"\forall"),
            ("∃", r"\exists"),
            ("→", r"\to"),
            ("⇒", r"\implies"),
            ("⇔", r"\iff"),
            ("∇", r"\nabla"),
        ]
        for idx, (lbl, code) in enumerate(syms):
            grid.addWidget(self._create_btn(lbl, code, code), idx // 4, idx % 4)
        return container

    def _build_matrices_widget(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 2, 0, 4)
        grid.setSpacing(4)
        mat_2x2 = r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}"
        mat_3x3 = (
            r"\begin{pmatrix} a & b & c \\ d & e & f \\ g & h & i \end{pmatrix}"
        )
        vec_col = r"\begin{pmatrix} x \\ y \end{pmatrix}"
        vec_row = r"\begin{pmatrix} x & y \end{pmatrix}"

        grid.addWidget(
            self._create_btn("Matrix 2×2", mat_2x2, "2x2 Matrix"), 0, 0
        )
        grid.addWidget(
            self._create_btn("Matrix 3×3", mat_3x3, "3x3 Matrix"), 0, 1
        )
        grid.addWidget(
            self._create_btn("Vektor (Spalte)", vec_col, "Spaltenvektor"), 1, 0
        )
        grid.addWidget(
            self._create_btn("Vektor (Zeile)", vec_row, "Zeilenvektor"), 1, 1
        )
        return container
