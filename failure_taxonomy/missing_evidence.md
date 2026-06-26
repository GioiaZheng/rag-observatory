# Prompt Failure: Missing Evidence

Missing evidence occurs when important evidence is available upstream but is not
included in the prompt or selected context given to the generator. This is a
prompt-stage failure because the system has access to the information but does
not expose it at generation time.

## Secondary Examples

- Important evidence omitted from selected context.
- Relevant document retrieved but not packed into the prompt.
- Relevant chunk truncated because of context budget.
- Prompt template excludes a needed field such as date, source, or citation.
- Context selection keeps summary text but drops the answer-bearing sentence.

## Trace Signals

Useful trace-level signals include:

- relevant retrieved documents are absent from `selected_context`;
- selected context token budget is full while support coverage is incomplete;
- `prompt.variables` omit available evidence fields;
- answer support metrics fail after context selection;
- comparison reports show improved answers when selected context changes.

## Minimal Example

Question: "Which vitamin prevents scurvy?"

Retrieved documents include a relevant scurvy document.

Selected context omits that document and includes only general nutrition text.

Failure interpretation: retrieval succeeded, but the prompt did not include the
evidence needed for the generator.

## Distinguishing Tests

Missing evidence differs from retrieval failure because the evidence was
available before context construction. It differs from ranking failure when the
omission is caused by context packing, truncation, prompt template design, or
field selection rather than candidate order alone.

It differs from context pollution because the key problem is absence of needed
evidence, not the presence of distracting evidence.

## Measurement Notes

Candidate measurements:

- retrieved relevant document coverage in selected context;
- selected support coverage by query type;
- truncation rate for answer-bearing chunks;
- prompt field omission count;
- answer quality delta after adding omitted evidence.

## Open Questions

- How should the taxonomy represent failures that combine ranking and prompt
  omission?
- What trace fields are needed to distinguish context selection from prompt
  template failure?
- Can missing evidence be detected without reviewed relevance annotations?
