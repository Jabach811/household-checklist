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

The research JSON that produced the current catalog is committed in
`research/` — one file per segment, shaped `{"segment": "...", "pins": [...]}`
and following `SCHEMA.md`. To rebuild from it:

```sh
python3 tools/build_catalog.py --research research
```

To add pins, drop another segment file in `research/` and re-run. Files whose
names start with `_` are ignored, so a research pass can keep scratch there.

The script normalises every record, enforces the controlled vocabularies,
de-duplicates on both id and name+series+year, merges partial duplicates
field-by-field, and reports every problem it found rather than silently
coercing bad data. It writes `data/catalog.js` and `data/sources.js`.

Validation catches, among other things: unknown franchise/edition/rarity
values, implausible years, negative or inverted price ranges, and records
citing no sources at all.

## What's actually in the catalog

403 pins across six research segments:

| Segment | Pins | What it covers |
|---------|-----:|----------------|
| `board-disney` | 34 | Disney items identified from the board photo |
| `board-wizarding` | 19 | Wizarding World items from the board photo (incl. 5 non-pin pieces) |
| `ear-headbands` | 94 | Ear-headband pin series across Loungefly/BoxLunch, Hidden Disney and park lines |
| `flagship` | 159 | Hidden Mickey, Disney100, passholder, princess, villains, Star Wars, Marvel, grails |
| `main-attraction-castles` | 48 | The complete Minnie (2020) and Mickey (2022) *The Main Attraction* runs, plus castles |
| `letters-dangles-food` | 49 | Letter/alphabet pins, tassel bookmark pins, boba and food pins |

53 of those are marked as physically on the board.

**Price coverage is the weak spot: only 15 of 403 pins (3%) carry a market
value.** That is a research limitation, not a design one — see below. The
sold-comp log exists precisely to close this gap over time.

### Known open questions in the data

These are recorded rather than resolved, and are worth knowing before trusting
a record:

- **The ear-headband grid has two competing identifications.** The segment that
  examined the photo at magnification reports Hidden Mickey icons on the pins
  and places them in the *Hidden Disney 2025 Wave A: Ear Headbands* cast-lanyard
  sets (WDW and Disneyland). The segment that researched ear-headband series
  without the photo places them in the *Loungefly/BoxLunch Minnie Ears Headband*
  blind-box waves. Both series are in the catalog; the board records follow the
  photo-based reading, which is the better evidence for these specific pins.
- **The four "D" pins are probably four different letters**, not four D's —
  most likely D/E/N plus one more from the *Character Alphabet Mystery
  Collection* (D=Dumbo, E=Elsa, N=Nala, and a fourth with goblets). That reading
  is the only one that explains a Frozen + Dumbo + Lion King combination.
- **Loungefly Series 1 and 2 have two conflicting naming conventions** (PinPics
  uses bow/finish names, Pin Trading Database uses flat colours). Individual
  positions in those sets are not authoritative.
- **Hidden Disney 2026 Wave A resort attribution is contradictory** across
  sources; likely two separate sets conflated.
- **The Disney Cruise Line ship, teal mermaid-scale, and white-bow-with-pink-
  Minnie headbands were never placed** to a series. The three gold-tone floral
  headbands on the bottom row are also unidentified.
- **Two board items were never researched at all** — the Walt Disney Family
  Museum logo pin and the sushi-in-a-hat food pin — because the search budget
  ran out. They are absent rather than guessed at.
- **Midnight Masquerade is two different lines.** The princess line is 2019,
  the villains line 2020. Cruella, Mother Gothel, Queen of Hearts and Dr.
  Facilier are widely but wrongly attributed to it — they belong to the 16-pin
  Villains Icons mystery set. Hades genuinely is a Masquerade villain and is
  usually left off lists.
- **Two edition sizes are left null on purpose**, with both claims in `notes`:
  the Disneyland 65th Marquee jumbo (LE 1,000 vs 1,500) and the Avengers
  Campus Opening Day jumbo (LE 1,000 vs 1,500).
- **Magic Key tier pins (Dream/Believe/Enchant/Imagine/Inspire) appear not to
  exist** as actual releases — don't model them.
- **Edition size does not determine value.** A Disney Auctions 101 Dalmatians
  LE 100 jumbo floors near $73 while a same-format Carousel Horse LE 100
  clears four figures. Both are in the catalog deliberately, as a counterweight
  to "low edition size = valuable".
- **The Lilo & Stitch Artist Proof set's $14,250 figure is disputed** — the
  value guide carrying it gives no source. Flagged in the record.
- **Rise of the Resistance opening-day pins have confirmed counterfeits** in
  circulation.

Records carry `confidence` (identification) and `price_confidence` separately.
A great many are `low`, and that is deliberate honesty: a descriptive name with
null fields is more useful than an invented official product name.

## Honest limits

- **There is no complete Disney pin database.** No public API exists. PinPics is
  the closest thing and it has neither an API nor terms that permit scraping.
  This catalog is a curated seed that grows — not an exhaustive index, and it
  never will be one.
- **There is no legitimate route to automated sold prices.** eBay's
  Marketplace Insights API is the correct one for sold comps and access
  "cannot be granted upon request"; the old Finding API `findCompletedItems`
  was restricted in 2020 and decommissioned in Feb 2025; the free Browse API
  explicitly cannot see sold listings. Mercari, PinPics and Pinvault have no
  public API at all. So the price-check buttons open real sold-listing
  searches in your browser, and the comp log lets you keep what you find.
  That combination is the honest version of "current price".
- **Counterfeits ("scrappers") make raw sold data bimodal.** Fakes cluster
  around $2–8 on exactly the most desirable designs, so the *median* of raw
  eBay sold results is close to worthless — you want the upper cluster. Hence
  the "$10+" sold link, the range-rather-than-a-number display, and the
  warning on low-confidence estimates. A $6 sale on an LE 250 pin is a fake,
  not a data point.
- **Condition and backer card are priced separately** by collectors: damage
  runs −40–70%, and losing only a special backer card can cost ~50% on its
  own. They're separate fields for that reason.
- **Why price coverage is only 3%.** This environment's network policy blocks
  every commerce and collector host at the gateway (eBay, Mercari, PinPics,
  DisneyPinsBlog, Reddit — all 403 at CONNECT), and the session's web-search
  budget was exhausted. Research therefore ran on search-result summaries with
  no page ever fetched, so no sold comps could be recorded. **This limits only
  our pre-recorded values — it does not affect the app**, whose price checks
  run in your browser. Filling the price fields needs either a session with
  those hosts reachable, or you logging comps as you go.

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
├── index.html                app shell
├── css/app.css               styles (dark + light)
├── js/app.js                 all application logic
├── data/catalog.js           GENERATED pin catalog — do not hand-edit
├── data/sources.js           GENERATED price-check URL templates
├── research/*.json           source research, one file per segment
├── tools/build_catalog.py    research JSON → catalog
├── docs/price-research.md    how pin pricing works: APIs, sources, valuation
└── SCHEMA.md                 the pin record schema
```

Verified in Chromium via Playwright: all five views render, search and facets
filter, the comp log persists across reload, CSV exports, and both themes work
with no console errors.
