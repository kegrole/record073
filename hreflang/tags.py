"""Language-tag normalization following the BCP 47 casing convention."""

import re

_GRANDFATHERED_TAGS = frozenset((
    "art-lojban",
    "cel-gaulish",
    "no-bok",
    "no-nyn",
    "zh-guoyu",
    "zh-hakka",
    "zh-min",
    "zh-min-nan",
    "zh-xiang",
))


def normalize_tag(tag):
    """Return a canonical BCP 47 representation of *tag*.

    Case and separator differences are normalized, so ``zh-Hans-CN``,
    ``zh-hans-cn`` and ``zh_HANS_cn`` become the same value. Region
    subtags remain distinct, therefore ``zh-CN`` and ``zh-TW`` are
    never merged.
    """
    if tag is None:
        raise ValueError("language tag must not be None")

    text = str(tag).strip()
    if not text:
        raise ValueError("language tag must not be empty")
    if text.lower() == "x-default":
        return "x-default"

    subtags = re.split(r"[-_]+", text.lower())
    if text.lower() in _GRANDFATHERED_TAGS:
        return text.lower()

    normalized = [subtags[0]]
    after_private = False
    for subtag in subtags[1:]:
        if subtag == "x":
            after_private = True
            normalized.append(subtag)
        elif after_private:
            after_private = True
            normalized.append(subtag)
        elif len(subtag) == 2 and subtag.isalpha():
            normalized.append(subtag.upper())
        elif len(subtag) == 4 and subtag.isalpha():
            normalized.append(subtag.title())
        elif len(subtag) >= 4 and subtag.isalnum():
            normalized.append(subtag.title())
        else:
            normalized.append(subtag.upper() if subtag.isalpha() else subtag)
    return "-".join(normalized)


def is_x_default(tag):
    """Return whether a raw or normalized tag is the hreflang fallback."""
    return str(tag).strip().lower() == "x-default"
