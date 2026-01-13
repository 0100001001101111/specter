# Methodology Checklist for Anomaly Investigations

**Lessons from SPECTER Phase 4: When a Reddit commenter correctly invalidated our headline finding.**

---

## The Mistake We Made

We claimed an 8.32x elevation in UFO reports before earthquakes. A community critic pointed out that using M≥1.0 earthquakes in the Bay Area creates near-continuous "active" windows, making the correlation meaningless. When we reran with M≥4.0 (rare events), the signal **inverted to 0.62x**.

The precursor hypothesis was an artifact of methodology, not evidence.

This checklist exists so we don't make these mistakes again.

---

## 1. Null Model Requirements

### The Rule
Never compare against uniform random. Real-world phenomena have structure.

### Checklist
- [ ] **Population density**: Do reports cluster where people live? That's not a finding.
- [ ] **Observation opportunity**: Clear skies, daylight hours, outdoor activity levels
- [ ] **Temporal patterns**: Day-of-week effects, seasonal variation, holiday spikes
- [ ] **Media cycles**: Did a news story cause a reporting wave?
- [ ] **Platform changes**: Did the reporting website change, go viral, or get mentioned?

### Test
If your "anomaly" disappears when you control for population, it was never real.

### SPECTER Example
We compared report rates to uniform baseline. Should have compared to population-weighted expectation. Portland's higher per-capita rate (61.2 vs 21.3) revealed our population assumptions were wrong.

---

## 2. Event Frequency Check

### The Rule
Before claiming correlation with events, calculate how often those events happen. If they happen constantly, any window will show overlap.

### Checklist
- [ ] **Baseline frequency**: How many events per year? Per month? Per day?
- [ ] **Window coverage**: What percentage of time is "active" under your definition?
- [ ] **Rare event threshold**: Use events rare enough to create discrete windows

### Formula
```
Window coverage = (events/year) × (window_days) / 365

If coverage > 50%, your "correlation" is likely spurious.
```

### SPECTER Example
**M≥1.0 earthquakes**: ~10,000/year in Bay Area
- 72-hour windows → coverage = 10,000 × 3 / 365 = 8,219% (overlapping constantly)
- Any report falls in an "active" window by chance

**M≥4.0 earthquakes**: ~30/year in Bay Area
- 72-hour windows → coverage = 30 × 3 / 365 = 25%
- Discrete windows, meaningful test
- Result: Signal inverted (0.62x)

**Lesson**: The 8.32x claim failed because we used events that happen hourly, not rarely.

---

## 3. Confound Identification

### The Rule
List all possible confounds BEFORE analysis. Test each one explicitly. If you can't rule it out, acknowledge it.

### Checklist
- [ ] **Geographic confounds**: Population, roads, airports, military bases, observatories
- [ ] **Temporal confounds**: Seasons, holidays, events, media coverage
- [ ] **Observer confounds**: Reporting platform changes, viral posts, demographic shifts
- [ ] **Physical confounds**: Weather, visibility, light pollution, air traffic
- [ ] **Selection confounds**: How was this region/period chosen? Was it cherry-picked?

### Pre-Analysis Documentation
Before running analysis, write:
```
Confounds we're controlling for: [list]
Confounds we can't control for: [list]
Confounds we're ignoring and why: [list]
```

### SPECTER Example
We identified magnetic anomaly as a factor but didn't adequately control for:
- Fine-grained population density at hotspot level
- Reporting platform changes over time
- Selection bias in choosing SF Bay as the focus

---

## 4. Multiple Testing Correction

### The Rule
Every comparison is a chance to find a false positive. Count them and correct.

### Checklist
- [ ] **Count all tests**: Regions, time windows, thresholds, categories, subgroups
- [ ] **Apply correction**: Bonferroni (α/n) or FDR (Benjamini-Hochberg)
- [ ] **Report survival rate**: "X of Y tests survived correction"
- [ ] **Highlight critical tests**: Which test would falsify your hypothesis?

### Bonferroni Quick Reference
```
Tests    Corrected α (for α=0.05)
5        0.010
10       0.005
20       0.0025
50       0.001
```

### SPECTER Example
We ran ~10 tests. With Bonferroni correction (α=0.005):

| Test | Raw p | Survives? |
|------|-------|-----------|
| Magnetic correlation | <0.0001 | ✓ YES |
| Shape-geology link | 0.002 | ✓ YES |
| M≥4.0 precursor | 0.0076 | ✗ NO |
| Loma Prieta spike | 0.01 | ✗ NO |

The **critical test** (M≥4.0 precursor) failed correction. We should have reported this prominently.

---

## 5. Pre-registration

### The Rule
Lock your analysis parameters before looking at the data. Post-hoc discoveries need independent validation.

### Checklist
- [ ] **Pre-specify**: Window size, magnitude threshold, geographic bounds, bin edges
- [ ] **Document timing**: What was decided before vs. after seeing data?
- [ ] **Exploratory vs. confirmatory**: Label analyses as one or the other
- [ ] **Validation requirement**: Any post-hoc finding needs replication on new data

### Documentation Template
```
PRE-REGISTERED (before analysis):
- Time window: 72 hours
- Magnitude threshold: M≥3.0
- Geographic bounds: [coordinates]

POST-HOC (discovered during analysis):
- Shape classification scheme
- Physical effects keywords
- These require independent validation
```

### SPECTER Example
We didn't pre-register. The 72-hour window, M≥1.0 threshold, and scoring weights were all chosen after initial data exploration. When an independent critic suggested M≥4.0, the finding collapsed.

---

## 6. Holdout Validation

### The Rule
Split your data temporally. Train on the past, validate on the future. If the pattern doesn't replicate, it's probably not real.

### Checklist
- [ ] **Temporal split**: Use pre-2015 for discovery, post-2015 for validation
- [ ] **No peeking**: Don't look at holdout data during model development
- [ ] **Same analysis**: Run identical analysis on holdout set
- [ ] **Report honestly**: If holdout fails, the finding is suspect

### Split Recommendations
```
Data range: 1990-2024
Training set: 1990-2015 (discovery)
Holdout set: 2016-2024 (validation)

Never adjust parameters based on holdout performance.
```

### SPECTER Example
We didn't perform holdout validation. When attempted post-hoc, insufficient M≥4.0 events in the holdout period prevented conclusive testing. This should have been planned from the start.

---

## 7. Skepticism Symmetry

### The Rule
Apply the same level of skepticism to all findings. Don't selectively explain away inconvenient results while accepting convenient ones.

### Checklist
- [ ] **Same standards**: If you dismiss one region as bias, apply that scrutiny everywhere
- [ ] **Explain both directions**: Why does SF show correlation AND why doesn't Portland?
- [ ] **Devil's advocate**: For each finding, write the skeptical counter-argument
- [ ] **Null hypothesis framing**: What would falsify your hypothesis?

### Red Flags
- "Portland's lower correlation is observer bias, but SF's higher correlation is real"
- "This outlier supports the hypothesis, that outlier is noise"
- "The effect is real where we see it, absent where we don't"

### SPECTER Example
We explained Portland's weaker signal as "different geology" while accepting SF's stronger signal as evidence. A symmetric analysis would ask: "What if SF's signal is also noise amplified by methodology?"

When we applied symmetric skepticism (M≥4.0 test), SF's signal collapsed too.

---

## 8. Effect Survival Ladder

### The Rule
A claim only survives if it passes progressively stricter tests. Be explicit about which rung each claim reached.

### The Ladder
```
Level 0: Raw correlation observed
Level 1: Survives population/observation control
Level 2: Survives multiple testing correction
Level 3: Survives holdout validation
Level 4: Replicates in independent dataset
Level 5: Mechanism identified and tested
```

### Reporting Template
```
CLAIM: [statement]
Level reached: [0-5]
Failed at: [which level and why]
Confidence: [none/low/moderate/high]
```

### SPECTER Example

**Claim: 8.32x precursor elevation**
- Level 0: ✓ Raw correlation observed
- Level 1: ✗ FAILED - Event frequency check (M≥4.0 → 0.62x)
- Confidence: **NONE** - Claim retracted

**Claim: Magnetic-UFO correlation (ρ=-0.497)**
- Level 0: ✓ Raw correlation observed
- Level 1: ✓ Survives population control (SF vs Portland comparison)
- Level 2: ✓ Survives Bonferroni correction (p<0.0001)
- Level 3: ? Holdout validation inconclusive
- Level 4: ? No independent replication yet
- Confidence: **MODERATE** - Correlation real, causation unproven

---

## Quick Reference Card

Before publishing any anomaly claim, verify:

```
□ Null model accounts for population, observation, temporal patterns
□ Event frequency creates discrete windows (<50% coverage)
□ All confounds listed and tested (or acknowledged)
□ Multiple testing correction applied and reported
□ Parameters pre-registered (or post-hoc findings labeled)
□ Holdout validation performed
□ Same skepticism applied to all regions/findings
□ Survival ladder level explicitly stated
```

**If any box is unchecked, the claim is preliminary at best.**

---

## The Honest Scientist's Oath

When a critic identifies a methodological flaw:

1. **Don't defend** - Test their critique
2. **Run the analysis they suggest** - Even if you expect it to fail
3. **Report the result honestly** - Even if it kills your hypothesis
4. **Thank them** - They saved you from publishing garbage
5. **Update your methods** - So it doesn't happen again

The Reddit commenter who suggested M≥4.0 was right. The 8.32x claim was wrong. Science worked.

---

*Created after SPECTER Phase 4 methodological review, January 2026*
