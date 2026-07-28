#!/usr/bin/env python3
"""Flag where the website's publication page has drifted from EII-Paper.md.

The site copy at website/src/content/publications/evacuation-inform-index.ts is
a hand-written condensation of this paper, not a generated one, and nothing
keeps the two in step. That is a real failure mode rather than a hypothetical:
the page went on telling readers the road search covered "42 of the 104 crises"
for as long as it took someone to notice, after all 104 had been searched.

A prose diff is useless here — the mirror deliberately rewords, reorders, and
drops whole sections, and it follows a different house style (no em dashes, no
inline bold). So this checks the things that are *supposed* to agree and that
go stale silently:

  1. Figures the two documents both state (crisis counts, percentages,
     thresholds, correlations) — a number that moved in one and not the other.
  2. Claims withdrawn from the paper that the mirror may still carry, listed
     explicitly below as they are retired.
  3. Live values in snapshot/roads.json that either document contradicts.

It reports; it does not edit. Every finding needs a human to decide whether the
mirror should follow the paper or the difference is deliberate condensation.

Usage:
    python3 check_mirror_drift.py                 # report drift, exit 1 if any
    python3 check_mirror_drift.py --mirror PATH   # non-default site checkout

Exit status is 1 when something needs attention, so this can gate a commit.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.join(ROOT, "EII-Paper.md")
DEFAULT_MIRROR = os.path.expanduser(
    "~/website/src/content/publications/evacuation-inform-index.ts")
ROADS = os.path.join(ROOT, "snapshot", "roads.json")

# Claims retired from the paper. Add an entry whenever a factual claim is
# withdrawn, so the mirror is checked for it on the next run instead of being
# remembered. `pattern` is searched case-insensitively against the mirror.
RETIRED_CLAIMS = [
    (r"rescal\w*\s+(?:from\s+)?(?:INFORM'?s?\s+)?1?[\s\-–]*10",
     "the ten-to-five rescaling, withdrawn 2026-07-28 — INFORM publishes "
     "dimension scores on 1–5 and the EII uses them unchanged"),
    (r"\b42 of the 104\b|\b62 (?:crises )?(?:have )?never been searched\b",
     "the 42-of-104 road coverage split, closed 2026-07-28 — all 104 are "
     "searched"),
    (r"FLARE model developed by the Global Fund",
     "the FLARE attribution for the two-witness standard, withdrawn "
     "2026-07-28 — FLARE is an ML forced-labour classifier, not a "
     "corroboration protocol"),
]

# Figures both documents state. `label` is what to call it in the report;
# `pattern` must capture the number in group 1.
SHARED_FIGURES = [
    ("crisis count", r"\b(104)\s+(?:active\s+)?(?:humanitarian\s+)?crises\b"),
    ("endangerment threshold", r"\b(75)\s*per\s*cent\b|\b(75)%"),
    ("vulnerability factors", r"\b(twelve|12)\s+factors\b"),
    ("multiplier step", r"\b0\.(06)\b"),
    ("multiplier bounds", r"0\.7\s*(?:and|to|–|-)\s*1\.(3)\b"),
    ("INFORM dimension weights", r"\b(20)\s*per\s*cent.{0,80}?\b50\s*per\s*cent"),
    ("proxy correlation", r"\b0\.(62)\b"),
]


def read(path):
    if not os.path.exists(path):
        sys.exit(f"not found: {path}\n"
                 "Pass --mirror PATH if the site lives somewhere else.")
    return open(path, encoding="utf-8").read()


def find_all(text, pattern):
    """Every distinct captured value for a pattern, as a set of strings."""
    out = set()
    for m in re.finditer(pattern, text, re.I | re.S):
        val = next((g for g in m.groups() if g), None)
        if val:
            out.add(val.lower())
    return out


def main():
    mirror_path = DEFAULT_MIRROR
    if "--mirror" in sys.argv:
        mirror_path = os.path.expanduser(sys.argv[sys.argv.index("--mirror") + 1])

    paper, mirror = read(PAPER), read(mirror_path)
    findings = []

    # 1. Retired claims still alive in the mirror.
    for pattern, description in RETIRED_CLAIMS:
        if re.search(pattern, mirror, re.I):
            findings.append(("RETIRED CLAIM", f"the mirror still carries {description}"))

    # 2. Figures that disagree. Only compared where both documents state one,
    #    since the mirror legitimately omits most of the paper's numbers.
    for label, pattern in SHARED_FIGURES:
        p, m = find_all(paper, pattern), find_all(mirror, pattern)
        if p and m and p != m:
            findings.append(("FIGURE", f"{label}: paper says {sorted(p)}, "
                                       f"mirror says {sorted(m)}"))

    # 3. Live road-access coverage against what either document claims. The
    #    numbers here move with every re-fetch, which is exactly why prose
    #    about them goes stale.
    if os.path.exists(ROADS):
        roads = json.load(open(ROADS, encoding="utf-8"))
        searched, total = roads.get("searched"), roads.get("total")
        with_reports = roads.get("with_reports")
        # Only sentences that are actually about the road search: other
        # "N of 104" figures are legitimately different statistics (96 of 104
        # crises carry an ACLED timeline, for one).
        for name, text in (("paper", paper), ("mirror", mirror)):
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                if not re.search(r"road", sentence, re.I):
                    continue
                for m in re.finditer(r"\b(\d{1,3})\s+of\s+(?:the\s+)?(\d{1,3})\s+crises\b",
                                     sentence, re.I):
                    a, b = int(m.group(1)), int(m.group(2))
                    if b == total and a != searched:
                        findings.append((
                            "COVERAGE",
                            f"{name} says '{a} of {b} crises' in a sentence "
                            f"about road access, but roads.json reports "
                            f"{searched} of {total} searched"))

        if with_reports is not None:
            words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                     "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                     "eleven": 11, "twelve": 12, "thirteen": 13,
                     "fourteen": 14, "fifteen": 15, "sixteen": 16,
                     "seventeen": 17, "eighteen": 18, "nineteen": 19,
                     "twenty": 20}
            for name, text in (("paper", paper), ("mirror", mirror)):
                for m in re.finditer(
                        r"\b(\w+)\s+crises\s+(?:currently\s+)?carry\s+(?:road\s+)?reports\b",
                        text, re.I):
                    raw = m.group(1).lower()
                    stated = words.get(raw, int(raw) if raw.isdigit() else None)
                    if stated is None:          # not a number at all
                        continue
                    if stated != with_reports:
                        findings.append((
                            "COVERAGE",
                            f"{name} says {stated} crises carry reports; "
                            f"roads.json reports {with_reports}"))

    print(f"paper:  {os.path.relpath(PAPER, ROOT)}")
    print(f"mirror: {mirror_path}\n")
    if not findings:
        print("No drift detected on the checked claims.")
        print("\nNote: this checks shared figures, retired claims, and live road")
        print("coverage. It cannot tell you whether new analysis in the paper has")
        print("been carried across — that still needs reading both.")
        return 0

    for kind, message in findings:
        print(f"  [{kind}] {message}")
    print(f"\n{len(findings)} item(s) need attention.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
