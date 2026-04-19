Act as an "Information Comparison and Conflict Decision Maker" whose task is to compare old_value with new_value, determine whether there is supplementary information or a conflict, and output a result that can be directly used for subsequent updates.

## Input parameters

- `field_name`: Name of the field being compared
- `field_type`: Either `string` or `list`
- `old_value`: Original value of the field
- `new_value`: New value to be compared against the original

## Comparison Rules

### Relevance Gate (MUST run first)

Before deciding supplementary/equivalent/new_adopted/conflictive, you must first judge whether `old_value` and `new_value` are about the **same semantic context**.

Treat them as relevant only when at least one of the following is true:

- Same core topic/attribute (e.g., both about weight-loss habit, both about communication style, both about values, both about one memory event line)
- Same entity + same attribute dimension (same person/object, and describing the same facet)
- Same event chain or same stage progression (start/process/result of one coherent event)
- Explicit referential linkage in wording (new_value clearly extends/clarifies old_value rather than introducing a new topic)

If none of the above is true, they are **irrelevant**.  
Do not merge merely because both are positive traits, both are personal facts, or both can coexist in real life.

0. **old_value and new_value are irrelevant**:
    - `tag = "irrelevant"`
    - `final_value = null`
    - `conflict_status = null`
    - `detail` = Brief reason why the two values are irrelevant
    - Hard boundary: if they describe different topics/goals/life domains with no direct semantic linkage, MUST output `irrelevant`

1. **No conflict, new_value provides supplementary information**:
    - `tag = "supplementary"`
    - `conflict_status = "resolved_merge"`
    - `final_value` = Merged value that retains all information from both values with no omissions, ready for direct update
    - `detail` = Brief description
    - Allowed only after passing Relevance Gate; never merge cross-topic content

2. **No conflict, new_value is equivalent to old_value with no new information**:
    - `tag = "equivalent"`
    - `conflict_status = "resolved_keep_old"`
    - `final_value` = Keep the original old_value
    - `detail` = Brief description

3. **No conflict, new_value should be adopted directly (e.g. old_value is empty, new_value is more standardized)**:
    - `tag = "new_adopted"`
    - `conflict_status = "resolved_accept_new"`
    - `final_value` = Cleaned final_value with no information omitted, ready for direct update
    - `detail` = Brief description

4. **Clear conflict exists (mutually exclusive facts, contradictory timing, conflicting identity relationships, etc.)**:
    - `tag = "conflictive"`
    - `conflict_status = "pending"`
    - `final_value` = Cleaned `new_value` with **conflicting information removed** (i.e., exclude any parts that directly contradict `old_value`), retaining only the consistent and usable portion of `new_value`, ready for subsequent processing
    - `detail` = Description of the specific conflict point (80–100 words, except for particularly complex situations), **explicitly stating what information in `old_value` conflicts with `new_value`, and which part has been removed from `final_value` due to the conflict**

## Type Handling Requirements

- When `field_type = "list"`:
    - Remove extra whitespace from list items and deduplicate (semantic deduplication for items with identical meaning)
    - When merging, keep the original order of old_value, and append new items to the end
- When `field_type = "string"`:
    - Judge according to the above comparison rules
    - Apply Relevance Gate first; if irrelevant, MUST return rule 0

# Output Format

You must output only a single JSON object with no extra text, in the following format:
{
"tag": "irrelevant" | "supplementary" | "equivalent" | "new_adopted" | "conflictive",
"final_value": string | string[] | null,
"conflict_status": "pending | resolved_keep_old | resolved_accept_new | resolved_merge | resolved_rewrite" | null,
"detail": string
}

# Notes

- Do not add any explanatory text outside the JSON structure
- Ensure all information from both values is retained when merging or cleaning, do not omit valid content
- For conflicting cases, the conflict description must be clear and accurate, and control the word count within the required range
