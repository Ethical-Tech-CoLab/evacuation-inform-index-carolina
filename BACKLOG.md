# Backlog

Known gaps, in the order they would mislead a reader. Each entry says what is
wrong, why it matters, and what closing it would take — so an item can be picked
up without re-deriving the problem.

The road-access layer dominates this list because it is the newest and the least
verifiable: it reads news prose for a fact — whether a route is passable — that
no open global feed publishes, and it feeds a penalty into the CERAI feasibility
score. Everything here was found by auditing the 23 stored road items in
July 2026; the [gate and classifier fixes](server.py) from that audit removed
roughly two thirds of them, and these are what survived.

---

## Road access — data quality

### 1. The 60-day window is not enforced — **CLOSED 2026-07-28**

The popup said reports were "over the last 60 days" but nothing enforced it.

**Fixed.** `road_date_window` in [server.py](server.py) now classifies each item
as in-window / out / undated against `query_days`; `tavily_roads` drops the
out-of-window ones (counting them as `stale`) and flags undated ones with an
`undated` field, which the popup renders as "· undated". `rescore_roads.py`
applies the same gate to the stored snapshots, and re-running it removed the
stale items: Niger's 2023 border closure (signal 0.2 → 0.0, so its pin is gone),
Malawi's Feb SCIAF item (0.32 → 0.16). The map now carries 7 road pins, not 8.
Two undated items (Malawi, Eritrea) are kept and labelled rather than dropped.

### 2. Source quality is unchecked — **CLOSED 2026-07-28**

DRC's only pin — and its entire −2-point feasibility penalty — was a
`wikitravel.org` "Travel news" index page; two other items were `facebook.com`
posts. The relevance gates judged the *text*; nothing judged the publisher.

**Fixed.** [`source_is_admissible`](server.py) applies a `SOURCE_DENYLIST` of
social / user-generated and open-wiki / travel-aggregator domains (matched on
the registrable domain, so subdomains like `m.facebook.com` are caught) *before*
the relevance gate, in both `tavily_roads` and `rescore_roads.py`; dropped items
are counted as `low_source`. The line is drawn as a **deny** list on purpose —
an allow list would silently exclude reliefweb, OCHA/IOM, and local-language
outlets, the worse error — so it names only sources that are categorically not
newsrooms.

Re-running dropped three pins: DRC (wikitravel), Eritrea and Malawi (both
Facebook posts — the Eritrea one was also the item-6 Tigray-attribution case).
The map now carries **4 road pins, all wire/newsroom-sourced** (Sudan, Syria,
Lebanon, Philippines). One judgment call left in: `yahoo.com` is kept, since
Yahoo News rehosts AP/Reuters wire copy rather than user posts.

### 3. De-duplication misses re-headlined wire copy — **PARTIALLY CLOSED 2026-07-28**

`_is_duplicate` caught identical URLs and near-identical headlines at 0.75 token
overlap. The AP and Greenwich Time versions of the same Abdin dispatch share
only ~45% of their headline words and were both counted, which is most of why
Syria carries the highest signal on the map (0.76, −9 points).

**Implemented.** [`_wire_dateline`](server.py) extracts a normalised
`city|agency` key from a wire dateline in the snippet ("ABDIN, Syria (AP) —"),
and `_is_duplicate` now treats two items that share one as the same story,
between the URL check and the headline check. It fires only when *both* items
carry a dateline, so it cannot merge two distinct blockages — the error this
tool must not make. Verified on synthetic pairs (same dateline merges; same
agency but different city does not).

**Still open — the stored Syria pair is not merged.** Only one item in the whole
snapshot carries an extractable dateline: the Greenwich rerun. The AP *original*
that seeded it has a snippet made of page navigation ("Test Your News I.Q. …
Elections …"), not the article body, so no dateline can be read from it and the
two do not share a key. This is a Tavily content-extraction artifact, not a flaw
in the rule. Re-fetching Syria (already on the item-8 re-fetch list) with cleaner
snippets is what would let the dateline rule collapse the pair and bring the
0.76 signal down. The rule will catch clean syndication as soon as it appears.

### 4. Cross-crisis duplicates are invisible — **CLOSED 2026-07-28**

A single URL can be counted under two neighbouring crises. The general case is
legitimate — one story really can bear on two crises — so it is *surfaced*, not
suppressed.

**Fixed.** [build_roads_layer.py](build_roads_layer.py) now indexes every item
URL across all crises, tags each shared item with an `also_in` list naming the
*other* crises that carry it, prints a `cross_crisis` count and the offending
URLs, and records the count in `roads.json`. The map popup marks a shared item
with an "also counted under …" badge. No URLs are shared in the current snapshot
(the el-Obeid place-gate bug that first prompted this was already fixed), but the
machinery is in place and verified against a synthetic set for when one recurs.

While here, `undated` was added to the layer's `ITEM_FIELDS` so the flag from
item 1 reaches the map-layer popup, not just the drawer.

### 5. Some items are not about roads at all

Syria carries "Airstrike killed senior ISIS commander in Syria" as `blocked`.
It passes the subject gate on incidental words and the place gate correctly. The
keyword classifier has no notion of what the *sentence* is about.

**To close.** Properly, this wants a model call over the snippet rather than
another regex. That is a real cost decision — one call per item on top of the
existing Tavily credit — and should be weighed against simply showing fewer,
better-sourced items.

### 6. Attribution: the pin names a party, not a place

Eritrea's only report concerns routes into **Tigray, Ethiopia**; Eritrea appears
because it is named as one of the parties closing them. The place gate passes it
correctly — the country really is in the text — but the road access being
described is in a different country from the pin.

**To close.** No clean rule. Worth flagging in the popup when the only match is
the country name and the item names another country's sub-national area.

*Note (2026-07-28): the specific Eritrea item above was a Facebook post and has
since been removed by the item-2 source gate, so there is no live instance right
now — but the attribution problem itself is unchanged and will recur.*

---

## Road access — coverage

### 7. 62 of 104 crises have never been searched — **CLOSED 2026-07-28**

The largest single gap: an unpinned crisis was ambiguous between *searched,
nothing found* and *never searched*, and the silent reading — no pin, roads
fine — is the dangerous one.

**Fixed.** `snapshot_roads.py` backfilled all 62 (~62 credits, news and ACLED
untouched), 0 failures. The layer now reports **104 searched, 0 never
searched**, so an unpinned crisis finally means only one thing.

Five of the 62 carry reports, taking the map from 4 pins to 9: Ukraine (5
items, signal 0.96 — now the highest on the map), Thailand (0.32), Venezuela→
Chile and Displacement to Italy (0.2 each), and Iraq (a reopening item, 0.0).
All 9 had curated locations already, so `unlocated` stays 0.

The new items arrived through the item 1–4 gates, which dropped 38
out-of-window and 55 inadmissible-source items that would otherwise have
reached the map.

### 8. 22 crises should be re-fetched after the gate changes

`rescore_roads.py` can only ever *remove* items — anything the old gate rejected
was never written to disk. Crises whose alias set has since expanded were
searched under a stricter rule than the one now in force and may be
under-counted. The script names them at the end of every run.

As of 2026-07-28 (22, ~22 credits): Afghanistan, Burkina Faso, CAR, Cameroon,
Chad, DRC, Ethiopia, Haiti, Lebanon, Mali, Mozambique, Myanmar, Niger, Nigeria,
Palestine, Somalia, South Sudan, Sudan, Syria, Ukraine, Venezuela, Yemen.

Two are worth doing first regardless of the alias question: **Syria**, whose
re-fetch is what would let the item-3 dateline rule collapse the AP/Greenwich
pair and bring the 0.76 down, and **Ukraine**, whose 0.96 is now the highest
signal on the map on the strength of a single unreviewed fetch.

---

## Map

### 9. Most of the nine road pins are country-level stand-ins

The pin sits at the crisis, never at the blockage, because news prose carries no
coordinates — that is inherent and the popup says so. But most crises are
themselves located only to a country, because INFORM publishes no affected admin
areas, so the pin stands in for a whole country. The scope chip says which, and
that is the honest limit rather than a defect.

**To close.** Only better upstream data would close it: affected admin areas per
crisis, from INFORM or hand-curated into `geo/locations.csv`.

---

## Housekeeping

- `_preview.html` and `_wntest.html` are untracked local scratch files. Decide
  whether either belongs in the repo or in `.gitignore`.
- `data.js` still carries the superseded country-centroid `lat`/`lng`. They are
  no longer read by the map, but they are what `geo/build_geo.py` measures
  corrections against, so removing them is not free.

---

## Credibility review — 2026-07-27

A hostile-but-fair peer-review sweep of the report copy (mirrored on the site in
`website/src/content/publications/evacuation-inform-index.ts`). Fix in both.

### Verify the INFORM weights stated as fact

§03 asserts flatly that INFORM Severity combines "31 core indicators into three
weighted dimensions: impact at 20%, conditions of affected people at 50%,
complexity at 30%." Wrong weights would undermine the tool's whole
proxy-substitution argument. Confirm the indicator count and dimension weights
against the current ACAPS/JRC methodology and correct if they differ.

---

## Peer-review findings (from PEER-REVIEW.md — "major revisions")

Full referee report in [PEER-REVIEW.md](PEER-REVIEW.md). Verify each against the
current report copy and check off any already fixed.

Major:
- [ ] **The central proxy is asserted, not validated (§4.2).** INFORM
      "Complexity" measures humanitarian *access for responders*, not the
      danger civilians face self-evacuating a corridor. Add a subsection naming
      1–2 crises where the two pull apart, the expected bias direction, and why
      the mapping is still defensible.
- [ ] **The headline ratio is arithmetically fragile (§4.1).** Dividing two
      rescaled ordinal 5-point scores treats them as ratio-scale; the 0.5
      denominator floor is arbitrary and can swing the ratio 2.5×; equal ratios
      hide different absolute stakes. Justify or drop the ratio-scale treatment,
      report a floor-sensitivity check, and consider demoting the ratio beneath
      the two-component display.
- [ ] **Designed vs built is interleaved (§4.3, §5.6 vs §8.3, §11.5).** Specific
      weight tables (50/35/15, etc.) and a twelve-factor profile are mostly
      "designed but not yet built" (only layer one is live). Add an
      implemented-vs-planned table near the top so the plan isn't read as operative.
- [ ] **No demonstration.** No named crisis is carried end-to-end. Add one
      worked example with real numbers (staying, evacuating, ratio, endangerment/
      feasibility, one vulnerability profile).

Internal inconsistencies to reconcile: "we resist a single number" vs "a single
ratio" (state the ratio is a pointer, not a verdict); multiplier saturation —
ten of twelve factors raise risk but the ±0.30 bound saturates after five 0.06
steps, contradicting the "cumulative" premise; "Risk of Evacuating" (§4.2) and
"Feasibility" (§5.3) are inverses of the same input but never reconciled — state
evac-risk ≈ (1 − feasibility).

Minor: data currency — state the 104-crises snapshot date and cadence (m1);
normalize the mixed citation styles and label CERAI/FLARE as internal projects
(m2); convert prose weight passages to the implemented-vs-planned table (m3).
**[Verify]** the "two-witness standard" attributed to GFEMS's FLARE (§7.2) —
supply a followable citation or mark FLARE/CERAI as internal sibling projects.
