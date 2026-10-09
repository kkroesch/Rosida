"""Zotero + Better BibTeX: local JSON-RPC interface (default port 23119).

Pure helpers only (request building, response parsing); the network calls
are made asynchronously by the References dock.
"""

from dataclasses import dataclass
import json

ZOTERO_RPC_URL = "http://127.0.0.1:23119/better-bibtex/json-rpc"
MAX_RESULTS = 50


@dataclass
class ZoteroEntry:
    key: str
    title: str
    authors: str
    year: str


def rpc_payload(method: str, params: list | None = None, request_id: int = 1) -> bytes:
    body = {"jsonrpc": "2.0", "method": method, "id": request_id}
    if params is not None:
        body["params"] = params
    return json.dumps(body).encode("utf-8")


def is_ready_response(data: bytes) -> bool:
    """True if the answer to `api.ready` shows a running Better BibTeX."""
    try:
        return "betterbibtex" in json.loads(data).get("result", {})
    except (ValueError, AttributeError, TypeError):
        return False


def format_authors(authors: list[dict]) -> str:
    """Family names only: 'Weitz', 'Weitz & Taleb', 'Weitz et al.'."""
    names = [a.get("family") or a.get("literal") or "" for a in authors]
    names = [n for n in names if n]
    if len(names) > 2:
        return f"{names[0]} et al."
    return " & ".join(names)


def parse_entries(data: bytes) -> list[ZoteroEntry]:
    """Converts the CSL-JSON answer of `item.search`; items without citation key are skipped."""
    try:
        items = json.loads(data).get("result") or []
    except (ValueError, AttributeError):
        return []
    entries = []
    for item in items:
        key = item.get("citekey") or item.get("citation-key")
        if not key:
            continue
        parts = (item.get("issued") or {}).get("date-parts") or [[]]
        year = str(parts[0][0]) if parts and parts[0] else ""
        entries.append(
            ZoteroEntry(
                key=key,
                title=item.get("title", ""),
                authors=format_authors(item.get("author") or item.get("editor") or []),
                year=year,
            )
        )
    return entries[:MAX_RESULTS]
