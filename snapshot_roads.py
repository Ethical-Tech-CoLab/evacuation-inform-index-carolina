#!/usr/bin/env python3
"""Backfill the road-access field into snapshots that predate the roads feature.

The road-access search shipped after snapshot/detail/*.json were generated, so
every baked file has `"roads": null` and the hosted site reports road access as
"not searched". This adds only that field.

Why not `snapshot.py --force`? Two reasons:
  1. It re-fetches the Tavily news for all 104 crises, which is already present
     and correct — 104 credits spent to rewrite identical data.
  2. It re-fetches ACLED, and with ACLED_PASSWORD unset that overwrites 96
     working conflict timelines with error stubs.

This script touches nothing but `roads`, so it costs 1 credit per crisis
instead of 2 and cannot damage data it did not fetch.

Usage:
    python3 snapshot_roads.py               # backfill crises missing roads
    python3 snapshot_roads.py --force       # refetch roads even where present
    python3 snapshot_roads.py --limit 5     # stop after N fetches (try it first)
    python3 snapshot_roads.py --days 60     # news window, must match snapshot.py
    python3 snapshot_roads.py --only sudan,syria      # just these slugs
    python3 snapshot_roads.py --missing-place         # re-fetch the ones searched
                                                      # without their place term

Every fetch is anchored on the crisis's curated `place` term (from geo.js, the
same rule snapshot.py uses) and records it under `roads.place`. Before
2026-07-28 this script omitted `place`, so 30 crises were searched as bare
countries under a looser place gate than the rest of the snapshot.

`--missing-place` re-fetches those, but selects 39: no stored data predating the
marker records whether `place` was used, so the 9 place-scoped crises that
snapshot.py searched *correctly* cannot be told apart from the 30 and are swept
in too. The 9 extra credits also refresh them, so this is not worth a more
elaborate rule — and once every file carries the marker the ambiguity is gone.

Resumable: each file is written as it completes, so an interrupted run picks up
where it stopped. Keys are read from the gitignored .env, exactly like
snapshot.py.
"""
import os, sys, json, glob, time, urllib.error
import server    # reuse load_env / tavily_roads
import snapshot  # reuse load_geo — the curated place terms must match snapshot.py

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "snapshot", "detail")

# Development keys (tvly-dev-*) are rate-limited hard enough that a tight loop
# gets 429/432 within a few dozen calls, and a failed call still costs the
# wall-clock of a round trip. Pace conservatively and back off rather than
# burning through the run producing error stubs.
PACE_SECONDS = 2.0
MAX_RETRIES = 5


def curated_place(geo, slug):
    """The affected-area term for a slug, or None for country-scope crises.

    Must stay identical to snapshot.py's rule: `place` both anchors the Tavily
    query via crisis_query() and tightens the place gate in
    road_item_is_relevant, so a run that omits it searches under a weaker rule
    than the one the rest of the snapshot was built with. Only subnational and
    reception scopes carry a usable term — a country-scope `place` is just the
    country name again ("Yemen — national") and adds nothing to the query.
    """
    g = geo.get(slug) or {}
    return g.get("place") if g.get("scope") in ("subnational", "reception") else None


def fetch_with_backoff(tk, country, crisis, days, place=None):
    """One roads fetch, retrying on throttling with exponential backoff.

    429 (too many requests) and 432 (plan limit) are both transient under a dev
    key, so they are retried; anything else is a real error and propagates
    immediately instead of wasting five sleeps on it.
    """
    delay = 4.0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return server.tavily_roads(tk, country, crisis, days=days, place=place)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 432) or attempt == MAX_RETRIES:
                raise
            print(f"      throttled (HTTP {e.code}), retry {attempt}/{MAX_RETRIES - 1} "
                  f"in {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def main():
    force = "--force" in sys.argv
    days = 60
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    # Comma-separated substrings matched against the slug, so the crises
    # rescore_roads.py names as needing a re-fetch can be targeted without
    # --force re-spending a credit on all 104.
    only = None
    if "--only" in sys.argv:
        only = [s.strip().lower() for s in
                sys.argv[sys.argv.index("--only") + 1].split(",") if s.strip()]
    # Re-fetch crises whose stored roads were searched without their curated
    # place term (this script omitted it before 2026-07-28), which is a weaker
    # query and a looser place gate than snapshot.py used for the rest.
    missing_place = "--missing-place" in sys.argv

    env = server.load_env()
    tk = env.get("TAVILY_API_KEY")
    if not tk:
        sys.exit("TAVILY_API_KEY is not set in .env — nothing to do.")

    files = sorted(glob.glob(os.path.join(OUT, "*.json")))
    if not files:
        sys.exit(f"no snapshots found in {OUT}")

    geo = snapshot.load_geo()

    todo = []
    for path in files:
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            print(f"skip (unreadable) {os.path.basename(path)}: {e}")
            continue
        slug = os.path.basename(path)[:-5]
        place = curated_place(geo, slug)
        if only and not any(s in slug for s in only):
            continue
        roads = d.get("roads")
        if missing_place:
            # `place` is recorded on every fetch from 2026-07-28 on, so a stored
            # roads block that has a curated term but no record of using it was
            # searched under the weaker country-only rule.
            if not (place and roads is not None and not roads.get("place")):
                continue
        elif roads is not None and not force and not only:
            continue
        todo.append((path, d, place))

    print(f"{len(files)} snapshots, {len(todo)} need roads"
          f"{f' (limited to {limit})' if limit else ''}")
    print(f"cost: 1 Tavily credit each -> ~{min(len(todo), limit or len(todo))} credits\n")

    done = failed = 0
    for i, (path, d, place) in enumerate(todo, 1):
        if limit and done + failed >= limit:
            print(f"\nstopped at --limit {limit}")
            break
        crisis, country = d.get("crisis"), d.get("country")
        try:
            roads = fetch_with_backoff(tk, country, crisis, days, place=place)
        except Exception as e:
            failed += 1
            # Record the failure rather than leaving null, so the UI can tell
            # "searched and found nothing" apart from "never searched". Drop any
            # earlier roads error first: this script is re-run after throttling,
            # and without this each pass would stack another stub on the same file.
            errs = [x for x in (d.get("errors") or [])
                    if not str(x).startswith("roads:")]
            errs.append(f"roads: {e}")
            d["errors"] = errs
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            print(f"[{i}/{len(todo)}] FAIL  {os.path.basename(path)}: {e}")
            continue

        # Record the place term this search actually used, so a later run can
        # tell a place-anchored fetch from a country-only one instead of
        # guessing from the geo file as --missing-place has to for old data.
        roads["place"] = place
        d["roads"] = roads
        # Write immediately so an interrupted run keeps completed work.
        json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        done += 1
        n = len(roads.get("items") or [])
        sig = roads.get("signal")
        print(f"[{i}/{len(todo)}] ok    {os.path.basename(path)}  "
              f"items={n} signal={sig if sig is None else round(sig, 2)}"
              f"{'  @ ' + place if place else ''}")
        time.sleep(PACE_SECONDS)  # stay under the dev-key rate limit

    print(f"\ndone={done} failed={failed}")
    if done:
        print("Commit snapshot/detail/ and push — GitHub Pages serves these files.")


if __name__ == "__main__":
    main()
