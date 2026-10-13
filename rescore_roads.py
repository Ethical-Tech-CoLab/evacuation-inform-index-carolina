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

The recency window is measured from the time each snapshot was fetched, not
from today: `roads.fetched` where the fetch recorded it, else the file's last
git commit date, else its mtime. Measuring from today would age every stored
item out as the snapshot aged, and a rescore run months later would empty the
map while reporting nothing but "stale". `--as-of YYYY-MM-DD` overrides the
anchor for every file.

Usage:
    python3 rescore_roads.py --dry-run   # report changes, write nothing
    python3 rescore_roads.py             # apply
    python3 rescore_roads.py --as-of 2026-07-28
"""
import json, glob, os, re, subprocess, sys
from datetime import datetime
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


def fetched_at(path, roads, override=None):
    """The moment this snapshot's window should be measured from."""
    if override:
        return override
    raw = roads.get("fetched")
    if raw:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ")
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", path],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return datetime.fromisoformat(out)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        pass
    return datetime.utcfromtimestamp(os.path.getmtime(path))


def main():
    dry = "--dry-run" in sys.argv
    as_of = None
    if "--as-of" in sys.argv:
        as_of = datetime.strptime(sys.argv[sys.argv.index("--as-of") + 1], "%Y-%m-%d")
    changed, stale = [], []
    anchors = set()
    places = load_places()

    for path in sorted(glob.glob(os.path.join(OUT, "*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        roads = d.get("roads")
        if not roads:
            continue
        country, crisis = d.get("country"), d.get("crisis")
        place = places.get(os.path.basename(path)[:-5])

        window_days = roads.get("query_days", 60)
        now = fetched_at(path, roads, as_of)
        anchors.add(now.strftime("%Y-%m-%d"))
        if not roads.get("fetched") and not dry:
            # Persist the anchor, so the git-date fallback is used once per
            # file at most: any later commit touching the file (this script
            # included) would otherwise move the window forward.
            roads["fetched"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
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
            w = server.road_date_window(it, window_days, now)
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
            it = dict(it, status=status, tags=tags)
            # Attribution: the item may be in this crisis only because its
            # country is named as a party to a closure somewhere else.
            it.pop("elsewhere", None)
            elsewhere = server.foreign_subplace(
                f"{server._strip_publisher(it.get('title'))} {it.get('snippet','')}",
                country, place, it.get("source"))
            if elsewhere:
                it["elsewhere"] = elsewhere
            kept.append(it)

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
        # the one now in force, so their stored items may be incomplete. A fetch
        # records the alias set it ran under; a file without one predates that
        # and is assumed current, because every aliased crisis was re-fetched
        # under the current set on 2026-07-28 (backlog item 8) and is stamped
        # here so the next expansion is detected.
        current = list(server.PLACE_ALIASES.get(country, ()))
        if current:
            stored = roads.get("aliases")
            if stored is None:
                if not dry:
                    roads["aliases"] = current
                    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            elif set(stored) != set(current):
                stale.append(country)

    print(f"{'[dry run] ' if dry else ''}{len(changed)} snapshots changed "
          f"(recency window measured from {', '.join(sorted(anchors))})\n")
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
