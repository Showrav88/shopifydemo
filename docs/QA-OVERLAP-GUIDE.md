# QA + word-overlap check — where to change what

## Flow

```
AI write listing
    ↓
Check text overlap     ← CODE: real % math (not AI)
    ↓
Update sheet listing
    ↓
AI QA score listing    ← AI: reads overlap results + both texts
    ↓
Update sheet QA score
    ↓
QA score check 90      ← PASS only if score ≥ 90 AND overlap_fail = false
```

## Node 1: `Check text overlap` (Code)

**What it measures:**

| Metric | Method | Default fail if |
|--------|--------|-----------------|
| **Jaccard %** | Shared words ÷ all unique words (title & description separate) | Title ≥ 45% or Description ≥ 50% |
| **Phrase overlap %** | % of 4–5 word chunks in generated text found in original | ≥ 25% |
| **Max consecutive words** | Longest identical word run | ≥ 7 words in a row |

**Edit thresholds** — open node → Code → top of file:

```javascript
const THRESHOLDS = {
  maxConsecutiveWords: 7,
  phraseOverlapPercent: 25,
  jaccardTitle: 0.45,
  jaccardDescription: 0.50,
};
```

**Outputs on sheet:** `Overlap %`, `QA Issues` (if fail)

**`overlap_fail: true`** → automatic FAIL_COPY — Shopify product NOT created.

---

## Node 2: `AI QA score listing` (OpenAI)

**Two messages:**

1. **System** — rubric, copyright rules, JSON shape
2. **User** — overlap stats from Code node + original vs generated text

**Edit here for:**
- Score bands (95–100, 90–94, etc.)
- “If overlap_fail → score below 70”
- Extra rules (UK spelling, banned words, brand names)

**Key rule in prompt:** If `overlap_fail` is true, AI **must** score below 70.

---

## Node 3: `QA score check 90` (IF)

**Both must be true to create Shopify product:**

1. `quality_score >= 90`
2. `overlap_fail === false`

**Change pass threshold:** edit first condition (e.g. 85 instead of 90).

---

## QA Status values on sheet

| Value | Meaning |
|-------|---------|
| **PASS** | Score ≥ 90 and overlap OK |
| **FAIL** | Score < 90, overlap OK |
| **FAIL_COPY** | Code overlap check failed (too similar to competitor) |

---

## Sheet columns added

| Column | Written by |
|--------|------------|
| **Overlap %** | Check text overlap (max of phrase/Jaccard metrics) |
| **QA Issues** | Overlap summary + AI issues list |

---

## Tuning tips

| Stricter (less copy risk) | Looser (fewer false fails) |
|---------------------------|----------------------------|
| `phraseOverlapPercent: 15` | `phraseOverlapPercent: 35` |
| `maxConsecutiveWords: 5` | `maxConsecutiveWords: 10` |
| `jaccardDescription: 0.40` | `jaccardDescription: 0.60` |
| QA threshold 92 | QA threshold 85 |
