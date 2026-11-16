"""Bidirectional hreflang declaration validation."""

from .tags import is_x_default


def find_one_way_links(declarations):
    """Return page pairs with a declaration in only one direction.

    The direction is between pages, not language tags. ``x-default`` is
    excluded, and repeated declarations for the same ordered page pair
    produce only one issue.
    """
    edges = set()
    for declaration in declarations:
        if is_x_default(declaration.language):
            continue
        if declaration.source == declaration.target:
            continue
        edges.add((declaration.source, declaration.target))

    issues = []
    seen = set()
    for source, target in sorted(edges):
        if (target, source) in edges:
            continue
        pair = tuple(sorted((source, target)))
        if pair in seen:
            continue
        seen.add(pair)
        issues.append({
            "type": "one_way_reciprocal",
            "pages": list(pair),
        })
    return issues
