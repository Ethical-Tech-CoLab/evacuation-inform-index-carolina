#!/usr/bin/env python3
"""Re-apply the road relevance gate to already-baked snapshots. Costs nothing.

Snapshots fetched before a gate fix hold items that the current rules would
reject — most importantly for "CAR" and "DRC", whose abbreviations produced no
place token, which disabled the location check entirely and let unrelated news
score as road obstruction.

This re-filters the stored items and recomputes counts and signal locally. It
can only ever *remove* items: anything the old gate discarded was never written
to the file, so a crisis whose gate has since become more permissive (the new
Gaza / West Bank aliases, for example) stays under-counted until it is
re-fetched. Those are reported at the end so they can be refreshed when API
credits allow.

Usage:
    python3 rescore_roads.py --dry-run   # report changes, write nothing
    python3 rescore_roads.py             # apply
"""
import json, glob, os, re, sys
import server

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "snapshot", "detail")
GEO = os.path.join(ROOT, "geo.js")


def load_places():
    """slug -> curated place label, for the crises that have a sub-national one.

    The sub-national gate cannot run without this. A crisis whose theatre is one
    province is judged against that province, not against its country, so
    re-filtering without the place would apply the loose country-level rule and
    keep exactly the items the gate was tightened to reject.
    """
    if not os.path.exists(GEO):
        sys.exit(f"missing {GEO} — run python3 geo/build_geo.py first")
    m = re.search(r"window\.EII_GEO\s*=\s*(\{.*\})\s*;",
                  open(GEO, encoding="utf-8").read(), re.S)
    if not m:
        sys.exit("could not parse window.EII_GEO from geo.js")
    geo = json.loads(m.group(1))
    return {slug: (g.get("place") if g.get("scope") in ("subnational", "reception")
                   else None)
            for slug, g in geo.items()}


def main():
    dry = "--dry-run" in sys.argv
    changed, stale = [], []
    places = load_places()

    for path in sorted(glob.glob(os.path.join(OUT, "*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        roads = d.get("roads")
        if not roads:
            continue
        country, crisis = d.get("country"), d.get("crisis")
        place = places.get(os.path.basename(path)[:-5])

        window_days = roads.get("query_days", 60)
        kept, counts = [], {"blocked": 0, "damaged": 0, "checkpoint": 0, "reopened": 0}
        dupes = expired = lowsrc = 0
        for it in roads.get("items") or []:
            blob = f"{it.get('title','')} {it.get('snippet','')}"
            # Publisher gate: drop social posts and travel-wiki link dumps.
            if not server.source_is_admissible(it.get("source") or it.get("url")):
                lowsrc += 1
                continue
            if not server.road_item_is_relevant(blob, country, place):
                continue
            # Recency: drop items published outside the stored window, flag undated.
            w = server.road_date_window(it, window_days)
            if w == "out":
                expired += 1
                continue
            if w == "undated":
                it = dict(it, undated=True)
            # Re-classify too: the status patterns were corrected alongside the
            # gate ("shuts" did not match \bshut\b, so closures read as reopenings).
            status, tags = server.classify_road(blob)
            if status == "unclear":
                continue
            # One wire story syndicated across four outlets is one blockage.
            if server._is_duplicate(it, kept):
                dupes += 1
                continue
            counts[status] += 1
            kept.append(dict(it, status=status, tags=tags))

        score = sum(server.ROAD_WEIGHTS[s] * n for s, n in counts.items())
        signal = round(max(0.0, min(1.0, score / server.ROAD_SATURATE)), 3)
        before = roads.get("signal")

        if kept != (roads.get("items") or []) or signal != before:
            changed.append((os.path.basename(path), country, before, signal,
                            len(roads.get("items") or []), len(kept)))
            if not dry:
                roads["items"] = kept
                roads["counts"] = counts
                roads["signal"] = signal
                roads["rescored"] = True
                if dupes:
                    roads["duplicates"] = roads.get("duplicates", 0) + dupes
                if expired:
                    roads["stale"] = roads.get("stale", 0) + expired
                if lowsrc:
                    roads["low_source"] = roads.get("low_source", 0) + lowsrc
                json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)

        # Crises whose alias list grew were searched under a stricter gate than
        # the one now in force, so their stored items may be incomplete.
        if country in server.PLACE_ALIASES:
            stale.append(country)

    print(f"{'[dry run] ' if dry else ''}{len(changed)} snapshots changed\n")
    for name, country, b, a, n_before, n_after in sorted(
            changed, key=lambda r: -(r[2] or 0)):
        print(f"  {country:22} signal {b:<6} -> {a:<6} items {n_before} -> {n_after}")

    if stale:
        uniq = sorted(set(stale))
        print(f"\n{len(uniq)} crises should be re-fetched when credits allow "
              f"(their alias set expanded, so the stored items may be incomplete):")
        print("  " + ", ".join(uniq))


if __name__ == "__main__":
    main()
