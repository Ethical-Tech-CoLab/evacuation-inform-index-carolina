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

### 1. The 60-day window is not enforced

The popup says reports are "over the last 60 days". Three stored items are
older: an IOM planning document at 226 days, a SCIAF Malawi item at 156, and an
FPRI analysis at 90 whose subject is a border closure from **2023**. Tavily's
`days` parameter is passed but evidently not honoured for every result, and
nothing downstream checks.

Two items also carry no `published_date` at all, so they cannot be placed in or
out of any window.

**Why it matters.** A three-year-old commodity-export border closure is
currently one of Niger's road-access reports. On a map read for whether people
can leave *today*, a stale item is worse than a missing one.

**To close.** Drop items whose `published_date` falls outside `query_days` in
`tavily_roads`, label undated ones as undated rather than silently keeping them,
and re-run `rescore_roads.py`. Cheap and offline.

### 2. Source quality is unchecked

DRC's only pin — and therefore its entire −2-point feasibility penalty — is a
`wikitravel.org` "Travel news" index page, a link dump that happens to mention
Congo and floods. Two other items are `facebook.com` posts. The relevance gates
judge the *text*; nothing judges the publisher.

**To close.** An allow/deny list of domains, or a minimum standard (wire
services, major outlets, UN/OCHA/IOM/NGO reporting), applied before
classification. Needs a judgment call on where the line sits — reliefweb and
local-language outlets must not be excluded along with the aggregators.

### 3. De-duplication misses re-headlined wire copy

`_is_duplicate` catches identical URLs and near-identical headlines at 0.75
token overlap. The AP and Greenwich Time versions of the same Abdin dispatch
share only ~45% of their headline words and are both counted, which is most of
why Syria now carries the highest signal on the map (0.76, −9 points).

The threshold is deliberately high: merging two genuinely distinct blockages
would *understate* obstruction, the one error this tool must not make. So this
is a known, chosen under-reach, not an oversight.

**To close.** Match on the wire dateline in the snippet ("ABDIN, Syria (AP) —")
rather than the headline, which survives re-titling. Falls back to the current
rule where no dateline is present.

### 4. Cross-crisis duplicates are invisible

A single URL can be counted under two neighbouring crises. The el-Obeid case
that prompted this was a place-gate bug and is fixed, but the general case is
legitimate — one story really can bear on two crises — so it should be
*surfaced*, not suppressed.

**To close.** Have `build_roads_layer.py` report URLs appearing under more than
one crisis, and mark them in the popup so a reader knows the same report is
being counted twice.

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

---

## Road access — coverage

### 7. 62 of 104 crises have never been searched

The largest single gap, and the layer states it: an unpinned crisis is ambiguous
between *searched, nothing found* and *never searched*, and the silent reading —
no pin, roads fine — is the dangerous one.

**To close.** `python3 snapshot_roads.py` (1 Tavily credit per crisis), then
`python3 build_roads_layer.py`, then commit `snapshot/`.

### 8. 20 crises should be re-fetched after the gate changes

`rescore_roads.py` can only ever *remove* items — anything the old gate rejected
was never written to disk. Crises whose alias set has since expanded were
searched under a stricter rule than the one now in force and may be
under-counted. The script names them at the end of every run.

---

## Map

### 9. Seven of eight road pins are country-level stand-ins

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
