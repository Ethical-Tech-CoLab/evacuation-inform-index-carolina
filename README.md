# Evacuation Inform Index (EII)

**[Live site](https://ethical-tech-colab.github.io/evacuation-inform-index-carolina/)** ·
**[Research report](EII-Paper.md)** (plain-language, non-technical)

A composite index for assessing evacuation conditions, with preliminary weights
synthesised from **INFORM**, **ACLED** and **FSI** logic — to be validated by
AHP expert surveys.

**🔗 Live site:** https://ethical-tech-colab.github.io/evacuation-inform-index-carolina/

## Overview

The index scores three weighted dimensions on a 1–5 scale:

- **Impact** (20%)
- **Conditions** (50%)
- **Complexity** (30%)

It is fed by a set of open data sources (see the *Feeds* section of the site),
with a live backend that pulls news, reported road blockages, and an ACLED
conflict timeline.

## Scope — what "conflict" means here, and what the index is for

Three definitions of *conflict* run through this model and are deliberately kept
apart (full treatment: **Methodology → Definitions** on the site, and §4.0 of
[EII-Paper.md](EII-Paper.md)):

1. **A counted event** — ACLED's six categories, queried unfiltered. But only
   **monthly fatalities** enter the score, so a month of mass arrests, forced
   relocation or checkpoint closures with no deaths reads as a quiet month. The
   ACLED tier used here carries a **~12-month embargo**.
2. **A crisis driver** — INFORM's labels. Of the 104 crises, 39 are Conflict/
   Violence; the rest are displacement, flood, drought, cyclone, economic. **All
   104 are scored with the same formula**; the driver label never enters the
   arithmetic.
3. **A legal classification** — IAC / occupation / NIAC / other situations of
   violence. **Not modelled at all.** This matters because the 75% marker comes
   from GC IV Art. 49, which governs *occupied territory* and binds an Occupying
   Power — the index draws that line on every crisis regardless.

**Unit of analysis:** one score per crisis, mostly at country level, refreshed
monthly. This is a strategic instrument for comparing crises — not a corridor, a
convoy, or an hour.

**Not fit for:** advising any individual or household whether to leave;
operational go/no-go; route selection; ranking who evacuates first; any
determination of legal status; or **justifying a restriction on movement** —
`EII > 1.0` is not a finding that anyone should be prevented from leaving
(UDHR Art. 13; ICCPR Art. 12).

The Dimension-3 vulnerability profile (elderly, pregnant, non-ambulatory,
targeted groups, and eight more) carries its own set of limits — equal ±0.06
increments, saturation at five factors, and no way to express *impossibility*
rather than difficulty. See **Limits specific to vulnerable subgroups** in the
Methodology tab and §9.11 of the paper before reading anything into those
toggles.

## Map

The map opens on **high-resolution Esri satellite imagery** (zoomable to ~1 m,
with a transparent place-name layer on top) and renders crises as a **heatmap**
of the selected metric. Crisis dots stay on top of the heat as click targets —
the heat carries the value, the dots carry the data. A *Display as* control
switches between heatmap, graduated circles, or both; it opens on both.

**Colour and size are two different variables.** Dot colour is the metric you
select; dot radius is the crisis's **INFORM Severity class (1–5)**, on a fixed
1–5 scale so filtering the map never re-scales the dots. Where several crises
share one point, the dot takes the highest severity among them, matching the
rule the colour already follows. A crisis with no severity class draws at the
smallest size and says so in its popup.

One caveat is stated on the map itself: a heatmap blurs between points, so the
colour *between* two crises is a rendering effect, not a measurement. EII scores
discrete crises, not a continuous risk surface.

**Crisis-type filter.** Four checkboxes group INFORM's drivers into
environmental (floods, drought, cyclone, earthquake), conflict & violence,
international displacement, and political & economic. The export truncates
driver strings at 60 characters (`"Political/econom"`, `"Cyc"`), so matching is
by prefix, which recovers the intended driver and makes the counts agree with
the Sense-2 figure in Methodology (50 / 39 / 25 / 22 / 18 / 9 / 1). Crises carry
several drivers, so the groups overlap by design and a crisis shows when *any*
of its drivers is ticked. All four are on by default and every one of the 104
crises lands in at least one, so the unfiltered map is the whole dataset. The
legend says so whenever a filter is narrowing the view.

**Roads & streets** is a transparent overlay that rides on whichever base layer
is showing, so the network reads *against* the imagery instead of replacing it.
Tiles are Esri World Transportation (OpenStreetMap / HERE / Garmin), keyless.
Not Google: Leaflet cannot lawfully consume Google's tiles directly, and the
supported route through the Maps JavaScript API needs a billing-enabled key
embedded in the page, which a public static deployment cannot hold safely.

### Water and crossings — two layers from Fika

A river with no crossing is a blocked route, and both halves of that sentence are
badly mapped. Two overlays come from **[Fika](https://fika.org)** (formerly
Bridges to Prosperity), whose rural-access work produces exactly this data.

**💧 Waterways — WaterNet.** A machine-learning model Fika ran over satellite
imagery to predict waterways worldwide; it roughly tripled the mapped extent, and
most of what it added is the small rural drainage that separates a village from
the road it would leave by. Served as PMTiles straight from Fika's public bucket
(CC-BY 4.0) — 51 GB globally, but HTTP range requests mean the browser fetches
only the tiles on screen, so nothing is vendored here.

These are **predictions, not surveyed hydrography**, so the layer draws streams
already present in TDX-Hydro in blue and the ones the model added in amber rather
than one confident web that hides which half is inference. Streams thin by
Strahler order as you zoom out, or the world view is a solid mat. Lines the model
routes *across lake surfaces* to keep the network connected are dropped — drawn,
they turn Lake Malawi into a hatched mat that reads as dozens of rivers. Nothing
in this layer says a stream is bridged, fordable, or flowing this month.

The tileset advertises zoom 11 but its top level is absent in places — over
Ethiopia the layer silently emptied above zoom 10 — so the map reads one level
lower and overzooms.

**🌉 Trail bridges.** 962 pedestrian crossings Fika has built, supported or
influenced, vendored into `fika/bridges.json`:

```bash
python3 build_fika_bridges.py      # refresh from Fika's published register
```

These are the inverse of the road pins in every way that matters. A road pin is a
crisis-level stand-in for a report with no coordinates; a bridge is a **surveyed
structure at a real point**, and it is positive evidence — a place where a river
that would otherwise stop people on foot does not.

The coverage caveat runs the other way, and it is the one a reader is most likely
to get wrong. Fika works where Fika works: Rwanda (305) and Ethiopia (283) hold
well over half of these, 14 of the 23 countries carry an EII crisis, and **most
crises on the map are in countries with no Fika bridge at all**. An empty area
means "Fika has not built here", never "there is no crossing here" — which is
what the note beside the layer says, because on a sparse map the silent reading is
the opposite one. 19 rows of the source register carry no usable coordinate and
are dropped rather than parked at (0, 0); the build script reports the count.

**Clickable legal citations.** Every provision cited in Methodology opens an
explainer with four parts: what it says in plain words, the operative text, why
this index cites it, and *how far that is justified*. The fourth is the point —
several do not survive it, and the panels say so. Thirteen provisions, also
listed outright at the foot of the tab.

## Where the crises actually are

INFORM publishes no coordinates. The original `data.js` therefore placed every
crisis at a rounded country centroid — and, where one country carried several
crises, at that centroid plus a ~0.9° offset so the markers would not overlap.
About three quarters of the points were somewhere the crisis is not: Gaza in
southern Syria (230 km), Cabo Delgado 800 km south of itself, Papua 2,054 km
west in Sulawesi. That is not only a cosmetic problem — the route weather, the
satellite zoom and the road-access search are all anchored to these coordinates.

Every crisis now has a curated location in **[`geo/locations.csv`](geo/locations.csv)**,
and the map states what each point represents rather than implying precision it
does not have:

| Scope | What the point is | Count |
|---|---|---|
| **Sub-national** | The crisis names an area; point is that area's centroid | 17 |
| **Reception** | Displacement concentrated in known hosting/transit areas; point is the main one, named | 22 |
| **Country** | The crisis is national in scope; point is the country's approximate **population-weighted** centroid | 65 |

Population-weighted, not geographic: for Libya, Algeria, Mali, Chad, Niger,
Mauritania and Egypt the two are hundreds of kilometres apart, and the
geographic centre is empty desert. Each row also carries a `confidence` value —
`low` marks the six crises whose name is national but whose impact is almost
certainly localised, where INFORM names no affected area and a more precise
point could not be assigned without inventing one. Those crises say so in the UI.

The ~0.9° anti-overlap offset is gone. Where several crises genuinely share a
country-level point (Ecuador has three), the map draws **one marker listing all
of them** instead of moving them ~100 km apart to solve a rendering problem.

```bash
python3 geo/build_geo.py           # validate locations.csv and rebuild geo.js
python3 geo/build_geo.py --check   # validate only
```

The build fails if any crisis is unlocated, any scope or confidence value is
unrecognised, or any point falls outside its own country's bounding box — the
guard that would have caught Gaza-in-Syria. `data.js` keeps its original
coordinates as the untouched INFORM export; `geo.js` is generated and overrides
them at load.

The curated place names also sharpen the live searches: Tavily is now queried
for "Cabo Delgado province, Mozambique" rather than "northern Mozambique", which
is how the reporting is actually written.

## Road access

Whether the roads out are usable is the most decisive input to evacuation
feasibility, and no open global feed reports it for conflict zones — so the
backend runs a second Tavily search per crisis for road closures, destroyed
bridges, checkpoints and impassable routes, classifies each item
(blocked / damaged / checkpoint / reopened), and turns the weighted counts into
a feasibility penalty in the CERAI lens, capped at 12 points.

The limits are shown in the UI, not buried: the status is keyword-derived from
headlines rather than verified, news prose carries no coordinates so blockages
cannot be drawn as routes on the map, and **zero reports is not evidence that
roads are open**. This doubles the Tavily cost of a detail call to 2 credits;
pass `?roads=0` (or `snapshot.py --no-roads`) to skip it.

**On the map.** `build_roads_layer.py` flattens the road block out of all 104
`snapshot/detail/*.json` into `snapshot/roads.json` (~10 KB), so the
*🚧 Road access — reported blockages* overlay costs one request instead of 104,
fetched only when the layer is switched on. A pin sits at the **crisis**, never
at the blockage, for the coordinate reason above, and says so in its popup.

Coverage is the part that matters, and the layer states it:

| | crises |
|---|---:|
| Searched, reports found (pinned) | 14 |
| Searched, nothing found | 90 |
| **Never searched** | **0** |
| Total | 104 |

Every crisis has now been searched, so an unpinned crisis means one thing:
searched, nothing found. The layer still states the split, because on a map
about whether people can get out the silent reading, no pin so roads fine, is
the dangerous one. When crises are added to the INFORM export, run
`python3 snapshot_roads.py` for the new ones (1 Tavily credit per crisis), then
`python3 build_roads_layer.py`, and commit `snapshot/`. The 60-day window is
measured from each snapshot's fetch time, so `python3 rescore_roads.py` can
re-apply the gates to stored items at any later date without ageing them out.

**What the layer still gets wrong** is written down rather than left implicit:
wire-copy de-duplication that has never fired on a live item, a pin that stands
in for a whole country, and a keyword classifier that reads headline wording
rather than the sentence. See **[BACKLOG.md](BACKLOG.md)**.

## Running locally

```bash
cp .env.example .env   # add your API keys
python server.py
```

Then open `index.html` (or the URL the server prints).

Every key is optional. With none set, the map, scores, weather and satellite
layers still work; only the news and conflict panels go quiet, each naming the
key it is missing. See **[INTEGRATIONS.md](INTEGRATIONS.md)** for every external
service the project calls, why each is called from the server or the browser,
and what to check when one misbehaves.

## Hosted site (static snapshot)

GitHub Pages serves static files only, so it can't run `server.py`. To make the
hosted site behave like the live app, the backend responses are **baked into
static JSON** and committed under `snapshot/`.

The frontend tries the live `/api/detail` endpoint first (works when you run
`server.py` locally) and falls back to `snapshot/detail/<slug>.json` when no
backend is present — so clicking a crisis on GitHub Pages still shows the Tavily
news and ACLED timeline, with a "📸 Snapshot" note indicating the data is frozen
at capture time.

To refresh the snapshot (re-runs the real Tavily + ACLED calls, needs a
populated `.env`):

```bash
python3 snapshot.py            # fill in missing crises (resumable)
python3 snapshot.py --force    # regenerate all 104 crises (~208 Tavily credits)
python3 snapshot.py --no-roads # skip road access, halving the credit cost
git add snapshot && git commit -m "Refresh snapshot" && git push
```

## Satellite damage assessment (Microsoft HASTE)

The Map tab can overlay AI **building/route damage maps** from
[Microsoft HASTE](https://aka.ms/HASTE) + Planet. HASTE is self-hosted (no public
API), so you run it and paste its damage-layer tile URL into EII — see
[HASTE_SETUP.md](HASTE_SETUP.md). Until connected, the overlay is empty (nothing
is faked). Damage feeds the CERAI lens: infrastructure loss raises endangerment,
blocked routes lower feasibility.

## Files

- `index.html` — the dashboard UI
- `data.js` — index data and weights (its `lat`/`lng` are superseded by `geo.js`)
- `geo/locations.csv` — curated location, scope and confidence for all 104 crises
- `geo/build_geo.py` — validates that table and generates `geo.js`
- `geo.js` — generated; the coordinates the map actually uses
- `server.py` — live backend (news + ACLED timeline, cached)
- `snapshot.py` — bakes the static snapshot the hosted site falls back to
- `snapshot_roads.py` — backfills the road-access field into existing snapshots
- `build_roads_layer.py` — flattens those road blocks into `snapshot/roads.json`
- `snapshot/` — pre-generated per-crisis JSON served on GitHub Pages
- `acled-api/` — ACLED helper script
- `rescore_roads.py` — re-applies the road gates to baked snapshots, offline
- `BACKLOG.md` — known gaps, why each matters, and what closing it would take
- `INTEGRATIONS.md` — every external API, how it is called, and how to debug it
- `HASTE_SETUP.md` — how to run Microsoft HASTE and overlay its damage tiles
- `EII-Paper.md` — plain-language research report on what the index does

---

## Peer Review

The full independent academic peer review of this report is in [PEER-REVIEW.md](PEER-REVIEW.md) (also available as [Word](peer-review/EII-Peer-Review.docx) under [`peer-review/`](peer-review/)).

**Recommendation:** Major revisions

**What the review found:**

- The central proxy is unvalidated: INFORM Complexity (humanitarian access for responders) is used as a stand-in for civilian-evacuation risk, and the report never shows where the two diverge. — **Fixed: examined against the live 104-crisis dataset (new S4.2a).**
- The headline ratio is fragile: the arbitrary 0.5 floor can swing it ~2.5x, and equal ratios hide very different absolute stakes. — **Fixed: the floor is shown to be inert on real data, the compression is quantified in the paper, and the crisis panel now warns where the ratio stops carrying information.**
- No worked example: a tool meant to make a comparison visible never walks one real crisis through the numbers. — **Fixed: two crises walked end to end (new S4.2b).**

**Noted strength:** Scoring leaving-vs-staying and danger-vs-feasibility as separate dimensions is a genuine contribution, paired with unusually honest self-disclosure.


### Revisions applied (peer review, Tier 3)

**The INFORM Complexity proxy is now examined rather than merely labelled** (new S4.2a), against the live April 2026 dataset of 104 crises:

- **Correlation between Conditions (RSS) and Complexity (RSE) is r = 0.62** — a real association that still leaves over half the variance unshared. Complexity is a different measurement, not a noisy copy.
- **The bias has a specific direction.** Complexity is largely a property of the *country* (conflict-driven operating environment for responders); Conditions is a property of *this crisis*. When a low-intensity crisis sits inside a high-conflict state, the two pull apart and the index reads an aid-delivery fact as a civilian-movement fact.
- **The worked divergence case is Yemen.** "2026 Floods in Yemen" carries the **highest EDI in the index (2.60)** — RSS 1.36 (the dataset minimum) against RSE 3.53. It earns that score because Yemen's *war* inflates Complexity, not because fleeing floodwater is dangerous. The favourable case is Bangladesh (EDI 0.50), where low Complexity genuinely reflects a well-rehearsed cyclone-evacuation system.
- **New finding the review did not anticipate: the ratio is least informative where stakes are highest.** Across the seventeen severity-5 crises, EDI spans only 0.83–1.13, with Somalia, Burkina Faso and Mali all at exactly 1.00. Both components saturate near the ceiling and the ratio collapses toward unity. Every large EDI in the index comes from a low- or mid-severity crisis.
- **The 0.5 floor is inert on real data:** zero of 104 crises have RSS below 0.5 (observed minimum 1.36), so the safeguard distorts no published figure.

**Two crises are now walked end to end** (new S4.2b): Sudan's complex crisis (RSS 4.87, RSE 4.73, EDI 0.97 — the compression case) and the 2026 Yemen floods (RSS 1.36, RSE 3.53, EDI 2.60 — the misreading case), each with the floor check shown.

**Also noted** (S5.3): Feasibility and the Risk Score for Evacuating are the same quantity under two names, both derived from INFORM Complexity and pointing in opposite directions. They do not contradict each other arithmetically, but presenting them as separate concepts implies two independent readings of movement where there is one.
