# Pin record schema (v1)

Every pin is one JSON object. Emit a single JSON file: `{"segment": "<your-segment>", "pins": [ ... ]}`.

**Honesty rules — these matter more than volume:**
- Never invent a PinPics ID, SKU, edition size, backstamp, or price. Use `null` when you don't know.
- `confidence` reflects how well-corroborated the *identity* of the pin is; `price_confidence` reflects the price data specifically.
- Every pin needs at least one real URL in `source_urls` that you actually fetched.
- Prices are approximate secondary-market observations. Record where each came from and the date.
- Prefer fewer, well-sourced pins over many guessed ones. A pin with `confidence: "low"` is fine — a fabricated one is not.

```jsonc
{
  "id": "minnie-main-attraction-space-mountain",   // kebab-case, globally unique
  "name": "Minnie Mouse Main Attraction — Space Mountain Pin Set",
  "franchise": "Disney",              // Disney | Pixar | Star Wars | Marvel | Wizarding World | Other
  "property": "Space Mountain",       // film/attraction/franchise the art comes from, or null
  "series": "Minnie Mouse The Main Attraction",  // collection name, or null
  "series_position": "7 of 12",       // or null
  "characters": ["Minnie Mouse"],
  "year": 2020,                        // integer release year, or null
  "release_date": "2020-07-01",        // ISO date if known, else null
  "origin": "Walt Disney World",      // Walt Disney World | Disneyland Resort | shopDisney |
                                       // Disney Cruise Line | Tokyo Disney Resort | Disneyland Paris |
                                       // Hong Kong Disneyland | Shanghai Disney Resort |
                                       // Disney Store | Loungefly | Universal Studios | Other
  "park_specific": "Magic Kingdom",   // specific park/land/shop, or null
  "edition_type": "Limited Release",  // Open Edition | Limited Edition | Limited Release | Mystery |
                                       // Hidden Mickey | Cast Exclusive | Annual Passholder |
                                       // Artist Proof | Pre-Production | Retail | Unknown
  "edition_size": null,                // integer if a stated LE size, else null
  "pin_type": ["enamel", "dangle"],   // enamel | dangle | hinged | spinner | slider | stained-glass |
                                       // glitter | 3D | jumbo | light-up | pearlized | pop-up | rubber
  "size_mm": "45x38",                 // or null
  "backstamp": null,                   // back marking text if documented, else null
  "pinpics_id": null,                  // ONLY if you actually saw it, else null
  "sku": null,
  "retail_price_usd": 19.99,          // original retail, or null
  "market_low_usd": 22,
  "market_median_usd": 38,
  "market_high_usd": 65,
  "price_confidence": "medium",       // high | medium | low
  "price_sources": [
    {"name": "eBay sold listings", "url": "https://...", "date": "2026-07-25",
     "note": "6 sold comps, Jun–Jul 2026"}
  ],
  "rarity": "uncommon",               // common | uncommon | rare | very-rare | grail
  "retired": true,                     // no longer sold at retail
  "tags": ["main-attraction", "minnie", "set"],
  "notes": "Sold as a boxed set with a matching ear headband release.",
  "image_url": null,                   // direct image URL if you found a stable one, else null
  "confidence": "high",
  "source_urls": ["https://...", "https://..."]
}
```

## Price research method

For market value, in priority order:
1. eBay **sold/completed** listings (the only reliable comp source).
2. Mercari / PinPics trade values / Pinvault / collector-forum sale threads.
3. Collector blog roundups and Reddit r/DisneyPinSwap sale posts.

If you cannot find real comps, set the three market fields to `null` and
`price_confidence: "low"` — do **not** extrapolate a number.
