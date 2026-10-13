#!/usr/bin/env python3
"""How much the vulnerability-profile step moves the CERAI display. Offline.

The twelve Dimension-3 toggles each move one multiplier by a fixed step (0.06
in the tool) inside a 0.7 to 1.3 band. The multiplier scales endangerment up
and feasibility down. It never enters the EII ratio, so the crisis ranking is
untouched by any setting of it; what it moves is the endangerment band a crisis
is shown in and whether the protection-gap flag (endangerment >= 75 and
feasibility <= 40) fires.

This recomputes both over the 104 crises in data.js for a range of step sizes
and numbers of upward toggles, from the INFORM inputs alone (no live ACLED,
weather or road penalty), and prints a markdown table for the paper.

Usage:
    python3 sensitivity_step.py
"""
import json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
STEPS = (0.03, 0.06, 0.09, 0.12)
TOGGLES = (1, 2, 3, 5, 10)
LO, HI = 0.7, 1.3


def clamp(v, a, b):
    return max(a, min(b, v))


def band(e):
    return ("Critical" if e >= 90 else "Extreme" if e >= 75 else
            "Severe" if e >= 55 else "Elevated" if e >= 35 else "Manageable")


def load():
    src = open(os.path.join(ROOT, "data.js"), encoding="utf-8").read()
    m = re.search(r"window\.EDI_DATA=(\[.*\]);?", src, re.S)
    return json.loads(m.group(1))


def scores(crises, m):
    # Same arithmetic as ceraiScores() and ceraiBlockHTML() in index.html.
    rows = []
    for c in crises:
        e = clamp((c["rss"] - 1) / 4 * 100, 0, 100)
        f = clamp((1 - (c["rse"] - 1) / 4) * 100, 0, 100)
        rows.append((clamp(e * m, 0, 100), clamp(f * (2 - m), 0, 100)))
    return rows


def main():
    crises = load()
    base = scores(crises, 1.0)
    n = len(crises)
    print(f"{n} crises, multiplier 1.0: "
          f"{sum(e >= 75 for e, _ in base)} at Extreme or above, "
          f"{sum(e >= 75 and f <= 40 for e, f in base)} protection gaps\n")
    print("| step | upward toggles | multiplier | Extreme or above | protection gaps | band changed |")
    print("|---:|---:|---:|---:|---:|---:|")
    for step in STEPS:
        for k in TOGGLES:
            m = clamp(1 + step * k, LO, HI)
            rows = scores(crises, m)
            over = sum(e >= 75 for e, _ in rows)
            gap = sum(e >= 75 and f <= 40 for e, f in rows)
            moved = sum(band(e2) != band(e1) for (e1, _), (e2, _) in zip(base, rows))
            sat = " (cap)" if m >= HI else ""
            print(f"| {step:.2f} | {k} | {m:.2f}{sat} | {over} | {gap} | {moved} |")


if __name__ == "__main__":
    main()
