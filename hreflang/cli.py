"""Command-line interface for the hreflang auditor."""

import argparse
import json
from pathlib import Path

from .parse import collect
from .report import build_report, load_config


def create_parser():
    parser = argparse.ArgumentParser(
        description="Audit HTML and sitemap hreflang declarations."
    )
    parser.add_argument(
        "--dir",
        required=True,
        dest="directory",
        help="Directory containing HTML pages, sitemap.xml and hreflang.json",
    )
    parser.add_argument(
        "--out",
        help="Optional JSON report output path",
    )
    return parser


def run(argv=None):
    args = create_parser().parse_args(argv)
    directory = Path(args.directory)
    pages, declarations = collect(directory)
    report = build_report(pages, declarations, load_config(directory))

    if args.out:
        output = Path(args.out)
        if output.parent and not output.parent.exists():
            output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    print(
        "pages={page_count} groups={group_count} issues={issue_count}"
        .format(
            page_count=report["page_count"],
            group_count=report["group_count"],
            issue_count=len(report["issues"]),
        )
    )
    return report


def main(argv=None):
    run(argv)


if __name__ == "__main__":
    main()
