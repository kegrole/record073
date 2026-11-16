import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hreflang.parse import Declaration, collect, parse_sitemap
from hreflang.reciprocal import find_one_way_links
from hreflang.report import build_report, load_config
from hreflang.tags import is_x_default, normalize_tag


PAGES = ["/", "/cn-a/", "/cn-b/", "/cn-c/", "/cn/", "/en/", "/tw/",
         "/zh-hans/", "/zh-hant/"]

CONFIG = {
    "en": {"primary": "/"},
    "zh-Hans-CN": {"primary": "/cn-b/"},
}


def page_directory(path):
    return Path(".") if path == "/" else Path(path.lstrip("/"))


def write_page(directory, path, links):
    target = Path(directory) / page_directory(path) / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    link_tags = "\n".join(
        '  <link rel="alternate" hreflang="{lang}" href="{href}">'.format(
            lang=lang, href=href
        )
        for lang, href in links
    )
    target.write_text(
        "<!doctype html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
        + link_tags + "\n</head>\n<body></body>\n</html>\n",
        encoding="utf-8",
    )


def make_fixture(directory, include_x_default=True):
    fallback = [("x-default", "/")] if include_x_default else []
    page_links = {
        "/": [("en", "/")],
        "/en/": [("en", "/en/"), ("zh-Hans", "/zh-hans/")],
        "/zh-hans/": [
            ("zh-Hans", "/zh-hans/"),
            ("zh-Hant", "/zh-hant/"),
        ],
        "/zh-hant/": [
            ("zh-Hant", "/zh-hant/"),
            ("zh-Hans", "/zh-hans/"),
        ],
        "/cn-a/": [("zh-Hans-CN", "/cn-a/")],
        "/cn-b/": [("zh-hans-cn", "/cn-b/")],
        "/cn-c/": [],
        "/cn/": [("zh-CN", "/cn/")],
        "/tw/": [("zh-TW", "/tw/")],
    }
    for page in PAGES:
        write_page(directory, page, page_links[page] + fallback)

    sitemap = Path(directory) / "sitemap.xml"
    sitemap.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        "  <url>\n"
        "    <loc>/cn-c/</loc>\n"
        '    <xhtml:link rel="alternate" hreflang="zh_HANS_cn" '
        'href="/cn-c/"/>\n'
        "  </url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    config = Path(directory) / "hreflang.json"
    config.write_text(json.dumps(CONFIG), encoding="utf-8")
    return Path(directory)


class HreflangFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = make_fixture(self.temp_dir.name)
        self.pages, self.declarations = collect(self.directory)
        self.report = build_report(
            self.pages, self.declarations, load_config(self.directory)
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parser_finds_nine_pages_and_attributes_sitemap_to_loc(self):
        self.assertEqual(self.pages, PAGES)
        self.assertEqual(len(self.pages), 9)
        sitemap_text = (self.directory / "sitemap.xml").read_text()
        self.assertEqual(sitemap_text.count("<url>"), 1)
        sitemap_declarations = parse_sitemap(sitemap_text)
        self.assertEqual(len(sitemap_declarations), 1)
        declaration = sitemap_declarations[0]
        self.assertEqual(declaration.source, "/cn-c/")
        self.assertEqual(declaration.target, "/cn-c/")
        self.assertEqual(declaration.language, "zh-Hans-CN")
        self.assertEqual(declaration.origin, "sitemap")

    def test_exactly_one_one_way_reciprocal_issue(self):
        reciprocal_issues = [
            issue for issue in self.report["issues"]
            if issue["type"] == "one_way_reciprocal"
        ]
        self.assertEqual(len(reciprocal_issues), 1)
        self.assertEqual(
            reciprocal_issues[0]["pages"], ["/en/", "/zh-hans/"]
        )

    def test_separator_and_case_variants_share_one_group(self):
        self.assertEqual(
            normalize_tag("zh-Hans-CN"),
            normalize_tag("zh-hans-cn"),
        )
        self.assertEqual(
            normalize_tag("zh-Hans-CN"),
            normalize_tag("zh_HANS_cn"),
        )
        self.assertEqual(
            self.report["groups"]["zh-Hans-CN"]["pages"],
            ["/cn-a/", "/cn-b/", "/cn-c/"],
        )

    def test_regions_remain_distinct_and_script_is_not_merged(self):
        self.assertIn("zh-CN", self.report["groups"])
        self.assertIn("zh-TW", self.report["groups"])
        self.assertNotEqual(
            normalize_tag("zh-CN"), normalize_tag("zh-TW")
        )
        self.assertEqual(
            self.report["groups"]["zh-CN"]["pages"], ["/cn/"]
        )
        self.assertEqual(
            self.report["groups"]["zh-TW"]["pages"], ["/tw/"]
        )
        self.assertIn("zh-Hans", self.report["groups"])
        self.assertIn("zh-Hant", self.report["groups"])
        self.assertEqual(
            self.report["groups"]["zh-Hans"]["pages"], ["/zh-hans/"]
        )
        self.assertEqual(
            self.report["groups"]["zh-Hant"]["pages"], ["/zh-hant/"]
        )
        self.assertNotIn("zh-Hans-CN", self.report["groups"]["zh-Hans"])

    def test_groups_and_configured_primary_pages(self):
        self.assertEqual(self.report["page_count"], 9)
        self.assertEqual(self.report["group_count"], 6)
        self.assertEqual(
            set(self.report["groups"]),
            {"en", "zh-Hans", "zh-Hant", "zh-Hans-CN", "zh-CN", "zh-TW"},
        )
        self.assertNotIn("x-default", self.report["groups"])
        self.assertEqual(
            self.report["groups"]["en"]["pages"], ["/", "/en/"]
        )
        self.assertEqual(self.report["groups"]["en"]["primary"], "/")
        self.assertEqual(
            self.report["groups"]["zh-Hans-CN"]["primary"], "/cn-b/"
        )
        for language in ("en", "zh-Hans-CN"):
            primary = self.report["groups"][language]["primary"]
            self.assertEqual(
                self.report["groups"][language]["pages"].count(primary), 1
            )

    def test_missing_x_default_is_reported_once_when_all_are_removed(self):
        with tempfile.TemporaryDirectory() as without_default:
            make_fixture(without_default, include_x_default=False)
            pages, declarations = collect(without_default)
            report = build_report(
                pages, declarations, load_config(without_default)
            )
        missing = [
            issue for issue in report["issues"]
            if issue["type"] == "missing_x_default"
        ]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["pages"], PAGES)

    def test_report_contains_required_fields(self):
        self.assertIn("groups", self.report)
        self.assertIn("issues", self.report)
        for issue in self.report["issues"]:
            self.assertIn("type", issue)
            self.assertIn("pages", issue)


class RuleUnitTests(unittest.TestCase):
    def test_normalization_preserves_bcp47_meaning(self):
        self.assertEqual(normalize_tag("EN-us"), "en-US")
        self.assertEqual(normalize_tag("zh_hant_tw"), "zh-Hant-TW")
        self.assertEqual(normalize_tag("zh-CN"), "zh-CN")
        self.assertEqual(normalize_tag("zh-TW"), "zh-TW")
        self.assertEqual(normalize_tag("X-DEFAULT"), "x-default")
        self.assertTrue(is_x_default("X-Default"))

    def test_duplicate_one_way_declaration_counts_once(self):
        declarations = [
            Declaration("/a/", "en", "/b/", "html"),
            Declaration("/a/", "zh-Hans", "/b/", "html"),
        ]
        issues = find_one_way_links(declarations)
        self.assertEqual(
            issues,
            [{"type": "one_way_reciprocal", "pages": ["/a/", "/b/"]}],
        )

    def test_x_default_is_excluded_from_reciprocal_validation(self):
        declarations = [
            Declaration("/a/", "x-default", "/", "html"),
            Declaration("/", "x-default", "/", "html"),
        ]
        self.assertEqual(find_one_way_links(declarations), [])


class DemoAndCommandLineTests(unittest.TestCase):
    def test_committed_demo_matches_specification(self):
        directory = ROOT / "demo" / "pages"
        pages, declarations = collect(directory)
        report = build_report(pages, declarations, load_config(directory))
        self.assertEqual(report["page_count"], 9)
        self.assertEqual(report["group_count"], 6)
        self.assertEqual(len(report["issues"]), 1)
        self.assertEqual(
            report["issues"][0]["pages"], ["/en/", "/zh-hans/"]
        )

    def test_cli_writes_report_and_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "nested" / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hreflang.cli",
                    "--dir",
                    str(ROOT / "demo" / "pages"),
                    "--out",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(completed.stdout.count("\n"), 1)
            self.assertIn("pages=9", completed.stdout)
            self.assertIn("groups=6", completed.stdout)
            self.assertIn("issues=1", completed.stdout)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(set(report),
                             {"page_count", "group_count", "groups",
                              "issues"})


if __name__ == "__main__":
    unittest.main()
