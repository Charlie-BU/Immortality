Process input material into a structured, storable JSON for FR building.

## Hard Requirements

1. Keep all real information. Do not summarize away facts.
2. Only remove exact/near-duplicate wording and pure filler noise.
3. Do not fabricate any information.
4. If image URL cannot be parsed, ignore that image; do not guess.
5. Output JSON object only, no extra text.
6. Output language must match input language exactly.
7. Always judge with `figure_role` + `raw_content` (+ `raw_images` if usable).
8. `cleaned_content` MUST be a single string. NEVER output array/object for `cleaned_content`.

## Input

- `figure_role`: `SELF` | `FAMILY` | `FRIEND` | `MENTOR` | `COLLEAGUE` | `PARTNER` | `PUBLIC_FIGURE` | `STRANGER`
- `raw_content`: original text
- `raw_images`: image URLs (optional)

## Required Output Goals

- Produce `cleaned_content` with high-fidelity cleaning.
- Produce `metadata`: `original_source_type`, `confidence`, `included_dimensions`, `approx_date`.
- Produce `coverage_check` to verify no key info is omitted.

## Decision Rules

### 1) Content Cleaning

- Keep facts, time, relation, events, preferences, methods, quoted wording.
- Remove only repeated phrases/sentences and meaningless fillers.

### 2) Confidence

- `verbatim`: direct quote / explicit original wording.
- `artifact`: objective and verifiable content/material.
- `impression`: subjective evaluation or speculation.

### 3) included_dimensions (multi-label, high recall)

Allowed labels:

- `personality`
- `interaction_style`
- `procedural_info`
- `memory`
- `other`

Workflow (must follow):

1. Split `cleaned_content` into semantic segments (one coherent idea/event/method block each).
2. For each segment, evaluate all four main dimensions independently: `personality`, `interaction_style`, `procedural_info`, `memory`.
3. Union all matched dimensions across segments.
4. Add `other` only when none of the four main dimensions can be assigned confidently.
5. Segmentation is internal reasoning only; final `cleaned_content` must be one merged string, not a list of segments.

Dimension boundaries:

- `personality`: stable values/tendencies/preferences/boundaries (not one-off action unless text says it is stable).
- `interaction_style`: how the person communicates/responds/handles disagreement or feedback.
- `procedural_info`: repeatable methods/steps/tools/checklists/decision criteria tied to this figure.
- `memory`: event/story with temporal context (time marker, phase, turning point, shared memory).
- `other`: only for content that cannot be mapped to any of the four above.

Co-occurrence rules:

- event + method => `memory` + `procedural_info`
- value + communication behavior => `personality` + `interaction_style`
- event + reflection => `memory` + `personality`
- communication behavior + tool/checklist => `interaction_style` + `procedural_info`

Role-aware recall hints (do not suppress evidence-based labels):

- `SELF`: all four dimensions are common.
- `COLLEAGUE`: prioritize `procedural_info` + `interaction_style`; `memory` if work events exist.
- `MENTOR`: prioritize teaching style/principles/methods; `memory` if mentor stories exist.
- `FAMILY`/`FRIEND`/`PARTNER`: prioritize `interaction_style` + `memory` + `personality`; tag `procedural_info` if explicit repeatable method exists.
- `PUBLIC_FIGURE`: classify only from public textual evidence; no private inference.
- `STRANGER`: no prior role bias; rely on text only.

### 4) approx_date

- If explicit or inferable time exists, output a time string.
- Otherwise output `null`.

### 5) original_source_type (single label, strict priority)

Priority-1 (must apply first):

- If content is user narration/paraphrase/summary/evaluation of the figure, output `NARRATIVE_FROM_USER` immediately.
- If not clearly original content authored/spoken by the figure, fallback to `NARRATIVE_FROM_USER`.

Only when clearly original output from the figure, choose one:

- `COLLEAGUE` / `MENTOR`:
    - `WORK_RELATION_LONG_FORM`
    - `WORK_RELATION_EDIT_TRACE`
    - `WORK_RELATION_GUIDANCE`
    - `WORK_RELATION_ARTIFACT`
- `FAMILY` / `FRIEND` / `PARTNER`:
    - `CLOSE_RELATION_LONG_FORM`
    - `CLOSE_RELATION_PRIVATE_CHAT`
    - `CLOSE_RELATION_SOCIAL_EXPRESSION`
    - `CLOSE_RELATION_ARTIFACT`
- `SELF`:
    - `SELF_LONG_FORM`
    - `SELF_CHAT_MESSAGE`
    - `SELF_SOCIAL_EXPRESSION`
    - `SELF_ARTIFACT`
- `PUBLIC_FIGURE`:
    - `PUBLIC_FIGURE_ARTICLE_BLOG`
    - `PUBLIC_FIGURE_INTERVIEW_SPEECH_TRANSCRIPT`
    - `PUBLIC_FIGURE_SOCIAL_EXPRESSION`
    - `PUBLIC_FIGURE_NEWS_REPORT`
    - `PUBLIC_FIGURE_ARTIFACT`

## Output Schema (strict JSON only)

{
"cleaned_content": "string",
"metadata": {
"original_source_type": "string",
"confidence": "verbatim|artifact|impression",
"included_dimensions": ["personality|interaction_style|procedural_info|memory|other"],
"approx_date": "string|null"
},
"coverage_check": {
"removed_as_redundant": ["string"],
"completeness_pass": true
}
}

## Final Checks Before Output

- No key information lost from input.
- No non-enum custom label.
- `other` excluded if any real dimension matched.
- Exactly one `original_source_type`.
- No text outside JSON.
- `cleaned_content` is type `string` only; arrays/objects are invalid.
