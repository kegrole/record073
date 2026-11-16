"""Aggregate normalized declarations into an audit report."""

import json
from collections import OrderedDict
from pathlib import Path

from .reciprocal import find_one_way_links
from .tags import is_x_default, normalize_tag

DEFAULT_CONFIG_NAME = "hreflang.json"


def load_config(directory):
    """Load optional primary-page selection from ``hreflang.json``."""
    path = Path(directory) / DEFAULT_CONFIG_NAME
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("hreflang.json must contain a JSON object")

    config = {}
    for language, value in data.items():
        normalized = normalize_tag(language)
        if isinstance(value, dict):
            primary = value.get("primary")
            if primary is not None:
                config[normalized] = str(primary)
        elif value is not None:
            config[normalized] = str(value)
    return config


def _build_groups(pages, declarations, config):
    members = OrderedDict()
    for page in pages:
        members.setdefault(page, set())

    for declaration in declarations:
        if is_x_default(declaration.language):
            continue
        if declaration.source != declaration.target:
            continue
        if declaration.source not in members:
            continue
        members[declaration.source].add(declaration.language)

    groups = {}
    for page in sorted(members):
        for language in sorted(members[page]):
            groups.setdefault(language, set()).add(page)

    result = OrderedDict()
    for language in sorted(groups):
        group_pages = sorted(groups[language])
        group = {"pages": group_pages}
        primary = config.get(language)
        if primary is not None:
            if primary not in group_pages:
                raise ValueError(
                    "configured primary {!r} is not in language group {!r}"
                    .format(primary, language)
                )
            group["primary"] = primary
        result[language] = group
    return result


def build_report(pages, declarations, config=None):
    """Build the complete serializable hreflang audit report."""
    config = config or {}
    groups = _build_groups(pages, declarations, config)
    issues = find_one_way_links(declarations)

    has_x_default = any(
        is_x_default(declaration.language) for declaration in declarations
    )
    if not has_x_default:
        issues.append({
            "type": "missing_x_default",
            "pages": sorted(pages),
        })

    return OrderedDict((
        ("page_count", len(pages)),
        ("group_count", len(groups)),
        ("groups", groups),
        ("issues", issues),
    ))
