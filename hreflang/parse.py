"""Parse hreflang declarations from HTML pages and XML sitemaps."""

from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from .paths import find_html_files, site_path
from .tags import is_x_default, normalize_tag


class Declaration:
    """One normalized hreflang declaration made by a source page."""

    __slots__ = ("source", "language", "target", "origin")

    def __init__(self, source, language, target, origin):
        self.source = source
        self.language = language
        self.target = target
        self.origin = origin

    def __eq__(self, other):
        if not isinstance(other, Declaration):
            return NotImplemented
        return (
            self.source == other.source
            and self.language == other.language
            and self.target == other.target
            and self.origin == other.origin
        )

    def __repr__(self):
        return (
            "Declaration(source={!r}, language={!r}, target={!r}, "
            "origin={!r})"
        ).format(self.source, self.language, self.target, self.origin)


class _AlternateLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "link":
            return
        attributes = {name.lower(): value for name, value in attrs}
        rel_values = (attributes.get("rel") or "").lower().split()
        if "alternate" not in rel_values:
            return
        language = attributes.get("hreflang")
        href = attributes.get("href")
        if language is None or href is None:
            return
        self.links.append((language.strip(), href.strip()))


def parse_html(content, source_path):
    """Parse ``link rel=alternate`` hreflang entries from HTML text."""
    parser = _AlternateLinkParser()
    parser.feed(str(content))
    parser.close()
    declarations = []
    for raw_language, href in parser.links:
        language = normalize_tag(raw_language)
        target = site_path(href, source_path)
        declarations.append(
            Declaration(source_path, language, target, "html")
        )
    return declarations


def _local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def parse_sitemap(content, sitemap_path=None):
    """Parse ``xhtml:link`` entries, attributing each one to its ``loc``."""
    root = ElementTree.fromstring(content)
    declarations = []
    for url_node in root.iter():
        if _local_name(url_node.tag) != "url":
            continue
        loc = None
        for child in url_node:
            if _local_name(child.tag) == "loc" and child.text:
                loc = child.text.strip()
                break
        if loc is None:
            continue
        source = site_path(loc)
        for child in url_node:
            if _local_name(child.tag) != "link":
                continue
            attributes = {
                _local_name(name): (value or "").strip()
                for name, value in child.attrib.items()
            }
            rel_values = attributes.get("rel", "").lower().split()
            if "alternate" not in rel_values:
                continue
            language = attributes.get("hreflang")
            href = attributes.get("href")
            if not language or not href:
                continue
            declarations.append(
                Declaration(
                    source,
                    normalize_tag(language),
                    site_path(href, source),
                    "sitemap",
                )
            )
    return declarations


def collect(directory):
    """Collect all known pages and their HTML/sitemap declarations."""
    root = Path(directory)
    pages = []
    declarations = []
    for page, path in find_html_files(root):
        pages.append(page)
        declarations.extend(parse_html(path.read_text(encoding="utf-8"), page))

    sitemap = root / "sitemap.xml"
    if sitemap.is_file():
        declarations.extend(
            parse_sitemap(sitemap.read_text(encoding="utf-8"), sitemap)
        )

    return sorted(set(pages)), declarations
