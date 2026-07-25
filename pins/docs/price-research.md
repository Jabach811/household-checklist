# Disney Pin Pricing — Source & Infrastructure Research

**Date:** 2026-07-25
**Purpose:** determine what a Disney pin app can actually do for price checks — which sources are deep-linkable, and whether cached pricing is feasible.
**Companion file:** `url-templates.json` (machine-readable templates)

---

## 0. Read this first: verification caveat

**Not one URL below was live-verified.** The research environment blocks outbound fetches:

- `WebFetch` returned **HTTP 403 for every host tested** — eBay, Mercari, Etsy, shopDisney, WorthPoint, PinPics, Pinvault, Reddit, `developer.ebay.com`, `en.wikipedia.org`, and even `example.com`. The uniformity across a control host proves this is the environment, not bot-blocking by the targets.
- `Bash` + `curl` was denied at the CONNECT stage by the org egress proxy (`gateway answered 403 to CONNECT`) for the same hosts. Per `/root/.ccr/README.md`, policy denials must be reported, not routed around.
- The `WebSearch` budget (200 calls) was exhausted during this research.

So every template is marked `verified: false` with a `confidence` rating instead. Confidence is grounded in one of three things: platform documentation, an **actual indexed URL of that exact shape** surfaced in search results (strongest available evidence short of a fetch), or multiple independent write-ups agreeing.

**Action required before shipping:** smoke-test each template in a real browser. The ones flagged `low`/`medium` — `mercari-sold`, `shopdisney`, `worthpoint`, `google-shopping` — are the ones most likely to be wrong.

One incidental finding worth keeping: essentially every commercial host in this space sits behind Cloudflare-class bot defense that 403s non-browser clients. That is a direct argument for the deep-link architecture and against any scraping plan.

---

## DELIVERABLE 1 — Search URL patterns

Full templates with parameters live in `url-templates.json`. Summary and the analysis that matters:

| Source | Template (abbrev.) | Kind | Confidence |
|---|---|---|---|
| **eBay sold** | `ebay.com/sch/i.html?_nkw={QUERY}&LH_Sold=1&LH_Complete=1` | sold comps | high |
| **eBay sold, pins cat.** | `…&_sacat=38004&LH_Sold=1&LH_Complete=1` | sold comps | high |
| eBay active | `ebay.com/sch/i.html?_nkw={QUERY}&_sacat=38004` | active | high |
| Mercari | `mercari.com/search/?keyword={QUERY}` | active | high |
| Mercari sold | `…&status=sold_out` | sold comps | **low — guess** |
| PinPics | `pinpics.com/pins/` (no search URL exists) | catalog | medium |
| PinPics workaround | `google.com/search?q=site%3Apinpics.com+{QUERY}` | catalog | high |
| Pinvault | App Store link only | catalog | high |
| shopDisney | `shopdisney.com/search?q={QUERY}` | retail | medium |
| Disney Store | `disneystore.com/search?q={QUERY}` | retail | medium |
| Etsy | `etsy.com/search?q={QUERY}&order=date_desc` | active | high |
| WorthPoint | `worthpoint.com/inventory/search?query={QUERY}` | price guide | medium |
| Google Shopping | `google.com/search?q={QUERY}&udm=28` | active | medium |
| Google Lens | `lens.google.com/uploadbyurl?url={IMAGE_URL}` | image search | medium |
| r/DisneyPinSwap | `reddit.com/r/DisneyPinSwap/search/?q={QUERY}&restrict_sr=1&sort=new` | community | high |

### eBay sold/completed — the important one

```
https://www.ebay.com/sch/i.html?_nkw={QUERY}&_sacat=38004&LH_Sold=1&LH_Complete=1
```

- **Both flags are required.** `LH_Complete=1` alone includes ended-but-unsold listings (asks that failed, useless as comps). `LH_Sold=1` alone reportedly falls back to active listings in some categories. Ship them together, always.
- **Do not set `_sop` on a sold search.** A sold search already defaults to *Ended Recently*, which is the recency sort you want. I could not confirm any `_sop` value for Ended Recently: one guide claimed `13` and then contradicted itself within the same page (calling 13 both "newly listed" and "ending soonest"), while eBay's own community lists the working values as **1** (ending soonest), **7** (nearest), **10** (newly listed), **12** (best match), **15**/**16** (price+shipping low/high) — with no 13. Omitting `_sop` sidesteps the uncertainty and gives the right ordering.
- **Roughly a 90-day window.** eBay's web UI exposes about the last 90 days of sold listings. This is the single most consequential constraint on the whole product: for a common Hidden Mickey you'll get dozens of comps, but for an LE 100 WDI pin that trades twice a year you'll often get **zero**. Plan for the empty-comp case as a first-class state, not an error.
- **Known trap in the data itself:** Ended Recently sorts by *listing end date, not sale date*. Sellers using the out-of-stock feature can sell an item and end the listing months later, so it appears with the wrong recency. Do not treat eBay's ordering as a reliable sale-date series.
- Other useful params: `_udlo`/`_udhi` (price bounds — very effective for cutting the scrapper cluster out, see §3), `_pgn` (page), `_ipg` (60/120/240 per page), `LH_TitleDesc=1` (search descriptions too), `LH_ItemCondition`.

**Category IDs** — harvested from indexed `ebay.com/b/<slug>/<id>/bn_<node>` URLs:

| ID | Category |
|---|---|
| **38004** | **Contemporary Disney Pins, Patches & Buttons (1968-Now)** ← primary |
| 38005 | Disney Cast Member Exclusive Pins, Patches & Buttons (1968-Now) |
| 143 | Other Disney Patches & Pins (1968-Now) |
| 1379 | Disney Limited Edition Collectibles (1968-Now) |
| 138 | Other Disney Collectibles (1968-Now) |
| 139 | Vintage Disney Collectibles (Pre-1968) |
| 137 | Disneyana (broad parent) |

So yes — a proper category ID for Disney pins exists (**38004**), which is a meaningful win. Scoping to it removes lanyards, books, apparel and pin-adjacent noise that otherwise wrecks a keyword comp search. Offer 137 as an escape hatch when 38004 returns nothing.

### Mercari

`https://www.mercari.com/search/?keyword={QUERY}` is solid. Confirmed additional params: `categoryId`, `itemConditions` (comma list), `priceMin`, `priceMax`, `sortBy` (e.g. `created_time`).

**The sold filter is the problem.** Mercari's UI has a Status → sold-out filter, but no documentation or observed URL confirms its query parameter. `status=sold_out` is inferred from unofficial client libraries only. Mercari's web app is a client-rendered SPA whose filter state isn't reliably reflected in shareable query params — meaning this may *silently* show active listings, which is worse than not offering the link at all. **Recommendation:** deep-link the keyword search, and instruct the user in-app to tap Sold + Newest.

### PinPics — no public search URL

This is a real limitation, stated plainly:

- Search lives inside the **logged-in** Pin Dashboard (per PinPics' own help page, "Pin Dashboard: How to Search Inside Pin Lists").
- Searching with the full filter set (edition size, origin, …) and the mobile app are **PREMIUM subscription** features.
- Individual pin-detail pages don't appear to be publicly indexed, so **no `/pins/<id>` pattern could be corroborated.** A legacy CGI URL (`pinpics.com/cgi-bin/browse.cgi?type=a&cl1=on`) circulates in old forum posts and is almost certainly dead.
- Scale: **~156,000 pin listings as of March 2026**, user-contributed, hundreds added weekly.

Two things follow. First, the only workable deep link is a Google `site:` search (`google.com/search?q=site%3Apinpics.com+{QUERY}`) — partial coverage, but honest if labelled as such. Second, and more useful: **PinPics "PP numbers" are the community's de-facto pin IDs.** Store them on your pin records as a catalog key even though you can't link to them; they're how collectors will describe pins to each other and to your app.

### Pinvault — not a price-check source at all

Pinvault is an **iOS app** ("PinVault – Collection Tracker", App Store id6759229089, also on TestFlight), free, offering set tracking, completion progress, scanning for *supported* sets, daily mystery boxes and digital-badge trading. No web search interface, no public pin URLs, **no pricing data whatsoever**. The only sensible deep link is its App Store page. Do not architect a price flow against it.

### shopDisney — mind the domain

`/search` is confirmed via an indexed `shopdisney.com/search?cgid=root&page=72`; `q` follows the Salesforce Commerce Cloud convention but was not directly observed. **The storefront now largely renders as `disneystore.com`** — most indexed product and category pages are on that domain — so `shopdisney.com` links may 301. Test both; prefer `disneystore.com`. Canonical browse page: `disneystore.com/collectibles/pins/` (new pins drop weekly, Tuesdays 8AM PT). Other SFCC params: `cgid`, `srule` (e.g. `sorting-option-78`), `start`/`sz`.

Value here is narrow: an **MSRP anchor** for current releases only. Most lookups will miss, because pins sell out fast and then only exist on the secondary market.

### Etsy, WorthPoint, Google, Reddit

- **Etsy** — params fully confirmed (`q`, `page`, `min_price`, `max_price`, `ship_to`, `order` ∈ `most_relevant|price_asc|price_desc|date_desc`). But Etsy exposes **no sold-price data**, so it is not a comp source; and it's saturated with fantasy/custom/unlicensed pins and outright scrappers, making Etsy asks a poor proxy for authentic value.
- **WorthPoint** — `worthpoint.com/inventory/search?query={QUERY}`; item pages at `/worthopedia/<slug>`. **Paywalled: $29.99/mo or $249.99/yr (Standard); $59.99/mo or $599.99/yr (Pro).** 1B+ realized results, 15+ years, 500+ auction houses. Its genuine edge over eBay is **history depth** — it reaches sales far older than eBay's ~90-day window, which is precisely what rare LE/WDI/AP pins need. Gate the link behind a "I have WorthPoint" preference so you don't dump free users on a paywall.
- **Google Shopping** — `udm=28` is the current vertical (corroborated by Google's own `google.com/shopping/departments?udm=28&shopmd=1`); `tbm=shop` is the legacy form and still generally resolves. Weak for collectibles: inventory lives on eBay/Mercari, which Shopping surfaces inconsistently.
- **Google Lens** — `lens.google.com/uploadbyurl?url={IMAGE_URL}`. Potentially the **highest-leverage source in the whole list** (identify an unknown pin from a photo, then find listings of that design), with two hard constraints: it takes an image *URL*, so the user's photo must first be publicly hosted somewhere — a genuine privacy decision, not a detail — and the endpoint is undocumented and unsupported, so Google can break it. On mobile, prefer a native share-intent to the Google/Lens app. Legacy `google.com/searchbyimage?image_url=` now redirects into Lens.
- **r/DisneyPinSwap** — `reddit.com/r/DisneyPinSwap/search/?q={QUERY}&restrict_sr=1&sort=new&t=all`, all params confirmed. Underrated as a *pricing* source: swap-community prices are far less scrapper-contaminated than eBay and reflect what collectors actually pay each other. Bonus — `search.rss` / `search.json` variants give a **machine-readable endpoint with no API key**, the only one in this entire research. Fine for light personal use; Reddit rate-limits unauthenticated clients hard (order of 10 req/min) and its ToS restricts commercial scraping.

---

## DELIVERABLE 2 — API availability

### eBay

**Which API is right for sold comps? Marketplace Insights — and you almost certainly cannot have it.**

| API | Sold comps? | Status |
|---|---|---|
| **Browse API** | **No — active listings only** | Available, free, OAuth client-credentials |
| **Marketplace Insights API** | **Yes — the correct one** | **Limited Release. Effectively closed.** |
| Finding API `findCompletedItems` | Was yes | **Dead** |

- **Browse API** — RESTful, returns details of *active* listings and explicitly **does not permit access to sold-listing information**. Auth: OAuth 2.0 **client-credentials** (application token), scope `https://api.ebay.com/oauth/api_scope`; free; requires a production keyset. Rate limit: **~5,000 calls/day at the application level** (not per user — all your users share one bucket), raisable for free via eBay's "Application Growth Check". *Correct tool for current asks; useless for comps.*
- **Marketplace Insights API** — searches **sold** items by keyword, GTIN, category and product, returning sales history. Scope `https://api.ebay.com/oauth/api_scope/buy.marketplace.insights`, client-credentials flow. It is a **"Limited Release" API available only to select developers approved by business units**, and — the decisive point — **eBay states access "cannot be granted upon request."** Developers who applied report being told it's limited to major partners and access can't be granted. Confirmed: **treat as unavailable.** The community read is that eBay restricts it deliberately to prevent bulk data extraction and to push people toward paid **Terapeak**.
- **Finding API** — `findCompletedItems` was deprecated and restricted on **2020-10-15** and the endpoint is no longer accessible; the whole Finding API (and Shopping API) was deprecated **2024-01-04** and **decommissioned 2025-02-05**. eBay's own migration guidance points to Browse, which cannot do sold data — so the migration path for comps simply doesn't exist. Some developers additionally report `findCompletedItems` returning rate-limit errors on the very first production call before shutdown.

**Net: there is no supported API path — free or paid-self-serve — to eBay sold comps.** That is the central finding of this research.

**Caching / ToS.** eBay's API License Agreement *encourages* local caching to use calls efficiently. The binding constraints: on an eBay or data-subject deletion request, or where your retention exceeds industry best practice, you must destroy the data **within a reasonable timeframe and in no case longer than 30 days**; and the ALA generally forbids retaining data beyond your app's purpose or using it to build a competing aggregation/marketplace. Practical read for a **personal** app: caching short-lived price snapshots for your own lookups is low-risk and expressly contemplated. Publishing a Disney-pin price database built from eBay data is a different thing and is where the ALA bites.

### Mercari

**No public or developer API. Full stop.** No developer program, no docs, no keys. What exists instead:

- An **internal GraphQL endpoint** the web app itself calls, which third-party scrapers read.
- **Unofficial community libraries** (a Go client on GitHub, a `mercari` package on PyPI with a `SOLD_OUT` status enum).
- **Commercial scraper proxies** — Apify actors, Oxylabs, ScrapingBee, HAR-file tools.

Mercari's ToS prohibits unauthorised automated access. None of these are a legitimate foundation for a shipped app. **Mercari is deep-link-only.**

### PinPics

**No public API found; no developer documentation exists.** The business model is tiered subscriptions (free / PREMIUM) that specifically gate search filters and the mobile app — i.e. the data access you'd want is the paid product. The database is user-contributed and PinPics asserts its own naming and numbering conventions over it. Assume **no API and no permission to mirror the catalog.**

### Pinvault

**Nothing to integrate.** iOS app only, no published API, no web endpoints, and — decisively — **no pricing data at all**. It's a collection tracker with gamification.

### Aside: Etsy

Etsy is the one platform here with a real, open, self-serve API — **Etsy Open API v3**, OAuth 2.0, free with app approval. It doesn't help: it exposes **active listings, not sold prices**. Worth knowing so nobody wastes a sprint on it.

### Feasibility verdict

**Real cached pricing is not feasible without paid access — not legitimately.** The reasoning:

1. The only large, free, relevant corpus of Disney pin comps is eBay sold listings.
2. No available API exposes it (Marketplace Insights closed, Finding API dead, Browse can't).
3. The HTML is protected by ToS *and* by bot defense that 403s non-browser clients — as my own attempts demonstrated on every commercial host tested.

Three honest options:

- **Free & clean — deep links only.** Zero auth, zero rate limits, zero ToS exposure. The user taps through and reads the prices themselves. Fully feasible today.
- **Free & clean — user-contributed comps.** Let users log what they paid and sold for, and optionally paste a price + eBay sold URL after a price check. You accumulate a legitimate, first-party comp database that *you own*, and it gets more valuable over time. This is the only route to genuine cached pricing without paying anyone. It's also the one nobody in this market has done well (see §4).
- **Paid middle path.** Third-party sold-comps scraping APIs exist (Apify eBay Sold Listings actor, sold-comps.com, SerpApi's eBay engine) at per-result or subscription pricing; or Terapeak via an eBay Store subscription for manual research. These work, but the data is scraped — the legal exposure sits with the provider, not with eBay's blessing — and a Terapeak subscription is seller-account-bound with a web UI, not an API.

**Recommendation:** ship deep links plus user-contributed comps. Treat any paid comps API as a later, optional enhancement, not a dependency.

---

## DELIVERABLE 3 — Valuation heuristics

### Edition type, roughly by scarcity

| Type | Meaning | Typical scarcity |
|---|---|---|
| **PP** — Pre-Production | Test pieces | ~1 of 3 |
| **AP** — Artist Proof | Marked/stamped AP | ~1 of 24 |
| **WDI / Imagineering** | Made for Imagineers & staff | often LE 250/300, very restricted distribution |
| **Disney Auctions / DisneyShopping.com** | Early-2000s online exclusives | LE 100–500 |
| **LE** — Limited Edition | Stated edition size, often numbered | LE 100 → LE 5000 |
| **LR** — Limited Release | Time-limited, **no stated size**, stamped "Limited Release" | moderate |
| **CM / CME** — Cast Member Exclusive | Cast-only | moderate |
| **HM** — Hidden Mickey | Silver Mickey head; park lanyard trading stock | very high |
| **OE** — Open Edition | Produced indefinitely | unlimited |

### Multiples over retail

Edition size is the single biggest lever — an LE 100 is dramatically rarer than the same art at LE 2,000 — but **demand gates it**. An LE 500 of an unloved character can trade below an Open Edition Stitch. Perennial demand drivers: Stitch, villains, Haunted Mansion, Figment, Nightmare Before Christmas.

| Tier | Typical value | Multiple vs. retail |
|---|---|---|
| **OE** | retail $8–15 → secondary **$5–10** | **~0.5–0.8× (below retail)** |
| **LR** | near retail | ~1× |
| **LE 2,000–5,000** | retail to slight premium | ~1–1.5× |
| **LE ≤ 500** | **$30–100+** | **~2–5×** |
| **LE 250, popular character + event exclusivity** | cited: **~10× a $20 retail within a few years** | **~10×** |
| **LE 100–250, WDI tier** | WDI Villains Profile LE 250: **$300–800+** (an Oogie Boogie sold **$1,384**); WDI Haunted Mansion stretching portraits LE 250: **$150–400+** each; an LE 100 Oogie Boogie Nightmare pin **~$1,400** | 15–70× |
| **AP / PP / Disney Auctions tail** | Lilo & Stitch AP set, 20 sets made: **$14,250**. Disney Auctions Belle-on-carousel-horse LE 100: **$5,000** | extreme |

Overall stated ranges: collectible pins **$35 to several thousand**; park-exclusives **$20–$2,500+**. On APs/PPs specifically, collectors note that **WDI** artist proofs run highest, while Disney Auctions / PINS / DisneyShopping APs and pre-production pieces form a separate, also-high class.

**Product implication:** edition type + edition size should be **structured fields** on your pin record, not free text. They're the strongest priors you have, and they let you sanity-check a comp: an eBay sold price of $6 on an LE 250 is not a comp, it's a scrapper.

### Condition and the backer card

- **Mint on the original backer card is the top tier**, always. Pins with original packaging/backing are worth substantially more than worn examples.
- **Scratches, dings, or a missing rubber back: −40% to −70%.**
- **Losing a special-event / special backer card can cost up to ~half the value.** Backer cards matter far more than newcomers expect — for event and limited releases they're part of the collectible, not packaging.
- Also discount for: enamel damage, "pin bites"/face scratches, tarnished or oxidised metal, bent posts, replaced non-Disney rubber backs.
- Sealed/unopened mystery pouches carry a premium over loose examples of the same pin.
- Custom packaging (retro boxes, glow-in-the-dark backer cards) adds appeal.

**Product implication:** a single "condition" enum is too coarse. Model **condition** and **has original backer card** as separate fields — they move value independently and the card is worth up to 50% on its own.

### The scrapper problem — and how it breaks naive comps

**What they are.** Scrappers are unauthorised pins produced outside Disney's licensing system: factory overruns and re-cast or digitally recreated molds. They exist structurally — Disney's molds aren't always destroyed after a production run, and its factories are known for overruns. Bulk lots sell for **$1–2 per pin** on eBay, Amazon and AliExpress. Concentration is worst on **cast lanyard pins and mystery / Hidden Mickey releases**, and on whatever is most in demand.

**How it suppresses value.** The most desirable designs get counterfeited most, so buyers can't tell authentic from fake in a listing photo — and they respond by discounting *every* listing of that design, or refusing to pay LE prices at all. Collectors describe high-demand LE pins being flooded until they're "worth virtually nothing." Note the market's own tell: sellers now advertise *"100 Real Guaranteed No Scrappers Ever"* — that language only exists because the default assumption is contamination.

**The critical consequence for the app:**

> For any design that has been scrappered, eBay sold comps are **bimodal** — a dense cluster of $2–8 scrapper sales and a thinner, higher cluster of authentic sales. **The median of raw sold data is worthless.** You need the upper mode.

Concrete mitigations, in rough order of value:
1. **Use `_udlo`** to floor the comp search near the edition type's plausible authentic band — this cuts the scrapper cluster out at the source.
2. **Prior-check against edition type/size.** A $6 sale on an LE 250 is a fake, not a data point.
3. **Cluster rather than average.** Take the upper mode, or a high percentile, not the mean or median.
4. **Weight community prices.** r/DisneyPinSwap and PinPics Trusted Sellers are far less contaminated than open eBay.
5. **Exclude lots.** Any listing of multiple pins is scrapper-dominated by default.
6. **Surface uncertainty.** With 3 comps spanning $6–$180, show a range and say why — don't print a confident single number.

### Back-stamp and physical fake signals

The **back stamp is the primary and most reliable authentication check.**

- **Back stamp** — authentic: crisp, sharp `© Disney`, era-appropriate wording, clean evenly-spaced letters, official logo, and an edition-size stamp where applicable. Scrappers: messy, blurry, missing, or wrong-era stamps. A **missing or incorrect edition-size stamp on a pin sold as LE is a hard red flag.**
- **Specific cited tell** — on scrapper Hidden Mickey backs, the dot of the "i" in "Hidden" **merges into the letter below** instead of being a separate mark.
- **Mickey-head waffle pattern** — authentic: full-bleed, heads reach every edge, consistent spacing, centred and clean. Fakes: off-centre or oversized heads, a **border/frame around the pattern**, heads that morph into glob shapes, or no pattern at all.
- **Nubbins** — genuine pins have two small alignment nubs flanking the post, distinct and well formed. Counterfeits show short, smudged, or missing nubs.
- **Metal, weight, finish** — authentic: solid metal with real weight; smooth hard-enamel finish flush with the metal lines. Fakes: light/flimsy; **soft enamel with ridges you can feel**; paint that looks "filled in" rather than laid smooth; jagged or bumpy outlines; metal flakes or chips on the edge; dull, uneven, or bleeding colour.
- **Provenance heuristics** — bulk lots; a seller with hundreds of the same "LE" pin; AliExpress/Amazon origin; a price far below the authentic comp band.

**Product implication:** the back-stamp checklist is a genuinely useful in-app feature and it needs no API — it's a photo prompt plus a checklist. It also feeds the pricing model: an unverified pin should display a scrapper-discounted range.

### A note on source quality

Much of the SEO-ranked writing in this space is affiliate content of low reliability (Antsy Labs, VIP Art Fair, TheGamer, and the various "AI review" sites). The **collector-native, trustworthy** sources are: **Disney Pin Forum** (`disneypinforum.com` — threads on backer-card importance, valuing APs/PPs, spotting scrappers, "how do you value your pins"), **PinPics forums**, **DisneyCanuck** (`disneycanuck.com/pins-realvsfakes`, `/pin-terms`), **PinHoarder** (`pinhoarder.com/how-to-spot-fake-disney-pins`), the **Disney Pin Wiki** glossary (`disneypins.fandom.com/wiki/Glossary`), **Disney Examiner**'s scrappers investigation, and **r/DisneyPinSwap**. Weight those; treat the content farms as corroboration only. The specific figures quoted above appear consistently across multiple independent write-ups, but none of them are an official Disney or auction-house price series — **there is no authoritative Disney pin price guide**, which is itself the market gap.

---

## DELIVERABLE 4 — Existing tools (competitive note)

| Tool | Does well | Lacks |
|---|---|---|
| **PinPics** (web) | The canonical catalog — ~156k pins, PP numbers are the community's de-facto pin IDs; OWNS/WANTS/TRADES lists, forums, Trusted Sellers | Dated UX; search/filters + mobile app behind PREMIUM; login-gated; **no pricing at all**; no public API or linkable pin pages |
| **Pinvault** (iOS, free) | Clean modern tracker; set-completion progress; scanning for supported sets; badge trading, mystery boxes | **No pricing**; iOS-only; coverage limited to "supported" sets; gamification over data |
| **Pin & Pop** (`pinandpop.com`) | Web-first public database (cited 99k–113k pins), collection management + trading + community | Pricing depth unverified; smaller catalog than PinPics |
| **Pinsdex** (iOS + Android) | Cataloguing, AI scan identification, **claims market-value tracking**, community | Closest direct competitor — worth hands-on evaluation before committing |
| **Pixie Pin** (`pixiepin.app`) | Value-guide content ("pin value", "most valuable pins") with an app angle | Reads as SEO-plus-app; editorial rather than live comps |
| **WorthPoint / Terapeak** | The real pricing incumbents — deep realized-sales history | Generic collectibles; paywalled; **zero pin-specific intelligence** — no edition-size awareness, no scrapper awareness |
| Long tail | Pin Trading – Scan & Collect, My Pin Tracker, iCollectEverything Pins, Pin Trackers, Disney Pinventory | Crowded, undifferentiated trackers |

**The gap.** Trackers have no prices; price tools have no pin knowledge. Nobody combines (a) a **scrapper- and authenticity-aware** read of comps, (b) **edition-type-aware** valuation priors, and (c) **one-tap deep links** across eBay sold / Mercari / WorthPoint / Lens from a single pin record. Given that no API will hand you prices, the defensible asset isn't a price feed — it's *interpretation* (edition priors + fake awareness + honest ranges) plus a first-party, user-contributed comp history that compounds.

---

## Bottom line

1. **Deep-linking works and is the right architecture.** ~14 usable templates, no auth, no rate limits, no ToS exposure. eBay sold + category 38004 is the workhorse.
2. **Cached pricing without paid access is not legitimately feasible.** Marketplace Insights is confirmed closed, the Finding API is dead, Browse can't see sold data, Mercari/PinPics/Pinvault have no APIs at all.
3. **The viable path to owned pricing data is user-contributed comps**, not scraping.
4. **Raw eBay comps are actively misleading** on scrappered designs. Any number the app prints needs edition-type priors, a price floor, upper-mode selection, and a visible range.
5. **Verify the templates in a browser before shipping** — especially `mercari-sold` (low confidence), `shopdisney` (domain likely moved to disneystore.com), `worthpoint`, and `google-shopping`.
