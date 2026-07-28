# The Evacuation Inform Index (EII)

### A Research Report on a Decision Support Tool for Weighing the Risk of Leaving Against the Risk of Staying

*Prepared as a plain language review of the EII research prototype*
*based on the software and documentation contained in this repository*

---

## Foreword

Every displacement crisis contains a question that is rarely asked out loud: is leaving actually safer than staying? Humanitarian practice tends to treat evacuation as the obvious good, the thing that rescues people from harm. In practice the journey itself carries risk. Roads are mined or blockaded. Checkpoints separate families. The elderly and the sick do not survive transit that a healthy adult would manage. A destination that looked open on Monday has closed by Thursday.

The Evacuation Inform Index, known as EII, is a research prototype that treats that question as the object of measurement. It does not tell anyone to move or to stay. It scores the two risks separately, side by side, so that the comparison between them becomes visible and can be argued with.

This report explains what the tool is, what it measures, where its numbers come from, and where its authors have marked the boundaries of what it can support. It is written for a policy, humanitarian, and legal readership rather than a technical one. Readers looking for the software itself will find it in the same repository as this document.

---

## 1. Executive Summary

1.1 The EII is an interactive web application that scores 104 active humanitarian crises on two dimensions: the risk of remaining in place, and the risk of attempting to leave. It expresses the relationship between them as a single ratio, while always displaying the two component scores that produced it.

1.2 The scores are not invented for the prototype. They are derived from the INFORM Severity Index, the monthly crisis severity model produced by ACAPS with the Joint Research Centre of the European Commission. The April 2026 release provides the live backbone, covering 104 crises.

*A note on currency.* INFORM Severity is published monthly, and the crisis count changes with each release as crises are added, merged, or closed. Every figure in this report — the 104 crises, the driver counts in 4.0.2, the correlation and range statistics in 4.2a, and both worked examples in 4.2b — is computed from the **April 2026 release** and should be read as a snapshot of that release, not as a standing fact about the world. Later releases will move these numbers. The tool recomputes its own figures from whatever export is loaded, so the application does not go stale in the way this document does; where a reader finds the two disagreeing, the application is current and the report is dated.

1.3 A second analytical layer, adapted from the Civilian Evacuation Risk Anticipation Index (CERAI), keeps two ideas deliberately apart: how dangerous a situation is, and how practical it is to move people out of it. Collapsing those into one number would let operational difficulty quietly cancel out legal obligation. The tool refuses that collapse.

1.4 Live feeds supplement the monthly baseline. Conflict event data comes from ACLED, recent developments from news retrieval, and route weather from Open-Meteo. An optional satellite damage overlay can be connected if the user runs Microsoft HASTE themselves.

1.5 The prototype is explicit that its weights are researcher estimates awaiting expert validation, that its endangerment and feasibility measures are architectural proxies rather than validated instruments, and that no independent ground truth for evacuation decisions exists against which it could be calibrated. Section 9 sets out these limits in full.

1.6 The intended use is to direct attention, not to issue verdicts. A human decision maker retains the call.

---

## 2. The Problem the Index Addresses

2.1 Existing humanitarian indices measure how bad a situation is. They rank crises by severity so that funding and attention can be allocated. What they do not do is model the alternative. A crisis scored as extremely severe tells a planner that people are suffering; it does not tell them whether moving those people would reduce or increase the harm.

2.2 That gap matters because the two risks move independently. A siege can be catastrophic to endure and simultaneously impossible to escape. A drought can be survivable in place while the routes out remain open and safe. Treating severity as a proxy for "should evacuate" conflates conditions that need to be distinguished.

2.3 International humanitarian law makes the distinction consequential rather than merely analytical. Under Article 49 of the Fourth Geneva Convention, an Occupying Power may undertake total or partial evacuation of a given area where the security of the population or imperative military reasons so demand, must return those evacuated to their homes once hostilities in the area have ceased, and must ensure proper accommodation, satisfactory conditions of hygiene, health, safety and nutrition, and that members of the same family are not separated. Evacuation is therefore a regulated act with conditions attached, not a self evidently benign one.

2.4 The prototype's response is to score staying and leaving as two separate quantities and to publish both.

---

## 3. What the Index Is

3.1 The EII is a browser based application. It consists of a world map of active crises, a panel of live developments per crisis, a methodology section, a catalogue of data sources, and a reference list. It runs against a small local server when live data is wanted, and falls back to a stored set of captured responses when hosted as a static site.

3.2 It is a research prototype. It is not deployed in any operational setting, has no institutional mandate, and produces no output that any organisation is obliged to act upon.

3.3 The repository contains the full methodology, including the parts that are designed but not yet built. The distinction between what is implemented and what is planned is marked throughout the interface rather than left to the reader to infer.

**3.4 What is built, and what is only designed.** The sections that follow describe the full design, including specific weights for components that do not yet exist. The specificity is a description of intent, not a report of a running system. This table is the boundary, and it should be consulted before any weight table in section 4 or 5 is read as operative.

| Component | Section | Status |
|---|---|---|
| INFORM mapping: Conditions → Risk of Staying, Complexity → Risk of Evacuating | 4.2 | **Live** — computed for all 104 crises |
| The EDI ratio, with denominator floor and mandatory two-component display | 4.1 | **Live** |
| Low-information warning where both components are at or above 3.5 | 4.2b | **Live** — thresholds computed from the loaded dataset at run time |
| Endangerment and Feasibility split, with protection-gap flag | 5.3 | **Live**, both derived from INFORM (a single input under two names) |
| ACLED conflict events and the three-month fatality trajectory | 5.5 | **Live** |
| News retrieval and route weather | 4.2, 5.3 | **Live** |
| Road-access signal from news retrieval | 6 | **Live**, prototype quality — see the repository backlog |
| Vulnerability profile: twelve factors, 0.06 step, 0.7–1.3 bound | 5.6 | **Live as an interactive display**; the factors, step size and bounds are researcher estimates, unvalidated, and the band saturates (9.12.2) |
| Satellite damage overlay (Microsoft HASTE) | 7.7 | **Optional**, empty unless the user self-hosts a deployment |
| Three-layer architecture with 50/35/15 weights and its sub-weights | 4.3 | **Designed only.** Layer one is approximated by the INFORM mapping above; layers two and three are not implemented as weighted components |
| Seven-dimension decomposition, corridor and checkpoint dynamics, destination-readiness gatekeepers | 8.3 | **Designed only** |
| Expert elicitation, fuzzy AHP weight validation, historical calibration | 11.2–11.4 | **Not started.** Every weight in this report is a single researcher's estimate |

The short version: the live instrument is the INFORM mapping, the ratio, the CERAI-style split, and the live feeds around them. The weight tables in 4.3 and the twelve-factor apparatus in 5.6 describe where the work is going, and only 5.6 has a working interface. No weight in this report has been validated by anyone.

---

## 4. How the Index Works

### 4.0 Definitions: what the index means by conflict

The word conflict does three different jobs in this index, and collapsing them is the most likely way to misread a score. They are set out separately here.

**4.0.1 Conflict as a counted event.** Operationally, the index defines conflict as ACLED defines it: a dated, geolocated, sourced incident falling into one of six categories. The query is country wide and unfiltered by category, and the interface shows the resulting type mix per crisis. The six, with their recorded volumes aggregated across the 96 of 104 crises that carry an ACLED timeline in the captured snapshot:

| ACLED event type | What it covers | Events | Share | Reaches the score? |
|---|---|---:|---:|---|
| Explosions / remote violence | Shelling, airstrikes, IEDs, drone strikes | 185,992 | 26.6% | Yes — fatalities expected |
| Protests | Non violent public demonstration | 183,943 | 26.3% | **No** — non violent by definition |
| Battles | Armed clash between two organised armed actors | 127,449 | 18.2% | Yes — fatalities expected |
| Violence against civilians | Attacks on unarmed civilians by an armed actor | 98,154 | 14.0% | Yes — fatalities expected |
| Strategic developments | Contextual events: arrests, agreements, looting | 66,187 | 9.5% | **No** — non violent by definition |
| Riots | Violent demonstration by a non organised mob | 38,410 | 5.5% | Sometimes — fatalities variable |
| **Total** | | **700,135** | **100%** | |

Two of the six, accounting for 250,130 events or 36 per cent of everything recorded, are non violent by ACLED's own definitions: a protest that turns violent is recoded as a riot, and strategic developments are explicitly contextual. They fill the timeline a user reads and contribute essentially nothing to the number the model computes. One caveat on this table's own evidence: the aggregation in `server.py` counts events per type but does not break fatalities down by type, so the final column is derived from ACLED's category definitions rather than from measured per type fatality data. Adding fatalities to that aggregation would let the claim be made from measurement.

The score, however, uses one number from that stream: monthly fatalities. Three consequences follow, and each is a limitation rather than a design choice made for a reason.

- A non lethal event contributes nothing. A month of mass arrest, forced relocation, checkpoint closure, property destruction, or looting in which nobody is killed reads as a quiet month.
- Fatalities measure lethality, not the danger facing a civilian who has not yet been killed. Displacement risk and death counts are related but distinct quantities, and only the second is in the trajectory.
- The ACLED access tier used here serves data on a roughly twelve month embargo. "Recent three months against the preceding three" may therefore mean recent as of a year ago. The interface reports the cutoff date it received rather than concealing it.

**4.0.2 Conflict as a crisis driver.** INFORM Severity labels each crisis with one or more drivers. In the April 2026 release carried here, of 104 crises, 39 are labelled Conflict or Violence, 50 International Displacement, 25 Floods, 22 Drought, 18 Political or economic crisis, 9 Cyclone, and 1 Earthquake; most crises carry several, which is why the counts sum to more than 104.

The index scores all 104 with the same formula. It does not restrict itself to armed conflict and it does not alter its arithmetic when the driver is a cyclone. A reader looking at the endangerment score for a drought is reading a quantity constructed for the same purpose as the one shown for a war. The driver label is carried in the data and displayed, but it does not enter the calculation.

**4.0.3 Conflict as a legal classification.** The 75 per cent obligation marker is drawn from Article 49 of the Fourth Geneva Convention. That article sits in Part III, Section III of the Convention, which governs occupied territory, and it binds an Occupying Power. The index draws the line on all 104 crises whether or not an occupation exists. This is a deliberate simplification, and read strictly it is an overreach: the marker is a reference to a legal standard, not a claim that the standard is in force in every crisis shown.

The classifications that actually determine which body of law applies are these.

| Classification | Trigger | Consequence for evacuation |
|---|---|---|
| International armed conflict | Resort to armed force between States (Common Art. 2, GC I–IV); no intensity threshold | Full GC IV protections; Art. 49 applies where the situation is also one of occupation |
| Belligerent occupation | Territory placed under the authority of a hostile army (Hague Regulations Art. 42) | The only situation in which the Art. 49 evacuation regime applies in terms: permitted for the security of the population or imperative military reasons, with return, accommodation, and family unity obligations attached |
| Non international armed conflict | Organised armed groups and protracted armed violence (Common Art. 3; AP II where its conditions are met; ICTY, *Tadić*, 1995, para. 70) | Forced displacement of civilians prohibited by AP II Art. 17 unless their security or imperative military reasons demand it |
| Other situations of violence | Internal disturbance, riot, gang and criminal violence below the armed conflict threshold | IHL does not apply. International and regional human rights law governs, together with the Guiding Principles on Internal Displacement |

The index does not classify any crisis into these categories. It has no field for the classification and INFORM does not supply one. This matters because the legal consequence of a high endangerment score is different in each row: in an occupation it engages a specific evacuation regime, in a non international armed conflict it engages a prohibition on forced displacement, and in a situation of gang violence it engages human rights law and no part of Article 49 at all. Several crises on the map sit in that last row, where the framing the interface uses does not fit. Carrying an explicit classification field is the single highest value addition a future version could make to this section.

**4.0.4 What falls outside the definition.** Criminal and gang violence is counted whenever ACLED records it, and nothing in the model distinguishes it from an armed conflict even though the legal consequences diverge sharply. Structural and slow onset harm — economic collapse, denial of services, statelessness — is partly present inside INFORM's Conditions score but absent from the conflict stream entirely. And three conflict forms are declared out of scope outright, inherited from the sibling calibration described in 8.4: genocide, large enclave precision operations, and sieges beyond roughly ninety days. In those three the model should not be used at all, rather than used with caution.

### 4.1 The central ratio

The index expresses its result as a ratio: the Risk Score for Evacuating divided by the Risk Score for Staying.

A value above 1.0 indicates that evacuation carries more risk than remaining. A value below 1.0 indicates the reverse. A value near 1.0 indicates that the two courses of action carry comparable risk, which is itself a meaningful finding rather than an absence of one.

Two safeguards apply. Ratios become unstable as the denominator approaches zero, so a floor of 0.5 on a five point scale is applied to the staying score. And the ratio is never shown alone: both component scores accompany it wherever it appears. On the current dataset the floor never engages — the lowest observed staying score is 1.36 — so no published figure depends on it; 4.2a gives the check.

**4.1.1 What kind of quantity this is, and what division assumes.** Dividing one score by another treats both as ratio-scale quantities: numbers with a true zero, where "twice as much" is meaningful. INFORM's underlying severity bands do not clearly meet that standard. They are built by aggregating indicators that are each scored on a one to five ordinal band, and the dimension score inherits that character: it behaves as a ranking with interval-like spacing rather than as a measured quantity. There is no defensible sense in which a Conditions score of 4 represents exactly twice the severity of a 2, and therefore no fully defensible sense in which the EDI's "2.60" means evacuation is 2.6 times riskier than staying.

The honest position is that the division is a *comparison device*, not a measurement. What the EDI supports is ordering and sign — whether evacuation scores worse than staying, and roughly how far apart they sit — not arithmetic on the result. Two consequences follow, and the prototype accepts both. Differences of a few hundredths between crises carry no meaning and should not be ranked against each other. And the EDI must never be averaged, summed across crises, or fed into a further calculation, because those operations require exactly the ratio-scale property the inputs lack.

This is a real limitation rather than a resolved one. The alternative that would remove it — reporting the two components as a labelled pair and abandoning the quotient — is genuinely worth considering, and 4.2a's finding that the ratio compresses toward 1.0 precisely in the most severe crises strengthens the case for it. The quotient is retained because a single ordered number is what makes 104 crises comparable at a glance, which is the tool's purpose; but it is retained on the understanding that it is a pointer, not a measurement.

**4.1.2 The ratio and the refusal to collapse.** Section 5 argues that danger and feasibility must never be collapsed into one score, while this section foregrounds a single ratio. The tension is worth stating directly rather than leaving to the reader. The EDI is a pointer that directs attention to crises where the staying/leaving comparison is unusual; it is not a verdict about either dimension, and it is not the object of section 5's critique, because both components remain visible wherever it is shown and neither is ever absorbed into it. The collapse section 5 forbids is the one that would let low feasibility quietly reduce apparent danger, extinguishing an obligation. A ratio that always carries its own numerator and denominator on its face cannot do that. Where the ratio does mislead, it is for the reasons in 4.2a — the proxy beneath it — not because it is a single number.

### 4.2 The live data backbone

The two component scores are drawn from the INFORM Severity Index rather than constructed independently.

INFORM assembles 31 core indicators into three weighted dimensions: the impact of the crisis at 20 per cent, the conditions of the affected people at 50 per cent, and the complexity of the situation at 30 per cent. ACAPS describes these weights as a current best estimate to be refined by expert analysis and statistical methods, which places the EII's own provisional weighting in familiar company.

The EII maps two of those dimensions onto its own question:

| INFORM dimension | Becomes | Represents |
|---|---|---|
| Conditions of affected people | Risk Score for Staying | How severe it is to remain in place |
| Complexity of the crisis (access constraints, society and safety, operating environment) | Risk Score for Evacuating | How difficult and dangerous it is to move |

Both are used exactly as INFORM publishes them. INFORM scores its indicators on a one to five scale and aggregates them into dimension scores on that same scale, so Conditions and Complexity arrive already on the five point scale the EII uses and no conversion is applied: RSS equals the published Conditions score and RSE equals the published Complexity score, for all 104 crises. The ten point figure that also appears in INFORM outputs, and in the worked examples below, is the *composite* severity index across all three dimensions, which the EII does not use as an input. Earlier drafts of this report, and the tool's own methodology notes, described a rescaling from ten points to five. There is no such step, and the claim has been withdrawn.

The choice is defensible on its face. Complexity in INFORM measures precisely the conditions that obstruct movement: humanitarian access, safety of operations, and the operating environment. It is nonetheless a substitution, and the prototype labels it as one.

### 4.2a Where the proxy breaks: an examination of the substitution

Labelling the substitution is not the same as testing it, and the peer review is right that this is the load-bearing validity question for the whole instrument. This section examines it against the live April 2026 dataset of 104 crises.

**The two dimensions are related but far from interchangeable.** Across the 104 crises the correlation between Conditions (RSS) and Complexity (RSE) is **r = 0.62**. That is a real association, but it leaves well over half the variance unshared. Complexity is not a noisy copy of Conditions; it is a different measurement, and the EII's whole output is the ratio between them.

**The direction of the bias is specific: Complexity is a property of the country, not of the crisis.** INFORM Complexity scores the operating environment responders face — access constraints, safety of operations, the wider society and security picture. Those are largely national and largely driven by conflict. Conditions, by contrast, tracks the affected population of *this* crisis. When a low-intensity crisis occurs inside a high-conflict country, the two come apart hard, and the EII reads that gap as a statement about civilian evacuation when it is a statement about aid delivery.

*The clearest case in the dataset is Yemen, which appears three times:*

| Yemen crisis | Severity | RSS (Conditions) | RSE (Complexity) | EDI |
|---|---|---|---|---|
| Complex crisis in Yemen | 5 | 4.56 | 4.69 | 1.03 |
| International Displacement to Yemen | 4 | 2.78 | 3.76 | 1.35 |
| **2026 Floods in Yemen** | **3** | **1.36** | **3.53** | **2.60** |

The floods entry carries **the highest EDI in the entire index, 2.60** — the index's strongest possible statement that leaving is more dangerous than staying. But it earns that score by combining the *lowest* Conditions score in the dataset (1.36, because a flood's effect on the affected population is moderate) with a Complexity score of 3.53 that reflects Yemen's war. A family deciding whether to move away from floodwater is not facing 3.53-worth of evacuation danger from the flood; the score is picking up the constraints that make it hard for *agencies* to reach them. The number is real, the inputs are real, and the interpretation the index invites is wrong.

*The favourable case runs the other way.* Bangladesh's climatic-shocks crisis scores RSS 4.11 against RSE 2.07, an EDI of 0.50 — strongly "staying is riskier." Here the proxy happens to land well: Bangladesh's low Complexity reflects a functioning, well-rehearsed disaster-response system, and its cyclone-shelter evacuation programme genuinely is among the safest mass movements in the world. The mapping works when the crisis type and the country's operating environment share a cause. It fails when they do not.

**Expected direction of bias, stated plainly.** The proxy will *overstate* evacuation risk for lower-intensity crises inside conflict-affected states — floods, displacement inflows, and disease outbreaks in countries such as Yemen, Somalia, or Mali — because national conflict conditions inflate Complexity independently of the hazard being scored. It will *understate* evacuation risk where a specific corridor is dangerous but the national operating environment is permissive, since Complexity has no corridor-level resolution at all.

**A third finding, which the review did not anticipate: the ratio is least informative where the stakes are highest.** Across the seventeen severity-5 crises, EDI ranges only from 0.83 (Colombia) to 1.13 (Myanmar), clustering tightly around 1.0 — Somalia, Burkina Faso and Mali all sit at exactly 1.00. In the most severe crises, Conditions and Complexity are both near the top of the scale, so their ratio collapses toward unity and discriminates almost nothing. Every large EDI value in the index comes from a low- or mid-severity crisis. The headline metric is therefore most confident precisely where it is least meaningful, which is a strong argument for the two-component display over the ratio.

**On the 0.5 denominator floor.** The review asks for a sensitivity check. On the current dataset the floor is **inert: zero of 104 crises have RSS below 0.5**, and the observed minimum is 1.36. The safeguard is therefore not distorting any published figure, though it remains untested rather than validated, and would begin to bite only if the index were extended to very low-severity situations.

**Why the substitution is still worth keeping, for now.** No public dataset scores civilian-evacuation difficulty at crisis level across 104 crises; building one is the work described in section 11. Complexity is the closest available construct with real coverage, real provenance, and a published methodology. The defensible position is to keep it, name it as a proxy at every point of use, and read the EDI as a *screening prompt* rather than a measurement — with the explicit caveat that low-intensity crises in high-conflict states will be systematically flagged as dangerous to leave for reasons that have nothing to do with the hazard.

### 4.2b A worked example, end to end

The review notes that the index is described but never run. Two crises, taken from the live April 2026 data.

**Sudan — Complex crisis.** INFORM severity 5, INFORM index 9.6.

1. INFORM Conditions of affected people = 4.87, used as published → **RSS = 4.87**.
2. INFORM Complexity = 4.73 → **RSE = 4.73**.
3. Denominator floor check: RSS 4.87 ≥ 0.5, so the floor does not engage.
4. **EDI = RSE / RSS = 4.73 / 4.87 = 0.97**.

*Reading it:* both components are near the ceiling, so the index is saying that staying and leaving are both close to maximally bad, and that on these measures leaving is marginally the less bad of the two. The ratio's proximity to 1.0 carries little information; the pair (4.87, 4.73) carries most of it. This is exactly the compression described above, and it is why the tool displays both components rather than the ratio alone.

**The tool now says so at the point the ratio is read.** Quantifying the compression in this paper does not help a user looking at a crisis panel, so the panel states it. Where both components sit at 3.5 or above on the five point scale, the panel carries a note that the ratio carries little information for that crisis, gives the pair, and says that staying and leaving are both close to maximally bad. The threshold is read off the distribution rather than chosen: the 25 crises in that band span an EII range of 0.30, from 0.83 to 1.13, while the other 79 span 2.14, from 0.46 to 2.60. The figures in the note are computed from the loaded dataset at run time, so a refreshed INFORM export cannot leave them stale. This is the residue of the review's second finding, which the earlier revision could only quantify.

**2026 Floods in Yemen.** INFORM severity 3, INFORM index 4.2.

1. INFORM Conditions = 1.36 → **RSS = 1.36** (the lowest in the dataset).
2. INFORM Complexity = 3.53 → **RSE = 3.53**.
3. Floor check: 1.36 ≥ 0.5, floor does not engage.
4. **EDI = 3.53 / 1.36 = 2.60** — the highest in the index.

*Reading it:* taken at face value the index says evacuation is two and a half times riskier than remaining. Taken correctly, it says the affected population's conditions are relatively mild while the operating environment in Yemen is severe — and the latter is a fact about the war, not about the flood. This is the single case a user is most likely to misread, and it is the reason 4.2a exists.

### 4.3 The three layer architecture

The fuller design, of which the live build implements the first layer, divides the problem into three:

| Layer | Weight | Function | Precedent |
|---|---|---|---|
| Objective Risk Score | 50 per cent | Universal factors identical for everyone in the geography: active hostilities, likelihood of future hostility, life risk from natural hazards | INFORM Severity, ACLED, Global Conflict Risk Index |
| Infrastructure and Access | 35 per cent | Availability of routes, resources, and connectivity | ACAPS Humanitarian Access, IDMC |
| Personal Vulnerability Modifier | 15 per cent | Household and demographic factors applied as a multiplier rather than an addition | CDC Social Vulnerability Index, IOM RICD |

Within the first layer, active hostilities carry the heaviest weight at 20 per cent on the reasoning that they represent the most immediate and fastest changing threat to life. Forward looking hostility risk and non conflict life risk take 15 per cent each. Within the second, route availability leads at 12 per cent, followed by infrastructure availability at 10 per cent, security alerts at 8 per cent, and weather at 5 per cent.

The third layer is deliberately multiplicative. A personal characteristic does not add a fixed quantity of risk; it scales the risk already present in the environment. Being elderly in a stable region and being elderly under bombardment are not the same increment.

### 4.4 Why the parts are multiplied rather than averaged

Indicators combine by weighted geometric mean rather than arithmetic mean. The practical consequence is that a catastrophic score on one component cannot be averaged away by comfortable scores elsewhere. If every evacuation route is closed, no amount of favourable weather or food security compensates for it.

This is the same non compensatory logic used by the Human Development Index and by INFORM Risk. It reflects a judgement about the world rather than a mathematical preference: some failures are absolute.

---

## 5. The CERAI Lens: Keeping Danger and Feasibility Apart

5.1 The prototype adopts a structural argument from the CERAI framework, which holds that danger and feasibility must never be collapsed into one score.

5.2 The reasoning is legal as much as analytical. The obligation to protect civilians arises from the danger they face. Operational difficulty does not extinguish that obligation. A single blended number would allow low feasibility to drag down the composite, making a desperate situation appear less urgent precisely because it is hard to resolve. Keeping the two visible produces the opposite effect: high danger combined with low feasibility becomes a signal that the problem has moved beyond operational reach and requires political engagement.

5.3 The tool renders the split live for each crisis.

| Dimension | Question it answers | How the prototype computes it |
|---|---|---|
| Endangerment | How dangerous is it to stay? | INFORM Conditions expressed as a percentage, with a 75 per cent obligation threshold marked, and a trajectory drawn from recent ACLED fatality trends |
| Feasibility | Can civilians realistically move? | INFORM Complexity inverted and expressed as a percentage, reduced by live route weather from Open-Meteo |
| Protection gap flag | Where is escalation needed? | Raised when endangerment is at or above 75 per cent while feasibility is at or below 40 per cent |

Note that Feasibility and the Risk Score for Evacuating are **the same quantity under two names**, pointing in opposite directions: 4.2 maps Complexity onto RSE so that higher Complexity means higher evacuation risk, while this table inverts Complexity so that higher Complexity means lower feasibility. Stated as an identity: evacuation risk ≈ (1 − feasibility). Both are internally consistent and they do not contradict each other arithmetically — high evacuation risk and low feasibility are the same claim — but presenting them as two separate concepts implies the tool has two independent readings of movement when it has one. They share a single input, INFORM Complexity, and therefore share every limitation set out in 4.2a. A future version should either derive Feasibility from an independent source or collapse the two into one reported quantity.

5.4 Endangerment is banded for readability: manageable, elevated, severe, extreme, and critical, with critical reserved for scores at or above 90 per cent.

5.5 The trajectory indicator compares ACLED fatalities in the most recent three months against the preceding three months. It answers whether a situation is deteriorating or stabilising, which a static severity score cannot convey.

### 5.6 The vulnerability profile

A crisis score describes a population. It does not describe a person within it. The prototype therefore offers an interactive profile of twelve factors that a user can switch on to represent a particular group.

Each factor shifts a multiplier by 0.06, bounded between 0.7 and 1.3. The multiplier raises endangerment and lowers feasibility, on the reasoning that these are two causally distinct pathways rather than one effect measured twice.

The twelve factors extend well beyond mobility. Young children, the elderly, the disabled and medically dependent, the wounded and acutely sick, and pregnant women and new mothers all bear on the physical capacity to travel. Unaccompanied and separated minors, people facing gendered violence risk, members of targeted ethnic, religious or political groups, undocumented people with identity gaps, and linguistic minorities with low literacy face a different kind of exposure: they are endangered by targeting, detention, or exclusion rather than by the difficulty of walking. Two factors work in the opposite direction, reducing assessed risk: prior evacuation experience and available financial resources.

The distinction matters. A demographic list alone would treat vulnerability as a question of who moves slowly. The protection based additions treat it as a question of who is hunted, who is turned back, and who cannot read the sign telling them where to go.

---

## 6. What a User Sees

6.1 The map presents all 104 crises as markers, and colour and size carry different variables. A marker is coloured by whichever measure the user selects: the ratio itself, the risk of staying, or the risk of evacuating. A marker is sized by the crisis's INFORM Severity class, on a fixed scale of one to five rather than the range present in the data, so that filtering the view never silently re-scales the dots. The two channels are therefore readable independently, and a severity five crisis draws large whether its ratio says stay or evacuate. Where several crises share a point the marker takes the highest severity among them, which is the rule the colour already followed. A crisis carrying no severity class draws at the smallest size and says so in its panel rather than being interpolated into a class it does not have. The legend carries a key for size as well as for colour. Selecting a crisis opens a panel with the full breakdown.

6.2 The live panel provides, for each crisis, recent developments retrieved from news sources and a structured conflict timeline from ACLED, with every item linked to its primary source. The time window is adjustable from thirty days to twelve months.

6.3 The methodology section carries the material summarised in sections 4 and 5 of this report, together with the variable tables and their proposed weights.

6.4 The data sources section catalogues eighteen feeds with their update frequency and cost, distinguishing those in use from those on the roadmap and marking which require payment.

6.5 The references section lists the methodological precedents and the academic literature the design draws on.

6.6 The map also supports high resolution satellite imagery, daily NASA imagery layers, and an optional damage assessment overlay described in section 7.

6.7 The map can be filtered by crisis type. INFORM's driver labels are grouped into four families: environmental, covering floods, drought, cyclone and earthquake; conflict and violence; international displacement; and political or economic crisis. The labels arrive from the INFORM export truncated at sixty characters, so they are matched on their opening characters rather than in full, which recovers the intended driver and makes the counts agree with the figure in section 4.0. Crises routinely carry several drivers, so the groups overlap deliberately and a crisis appears whenever any of its drivers is selected. All four are selected by default and every one of the 104 crises belongs to at least one, so the unfiltered map is the whole dataset. Whenever a filter is narrowing the view the legend says how many crises are being shown and which types are selected, because a filtered map that does not announce itself misleads by omission.

6.8 Every legal provision cited in the methodology section is clickable and opens an explanation written for a reader with no legal training. Each explanation has four parts: what the provision requires in plain words, the operative text of the provision itself so the plain language rendering can be checked against the source, why this index invokes it, and how far that invocation is justified. The fourth part is the reason the feature exists. A citation that is only ever displayed reads as authority the model has not earned, and several of these citations do not survive the examination: the endangerment threshold is labelled with Article 49 of the Fourth Geneva Convention on every crisis, including floods and droughts where an article governing occupied territory has no application at all, and Article 17 of Additional Protocol II is the more relevant rule for most of the armed conflicts shown and is not used. Thirteen provisions are covered, and they are also listed outright at the foot of the methodology section, since a clickable citation is only discoverable once a reader notices that it is clickable.

6.9 Two further map layers address the roads themselves. A transparent road network overlay can be switched on over any base layer, so streets and highways can be read against the satellite imagery rather than replacing it. The tiles come from Esri's World Transportation service, which is drawn from OpenStreetMap, HERE and Garmin data and requires no key. Google's tiles were considered and rejected: they cannot lawfully be consumed by a general mapping library, and the supported route through the Google Maps JavaScript API requires a billing enabled key embedded in the page, which a public static deployment cannot hold safely. Separately, the road access reports described in 6.2 can be pinned on the map. A pin marks the crisis a report belongs to and never the blockage itself, because news prose carries no coordinates: a report that a named road has been cut identifies no point that can be plotted. The layer states its own coverage whenever it is switched on, for the reason given in 9.10.

---

## 7. Evidence, Provenance, and the Treatment of Uncertainty

7.1 The laboratory hosting this work has a lineage in supply chain traceability and forced labour mitigation, and several practices carry over from that domain into how this index treats evidence.

7.2 A two witness standard separates a fact corroborated by two or more independent reports from a single unverified claim, sharpening source credibility into a graded ladder rather than a binary. Earlier drafts attributed this standard to the FLARE model developed by the Global Fund to End Modern Slavery. That attribution was wrong and has been withdrawn: FLARE is a machine learning classifier that predicts company level forced labour risk, not a corroboration protocol, and no published GFEMS methodology describes a formally named two witness standard. The convention is this project's own, in the spirit of the corroboration practices common to the supply chain traceability work described in 7.1, and it is claimed as nothing more than that. CERAI and FLARE are named throughout this report as sibling and internal projects supplying design lineage, not as external authorities a reader can consult.

7.3 The score is deterministic rather than generated. Every number the tool produces comes from a fixed, auditable formula. Where a language model is involved, it supplies source grounded facts and never overrides the arithmetic. A reader can reconstruct any score by hand.

7.4 An evidence gap is treated as a risk signal rather than a neutral absence. An unverified corridor segment is penalised, not assumed safe. This inverts the common default in which missing information quietly reads as an acceptable situation.

7.5 Where the tool falls back to background knowledge rather than a live verified source, that fallback is labelled, capped below verified status, and flagged. Absence of verification never presents itself as verification.

7.6 The prototype states plainly which methods it has not implemented. It does not use the eleven forced labour indicators of the International Labour Organization, machine learning classifiers, or cryptographically signed credentials. Those belong to the models cited as design lineage and are not claimed as features here.

7.7 The satellite damage layer follows the same discipline. Microsoft HASTE, developed with Planet, converts satellite imagery into building and route damage maps. It has no public interface and must be self hosted, so the overlay stays empty until a user connects their own deployment. The interface reports the real state of that connection: it requests tiles, turns green only when tiles actually arrive, reports failure when none do, and distinguishes partial coverage from failure, since a damage layer legitimately returns nothing outside its project area. Nothing about the connection is asserted before it is observed.

---

## 8. Inheritance from Sibling Projects

8.1 The index draws structures from several related evacuation projects within the same organisation, and marks each as either incorporated or planned.

8.2 Incorporated: the protection based vulnerable group categories described in section 5.6, each carrying a basis in international humanitarian law; and the non compensatory geometric aggregation with its floor on the staying score.

8.3 Planned: destination readiness gatekeepers, under which a confirmed refusal by a host authority would cap feasibility outright rather than merely reducing it; a seven dimension decomposition that would replace the current single score inputs with scored sub dimensions; and corridor and checkpoint dynamics covering exit gates, ceasefire windows, congestion, siege conditions, and degradation of the information environment.

8.4 A calibration harness from a sibling project, fitted to sixteen historical cases, contributes something other than a number. Its documented failure modes, in which the model is declared out of scope for genocide, large enclave precision operations, and sieges beyond roughly ninety days, are cited as a practice worth copying. Declaring where a model stops working is presented as part of the model.

---

## 9. What the Index Does Not Do

9.1 The repository states its limitations openly. They are reproduced here because they are the most important part of the document for any reader considering what weight to give the tool. Section 9.12 sets out a further set specific to vulnerable subgroups, since the treatment of those groups is where the gap between what the interface implies and what the arithmetic does is widest.

9.2 Proxy construct. Endangerment and feasibility derive from INFORM sub scores supplemented by conflict and weather data. They are not CERAI's full twenty two variable engine. They should be read as a faithful architectural proxy, not a validated instrument.

9.3 Researcher assigned weights. Every weight is a best estimate pending expert validation through structured elicitation. This places them at the same evidentiary level as INFORM's own initial weights, which is to say provisional and untested by consensus.

9.4 No ground truth calibration. Independent ground truth for evacuation decisions does not exist. There is no register of correct historical calls against which the index could be scored. Sibling calibration provides face validity, not statistical generalisation.

9.5 Population level vulnerability. The demographic profile is a scenario the user sets, not measured household data. It cannot capture individual circumstance.

9.6 Static snapshot. The endangerment and feasibility pair has no corridor dynamics, ceasefire windows, or modelling of misinformation. When hosted as a static site, news and conflict data are captured rather than live; weather remains live.

9.7 No modelling of political will. The index cannot represent actor behaviour, negotiation status, sudden shifts in belligerent intent, or the granting and withdrawal of consent. In many real evacuations these are the determining factors.

9.8 Variable evidence quality. Source credibility tiering is a stated design principle that is not yet weighted in the code. Live inputs differ in their verification standards.

9.9 Optional damage layer. Without a self hosted deployment, physical damage evidence is simply absent from the assessment.

9.10 Road access is searched everywhere, but read from prose. The road access search has now been run for all 104 crises, so an absence of reports means one thing rather than two: the search ran and returned nothing. Fourteen crises carry reports. What remains is the harder limit, and it is a limit of method rather than of coverage. The signal is read from news prose by keyword matching, which has no notion of what a sentence is about: an item reporting an airstrike can be classified as a road blockage because the surrounding words match. Items are gated for recency and for whether the publisher is a newsroom rather than a social platform or a travel wiki, but nothing checks whether the road described is the road that matters, and an item can be attributed to a country because that country is named as a party while the route it describes lies elsewhere. The pin marks the crisis, never the blockage, because news prose carries no coordinates. The layer should be read as a prompt to look, not as a map of which roads are open.

9.11 Correlation, not causation. The index prioritises attention. It is decision support and must not be the sole basis for an evacuation decision.

### 9.12 Limits specific to vulnerable subgroups

The vulnerability profile described in 5.6 is the part of the tool most likely to be read as saying something about a particular person, and it is the part least able to. Twelve toggles each move a single multiplier by 0.06 within a band of 0.7 to 1.3. Every property of that construction is a limitation.

**9.12.1 Equal increments assert an equivalence nobody has established.** Being non ambulatory and being a linguistic minority move the score by the same 0.06. No evidence supports that parity. It was a placeholder chosen so that the mechanism could be demonstrated, and it has not been replaced by anything better.

**9.12.2 The band saturates at five factors.** Five upward toggles reach the 1.3 ceiling. The sixth through the tenth change nothing at all. The households carrying the most compounded vulnerability — an elderly, disabled, undocumented, non literate member of a targeted minority — are precisely where the model stops discriminating between cases.

**9.12.3 A multiplier cannot express impossibility.** For some conditions evacuation is not harder, it is foreclosed: a non ambulatory person with no vehicle, a woman in obstructed labour, a dialysis patient with a three day interval, a ventilated patient without power. These require a hard cap on feasibility of the kind the roadmap's destination readiness gatekeepers apply to host authorities. Nothing in the model applies such a cap on behalf of a person. The law recognises the category even though the index does not: Article 17 of the Fourth Geneva Convention provides for local agreements to remove the wounded, the sick, the infirm, the aged, children and maternity cases from besieged or encircled areas, precisely because ordinary movement is not available to them.

**9.12.4 Factors are treated as independent when they are correlated and interacting.** Elderly, disabled or medically dependent, and wounded or acutely sick overlap heavily in any real population; adding 0.06 for each counts one underlying condition up to three times. The error also runs the other way. Pregnancy combined with the absence of a functioning obstetric facility is worse than the sum of the two terms, and an additive form cannot represent that.

**9.12.5 The two pathways are forced to mirror each other.** The implementation raises endangerment by the multiplier and lowers feasibility by its complement, the same magnitude with the sign reversed. That is wrong for most of the twelve. Being targeted for one's ethnicity multiplies the danger of remaining while leaving physical mobility untouched. Late term pregnancy does close to the reverse. A wheelchair user facing a flooded road suffers a collapse in feasibility without a corresponding jump in the danger of staying. Each factor needs two coefficients, one per pathway, not one number applied twice.

**9.12.6 Binary toggles hide the variation that matters clinically.** Elderly, defined as 65 and over, spans an independent 66 year old and a bedbound 92 year old. Pregnant spans the first trimester and the thirty ninth week, states that differ by an order of magnitude for both danger and movement. Disabled covers a controlled chronic condition and complete dependence on assistive equipment and a carer. The toggle records the category and discards the severity, which is the part that determines whether the person can move.

**9.12.7 The household is the evacuating unit, not the individual.** Families move at the pace of their least mobile member and frequently refuse to separate, a refusal the law supports: Article 49 requires that members of the same family not be separated. A profile of individual attributes cannot represent the fact that one immobile member can immobilise a household of eight, nor that the alternative to immobility is a separation international law discourages.

**9.12.8 Care relationships are absent.** Both the dependent and the carer are constrained, and only the dependent appears in the list. The toggle for unaccompanied and separated minors exists; the adult whose own evacuation is constrained by three children and a parent with dementia does not.

**9.12.9 No prevalence, therefore no caseload.** The profile answers how a scenario would shift a score. It never answers how many people in a given crisis are in that scenario. Standard planning figures exist and could be used: the World Health Organization estimates that roughly 16 per cent of the global population lives with a significant disability, and inter agency reproductive health planning commonly assumes that around 4 per cent of a crisis affected population is pregnant at any time. The index carries neither. Without prevalence, the multiplier describes a hypothetical person rather than the population the underlying crisis score is about.

**9.12.10 The legal basis is cited but not operative.** The protection based groups were added because each has a footing in international law — Article 8(a) of Additional Protocol I classes maternity cases, newborn babies, the infirm and expectant mothers as wounded and sick and extends that protection to them; customary IHL Rule 138 entitles the elderly, disabled and infirm to special respect and protection; Rules 134 and 135 address women and children; Article 11 of the Convention on the Rights of Persons with Disabilities addresses persons with disabilities in situations of risk and humanitarian emergency. None of this changes the arithmetic. The legal basis explains why a group is on the list; it does not set that group's coefficient, and a reader should not infer that a strong legal footing has produced a strong weight.

---

## 10. Governance and Intended Use

10.1 The governance position is stated in a single sentence borrowed from the FLARE project: a decision support tool, not an executioner.

10.2 In practice this means the index is built to inform a judgement rather than to replace one. It surfaces which crises show a wide divergence between the risk of staying and the risk of leaving, which show a protection gap requiring political rather than operational escalation, and which are deteriorating on recent evidence.

10.3 It does not recommend evacuation. It does not rank populations for priority. It does not produce a threshold at which action becomes mandatory. The 75 per cent marker on the endangerment scale is a reference line drawn from the legal framework, not a trigger the software acts upon.

### 10.4 Unit of analysis and resolution

Before any statement of use, the scale of the instrument has to be explicit. The index produces one score per crisis, and most crises in INFORM are defined at country level. INFORM Severity refreshes monthly, ACLED weekly and subject to the embargo described in 4.0.1, weather live. The tool therefore operates at the scale of a national crisis over a month. It is not a corridor, a district, a convoy, or an hour, and no amount of care in reading it will make it those things.

### 10.5 Questions the index is built to answer

- Across a portfolio of active crises, where does the risk of staying diverge most sharply from the risk of leaving?
- Where does high endangerment coincide with low feasibility, meaning the problem has passed beyond operational reach and become political?
- Which crises are deteriorating on recent conflict evidence rather than on reputation or news volume?
- What does an explicitly two sided, non compensatory evacuation model look like when it is actually built? This is a methodological demonstration and a teaching artefact as much as an analytical one.

Its readers are analysts and advocacy staff comparing crises, researchers, and students of humanitarian method. It is not built for field operations and it is not built for affected people.

### 10.6 Uses the index is not fit for

Stated positively, so that a reader can check a proposed use against the list.

- **Advising an individual or household whether to leave.** The scores are population level and the vulnerability profile is a scenario the user sets, not a record of anyone. Section 9.12 sets out why the profile in particular cannot bear this weight.
- **Operational go or no go decisions** on a convoy, a corridor, or a movement window. The model holds no corridor state, no checkpoint state, and no ceasefire clock.
- **Route selection or timing.** There is no route geometry in the index at all; the road access signal is keyword derived from news headlines and capped so that it can shade a score but never drive one.
- **Ranking who evacuates first.** The tool does not prioritise populations and has no defensible basis on which to do so.
- **Any determination affecting a person's legal status** — asylum, visa, protection claim, or eligibility.
- **Justifying a restriction on movement.** This is the misuse the design most needs to name. A ratio above 1.0 records that the model scored evacuation as carrying more risk than remaining. It is not a finding that anyone should be prevented from leaving. Freedom of movement, affirmed in Article 13 of the Universal Declaration and Article 12 of the ICCPR, is not conditioned on the output of a risk model. Any use of this index to support a closure order, an exit ban, or a refusal of passage inverts its purpose, and the fact that the tool already flags such restrictions as constraints on evacuation, in 10.7 below, should make that reading harder rather than easier.

10.7 Two constraint layers sit outside the scoring entirely, on the view that they should filter a recommendation rather than dilute it. A financial feasibility check asks whether a recommended action is affordable once transport, accommodation, asset loss, and income disruption are counted. A legal and rights check, referencing the freedom of movement affirmed in Article 13 of the Universal Declaration of Human Rights, flags exit visa requirements, travel bans, and closure orders that restrict people from evacuating themselves.

---

## 11. From Prototype to Instrument

11.1 The repository sets out a three phase sequence for turning the current build into something defensible.

11.2 Phase one covers variable design, using structured expert elicitation across two rounds with a panel of eight to twelve specialists, to set initial weights at the layer and sub variable level.

11.3 Phase two covers weight validation using fuzzy analytic hierarchy process methods, chosen because they accommodate the ambiguity in expert judgement that ordinary pairwise comparison forces experts to suppress.

11.4 Phase three covers calibration against historical cases, including Sudan in 2023, Ukraine in 2022, Kabul in 2021, Lebanon in 2006, and Haiti in 2010, together with statistical analysis to identify and remove redundant variables.

11.5 Until phase two is complete, the weights on the map are the considered estimates of a single researcher. The tool says so on the page where those weights appear.

---

## 12. Conclusion

12.1 The contribution of this prototype is not a novel algorithm. It is a reframing. By insisting that the risk of leaving be scored separately from the risk of staying, and that danger be scored separately from feasibility, it makes visible a comparison that humanitarian assessment usually leaves implicit.

12.2 Its second contribution is its treatment of its own uncertainty. The weights are labelled as unvalidated. The proxies are labelled as proxies. The absent capabilities are listed rather than omitted. The satellite overlay reports honestly that it is not connected. For a tool that touches decisions about who moves and who remains, this reticence is not a weakness in the work; it is a substantial part of what the work is demonstrating.

12.3 The index does not know whether anyone should evacuate. It is built to make the question harder to answer carelessly.

---

## Attribution

This report describes a research prototype developed by Carolina Morón as masters research at the NYU Center for Global Affairs, published under Ethical Tech CoLab.

The live application is available at https://ethical-tech-colab.github.io/evacuation-inform-index-carolina/

---

## Sources

Entries are grouped by kind and given in a single style: author or publisher, title, date where one is published, and a locator. Data sources are live services and are cited by publisher and access route rather than by publication date.

**Internal and sibling projects.** CERAI (Civilian Evacuation Risk Anticipation Index) and FLARE are referred to throughout this report as design lineage. CERAI is an internal Ethical Tech CoLab project with no public release, and the EII implements an adaptation of its danger/feasibility structure rather than its engine. FLARE is a machine learning forced labour risk model developed by the Global Fund to End Modern Slavery; it is named here only as background to the evidence practices in section 7, and no methodological claim in this report rests on it — see 7.2 for a correction to an earlier draft that did. Neither is a citable external authority, and readers should treat references to them accordingly.

**Data sources**

- [INFORM Severity Index](https://www.acaps.org/en/thematics/all-topics/inform-severity-index), ACAPS with the Joint Research Centre of the European Commission, April 2026 release, 104 crises
- [ACLED](https://acleddata.com), Armed Conflict Location and Event Data Project, conflict event and fatality data
- [Open-Meteo](https://open-meteo.com), route weather and daylight
- [Microsoft HASTE](https://aka.ms/HASTE), Microsoft with Planet, satellite damage assessment, self hosted

**Legal instruments**

- International Committee of the Red Cross. [Article 49, Geneva Convention (IV) relative to the Protection of Civilian Persons in Time of War](https://ihl-databases.icrc.org/en/ihl-treaties/gciv-1949/article-49), 1949
- International Committee of the Red Cross. [Article 17, Protocol Additional (II) to the Geneva Conventions](https://ihl-databases.icrc.org/en/ihl-treaties/apii-1977/article-17), 1977
- United Nations General Assembly. *Universal Declaration of Human Rights*, Article 13, 1948
- United Nations General Assembly. *International Covenant on Civil and Political Rights*, Article 12, 1966
- International Criminal Tribunal for the former Yugoslavia. *Prosecutor v. Tadić*, Decision on the Defence Motion for Interlocutory Appeal on Jurisdiction, 1995, paragraph 70

**Composite-index precedent and method**

- OECD and Joint Research Centre. [*Handbook on Constructing Composite Indicators: Methodology and User Guide*](https://publications.jrc.ec.europa.eu/repository/handle/JRC31473), 2008
- Saaty, Thomas L. "How to Make a Decision: The Analytic Hierarchy Process." *European Journal of Operational Research*, volume 48, issue 1, 1990, pages 9–26
- Beccari, Benjamin. "A Comparative Analysis of Disaster Risk, Vulnerability and Resilience Composite Indicators." *PLoS Currents Disasters*, 2016
- Al Fozaie, Muhammad. "A Guide to Integrating Expert Opinion and Fuzzy AHP When Generating Weights for Composite Indices." *Advances in Fuzzy Systems*, 2022
- International Organization for Migration. [Risk Index for Climate Displacement](https://environmentalmigration.iom.int/CMIL-AP/RICD), two tier macro and micro precedent
- Centers for Disease Control and Prevention. [Social Vulnerability Index](https://www.atsdr.cdc.gov/placeandhealth/svi/index.html), personal vulnerability layer
- Fund for Peace. [Fragile States Index](https://fragilestatesindex.org)

---

> This document is a plain language description of a research prototype. The Evacuation Inform Index has not been validated, carries no institutional mandate, and must not be used as the sole basis for any decision affecting the movement or safety of civilians.
