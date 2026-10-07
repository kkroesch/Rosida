import base64
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
import sympy as sp


def _lines(text: str) -> list[str]:
    """nbformat stores multi-line strings as a list of lines, newlines kept."""
    return text.splitlines(keepends=True)


def _strip_fence(code: str) -> str:
    for fence in ("```python", "```py"):
        if code.startswith(fence) and code.rstrip().endswith("```"):
            return code[len(fence) :].strip("\n").rsplit("```", 1)[0].rstrip()
    return code


def _mime_bundle(val) -> dict:
    """MIME bundle for a cell result, mirroring what the cell shows in Rosida."""
    if isinstance(val, (sp.Basic, sp.MatrixBase)):
        return {
            "text/latex": _lines(f"$${sp.latex(val)}$$"),
            "text/plain": _lines(str(val)),
        }
    if isinstance(val, pl.DataFrame):
        return {
            "text/html": _lines(val._repr_html_()),
            "text/plain": _lines(str(val)),
        }
    if isinstance(val, plt.Figure):
        buf = io.BytesIO()
        val.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        return {
            "image/png": base64.b64encode(buf.getvalue()).decode("ascii"),
            "text/plain": ["<Figure>"],
        }
    return {"text/plain": _lines(str(val))}


class IpynbRenderer:
    def __init__(self):
        self.cells: list[dict] = []
        self._execution_count = 0

    def add_raw(self, text: str) -> None:
        self.cells.append(
            {"cell_type": "raw", "metadata": {}, "source": _lines(text)}
        )

    def add_markdown(self, text: str) -> None:
        self.cells.append(
            {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}
        )

    def add_code(self, code: str, stdout: str = "", value=None) -> None:
        outputs = []
        if stdout:
            outputs.append(
                {"output_type": "stream", "name": "stdout", "text": _lines(stdout)}
            )
        if value is not None:
            self._execution_count += 1
            outputs.append(
                {
                    "output_type": "execute_result",
                    "execution_count": self._execution_count,
                    "metadata": {},
                    "data": _mime_bundle(value),
                }
            )
        self.cells.append(
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": self._execution_count if value is not None else None,
                "outputs": outputs,
                "source": _lines(_strip_fence(code)),
            }
        )

    def dump(self, filepath: str) -> None:
        nb = {
            "cells": self.cells,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        out = Path(filepath)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
