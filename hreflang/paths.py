"""Site-relative path helpers shared by HTML and sitemap parsers."""

from pathlib import Path
from urllib.parse import urldefrag, urlsplit

def site_path(href, base_path=None):
    """Convert an href to a root-relative site path.

    Absolute URLs keep their path component. Relative URLs are resolved
    against *base_path*, which must itself be a root-relative directory
    path ending in ``/`` when supplied.
    """
    if href is None:
        raise ValueError("href must not be None")
    value = str(href).strip()
    if not value:
        raise ValueError("href must not be empty")

    value, _fragment = urldefrag(value)
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        path = parts.path or "/"
    elif value.startswith("/"):
        path = value
    else:
        base = base_path or "/"
        if not base.endswith("/"):
            base = base.rsplit("/", 1)[0] + "/"
        path = base + value

    if not path.startswith("/"):
        path = "/" + path
    parts_stack = []
    for segment in path.split("/"):
        if segment == "..":
            if parts_stack:
                parts_stack.pop()
        elif segment and segment != ".":
            parts_stack.append(segment)
    result = "/" + "/".join(parts_stack)
    if path != "/" and path.endswith("/") and not result.endswith("/"):
        result += "/"
    return result or "/"


def file_site_path(path, root):
    """Return the site path represented by an HTML file under *root*."""
    relative = Path(path).resolve().relative_to(Path(root).resolve())
    name = relative.name
    if name in ("index.html", "index.htm"):
        relative = relative.parent
        text = "/" if str(relative) == "." else "/" + relative.as_posix() + "/"
    else:
        text = "/" + relative.as_posix()
    return text


def find_html_files(directory):
    """Find HTML files deterministically, paired with their site paths."""
    root = Path(directory)
    files = []
    candidates = [root, *root.rglob("*")]
    for path in sorted(candidates, key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        if path.suffix.lower() in (".html", ".htm"):
            files.append((file_site_path(path, root), path))
    return files
