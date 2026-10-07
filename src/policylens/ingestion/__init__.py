"""Document ingestion module for PolicyLens."""

from policylens.ingestion.chunker import (
    Chunk,
    chunk_pages,
    chunk_text,
    get_text_splitter,
)
from policylens.ingestion.cleaner import (
    clean_text,
    fix_hyphenated_line_breaks,
    normalize_unicode,
    normalize_whitespace,
)
from policylens.ingestion.heading_detector import (
    canonicalize_heading,
    detect_section_heading,
    is_subtitle_line,
    split_text_into_sections,
)
from policylens.ingestion.metadata import (
    ChunkMetadata,
    build_chunk_metadata,
    compute_content_hash,
    generate_doc_id,
    get_document_metadata,
    load_manifest,
)
from policylens.ingestion.parser import (
    DEFAULT_LOW_TEXT_THRESHOLD,
    EmptyPDFError,
    InvalidPDFError,
    ParsedPage,
    PDFParserError,
    parse_pdf,
)
from policylens.ingestion.validators import (
    is_toc_page,
    is_valid_chunk,
)

__all__ = [
    "DEFAULT_LOW_TEXT_THRESHOLD",
    "Chunk",
    "ChunkMetadata",
    "EmptyPDFError",
    "InvalidPDFError",
    "PDFParserError",
    "ParsedPage",
    "build_chunk_metadata",
    "canonicalize_heading",
    "chunk_pages",
    "chunk_text",
    "clean_text",
    "compute_content_hash",
    "detect_section_heading",
    "fix_hyphenated_line_breaks",
    "generate_doc_id",
    "get_document_metadata",
    "get_text_splitter",
    "is_subtitle_line",
    "is_toc_page",
    "is_valid_chunk",
    "load_manifest",
    "normalize_unicode",
    "normalize_whitespace",
    "parse_pdf",
    "split_text_into_sections",
]
