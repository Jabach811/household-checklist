#!/usr/bin/env python3
"""Build pins/data/catalog.js and pins/data/sources.js from research JSON.

The catalog is generated, never hand-edited. Drop segment files shaped like
``{"segment": "...", "pins": [...]}`` into a research directory and run:

    python3 pins/tools/build_catalog.py --research <dir>

Records are normalised, validated, and de-duplicated. Anything that fails
validation is reported and skipped rather than silently coerced, so a bad
research pass can't quietly poison the catalog.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from datetime import date

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent / 'data'

FRANCHISES = {'Disney', 'Pixar', 'Star Wars', 'Marvel', 'Wizarding World', 'Other'}
EDITIONS = {
    'Open Edition', 'Limited Edition', 'Limited Release', 'Mystery', 'Hidden Mickey',
    'Cast Exclusive', 'Annual Passholder', 'Artist Proof', 'Pre-Production', 'Retail', 'Unknown',
}
RARITIES = {'common', 'uncommon', 'rare', 'very-rare', 'grail'}
CONFIDENCE = {'high', 'medium', 'low'}

STR_FIELDS = [
    'name', 'franchise', 'property', 'series', 'series_position', 'release_date',
    'origin', 'park_specific', 'edition_type', 'size_mm', 'backstamp',
    'pinpics_id', 'sku', 'rarity', 'notes', 'image_url', 'confidence',
    'price_confidence', 'board_note', 'item_kind',
]
NUM_FIELDS = [
    'year', 'edition_size', 'retail_price_usd',
    'market_low_usd', 'market_median_usd', 'market_high_usd',
]
LIST_FIELDS = ['characters', 'pin_type', 'tags', 'source_urls']

# Deep-link templates. The research pass can override or extend these via
# url-templates.json; these are the verified-by-hand baseline so the app always
# has working price links even with no research input.
DEFAULT_SOURCES = [
    {
        'id': 'ebay-sold', 'name': 'eBay — sold', 'kind': 'sold-comps',
        'url_template': 'https://www.ebay.com/sch/i.html?_nkw={QUERY}&LH_Sold=1&LH_Complete=1&_sop=13',
        'notes': 'Completed + sold, newest first. The only reliable comp source.',
    },
    {
        'id': 'ebay-active', 'name': 'eBay — active', 'kind': 'asking',
        'url_template': 'https://www.ebay.com/sch/i.html?_nkw={QUERY}&_sop=15',
        'notes': 'Active listings, cheapest first. Asking prices run high.',
    },
    {
        'id': 'mercari', 'name': 'Mercari', 'kind': 'asking',
        'url_template': 'https://www.mercari.com/search/?keyword={QUERY}',
        'notes': '',
    },
    {
        'id': 'pinpics', 'name': 'PinPics', 'kind': 'database',
        'url_template': 'https://www.pinpics.com/search?q={QUERY}',
        'notes': 'Reference catalog; some features need a login.',
    },
    {
        'id': 'shopdisney', 'name': 'shopDisney', 'kind': 'retail',
        'url_template': 'https://www.shopdisney.com/search?q={QUERY}',
        'notes': 'Current retail, for pins still being sold.',
    },
    {
        'id': 'etsy', 'name': 'Etsy', 'kind': 'asking',
        'url_template': 'https://www.etsy.com/search?q={QUERY}',
        'notes': 'Heavy counterfeit presence — cross-check before trusting.',
    },
    {
        'id': 'worthpoint', 'name': 'WorthPoint', 'kind': 'sold-comps',
        'url_template': 'https://www.worthpoint.com/search?query={QUERY}',
        'notes': 'Historical sold archive; paywalled beyond previews.',
    },
    {
        'id': 'reddit-swap', 'name': 'r/DisneyPinSwap', 'kind': 'community',
        'url_template': 'https://www.reddit.com/r/DisneyPinSwap/search/?q={QUERY}&restrict_sr=1&sort=new',
        'notes': 'Collector sale/trade posts.',
    },
    {
        'id': 'google-shopping', 'name': 'Google Shopping', 'kind': 'asking',
        'url_template': 'https://www.google.com/search?tbm=shop&q={QUERY}',
        'notes': '',
    },
    {
        'id': 'google-images', 'name': 'Google Images', 'kind': 'identify',
        'url_template': 'https://www.google.com/search?tbm=isch&q={QUERY}',
        'notes': 'For confirming you have the right pin.',
    },
]


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", '-', (s or '').lower()).strip('-')
    return re.sub(r'-{2,}', '-', s) or 'pin'


def as_num(v):
    if v in (None, '', 'null'):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    m = re.search(r'-?\d[\d,]*\.?\d*', str(v))
    if not m:
        return None
    try:
        n = float(m.group(0).replace(',', ''))
    except ValueError:
        return None
    return int(n) if n == int(n) else n


def as_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        v = [x.strip() for x in v.split(',')]
    if not isinstance(v, list):
        return []
    return [str(x).strip() for x in v if str(x).strip()]


def normalise(raw: dict, segment: str, problems: list) -> dict | None:
    name = as_str(raw.get('name'))
    if not name:
        problems.append(f'[{segment}] record with no name, skipped')
        return None

    p: dict = {}
    for f in STR_FIELDS:
        p[f] = as_str(raw.get(f))
    for f in NUM_FIELDS:
        p[f] = as_num(raw.get(f))
    for f in LIST_FIELDS:
        p[f] = as_list(raw.get(f))

    p['name'] = name
    p['id'] = slugify(as_str(raw.get('id')) or f"{name}-{raw.get('year') or ''}")
    p['segment'] = segment
    p['on_board'] = bool(raw.get('on_board'))
    p['retired'] = raw.get('retired') if isinstance(raw.get('retired'), bool) else None
    p['image'] = as_str(raw.get('image') or raw.get('image_url'))

    # controlled vocabularies — repair what we can, flag the rest
    if p['franchise'] not in FRANCHISES:
        guess = {'harry potter': 'Wizarding World', 'hp': 'Wizarding World',
                 'wizarding': 'Wizarding World'}.get((p['franchise'] or '').lower())
        if guess:
            p['franchise'] = guess
        elif p['franchise']:
            problems.append(f"[{segment}] {name}: unknown franchise {p['franchise']!r}")
            p['franchise'] = 'Other'
        else:
            p['franchise'] = 'Other'
    if p['edition_type'] and p['edition_type'] not in EDITIONS:
        problems.append(f"[{segment}] {name}: unknown edition_type {p['edition_type']!r}")
        p['edition_type'] = 'Unknown'
    for f in ('rarity',):
        if p[f] and p[f] not in RARITIES:
            problems.append(f'[{segment}] {name}: unknown {f} {p[f]!r}')
            p[f] = None
    for f in ('confidence', 'price_confidence'):
        if p[f] and p[f] not in CONFIDENCE:
            p[f] = None

    y = p['year']
    if y is not None and not (1950 <= y <= 2035):
        problems.append(f'[{segment}] {name}: implausible year {y}, dropped')
        p['year'] = None

    # price sanity: low <= median <= high, and nothing negative
    lo, med, hi = p['market_low_usd'], p['market_median_usd'], p['market_high_usd']
    vals = [v for v in (lo, med, hi) if v is not None]
    if any(v < 0 for v in vals):
        problems.append(f'[{segment}] {name}: negative price, prices dropped')
        lo = med = hi = None
    if lo is not None and hi is not None and lo > hi:
        problems.append(f'[{segment}] {name}: low {lo} > high {hi}, swapped')
        lo, hi = hi, lo
    if med is not None and lo is not None and med < lo:
        med = None
    if med is not None and hi is not None and med > hi:
        med = None
    p['market_low_usd'], p['market_median_usd'], p['market_high_usd'] = lo, med, hi

    srcs = []
    for s in (raw.get('price_sources') or []):
        if not isinstance(s, dict):
            continue
        srcs.append({k: as_str(s.get(k)) for k in ('name', 'url', 'date', 'note')})
    p['price_sources'] = [s for s in srcs if s.get('name') or s.get('url')]

    if not p['price_sources'] and not p['source_urls']:
        problems.append(f'[{segment}] {name}: no sources cited')

    if p['market_low_usd'] is None and p['market_median_usd'] is None \
            and p['market_high_usd'] is None:
        p['price_confidence'] = p['price_confidence'] or 'low'

    p['tags'] = sorted(set(p['tags']))
    return p


def merge(a: dict, b: dict) -> dict:
    """Merge duplicate records, preferring whichever value is actually present."""
    out = dict(a)
    for k, v in b.items():
        if k in ('price_sources', 'source_urls', 'tags', 'characters', 'pin_type'):
            seen, joined = set(), []
            for x in (a.get(k) or []) + (v or []):
                key = json.dumps(x, sort_keys=True) if isinstance(x, dict) else x
                if key not in seen:
                    seen.add(key)
                    joined.append(x)
            out[k] = joined
        elif out.get(k) in (None, '', False) and v not in (None, '', False):
            out[k] = v
    out['on_board'] = bool(a.get('on_board') or b.get('on_board'))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--research', required=True, help='directory of segment JSON files')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    rdir = pathlib.Path(args.research)
    if not rdir.is_dir():
        print(f'error: {rdir} is not a directory', file=sys.stderr)
        return 1

    problems: list[str] = []
    by_id: dict[str, dict] = {}
    by_key: dict[tuple, str] = {}
    seg_counts: Counter = Counter()

    files = sorted(f for f in rdir.glob('*.json') if f.name != 'url-templates.json')
    if not files:
        print(f'error: no segment JSON found in {rdir}', file=sys.stderr)
        return 1

    for f in files:
        try:
            doc = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            problems.append(f'[{f.name}] unparseable JSON: {e}')
            continue
        segment = doc.get('segment') or f.stem
        pins = doc.get('pins') if isinstance(doc, dict) else doc
        if not isinstance(pins, list):
            problems.append(f'[{f.name}] no "pins" array')
            continue

        for raw in pins:
            if not isinstance(raw, dict):
                continue
            p = normalise(raw, segment, problems)
            if p is None:
                continue

            # de-dupe on identity, then on name+series+year
            key = (slugify(p['name']), slugify(p['series'] or ''), p['year'])
            if p['id'] in by_id:
                by_id[p['id']] = merge(by_id[p['id']], p)
                continue
            if key in by_key:
                tgt = by_key[key]
                by_id[tgt] = merge(by_id[tgt], p)
                continue
            by_id[p['id']] = p
            by_key[key] = p['id']
            seg_counts[segment] += 1

    pins = sorted(by_id.values(), key=lambda p: (p['name'] or '').lower())

    # sources: defaults, overridden/extended by research output
    sources = {s['id']: s for s in DEFAULT_SOURCES}
    tpl = rdir / 'url-templates.json'
    if tpl.exists():
        try:
            doc = json.loads(tpl.read_text())
            for s in doc.get('sources', []):
                sid = s.get('id') or slugify(s.get('name', ''))
                if not s.get('url_template') or '{QUERY}' not in s['url_template']:
                    problems.append(f'[url-templates] {sid}: no {{QUERY}} placeholder, skipped')
                    continue
                base = sources.get(sid, {})
                sources[sid] = {**base, **{k: v for k, v in s.items() if v not in (None, '')}, 'id': sid}
        except json.JSONDecodeError as e:
            problems.append(f'[url-templates.json] unparseable: {e}')
    else:
        problems.append('url-templates.json missing — using built-in defaults only')

    order = {s['id']: i for i, s in enumerate(DEFAULT_SOURCES)}
    src_list = sorted(sources.values(), key=lambda s: (order.get(s['id'], 99), s.get('name', '')))

    DATA.mkdir(parents=True, exist_ok=True)
    meta = {
        'generated': date.today().isoformat(),
        'count': len(pins),
        'segments': sorted(seg_counts),
        'segment_counts': dict(seg_counts),
    }
    banner = '/* GENERATED by pins/tools/build_catalog.py — do not hand-edit. */\n'
    (DATA / 'catalog.js').write_text(
        banner
        + 'window.PIN_CATALOG_META = ' + json.dumps(meta, indent=1) + ';\n'
        + 'window.PIN_CATALOG = ' + json.dumps(pins, indent=1, ensure_ascii=False) + ';\n')
    (DATA / 'sources.js').write_text(
        banner + 'window.PIN_SOURCES = ' + json.dumps({'sources': src_list}, indent=1) + ';\n')

    priced = sum(1 for p in pins if any(p[k] is not None for k in
                 ('market_low_usd', 'market_median_usd', 'market_high_usd')))
    print(f'{len(pins)} pins written to {DATA / "catalog.js"}')
    print(f'  segments      : ' + ', '.join(f'{k}={v}' for k, v in sorted(seg_counts.items())))
    print(f'  with prices   : {priced} ({priced * 100 // max(len(pins), 1)}%)')
    print(f'  on real board : {sum(1 for p in pins if p["on_board"])}')
    print(f'  franchises    : ' + ', '.join(f'{k}={v}' for k, v in
          Counter(p['franchise'] for p in pins).most_common()))
    print(f'  price links   : {len(src_list)}')
    if problems and not args.quiet:
        print(f'\n{len(problems)} data problem(s):')
        for x in problems[:60]:
            print('  -', x)
        if len(problems) > 60:
            print(f'  … and {len(problems) - 60} more')
    return 0


if __name__ == '__main__':
    sys.exit(main())
