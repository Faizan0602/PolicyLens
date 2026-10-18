"""Extract document/page citations without verifying their evidence support."""

import re

# Match one ASCII or Unicode bracket pair; the conditional requires matching closers.
_CITATION_PATTERN = re.compile(
    r"(?<![\[【])(?:(?P<ascii>\[)|【)"
    r"(?P<doc_id>[A-Za-z0-9_-]+) p\.(?P<page>[1-9][0-9]*)"
    r"(?(ascii)\]|】)(?![\]】])"
)


def parse_citations(answer: str) -> list[dict[str, str | int]]:
    """Extract [doc_id p.N] or 【doc_id p.N】 in order, retaining full IDs and duplicates.

    Malformed citations and [Source N] tags are ignored. IDs may contain ASCII
    letters, digits, underscores, or hyphens; no length limit is imposed.
    Pages use positive decimal integers without leading zeros. This checks
    syntax only, not document existence or whether evidence supports a claim.
    """
    return [
        {"doc_id": match.group("doc_id"), "page": int(match.group("page"))}
        for match in _CITATION_PATTERN.finditer(answer)
    ]
