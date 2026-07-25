#!/usr/bin/env python3
"""Flatten the app into one self-contained HTML file.

Needed for hosts that serve a single document with no sibling assets (and
where a strict CSP blocks external requests anyway). Output is byte-identical
in behaviour to the multi-file version — same CSS, same JS, same data.

    python3 pins/tools/inline.py -o /tmp/pin-board.html
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        sys.exit(f'error: missing {p} — run build_catalog.py first')
    return p.read_text()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--strip-head', action='store_true',
                    help='drop <html>/<head>/<body> scaffolding, for hosts that supply it')
    args = ap.parse_args()

    html = read('index.html')

    # </script> inside a JS string would close the tag early; nothing in this
    # codebase does that today, but guard anyway since data is generated.
    def shield(js: str) -> str:
        return js.replace('</script', '<\\/script')

    css = read('css/app.css')
    html = re.sub(r'<link rel="stylesheet" href="css/app\.css">',
                  lambda m: '<style>\n' + css + '\n</style>', html, count=1)

    for src in ('data/catalog.js', 'data/sources.js', 'js/app.js'):
        js = shield(read(src))
        pat = r'<script src="' + re.escape(src) + r'"></script>'
        if not re.search(pat, html):
            sys.exit(f'error: no <script> tag found for {src}')
        html = re.sub(pat, lambda m, js=js: '<script>\n' + js + '\n</script>', html, count=1)

    if '<link rel="stylesheet"' in html or re.search(r'<script src=', html):
        sys.exit('error: an external reference survived inlining')

    if args.strip_head:
        # keep the pre-paint theme script, which lives in <head>
        head = re.search(r'<head>(.*?)</head>', html, re.S)
        body = re.search(r'<body>(.*?)</body>', html, re.S)
        if not (head and body):
            sys.exit('error: could not split head/body')
        keep = '\n'.join(
            m.group(0) for m in re.finditer(r'<script>.*?</script>|<style>.*?</style>',
                                            head.group(1), re.S))
        html = keep + '\n' + body.group(1)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f'{out} — {len(html) / 1024:.0f} KB, fully self-contained')
    return 0


if __name__ == '__main__':
    sys.exit(main())
