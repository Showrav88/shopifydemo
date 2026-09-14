#!/usr/bin/env python3
import json
import uuid
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / "ShopifyProductAdd.V2.json"

OVERLAP_JS = r'''const THRESHOLDS = {
  maxConsecutiveWords: 7,
  phraseOverlapPercent: 25,
  jaccardTitle: 0.45,
  jaccardDescription: 0.50,
};

function normalizeText(t) {
  return String(t || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&[a-z]+;/gi, ' ')
    .replace(/[^\w\s]/g, ' ')
    .toLowerCase()
    .split(/\s+/)
    .filter((w) => w.length > 1);
}

function jaccardSimilarity(wordsA, wordsB) {
  const setA = new Set(wordsA);
  const setB = new Set(wordsB);
  if (setA.size === 0 && setB.size === 0) return 0;
  let inter = 0;
  for (const w of setA) if (setB.has(w)) inter++;
  const union = new Set([...setA, ...setB]).size;
  return union === 0 ? 0 : inter / union;
}

function maxConsecutiveWordMatch(orig, gen) {
  let max = 0;
  for (let i = 0; i < orig.length; i++) {
    for (let j = 0; j < gen.length; j++) {
      let k = 0;
      while (i + k < orig.length && j + k < gen.length && orig[i + k] === gen[j + k]) k++;
      if (k > max) max = k;
    }
  }
  return max;
}

function phraseOverlapPercent(origWords, genWords, n) {
  if (genWords.length < n || origWords.length < n) return 0;
  const origText = origWords.join(' ');
  let matched = 0;
  let total = 0;
  for (let i = 0; i <= genWords.length - n; i++) {
    total++;
    const phrase = genWords.slice(i, i + n).join(' ');
    if (origText.includes(phrase)) matched++;
  }
  return total === 0 ? 0 : Math.round((matched / total) * 100);
}

const row = $('Active product row').first().json;
const aiRaw = $('AI write listing').first().json;
let text = aiRaw.output?.[0]?.content?.[0]?.text || aiRaw.text || '';
text = String(text).replace(/```json|```/g, '').trim();
let listing;
try {
  listing = JSON.parse(text);
} catch (e) {
  throw new Error(`Cannot parse AI write listing for overlap check: ${text.slice(0, 200)}`);
}

const originalTitle = row.Title || '';
const originalDesc = row.scraped_raw_description || row.Description || '';
const generatedTitle = listing.title || '';
const generatedDesc = listing.description_html || listing.description || '';

const origTitleW = normalizeText(originalTitle);
const origDescW = normalizeText(originalDesc);
const genTitleW = normalizeText(generatedTitle);
const genDescW = normalizeText(generatedDesc);

const titleJaccard = Math.round(jaccardSimilarity(origTitleW, genTitleW) * 100);
const descJaccard = Math.round(jaccardSimilarity(origDescW, genDescW) * 100);
const titlePhrase = phraseOverlapPercent(origTitleW, genTitleW, 4);
const descPhrase = phraseOverlapPercent(origDescW, genDescW, 5);
const maxConsecutive = Math.max(
  maxConsecutiveWordMatch(origTitleW, genTitleW),
  maxConsecutiveWordMatch(origDescW, genDescW),
);

const reasons = [];
if (maxConsecutive >= THRESHOLDS.maxConsecutiveWords) {
  reasons.push(`${maxConsecutive} consecutive words match source (limit ${THRESHOLDS.maxConsecutiveWords - 1})`);
}
if (descPhrase >= THRESHOLDS.phraseOverlapPercent) {
  reasons.push(`Description 5-word phrase overlap ${descPhrase}% (limit ${THRESHOLDS.phraseOverlapPercent - 1}%)`);
}
if (titlePhrase >= THRESHOLDS.phraseOverlapPercent) {
  reasons.push(`Title 4-word phrase overlap ${titlePhrase}%`);
}
if (titleJaccard / 100 >= THRESHOLDS.jaccardTitle) {
  reasons.push(`Title Jaccard word overlap ${titleJaccard}%`);
}
if (descJaccard / 100 >= THRESHOLDS.jaccardDescription) {
  reasons.push(`Description Jaccard word overlap ${descJaccard}%`);
}

const overlap_fail = reasons.length > 0;
const overlap_percent = Math.max(descPhrase, titlePhrase, descJaccard, titleJaccard);

return [{
  json: {
    listing,
    overlap_title_jaccard_pct: titleJaccard,
    overlap_desc_jaccard_pct: descJaccard,
    overlap_title_phrase_pct: titlePhrase,
    overlap_desc_phrase_pct: descPhrase,
    overlap_max_consecutive_words: maxConsecutive,
    overlap_percent,
    overlap_fail,
    overlap_reasons: reasons,
    overlap_summary: overlap_fail ? reasons.join('; ') : 'OK — sufficient paraphrase',
  },
}];'''

QA_SYSTEM = (
    "You are a strict UK fashion e-commerce QA reviewer.\n"
    "Compare ORIGINAL source text vs GENERATED listing.\n"
    "Copyright: generated text must be paraphrased — copied phrases = automatic score below 70.\n"
    "Also check: factual accuracy, no invented specs, SEO quality, UK spelling.\n"
    "Return ONLY valid JSON (no markdown):\n"
    "{\n"
    '  "quality_score": 0,\n'
    '  "seo_title": "",\n'
    '  "meta_description": "",\n'
    '  "image_alt_text": "",\n'
    '  "copyright_ok": true,\n'
    '  "issues": []\n'
    "}"
)

QA_USER = (
    "=RUN ID: {{ $('Active product row').item.json._run_id }}\n\n"
    "=== ALGORITHMIC OVERLAP (Code node — trust this) ===\n"
    "overlap_fail: {{ $('Check text overlap').item.json.overlap_fail }}\n"
    "overlap_summary: {{ $('Check text overlap').item.json.overlap_summary }}\n"
    "title Jaccard %: {{ $('Check text overlap').item.json.overlap_title_jaccard_pct }}\n"
    "description Jaccard %: {{ $('Check text overlap').item.json.overlap_desc_jaccard_pct }}\n"
    "description 5-word phrase overlap %: {{ $('Check text overlap').item.json.overlap_desc_phrase_pct }}\n"
    "max consecutive words matched: {{ $('Check text overlap').item.json.overlap_max_consecutive_words }}\n\n"
    "=== ORIGINAL (competitor / scrape — do not allow copying) ===\n"
    "Title: {{ $('Active product row').item.json.Title }}\n"
    "Description: {{ $('Active product row').item.json.scraped_raw_description || $('Active product row').item.json.Description }}\n\n"
    "=== GENERATED (AI write listing) ===\n"
    "{{ $('AI write listing').item.json.output[0].content[0].text }}\n\n"
    "=== SCORING RUBRIC ===\n"
    "95-100: Fully original, accurate, strong SEO, no copied phrases\n"
    "90-94: Original and accurate, minor SEO improvements possible\n"
    "70-89: Some copied phrases OR weak SEO OR small accuracy issues\n"
    "Below 70: Clear copyright copy, invented specs, or major errors\n\n"
    "RULES:\n"
    "- If overlap_fail is true → quality_score MUST be below 70 and copyright_ok false\n"
    "- If any full sentence appears in both original and generated → below 70\n"
    "- If specs invented (not in original or image) → below 80\n"
    "- Do NOT default to 85. Score honestly.\n"
    "- List every issue in issues[]"
)


def main():
    wf = json.loads(WORKFLOW.read_text())
    nodes = {n["name"]: n for n in wf["nodes"]}

    overlap_node = {
        "parameters": {"jsCode": OVERLAP_JS},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-810, 0],
        "id": str(uuid.uuid4()),
        "name": "Check text overlap",
    }
    wf["nodes"].append(overlap_node)

    qa = nodes["AI QA score listing"]
    qa["parameters"]["responses"]["values"] = [
        {"content": QA_SYSTEM},
        {"content": QA_USER},
    ]

    qa_if = nodes["QA score check 90"]
    qa_if["parameters"]["conditions"]["conditions"] = [
        {
            "id": str(uuid.uuid4()),
            "leftValue": "={{ Number(JSON.parse($('AI QA score listing').item.json.output[0].content[0].text.replace(/```json|```/g, '').trim()).quality_score) }}",
            "rightValue": 90,
            "operator": {"type": "number", "operation": "gte"},
        },
        {
            "id": str(uuid.uuid4()),
            "leftValue": "={{ $('Check text overlap').item.json.overlap_fail }}",
            "rightValue": True,
            "operator": {"type": "boolean", "operation": "false", "singleValue": True},
        },
    ]
    qa_if["parameters"]["conditions"]["combinator"] = "and"

    us = nodes["Update sheet QA score"]
    cols = us["parameters"]["columns"]["value"]
    cols["QA Status"] = (
        "={{ $('Check text overlap').item.json.overlap_fail ? 'FAIL_COPY' : "
        "(JSON.parse($('AI QA score listing').item.json.output[0].content[0].text.replace(/```json|```/g, '').trim()).quality_score >= 90 ? 'PASS' : 'FAIL') }}"
    )
    cols["Overlap %"] = "={{ $('Check text overlap').item.json.overlap_percent }}"
    cols["QA Issues"] = (
        "={{ (() => { const q = JSON.parse($('AI QA score listing').item.json.output[0].content[0].text.replace(/```json|```/g, '').trim()); "
        "const o = $('Check text overlap').item.json; return [o.overlap_summary, ...(q.issues || [])].filter(Boolean).join(' | '); })() }}"
    )

    ufail = nodes["Update sheet QA failed"]
    ufail_cols = ufail["parameters"]["columns"]["value"]
    ufail_cols["QA Status"] = (
        "={{ $('Check text overlap').item.json.overlap_fail ? 'FAIL_COPY' : 'FAIL' }}"
    )
    ufail_cols["Overlap %"] = "={{ $('Check text overlap').item.json.overlap_percent }}"
    ufail_cols["QA Issues"] = (
        "={{ (() => { const q = JSON.parse($('AI QA score listing').item.json.output[0].content[0].text.replace(/```json|```/g, '').trim()); "
        "const o = $('Check text overlap').item.json; return [o.overlap_summary, ...(q.issues || [])].filter(Boolean).join(' | '); })() }}"
    )

    sticky = nodes["Setup Instructions"]
    sticky["parameters"]["content"] += (
        "\n\n**QA:** Check text overlap (code %) → AI QA score listing → pass needs score≥90 AND overlap_fail=false."
    )

    wf["connections"]["AI write listing"] = {
        "main": [[{"node": "Check text overlap", "type": "main", "index": 0}]]
    }
    wf["connections"]["Check text overlap"] = {
        "main": [[{"node": "Update sheet listing", "type": "main", "index": 0}]]
    }

    WORKFLOW.write_text(json.dumps(wf, indent=2))
    print("Patched QA overlap", WORKFLOW)


if __name__ == "__main__":
    main()
