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

Classify the original source type of given content following strict unique matching rules, based on figure_role and the content perspective of cleaned_content. The core principle is: first determine "who wrote/said this content", then determine "content form".

#### Steps

1. First, perform the highest priority source perspective judgment:
    - If the content is the user describing the person/relationship/event (even if detailed and long), always classify as `NARRATIVE_FROM_USER` and end the judgment. This applies to:
        - Content that begins with words like "I think / he is / she usually / we used to / he once..."
        - Content that is paraphrase, summary, evaluation, memory, not original output
        - Content that includes quotes of the other person's words embedded in the user's narration, not original records
        - Any content that is not the original text written by the figure personally, even if it has a complete structure similar to an article
    - Only proceed to the next step of detailed classification if the content is original output directly produced by the figure personally. This requires meeting at least one of the following:
        - Explicitly first-person original text (not user paraphrase)
        - Explicitly chat screenshot/chat text (not paraphrase)
        - Explicitly original carrier content such as documents, articles, code
2. If the content is confirmed to be original output from the figure, classify into the unique matching type based on figure_role and content form:
    - **When figure_role = COLLEAGUE / MENTOR (work relationship):**
        - `WORK_RELATION_LONG_FORM`: Complete long text written by the figure personally, e.g. design documents, technical solutions, review reports, oncall records; features strong structure (complete titles/paragraphs/logic)
        - `WORK_RELATION_EDIT_TRACE`: The figure's modification traces on others' content, e.g. code review comments, document annotations, inline comments; features fragmented, comments on specific content
        - `WORK_RELATION_GUIDANCE`: Guidance content from the figure to you/others, e.g. mentoring records, instructive statements (not casual chat); features clear intention to "teach/guide/advise"
        - `WORK_RELATION_ARTIFACT`: The output artifact of the figure, e.g. code, design drafts, configuration files; features primarily non-natural language or strong tool attributes
    - **When figure_role = FAMILY / FRIEND / PARTNER (close relationship):**
        - `CLOSE_RELATION_LONG_FORM`: Long text written by the figure, e.g. letters, long messages, articles; features continuous expression, complete emotional or opinion expansion
        - `CLOSE_RELATION_PRIVATE_CHAT`: Original private chat records, e.g. WeChat/SMS conversations; features conversational structure (you say one sentence, I say one sentence)
        - `CLOSE_RELATION_SOCIAL_EXPRESSION`: Public expression from the figure, e.g. WeChat Moments, social media posts; features intended for public/friend circles
        - `CLOSE_RELATION_ARTIFACT`: Creative works from the figure, e.g. photos, works, handicrafts (text description of the content is also acceptable)
    - **When figure_role = SELF (yourself):**
        - `SELF_LONG_FORM`: Long text written by yourself, e.g. blog/diary/notes
        - `SELF_CHAT_MESSAGE`: Chat content sent by yourself
        - `SELF_SOCIAL_EXPRESSION`: Your own public expression on social media
        - `SELF_ARTIFACT`: Your own creative works, e.g. code/design
    - **When figure_role = PUBLIC_FIGURE (public figure):**
        - `PUBLIC_FIGURE_ARTICLE_BLOG`: Articles/blogs published by the figure personally
        - `PUBLIC_FIGURE_INTERVIEW_SPEECH_TRANSCRIPT`: Text transcripts of interviews or speeches
        - `PUBLIC_FIGURE_SOCIAL_EXPRESSION`: Social media statements
        - `PUBLIC_FIGURE_NEWS_REPORT`: Media reports (third-party, not user narration)
        - `PUBLIC_FIGURE_ARTIFACT`: Creative works, e.g. works/code

## Output Schema (strict JSON only)

{
"cleaned_content": "string",
"metadata": {
"original_source_type": "NARRATIVE_FROM_USER|WORK_RELATION_LONG_FORM|WORK_RELATION_EDIT_TRACE|WORK_RELATION_GUIDANCE|WORK_RELATION_ARTIFACT|CLOSE_RELATION_LONG_FORM|CLOSE_RELATION_PRIVATE_CHAT|CLOSE_RELATION_SOCIAL_EXPRESSION|CLOSE_RELATION_ARTIFACT|SELF_LONG_FORM|SELF_CHAT_MESSAGE|SELF_SOCIAL_EXPRESSION|SELF_ARTIFACT|PUBLIC_FIGURE_ARTICLE_BLOG|PUBLIC_FIGURE_INTERVIEW_SPEECH_TRANSCRIPT|PUBLIC_FIGURE_SOCIAL_EXPRESSION|PUBLIC_FIGURE_NEWS_REPORT|PUBLIC_FIGURE_ARTIFACT",
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
