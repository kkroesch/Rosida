from pathlib import Path
import re
import matplotlib.pyplot as plt
import polars as pl
import sympy as sp


def df_to_qmd_table(df: pl.DataFrame, caption: str = "Tabelle", tbl_id: str = "tbl-data") -> str:
    """Erzeugt eine Quarto-Tabelle mit Beschriftung und Referenzanker."""
    header = "| " + " | ".join(df.columns) + " |"
    sep = "| " + " | ".join(["---"] * df.width) + " |"
    rows = [
        "| " + " | ".join("" if v is None else str(v) for v in row) + " |"
        for row in df.iter_rows()
    ]
    table_str = "\n".join([header, sep] + rows)
    return f"\n\n{table_str}\n\n: {caption} {{#{tbl_id}}}\n\n"


class QmdRenderer:
    def __init__(self, output_dir: Path, asset_subfolder: str = "assets"):
        self.output_dir = Path(output_dir)
        self.assets_dir = self.output_dir / asset_subfolder
        self.asset_subfolder = asset_subfolder
        self.fig_counter = 0

    def _save_figure(self, fig: plt.Figure, caption: str = "Visualisierung") -> str:
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.fig_counter += 1
        filename = f"fig_{self.fig_counter}.svg"
        fig_id = f"fig-{self.fig_counter}"

        fig.savefig(self.assets_dir / filename, format="svg", bbox_inches="tight")
        plt.close(fig)
        return f"\n\n![{caption}]({self.asset_subfolder}/{filename}){{#{fig_id}}}\n\n"

    def format_value(self, val, is_block: bool = False) -> str:
        if isinstance(val, (sp.Expr, sp.Matrix)):
            latex = sp.latex(val)
            return f"\n$$\n{latex}\n$$\n" if is_block else f"${latex}$"

        if isinstance(val, pl.DataFrame):
            return df_to_qmd_table(val)

        if isinstance(val, plt.Figure):
            return self._save_figure(val)

        if isinstance(val, float):
            return f"{val:.4f}"

        return str(val)

    def render(self, template: str, context: dict, metadata: dict | None = None) -> str:
        # 1. YAML Frontmatter generieren
        meta = metadata or {}
        yaml_lines = ["---"]
        for key, value in meta.items():
            if isinstance(value, dict):
                yaml_lines.append(f"{key}:")
                for sub_k, sub_v in value.items():
                    yaml_lines.append(f"  {sub_k}: {sub_v}")
            else:
                yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---\n\n")

        frontmatter = "\n".join(yaml_lines) if meta else ""

        # 2. Template-Variablen auflösen
        def replacer(match: re.Match) -> str:
            expr = match.group(1).strip()
            try:
                val = eval(expr, {}, context)
                start = match.string.rfind("\n", 0, match.start()) + 1
                end = match.string.find("\n", match.end())
                prefix = match.string[start:match.start()].strip()
                suffix = match.string[match.end():end].strip() if end != -1 else match.string[match.end():].strip()
                is_block = (prefix == "" and suffix == "")
                return self.format_value(val, is_block=is_block)
            except Exception as e:
                return f"`[Fehler: {expr} -> {e}]`"

        body = re.sub(r"\{\{\s*(.*?)\s*\}\}", replacer, template)
        return frontmatter + body


def export_to_qmd(template_text: str, context: dict, out_qmd_path: Path, metadata: dict | None = None):
    out_qmd_path = Path(out_qmd_path)
    renderer = QmdRenderer(output_dir=out_qmd_path.parent)

    # Standard-Metadaten für Typst & HTML, falls keine übergeben werden
    default_meta = {
        "title": "Berechnungsbericht",
        "format": {
            "typst": "default",
            "html": "default"
        }
    }
    meta = {**default_meta, **(metadata or {})}

    qmd_content = renderer.render(template_text, context, metadata=meta)
    out_qmd_path.parent.mkdir(parents=True, exist_ok=True)
    out_qmd_path.write_text(qmd_content, encoding="utf-8")
