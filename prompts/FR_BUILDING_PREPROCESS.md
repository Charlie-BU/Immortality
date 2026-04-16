Process input material into a structured, storable result by performing high-fidelity content cleaning, metadata judgment, and completeness self-check according to the specified rules.

## Hard Requirements

1. All valuable content must be 100% completely retained; do not omit any important information. Do not use summary compression that causes information loss.
2. Only allow deletion of repeated expressions, repeated sentences, and verbal nonsense. Do not delete any real information including facts, time, character relationships, original words, preferences, events, method steps, etc.
3. Do not fabricate or supplement any information that does not appear in the input.
4. If an image URL is inaccessible or unparseable, ignore it completely; do not guess the image content.
5. Output must be a strict JSON object; do not output Markdown or any additional explanatory text.
6. Output language must be exactly consistent with the input content, including `cleaned_content` and all field values.
7. All judgments must be made in combination with the character role `figure_role` and the original input content `raw_content` (and images if any); do not deviate from the role context.

## Input Definition

Input contains three fields:

- `figure_role`: Character role, selected from the following enumeration: `SELF` | `FAMILY` | `FRIEND` | `MENTOR` | `COLLEAGUE` | `PARTNER` | `PUBLIC_FIGURE` | `STRANGER`
- `raw_content`: Original text content
- `raw_images`: Original image URLs (if any)

## Task Objectives

A. High-fidelity content cleaning: generate `cleaned_content` that is completely faithful, with duplicate and noise removed
B. Metadata judgment: determine `original_source_type`, `confidence`, `included_dimensions`, `approx_date` according to rules
C. Completeness self-check: output `coverage_check` to confirm no key information is omitted

## Judgment Rules

### 1. Content Cleaning Rules

- `cleaned_content` must completely retain all valuable information; do not cause information loss through compression or rewriting.
- Only remove redundant repeated expressions; do not remove real facts.

### 2. Confidence Rule

`confidence` can only be one of the following values:

- `verbatim`: Explicit original words / direct quotation
- `artifact`: Objective material or verifiable statement
- `impression`: Subjective impression, speculation, or evaluation

### 3. Included Dimensions Rule

`included_dimensions` can select multiple values, limited to the following enumeration:

- `personality`: values, stable tendencies, preferences, motivations, boundaries
- `interaction_style`: speaking style, response style, conflict/feedback behavior
- `procedural_info`: methods, steps, tools, execution patterns, decision criteria
- `memory`: life events, stories, time markers, milestones, shared experiences
- `other`: content that cannot be reliably mapped to any category above

#### High-Recall Classification Workflow (must follow)

1. Split `cleaned_content` into semantic segments first (each segment = one coherent idea/event/method block).
2. For each segment, evaluate **all four** dimensions independently (`personality`, `interaction_style`, `procedural_info`, `memory`), then take the union.
3. Apply role-aware recall checks (below) to avoid under-tagging in role-specific scenarios.
4. Merge all matched dimensions across segments into final `included_dimensions`.
5. Add `other` only when no segment matches any of the four dimensions with confidence.

Never do single-pass "pick one best label" classification. Multi-label is mandatory whenever supported by text.

#### Dimension Decision (expanded)

##### A. `personality`

Tag when text contains relatively stable orientation or recurring tendency:

- value priorities (e.g., fairness over speed, safety first)
- long-term likes/dislikes and stable motivation/avoidance patterns
- explicit principles, non-negotiable boundaries, taboo lines
- emotional pattern as trait-level tendency (not one-off mood)
- social preference pattern (distance/frequency/depth, role in groups)
- self-description vs others' description gap

Do **not** tag `personality` for one-off actions unless text explicitly frames them as stable pattern/value.

##### B. `interaction_style`

Tag when text describes **how the person communicates/reacts to others**:

- default communication style (length, structure, channel, response rhythm)
- wording/tone style (directness, politeness, humor, intensity shifts)
- question/pushback/challenge/refusal/negotiation/feedback behavior
- conflict handling under ambiguity, missing docs, cross-team friction
- communication gotchas: explicit "won't do this way" interaction boundaries
- in close relationships: emotional interaction patterns and relationship dynamics

If a segment is about expression/response behavior under condition X, tag `interaction_style`.

##### C. `procedural_info`

Tag when text contains actionable "how to do" pattern tied to this figure:

- explicit steps, workflow, checklist, sequence, playbook
- tools/stack/environment/platform/terminology used by this figure
- acceptance standards, delivery criteria, quality bar, rollback/monitoring habits
- decision logic ("because X, choose Y"), escalation boundaries
- repeated correction patterns and anti-pattern gotchas ("don't do this")

Do **not** tag `procedural_info` for generic industry common sense unless tied to this figure's actual practice.

##### D. `memory`

Tag when text contains narrative/time-context experiences:

- specific events/incidents/turning points (life or work)
- explicit or implicit time markers (year/period/before-after/phase)
- repeatedly told stories, shared memories, internal jokes/rituals
- emotional map around memories (fondly mentioned topics, avoided topics)
- era/environment imprint on worldview

If a segment is story/event-centered with temporal context, tag `memory` even if brief.

##### E. `other`

Use only when none of the four dimensions can be assigned confidently:

- pure metadata/noise (IDs, links, boilerplate with no semantic signal)
- vague statements with no clear personality/interaction/procedure/memory meaning
- content outside scope that cannot be reliably mapped

If any one of the four dimensions matches, `other` must be excluded.

#### Role-Aware Recall Rules (coverage first, then precision)

Role affects **expected hotspots**, not hard exclusion.  
If textual evidence exists, always tag; do not suppress a matched dimension because of role.

- `SELF`:
    - High likelihood of all four dimensions.
    - Pay extra attention to life decisions, personal systems, creative/workflow habits, self-reflection over time.

- `COLLEAGUE`:
    - Prioritize recall for `procedural_info` + `interaction_style`.
    - `personality` should be work-related value tendencies and stress/decision style.
    - `memory` usually low-priority, but must be tagged when work events/milestones/incidents are present.

- `MENTOR`:
    - Prioritize `interaction_style` (teaching/feedback style) + `personality` (teaching principles) + `procedural_info` (method/path).
    - Tag `memory` when mentor stories/career turning points are explicitly mentioned.

- `FAMILY` / `FRIEND` / `PARTNER`:
    - Prioritize `interaction_style` + `memory` + `personality`.
    - `procedural_info` is optional but must be tagged if there is explicit skill transfer or repeatable methods.
    - For `PARTNER`, relationship rhythm/conflict-repair signals strongly indicate `interaction_style`; shared timeline events strongly indicate `memory`.

- `PUBLIC_FIGURE`:
    - Only classify based on public-material content itself.
    - Often includes `interaction_style` (public Q&A/replies), `personality` (publicly stated principles), `procedural_info` (published methodology), `memory` (publicly shared life events).
    - Do not infer private traits beyond textual evidence.

- `STRANGER`:
    - No role prior; rely fully on text signals.
    - Keep high recall by checking all four dimensions before falling back to `other`.

#### Co-occurrence and Boundary Rules

- event + method/process => `memory` + `procedural_info`
- value/principle + communication behavior => `personality` + `interaction_style`
- event + reflection/lesson => `memory` + `personality`
- communication behavior + tool/decision checklist => `interaction_style` + `procedural_info`
- relationship episode + response pattern => `memory` + `interaction_style`

Classify by **information type in text**, not by source type label or guess of the person.

#### Anti-Miss Checklist (must pass before output)

- Did you evaluate all four dimensions for each segment (instead of one-label shortcut)?
- Did you include role-expected hotspots for the given `figure_role`?
- Did you preserve multi-label co-occurrence where present?
- Did you avoid adding `other` when any real dimension is already matched?

### 4. Approximate Date Rule

- If there is explicit time or inductive time in the text, fill in the time as a string
- Otherwise output `null`

### 5. Original Source Type Rule

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

#### Notes

- You must make only one unique matching classification, do not output multiple labels
- Always follow the priority: first check if it is user narration, if yes output `NARRATIVE_FROM_USER` immediately, do not proceed to further classification
- As long as it is user perspective narration, it is strictly forbidden to misclassify as any LONG_FORM / CHAT / ARTIFACT type
- If the content is not original output from the figure personally, always fall back to `NARRATIVE_FROM_USER`

## Output Format

Output a strictly valid JSON object that conforms to the following schema, no extra content allowed:
{
"cleaned_content": "string",
"metadata": {
"original_source_type": "string",
"confidence": "verbatim|artifact|impression",
"included_dimensions": ["personality|interaction_style|procedural_info|memory|other"],
"approx_date": "string|null"
},
"coverage_check": {
"removed_as_redundant": ["list of content removed as redundant repetition/nonsense; empty array if no content removed"],
"completeness_pass": true
}
}

## Notes

- All field values must strictly follow the enumeration requirements; do not use custom values that are not in the given enumeration
- Do not add any explanatory text outside the JSON object
- Ensure all valuable information is retained; only true redundant content is removed
- Output language is exactly consistent with the input language
