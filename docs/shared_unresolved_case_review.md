# Shared Unresolved Case Review

A qualitative diagnostic review of the 15 missed-failure cases that the R=5 repetition study
left unexplained. The question is deliberately not "which evaluator should we route to" but:

> When multiple evaluators agree on the wrong answer, is the problem actually the evaluator --
> or did the assurance system fail earlier by losing, omitting, or failing to formalize the
> evidence needed to judge correctly?

No new model inference was purchased. No planner code was changed. No files were downloaded
from upstream: everything here comes from the already-local HuggingFace snapshot
(`b6d17e646009d6cb63d5dd7be78807b680693f61`) and committed repo data.

Artifacts:

- `data/shared_unresolved_case_review.csv` -- one row per case, the structured findings
- `data/REAL_arb_case_evidence/` -- the Phase 0 evidence bundle per case
- `scripts/arb_case_evidence.py` -- evidence extraction
- `scripts/arb_case_review_table.py` -- the structured artifact (analyst judgments joined to archive data)
- `scripts/arb_shared_unresolved_membership.py` -- the membership criterion check

---

## 0. Membership: what these 15 cases actually are

This had to be established before anything else, and the answer changed a claim committed
earlier the same day.

**Criterion actually implemented** (and therefore the definition of this review set): the
reference label is `fail`, the functional primary said success, the historical March 2025
`aer` judgment said success, and all five current AER repetitions said success (k=0/5).
That is **three evidence sources, two distinct evaluators**.

**Criterion that predeclaration section A1.6 defines for the term "shared unresolved
errors":** wrong under the primary, unresolved by **all eight** cached alternates, and
repetition-consistent. Scoring all eight alternates gives **5 cases, not 15**.

So the answer to "does 'shared unresolved' mean all available judges failed?" is **no**.

| case (task / agent) | alternates wrong | alternates that were correct |
| --- | --- | --- |
| assistantbench.improved.validation.14 / gpt-4o | 7/8 | nnetnav |
| visualwebarena.resized.569 / Qwen | **2/8** | gpt-4o-mini-noscreen, gpt-4o-mini-noscreen-noaxtree, gpt-4o-noscreen, llama-3.3-70b-noscreen, nnetnav, qwen-2.5-vl-noscreen |
| visualwebarena.resized.598 / Qwen | 8/8 | -- |
| visualwebarena.resized.730 / Qwen | 7/8 | gpt-4o-mini-noscreen-noaxtree |
| visualwebarena.resized.332 / claude-3.7 | 8/8 | -- |
| visualwebarena.resized.598 / claude-3.7 | 8/8 | -- |
| visualwebarena.resized.601 / claude-3.7 | 7/8 | gpt-4o-mini-noscreen-noaxtree |
| webarena.24 / Qwen | 7/8 | llama-3.3-70b-noscreen |
| webarena.426 / Qwen | 7/8 | llama-3.3-70b-noscreen |
| webarena.491 / Qwen | 8/8 | -- |
| webarena.599 / Qwen | 8/8 | -- |
| webarena.723 / claude-3.7 | **2/8** | claude-3.7-sonnet-noscreen, gpt-4o-mini-noscreen, gpt-4o-mini-noscreen-noaxtree, gpt-4o-noscreen, llama-3.3-70b-noscreen, qwen-2.5-vl-noscreen |
| webarena.726 / gpt-4o | 5/8 | gpt-4o-mini-noscreen, nnetnav, qwen-2.5-vl-noscreen |
| webarena.426 / llama-3.3-70b | 6/8 | gpt-4o-mini-noscreen, llama-3.3-70b-noscreen |
| workarena.servicenow.infeasible-navigate-and-order-loaner-laptop-l2 / Qwen | 7/8 | claude-3.7-sonnet-noscreen |

Ten of the fifteen had at least one cached alternate return the correct verdict. Two had six
of eight correct. The narrower 15-case set is preserved as the review set, per instruction,
but the A1.6 label has been withdrawn from it and the correction applied in place in
`docs/repetition_study_findings.md`.

### The nine judges are not nine mechanisms

Three structural facts that bound every "multiple evaluators agreed" statement in this study:

1. **`functional` is not an LLM.** It has no `chat_messages` at all; its verdict is
   `trajectory_info.summary_info.cum_reward > 0.5`. It is the benchmark's own programmatic
   verifier. When this report says "the primary and the judges agreed", one of those is a
   scripted checker, not an opinion.
2. **The eight alternates split into two representation tiers, not eight.** Five receive the
   accessibility tree (`claude-3.7-sonnet-noscreen`, `gpt-4o-mini-noscreen`,
   `gpt-4o-noscreen`, `llama-3.3-70b-noscreen`, `qwen-2.5-vl-noscreen`) at ~26k characters;
   three receive only a natural-language caption of the final screenshot (`aer`,
   `gpt-4o-mini-noscreen-noaxtree`, `nnetnav`) at 3-11k characters. Within a tier the prompts
   are near-identical. Agreement within a tier is weak evidence of anything.
3. **No judge receives a screenshot or an input image.** All nine have
   `use_screenshot: False` and no image part in their messages.

Fact 2 is a gift: it means the archive already contains a controlled
representation-richness comparison, and it cost nothing to run.

---

## 1. Phase 0 -- what evidence exists

Availability was uniform across all 15 cases.

| evidence item | available | source |
| --- | --- | --- |
| case id, benchmark, agent | yes (15/15) | repo pair YAML |
| task instruction (goal) | yes (15/15) | judgment JSON `goal` |
| reference label | yes (15/15) | `annotations.csv` |
| expert structured metadata (side effect, optimality, looping) | yes (15/15) | `annotations.csv` |
| **expert free-text rationale** | **no (0/15)** | does not exist in this dataset |
| trajectory / action history | yes (15/15), agent-reported | AER `chat_messages` |
| final-state caption | yes (15/15) | tail of AER user message |
| **raw screenshots / DOM** | **no (0/15)** | not in this snapshot |
| accessibility tree | yes, but only as delivered to 5 of 8 alternates | their `chat_messages` |
| stored AER `chat_messages` | yes (15/15) | judgment JSON |
| historical AER verdict + raw response | yes (15/15) | judgment JSON |
| five current AER verdicts + responses | yes (15/15, 5 each) | `REAL_arb_repetition_raw.jsonl` |
| functional primary verdict | yes (15/15) | `summary_info.cum_reward` |
| other cached judge verdicts + explanations | yes (8/8 per case) | judgment JSONs |
| upstream programmatic verifier outcome | yes -- it **is** the functional verdict | `cum_reward` |
| task-success signal distinct from the expert label | yes, and it disagrees | `cum_reward` vs `trajectory_success` |

Two gaps matter, and both limit what can be concluded:

**No expert rationale exists.** `annotations.csv` has four columns and none is free text. Every
statement in this review about *why* an expert called a trajectory unsuccessful is a
reconstruction from the trajectory plus the three metadata flags. Where that reconstruction is
weak, the case is marked `PLAUSIBLE BUT AMBIGUOUS` rather than resolved.

**No raw trajectory exists outside judge inputs.** This makes the Phase 2 (A) vs (B) split --
"absent from the world" vs "present in the world but lost in representation" -- untestable in
general. It is testable only where one tier of judge received something another did not. That
is why the axtree/caption split carries so much of the weight below.

**The programmatic verifier and the expert disagree on all 15 by construction**, since the
review set is defined by the primary being wrong. Worth stating plainly: `cum_reward` is 1.0
in 13 of 15 and 0.85 in one. These are cases where the benchmark's own checker certified
success and a human said otherwise. AgentRewardBench exists because that happens; the review
set is a sample of exactly that phenomenon.

---

## 2. Phase 1 -- is the reference sound?

Checked before blaming any judge. This is a diagnostic audit: the benchmark label remains the
reference for every quantitative result in this repo, unchanged.

| classification | n | cases |
| --- | --- | --- |
| CLEAR | 12 | the five image-grounded vwa cases, webarena.426 x2, .723, .726, .491, assistantbench.14, workarena loaner |
| PLAUSIBLE BUT AMBIGUOUS | 2 | visualwebarena.resized.332, webarena.599 |
| NOT VERIFIABLE FROM AVAILABLE MATERIAL | 0 | -- |
| POSSIBLY INCORRECT | 1 | webarena.24 |

**webarena.24 is the one that should not be counted as an evaluator failure.** Two experts
annotated this trajectory. The primary annotator (A) marked it Unsuccessful. The secondary
annotator (H) marked it **Successful and "4. Completely Optimal"**. The repo takes the first
annotator per `(benchmark, model, task)` and discards the rest
(`scripts/arb_extract.py:128-134`), which is a defensible and predeclared rule -- but it means
this "shared error" is one side of a human coin-flip that all nine automated systems resolved
the other way. The single alternate that scored "correct" here
(`llama-3.3-70b-noscreen`) argued from optimality, not from the success criterion, and its
text agrees with the agent that no reviewer mentioned unfair pricing.

The other two-annotator case in the set, `webarena.726`, has both experts marking Complete
Failure. It is correspondingly firm.

The two AMBIGUOUS cases turn on genuine definitional slack: whether reaching a post page
counts as "navigating to the comments section" (332), and whether subscribing to a forum
satisfies "open the thread ... and subscribe" (599).

---

## 3. Phase 2 -- observability audit

The question is whether the evidence needed to reach the correct verdict was in the judge's
input at all.

| category | n | meaning |
| --- | --- | --- |
| (A) absent from the benchmark's own observation channel | 5 | the goal's premise is an image no judge receives |
| **(B) present upstream, lost in the representation given to AER** | **0** | no case established |
| (C) present in AER's actual input | 10 | continue to evaluator diagnosis |

The empty (B) row is the surprise of this review and it was arrived at by trying to fill it.
The obvious candidates were the two `webarena.426` cases, which axtree-tier judges caught and
every caption-tier judge missed. That looks like representation loss until the caption is
actually read. AER's input for that case contains the final URL
`.../search?query=Shanksville%2C%20Pennsylvania#map=16/...` and a caption whose left panel is
headed **"Search Results"** with the place rendered as "a clickable link in blue". The
discriminating evidence was there. The axtree judges were not better informed; they reasoned
differently on the same facts.

The same test was applied to the other candidates and came back the same way. For
`webarena.24`, the caption contains the full text of both customer reviews -- so AER could see
that neither mentions price fairness, which is precisely why its verdict is defensible and why
this case is a reference dispute rather than a judge error. For `webarena.491`, `.599` and
`visualwebarena.resized.332`, the decisive detail is in the caption (retained comment text, an
activated upvote arrow, a comment *count* rather than rendered comments).

**So richer representation is not the fix for any of the 15.** This matters because "give the
judge the accessibility tree" is the intervention the cross-evaluator numbers most invite: in
7 of 15 at least one axtree-tier judge was correct. That correlation is real and it is not
causal in the way it looks.

**(A) -- the unseeable premise.** Five cases have goals of the form "this exact item", "the
product in this picture", "what the person is sitting on", each accompanied by an
`Input image 1/1 below (local path: ..., url: ...)` line. Every judge is text-only with
`use_screenshot: False`. The image URL is printed in the prompt and cannot be fetched. These
goals are not hard for the judge; they are **undecidable** for it.

The most telling instance is `visualwebarena.resized.598`, which appears twice with different
agents and is 8/8 wrong both times. AER's own words:

> "The agent correctly identified the brand (Sony) from the image"

AER never saw the image. It inferred the premise from the agent's search query and then used
that inference as evidence that the agent's behaviour was correct. **The judge accepted the
subject's claim about an unobservable input as evidence about that input.** That is circular,
and it is not a reasoning lapse that a stronger model fixes -- with the image withheld, the
only alternatives are to guess or to abstain.

Corpus-wide structural fact: **90 of the 1,106 cases** in this pair file have goals
referencing an input image no judge can see, all in visualwebarena (90 of 276 in that slice;
0 in webarena, workarena, assistantbench). This is a statement about how the evaluation was
configured, not a claim about how many production errors it causes.

**(C) -- present and missed.** Ten cases, including all five that meet the strict A1.6
criterion. The sharpest is `webarena.491`. The axtree handed to five judges contains:

```
[1026] textbox 'Comment' value='the order is ready to be shipped soon!', visible
[1030] checkbox 'Notify Customer by Email', checked='true'
[1036] button 'Submit Comment', clickable, visible, focused
[1038] list '', visible
```

A comment box still holding its text, after six no-op steps, with an empty adjacent history
list. In Magento the field clears on successful submission. Five axtree judges had this and
all five said success. AER, on the caption, went further and cited the retained text as
*positive* evidence:

> "The final state of the webpage confirms that the comment is present, the checkbox is
> checked, and no errors are reported. Therefore, the notification should have been sent."

This is a reasoning failure on available evidence, not a representation failure. One honest
caveat: the Comments History tab is `expanded=False` in the axtree, so non-submission is
strongly indicated but not conclusively observable. There is a real observability limit
underneath a real reasoning failure.

**The headline result of this phase:** for 10 of 15 the evidence needed to reach the correct
verdict was already in AER's own input, and for the other 5 it is in nobody's input. There is
no middle category here. The assurance system did fail earlier than the evaluator in a third
of these cases -- but at the *specification* and *reference* layers, not by losing evidence in
transit.

---

## 4. Phase 3 -- evaluator diagnosis

Categories used only where the evidence supports them. Note that two categories do the most
work, and neither is "the model reasoned poorly".

**Specification / rubric failure (4 cases, plus contributing in 2 more).** AER's system prompt
contains this clause:

> "The bot's response must contain the information the user wants, **or explicitly state that
> the information is not available.**"

There is no truth condition on the claim, and the clause is scoped to information-seeking
tasks. Seven of the 15 trajectories end in `report_infeasible` or an abstention message, and in
four of them AER explicitly cites the abstention as its ground for success:

- `webarena.723` -- "Like all submissions created by FTorrez81 in subreddit iphone13". AER:
  *"it explicitly stated that the information was not available"*. This is a
  **content-modification** task. Abstention cannot be success. AER misclassified the task type
  under its own three-type taxonomy and then applied the clause faithfully.
- `webarena.726` -- "DisLike all submissions created by jacyanthis in subreddit earthporn".
  Identical structure.
- `webarena.24` and `visualwebarena.resized.569` -- information-seeking, where the clause
  applies, but the agent's "not available" claim was false.

This is the single most actionable finding in the review. The rubric is wrong, AER followed
it correctly, and the two cases where six of eight alternates were correct
(`webarena.723`, `visualwebarena.resized.569`) are both in this group -- the alternates
"outperformed" AER largely because their prompts lack this clause.

Two further specification gaps:

- **No side-effect criterion in AER's rubric.** AER asks only whether the execution succeeded.
  The other seven judges emit `<side>`, `<optimal>` and `<loop>` tags -- and the pipeline
  parses only `<success>`. In `webarena.599` the caption AER received reports an activated
  (orange) upvote arrow on a post the user never asked to vote on. The evidence was in the
  input; the rubric had no slot for it.
- **Withheld infeasibility.** `workarena.servicenow.infeasible-navigate-and-order-loaner-laptop-l2`
  belongs to a task family whose whole point is that the requested configuration
  (`'Exactly build': 'teach, pattern, office'`) does not exist and the correct agent behaviour
  is to refuse. The judge is shown the steps as though achievable and is never told the task is
  infeasible. It cannot know that placing the order *is* the failure. The agent submitted a
  real order for 5 laptops and then called `report_infeasible(reason="The task of ordering a
  loaner laptop has been successfully completed.")`.

**Evidence-use failure (5 cases).** Grouped below as "affordance mistaken for accomplishment"
(4) plus one sufficiency failure (`assistantbench.14`, where the agent answered a
three-carrier comparison question from a single third-party aggregator, and AER did not apply
the sufficiency warning its own prompt contains).

**Shared semantic blind spot: not claimed anywhere.** The preconditions for that label are not
met. Where all eight alternates failed, either the rubric was shared, the representation was
shared, or the premise was unobservable to all of them. Five of the eight alternates are
`-noscreen` axtree variants and two are gpt-4o-mini variants differing only by axtree; their
agreement is not eight independent observations.

**A caution about the "correct" alternates.** Several right answers came from wrong reasons.
`gpt-4o-mini-noscreen-noaxtree` called `visualwebarena.resized.730` unsuccessful because "the
last action was 'None'" -- a parsing artifact present in every trajectory in the corpus. On
`visualwebarena.resized.601` it argued the agent "did not check the price" when the price was
$42.30 inside the required $30-$50 band. Counting these as evidence that an alternate judge
is better would be a mistake.

---

## 5. Phase 4 -- deterministic verifier opportunity

Nothing implemented. This records the shape of the solution only.

| classification | n | cases |
| --- | --- | --- |
| DETERMINISTICALLY VERIFIABLE | 6 | vwa.332, webarena.426 x2, .723, .726, workarena loaner |
| PARTIALLY DETERMINISTIC | 4 | assistantbench.14, vwa.601, webarena.491, webarena.599 |
| GENUINELY SEMANTIC | 4 | vwa.569, vwa.598 x2, vwa.730 |
| UNKNOWN | 1 | webarena.24 (contested reference) |

The minimal invariants, in ascending order of cost:

> **Correction (2026-09-29), in place.** Invariants 1 and 3 below are stated in terms of
> information the benchmark holds rather than information a deployed evaluator could have.
> The deployability audit in `docs/production_signal_audit.md` finds:
> (a) **invariant 3 is oracle leakage and is withdrawn** -- `infeasible` exists only as a
> substring of the benchmark task id, `annotations.csv` has no such column, and for that task
> family the flag very nearly *is* the reference verdict. The production-valid replacement
> needs no flag: the agent called `report_infeasible` while asserting the task was
> "successfully completed", a self-contradiction visible from the agent's own tool call. It
> also reaches the 57 `report_infeasible` sessions *outside* the infeasible family that a
> flag-based rule could never see.
> (b) **invariant 1 is narrowed.** No task-type label exists in the benchmark; task type must
> be *inferred* from the goal text, imperfectly. And "no state-changing action occurred" is
> not a sound failure test -- a modification goal can be legitimately satisfied with no action
> when the desired state already holds (`visualwebarena.133`). The surviving rule keys on the
> agent's explicit negative self-report instead.
> Invariants 2, 4, 5 and 6 are unaffected in their diagnostic content; invariant 2 is
> relabelled application-specific there.

1. **Abstention on a modification goal is not success.** If the goal is content-modifying and
   the trajectory contains no state-changing action, the verdict is failure regardless of what
   the agent said. Fixes `webarena.723` and `.726` outright. ~~Needs a task-type label the
   benchmark already has.~~ **[SUPERSEDED — see correction (b) above: no such label exists;
   task type must be inferred from goal text, imperfectly.]**
2. **Terminal route check.** For "navigate to / find the page of X", the final URL must match
   the detail route, not the search route. Fixes both `webarena.426` cases.
3. **Infeasible-task contract.** For `infeasible-*` tasks: no submission event occurred AND the
   terminal `report_infeasible` reason actually asserts infeasibility. Fixes the workarena
   case, and the flag already exists in the benchmark.
4. **Post-submit state contract.** After a submit action the bound input must be cleared or a
   confirmation row must appear. Covers `webarena.491` up to the collapsed-tab limit.
5. **Rendered-content check.** "Navigate to the comments section" requires a rendered comment,
   not a link showing a comment count. Covers `vwa.332`.
6. **No unrequested state delta.** No vote-state or subscription change on an entity the goal
   did not name. Covers `webarena.599`.

Invariants 1-3 require no new observation channel, no model, and information the benchmark
already holds. Together they address 5 of 15.

The four GENUINELY SEMANTIC cases are all image-grounded. They are not semantic because the
judgment is subtle; they are semantic because the evidence is missing. Supply the image and
at least the price-constraint half of `vwa.601` becomes checkable.

---

## 6. Phase 5 -- cross-case clusters

Formed only after all 15 were read individually. Cases carry a primary mechanism and,
where real, a secondary; they were not merged to make the taxonomy tidier. Two clusters have
a single member and are left that way.

| cluster | n | cases |
| --- | --- | --- |
| **A. Unseeable premise** -- goal defined by an image no judge receives | 5 | vwa.569, vwa.598 (Qwen), vwa.598 (claude), vwa.730, vwa.601 |
| **B. Abstention accepted as success** -- rubric clause with no truth condition, applied across task types | 4 | vwa.569*, webarena.24*, webarena.723, webarena.726 |
| **C. Affordance mistaken for accomplishment** -- a UI element that enables the goal read as the goal being met | 4 | webarena.491, webarena.426 (Qwen), webarena.426 (llama), vwa.332 |
| **D. Unrequested state change with no rubric slot** | 1 primary (+3 secondary) | webarena.599 primary; also present in .491, vwa.730, workarena loaner |
| **E. Withheld specification** -- benchmark knows the task is infeasible, judge is not told | 1 | workarena loaner laptop |
| **F. Sufficiency failure** -- answer produced without the enumerated evidence the goal requires | 1 | assistantbench.14 |

\* `vwa.569` is primary-A / secondary-B; `webarena.24` is primary-Reference / secondary-B.

Cluster C is the one that looks most like a classic "the judge reasoned badly" failure, and it
is internally consistent: a populated comment box read as a sent message, a search-results
page read as a place page, a "89 comments" link read as being in the comments section. In
every instance the judge treated *the affordance for doing X* as *evidence X was done*. It is
also the cluster most cheaply fixed by a deterministic check.

Two duplications are informative rather than redundant. `webarena.426` appears under two
different agents with the same two-action trajectory and produces the identical AER error --
that is a reproducible rubric gap, not a sampling accident. `visualwebarena.resized.598`
appears under two agents and is 8/8 wrong both times -- which is what a representation gap
looks like, since it does not vary with the agent.

---

## 7. Phase 6 -- earliest failed layer

Assigned on the principle that later-layer sophistication cannot repair earlier-layer
information loss.

| layer | n | cases |
| --- | --- | --- |
| 1 Reference | 1 | webarena.24 |
| 2 Observation | 0 | -- |
| 3 Representation | 5 | the five image-grounded vwa cases |
| 4 Specification | 4 | webarena.599, .723, .726, workarena loaner |
| 5 Evaluation / reasoning | 5 | assistantbench.14, vwa.332, webarena.426 x2, webarena.491 |
| 6 Decision | 0 | -- |

**Only 5 of 15 fail first at the evaluator's reasoning.** Ten fail earlier -- at a contested
reference, at a representation that omits the goal's premise, or at a specification that never
told the judge what correct behaviour was.

Layer 2 is empty for a defensible reason and one honest caveat. The reason: in the image cases
the benchmark *did* observe the image -- it is the task input -- so the loss is in what was
passed to the judge, which is Layer 3. The caveat: the raw trajectory is not in the snapshot,
so a Layer 2 gap that never reached any judge's input would be invisible to this review. Layer
2 being empty is a limit of the evidence as much as a finding.

A note on Layer 6: `assistantbench.14` has `cum_reward = 0.852` with `cum_raw_reward = 0` --
a continuous answer-similarity score binarised by the planner's `> 0.5` rule. Its membership in
the "primary missed a failure" stratum is partly an artifact of that threshold. The judge error
is real and independent, so the case stays at Layer 5, but the decision rule deserves scrutiny
separately.

---

## 8. Phase 7 -- does the project's framing survive?

**Q1. Are these actually evaluator failures?** Mostly not. One (webarena.24) is a reference
dispute; five are representation gaps where the judge could not observe the goal's premise;
four are specification gaps where the rubric either licensed the wrong answer or withheld the
definition of correctness. Five are genuine evaluator reasoning failures. "Shared unresolved
error" was the right name for the cell only in the sense that it committed to nothing -- and
even the narrower A1.6 name turned out to be an overclaim.

**Q2. Would alternate judges ever have been the right intervention?** Rarely, and less than
the cross-evaluator numbers suggest. In 2 of 15 a well-chosen alternate was correct 6 times out
of 8 -- but in both, the alternates were right because their prompts lack AER's abstention
clause, not because they are better reasoners. That makes it a **prompt fix wearing an
evaluator-diversity costume**: buying a second judge would work, and buying a one-line rubric
edit would work better and cheaper. In the 8 cases where no alternate was correct, no amount of
judge diversity from this pool helps, because the pool shares representations and rubrics.

**Q3. Would repetition ever have helped?** No, and this review explains why the R=5 study found
nothing. Every one of these 15 is a deterministic consequence of an input the judge did not
have or a rule it was given. Repeating a call cannot conjure an image that was never passed,
and cannot contradict a rubric clause that says abstention is success. Repetition was measuring
sampling noise in a pipeline whose errors are not noise.

**Q4. Does deterministic-first become more important?** Yes, and more than expected. Six of 15
are fully deterministically checkable and four more are partially so, and the three cheapest
invariants need no new observation channel and no model -- only a task-type label and an
infeasibility flag the benchmark already stores. The current architecture spends money on a
second LLM opinion to adjudicate questions like "did the final URL change".

> **Correction (2026-09-29), in place.** "only a task-type label and an infeasibility flag the
> benchmark already stores" is wrong twice over: the benchmark stores neither as a field, and
> the infeasibility flag would be oracle leakage if it did. See the correction above at the
> invariant list and `docs/production_signal_audit.md` section 3. The claim that
> deterministic-first matters more than expected is unaffected -- but the checks must be built
> from the agent's own tool calls and the goal text, which is more work than "pass along a
> label", and none of them is yet validated on held-out data.

**Q5. Is "shared unresolved error" one phenomenon?** No. It is at least six, spanning four
distinct pipeline layers, with different and non-overlapping fixes. Treating the cell as a
single quantity -- which is what the 2x2 did, and what Outcome E would have tested -- was
measuring the size of a heterogeneous bucket.

**Q6. What is the smallest production architecture the evidence supports?** See section 10.

---

## 9. Phase 8 -- the false-alarm side

The 15-case analysis does point there, on one specific ground, so a bounded look was taken and
no further.

The `workarena.servicenow.infeasible-*` family dominates the false-alarm stratum's
two-evaluator unresolved cell. The specification gap identified in cluster E -- the judge is
never told that an `infeasible-*` task is meant to be impossible -- is therefore not confined
to these 15 and plausibly acts in both error directions: judges cannot tell a correct refusal
from a failure to try, nor an improper completion from a success.

That is the entire Phase 8 claim. No false-alarm case was individually diagnosed, and the
strict A1.6 count in that stratum (6 of 50) is reported in the findings document without
further interpretation.

---

## 10. The smallest production assurance architecture this evidence supports

Ordered by cost, cheapest first. This is a description of what the 15 cases imply, not a plan
that has been agreed.

> **Correction (2026-09-29), in place.** This section is superseded by
> `docs/production_signal_audit.md` sections 8 and 11, and by the Commit 3 architecture gate.
> Two defects: item 1 is **partly oracle leakage** (the feasibility half), and the whole list
> was presented as "the architecture this evidence supports" when the evidence supported the
> *diagnosis* only -- no component here has been validated on data outside the 15 cases it was
> derived from. Item 3's side-effect half is now **dead**: the cached `<side>` tags answer a
> different question ("unnecessary actions that *could lead to* side effects") and agree with
> the optimality tag up to 91%, against a 6.5% expert base rate. Items 2, 4 and 5 survive in
> narrowed form.

1. ~~**A task-type and feasibility label on every case, carried into the judge's input.** Not a
   model. A field. It makes invariants 1 and 3 possible and would have changed 3 of 15.~~
   **[SUPERSEDED — see the correction above. Neither is a field: task type is class C,
   inferred from goal text; the feasibility half is class D oracle leakage and its use as a
   judge input is withdrawn. "Not a model, a field" was the load-bearing error — it is a
   model, and that is where the cost reappears.]**
2. **A small set of deterministic post-conditions keyed to task type** -- terminal route,
   post-submit state, no-unrequested-state-delta. Addresses 6 of 15 fully and 4 partially, at
   no per-case inference cost.
3. **A rubric that cannot license abstention as success, and that has a slot for side
   effects.** One prompt edit; 4 of 15 plus contributing factors in 2 more. Note that the
   signal already exists and is discarded: seven of the eight judges emit a `<side>` tag that
   the pipeline does not parse.
4. **An abstain-and-escalate path for goals whose premise the judge cannot observe.** The
   correct output for the five image-grounded cases is not a verdict; it is
   `NOT DECISION-SUFFICIENT`, which is the output discipline this repo already applies to a
   missing `r*`. A judge that cannot see the image should say so rather than guess. This is the
   one place where the planner's existing philosophy maps directly onto a measured defect.
5. **Human review, scoped to two specific things** -- not as a general fallback. (a) Visual
   identity and similarity judgments, 5 cases, which no text-only judge can do and which
   supplying the image only partly fixes. (b) Reference adjudication where annotators disagree,
   1 case, which is not an evaluator-qualification question at all. This is the concrete form
   of "some evaluator qualification questions are irreducibly human rather than a stronger
   model purchase": the irreducible part is small, identifiable in advance from the task
   schema, and different in kind from the rest.
6. **A stronger LLM judge.** Last, and justified by 5 cases at most -- the cluster C reasoning
   failures and the sufficiency failure -- several of which a deterministic check handles more
   cheaply anyway.

---

## 11. What this review may not be used to claim

These 15 cases were selected *because* multiple evaluators failed on them. They are explicitly
enriched and nonrepresentative. Nothing here supports:

- any statement of the form "X% of production errors are caused by ...";
- any population prevalence for any cluster, layer, or mechanism;
- "15/15 are structural blind spots" or any variant -- 5 of 15 are evaluator reasoning
  failures on evidence the evaluator had;
- any inference from cluster size to importance. Cluster A is the largest partly because
  visualwebarena contributes 90 image-grounded goals to this corpus.

The corpus-wide counts that do appear (90 of 1,106 image-grounded goals; 5 and 6 strict-A1.6
cases in the two strata) are structural facts about how the evaluation is configured, not
error rates.

The standing A1.6 confound also still applies: the eight alternates were run once each on a
March 2025 endpoint and the R=5 study ran one judge five times on a September 2026 endpoint.
The axtree/caption comparison in section 3 is a comparison across judges that differ in
representation *and* model *and* date. It is suggestive, not a controlled experiment.

---

## 12. Retractions and corrections to earlier documents

**C1. "Shared unresolved errors" applied to a two-evaluator criterion.** Recorded in full in
`docs/repetition_study_findings.md`, with in-place narrowing in sections 10 and 13 and a note
in `scripts/arb_repetition_analysis.py`. The term now applies only to the 5-case subset. No
count or estimand changed; Outcome E does not fire under either criterion.

**C2. Narrowed: "characterize the 15 ... whether their shared feature is a prompt defect, a
label ambiguity, or a task type that the AER evaluator structurally cannot judge."**
(`docs/repetition_study_findings.md` section 15.) The question presupposed a single shared
feature. There is none. All three of the named candidates occur, in different cases, together
with three more. The disjunction was right and the singular was wrong.

**C3. Weakened: the cross-evaluator diversity framing.** Phase 2 measured phi between judge
pairs and treated low correlation as evidence of mechanism diversity. This review shows the
pool contains two representation tiers and a shared rubric lineage, and that in the two cases
where alternates most clearly outperformed AER, the cause was a prompt clause the alternates
happen to lack. Cross-evaluator disagreement in this corpus is at least partly a measurement
of rubric text, not of independent judgment. This reinforces rather than contradicts the
existing memoed lesson that measured phi may be tracking threshold alignment rather than
mechanism diversity.

No quantitative result in any earlier document is altered by this review.

---

## 13. Highest-value next action

**Add the task-type and infeasibility labels to the judge's input and implement invariants 1-3
as a deterministic pre-check, then re-score the 1,106-case corpus offline.**

> **Correction (2026-09-29), in place.** The first half of this recommendation is withdrawn:
> the infeasibility label is oracle leakage and the task-type label does not exist as a field.
> See `docs/production_signal_audit.md` section 3 and 11. The second half -- build
> deterministic pre-checks and re-score the corpus offline -- survives and has been carried
> out as a frozen rule set in `scripts/arb_production_signals.py`, but it must be scored on a
> held-out split that excludes these 15 cases and their same-task siblings, which this
> document was not in a position to specify. **This document may not be cited as evidence
> that any pre-check works.** It is discovery data.

It requires no new inference spend, no new evaluator, and no new observation channel; it uses
fields the benchmark already stores; it is testable against the existing archive; and it is
the only intervention in this review that is cheap enough to be worth doing before the
question of a better judge is reopened.

The second-most-valuable action is the negative one: **do not buy a stronger LLM judge on the
strength of this cell.** At most 5 of 15 cases support it, and 3 of those 5 are more cheaply
addressed by a deterministic check.
