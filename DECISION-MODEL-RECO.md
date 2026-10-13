# Decision-model recommendation: dated news and source triage

Date: 2026-10-11. Public-source research proposal.
Reviewed [README](https://github.com/Ethical-Tech-CoLab/evacuation-inform-index-carolina/blob/8a1ac09cdb8a8cb6bcbbe52a546fd170aa400178/README.md).
Assessment is document-led, not validation of index weights or feeds.

## Recommended task

After retrieval, classify a public report's relevance to the stated crisis
and period; flag source/claim support for analyst review. Preserve event time,
publication time, embargo/freshness and access coverage separately.
Use relevant / unrelated / ambiguous and supports / not established.

The README distinguishes counted conflict events, crisis drivers and legal
classification. A model must not collapse these or infer that zero reported
fatalities means no coercion, blockage or protection risk.

## Evaluation

Compare exact geography/time filters and human review with a local classifier,
Jev's [citation pattern](https://docs.typesafe.ai/cookbooks/citation_check.md),
Microsoft-Decision-1 and Sage on public sources.
Split by crisis/source/time. Include embargoed reports, no-death events,
country-versus-corridor granularity and incompatible legal scope.

Measure false support, missed relevant reports, calibration, unknown handling,
reviewer effort and total accepted-report cost. Keep original source records,
including failures and unavailable coverage.

## Hard boundaries

No change to weights, index arithmetic or legal thresholds; no household
leave/stay advice, operational go/no-go, route selection or ordering of evacuees.
This is read-only strategic research support. Hosted data use requires approval;
exact proprietary models are not locally downloadable. No performance or
savings result is asserted.
