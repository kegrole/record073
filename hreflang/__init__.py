"""Static hreflang declaration parsing and reciprocal-link auditing."""

from .parse import Declaration, collect, parse_html, parse_sitemap
from .report import build_report, load_config

__all__ = [
    "Declaration",
    "build_report",
    "collect",
    "load_config",
    "parse_html",
    "parse_sitemap",
]
