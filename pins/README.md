# Pin Board

A searchable catalog and virtual cork board for a Disney + Wizarding World pin
collection. Static site, no build step, no dependencies — open `index.html` and
it works, including straight off the filesystem.

## What it does

| View | Purpose |
|------|---------|
| **Cork Board** | Showcase. Every pin marked *owned* appears pinned to a cork board, grouped by franchise, with a running total value. |
| **Browse** | Card grid over the whole catalog with instant search and faceted filters. |
| **Table** | The full dataset, ~40 sortable columns, column picker, CSV export. |
| **Wishlist** | Pins you're hunting, with a target price that flags when market value drops to it. |
| **Stats** | Collection totals, unrealised gain, and distribution by franchise / edition / origin / decade. |

Per pin, the detail drawer gives you the full catalog record, an estimated
value with its confidence level, links to wherever the data came from, and
one-click **price checks** that open pre-filled searches on eBay sold listings,
Mercari, PinPics, WorthPoint, shopDisney, Etsy, r/DisneyPinSwap and Google.

## Two data layers, kept apart

**`data/catalog.js` — reference data. Generated, never hand-edited.**
Researched pin facts: names, series, years, edition sizes, market value
ranges, and the sources each claim came from. Rebuilt by the build script.

**`localStorage` — your collection.** Owned flag, quantity, condition, what you
paid, acquisition date and source, your own valuation, wishlist flag, target
price, private notes. This never gets written into the catalog, and the catalog
can be regenerated freely without touching it.

Because it lives in one browser, **use the Export button** to back it up to
JSON. Import merges a backup back in.

## Rebuilding the catalog

Research output goes in a directory as one JSON file per segment, shaped
`{"segment": "...", "pins": [...]}`, following `SCHEMA.md`. Then:

```sh
python3 tools/build_catalog.py --research path/to/research
```

The script normalises every record, enforces the controlled vocabularies,
de-duplicates on both id and name+series+year, merges partial duplicates
field-by-field, and reports every problem it found rather than silently
coercing bad data. It writes `data/catalog.js` and `data/sources.js`.

Validation catches, among other things: unknown franchise/edition/rarity
values, implausible years, negative or inverted price ranges, and records
citing no sources at all.

## Honest limits

- **There is no complete Disney pin database.** No public API exists. PinPics is
  the closest thing and it has neither an API nor terms that permit scraping.
  This catalog is a curated seed that grows — not an exhaustive index, and it
  never will be one.
- **Prices are researched observations, not a live feed.** A static page can't
  query eBay from the browser (API keys, CORS). The price-check buttons take
  you to real sold-listing searches instead, which is the honest version of
  "current price". Recorded values carry a `price_confidence` field — treat
  `low` as a rough hint.
- **Counterfeits ("scrappers") distort the market.** A cheap sold comp is often
  a fake. Check the backstamp before trusting a low price.

## Roadmap to an app

The static structure is deliberately one step from a real app:

1. **Now** — static page, catalog in a JS file, collection in localStorage.
2. **Images** — replace the placeholder glyphs with real cutouts of each pin,
   positioned on the board to mirror the physical one.
3. **Sync** — swap localStorage for a hosted database so phone and laptop share
   one collection.
4. **Live prices** — a scheduled backend job caching eBay sold comps per pin,
   turning the static value fields into a real price history with charts.
5. **Capture** — photograph a pin and match it against the catalog.

Steps 3 and 4 are the ones that need infrastructure — an eBay developer key and
somewhere to host. Everything before them is free.

## Files

```
pins/
├── index.html              app shell
├── css/app.css             styles (dark + light)
├── js/app.js               all application logic
├── data/catalog.js         GENERATED pin catalog
├── data/sources.js         GENERATED price-check URL templates
├── tools/build_catalog.py  research JSON → catalog
└── SCHEMA.md               the pin record schema
```
