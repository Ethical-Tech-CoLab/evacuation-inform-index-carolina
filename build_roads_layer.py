#!/usr/bin/env python3
"""Aggregate the per-crisis road-access findings into one file the map can draw.

The road-access reports live in snapshot/detail/<slug>.json, one file per
crisis, and the drawer fetches a single file when you open a crisis. Drawing
pins for the whole world needs every crisis at once, and 104 requests to paint
one layer is not a trade worth making — so this flattens the road block out of
each detail file into snapshot/roads.json.

Coverage is the thing this file has to be honest about. Of the 104 crises, the
road search has only ever run for some of them; the rest carry "roads": null
and have never been looked at. A crisis with no pin is therefore ambiguous
between "searched, nothing found" and "never searched", and those two mean
very different things on a map about whether people can leave. So the output
records all three states explicitly and the map reports the split.

Coordinates come from geo.js, the same curated source the crisis markers use,
NOT from snapshot/index.json. index.json carries whatever coordinates were
current when the snapshot last ran, so a stale one silently reverts the pins to
the data.js country centroids geo/locations.csv exists to replace — which is how
the Mindanao pin once landed in the sea off Luzon and the Lebanon pin inside
Syria, each hundreds of kilometres from the crisis marker on the same map.
Reading geo.js directly means the two can no longer drift apart.

Usage:
    python3 build_roads_layer.py            # rebuild snapshot/roads.json

Cheap and offline: it only reads files snapshot.py / snapshot_roads.py already
wrote, so it costs no API credits and can be re-run at will.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(ROOT, "snapshot")
INDEX = os.path.join(SNAP, "index.json")
DETAIL = os.path.join(SNAP, "detail")
GEO = os.path.join(ROOT, "geo.js")
OUT = os.path.join(SNAP, "roads.json")

# Kept in the same order the drawer lists them, worst first, so the map can take
# the first status present as the one to colour a pin by.
ORDER = ["blocked", "damaged", "checkpoint", "reopened"]

# The map popup shows the same fields the drawer does; anything else in an item
# is search-engine bookkeeping the reader has no use for.
ITEM_FIELDS = ("title", "url", "date", "source", "status", "tags", "undated")


def load_geo():
    """Curated crisis locations from geo.js — same parse as snapshot.load_geo()."""
    if not os.path.exists(GEO):
        sys.exit(f"missing {GEO} — run python3 geo/build_geo.py first")
    m = re.search(r"window\.EII_GEO\s*=\s*(\{.*\})\s*;",
                  open(GEO, encoding="utf-8").read(), re.S)
    if not m:
        sys.exit("could not parse window.EII_GEO from geo.js")
    return json.loads(m.group(1))


def main():
    if not os.path.exists(INDEX):
        sys.exit(f"missing {INDEX} — run snapshot.py first")

    index = json.load(open(INDEX, encoding="utf-8"))
    items = index.get("items", [])
    geo = load_geo()

    out, searched, unsearched, with_reports, unlocated = [], 0, 0, 0, []

    for entry in items:
        slug = entry.get("slug")
        path = os.path.join(DETAIL, f"{slug}.json")
        if not os.path.exists(path):
            unsearched += 1
            continue

        detail = json.load(open(path, encoding="utf-8"))
        roads = detail.get("roads")

        # null means the road search never ran for this crisis — not that it ran
        # and found nothing. Recorded as a count, not as a pin.
        if not roads:
            unsearched += 1
            continue

        searched += 1
        reports = roads.get("items") or []
        if not reports:
            continue
        with_reports += 1

        counts = roads.get("counts") or {}
        # Colour the pin by the most serious status actually reported.
        worst = next((s for s in ORDER if counts.get(s)), None)

        # No curated point means no pin. Falling back to entry["lat"] would put
        # the pin wherever the last snapshot happened to place it — the stale
        # centroid this file exists to stop using — so an uncurated crisis is
        # reported as unlocated instead of drawn somewhere plausible-looking.
        g = geo.get(slug)
        if not g:
            unlocated.append(slug)

        out.append({
            "slug": slug,
            "crisis": entry.get("crisis"),
            "country": entry.get("country"),
            "lat": g.get("lat") if g else None,
            "lng": g.get("lng") if g else None,
            # What the point represents, so the popup can avoid claiming a
            # precision a country-level stand-in does not have.
            "place": g.get("place") if g else None,
            "scope": g.get("scope") if g else None,
            "confidence": g.get("confidence") if g else None,
            "counts": {k: v for k, v in counts.items() if v},
            "worst": worst,
            "signal": roads.get("signal"),
            "considered": roads.get("considered"),
            "query_days": roads.get("query_days"),
            "items": [
                {k: it.get(k) for k in ITEM_FIELDS if it.get(k) is not None}
                for it in reports
            ],
        })

    # Cross-crisis duplicates. One URL can be counted under two neighbouring
    # crises. That is sometimes legitimate — a single dispatch really can bear on
    # both — so this surfaces it rather than suppressing it: each shared item is
    # told which *other* crises carry it, and the popup marks it so a reader knows
    # the same report is being counted more than once.
    by_url = {}
    for c in out:
        for it in c["items"]:
            u = it.get("url")
            if u:
                by_url.setdefault(u, []).append(c)
    shared = {u: cs for u, cs in by_url.items() if len(cs) > 1}
    for u, crises_sharing in shared.items():
        labels = [c.get("crisis") or c.get("country") or c["slug"]
                  for c in crises_sharing]
        for c in crises_sharing:
            here = c.get("crisis") or c.get("country") or c["slug"]
            for it in c["items"]:
                if it.get("url") == u:
                    it["also_in"] = [n for n in labels if n != here]

    payload = {
        "total": len(items),
        "cross_crisis": len(shared),
        "searched": searched,
        "unsearched": unsearched,
        "with_reports": with_reports,
        "unlocated": len(unlocated),
        "crises": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print(f"  {len(items)} crises: {searched} searched, {unsearched} never searched")
    print(f"  {with_reports} carry road-access reports, "
          f"{with_reports - len(unlocated)} of them pinned")
    if unlocated:
        print(f"  {len(unlocated)} have reports but no curated location "
              f"and are NOT pinned: {', '.join(unlocated)}")
    print(f"  {sum(len(c['items']) for c in out)} reports total")
    if shared:
        print(f"  {len(shared)} URL(s) counted under more than one crisis "
              f"(marked in the popup):")
        for u, crises_sharing in shared.items():
            labels = [c.get("crisis") or c.get("country") or c["slug"]
                      for c in crises_sharing]
            print(f"    {' + '.join(labels)}: {u}")


if __name__ == "__main__":
    main()
