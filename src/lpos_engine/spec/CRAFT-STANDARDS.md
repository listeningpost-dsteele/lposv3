# LPOS Craft Standards


---

## Source: `craft-standards/CS-001-commercial-copy.md`

---
id: CS-001
title: Commercial Copy Standard
version: 2.0.0
status: Accepted
owner: Listening Post
---

# Commercial Copy Standard

Write for the buyer, not for the model. Copy is one person telling another
person something useful. It is never the product describing its own insides.

Required inputs: audience, current belief, desired belief, problem, outcome,
proof, objections, next action, tone, and the brand voice spec
(the versioned `voice:<brand>` ArtifactSpecification). No voice spec, no copy: seed one first.

## Four tests every passage must survive

1. The swap test. If a competitor could paste the passage unchanged, it is
   filler. Rewrite until only this company could say it.
2. The out-loud test. If a person would not say the sentence to another person
   across a table, rewrite it until they would.
3. The count test. A number may appear only when the reader would decide
   differently by knowing it. Otherwise write what the number means to them.
   "32 specialists" is inventory; "your request goes to someone whose whole
   job is that kind of work" is copy. Inventory belongs in spec sheets and
   diagrams, never in prose.
4. The so-what test. Every sentence answers a question the reader actually
   has. A sentence that only describes the product fails.

## Banned structures

- Number parades: strings of counts presented as impressiveness.
- Triad parades: "faster, smarter, better" rhythm; any list of three used as
  decoration rather than information.
- The antithesis reflex: "it is not just X, it is Y."
- Mirrored sentence runs where consecutive sentences share one skeleton.
- Rhetorical-question openers and "imagine a world" framings.
- Vocabulary: seamless, effortless, unlock, supercharge, elevate, empower,
  game-changing, revolutionize, delve, robust, cutting-edge, "in today's
  world," "look no further."
- Em dashes. Exclamation marks. Title Case Headline Stacks.
- Uniform paragraph rhythm: vary sentence length; one idea per sentence.

## Required process

1. Draft for substance against the brief and the voice spec.
2. De-AI pass: the Editor specialist rewrites the draft line by line against
   the four tests and the ban list. This pass is mandatory, not optional
   polish. The pass is recorded in the run record.
3. Review: the independent reviewer quotes the three passages that sound most
   machine-written, and for each either clears it with a reason or rejects
   with a rewrite. "Sounds fine overall" is not a review.

Use concrete claims, credible mechanism, real proof, clear hierarchy, and a
specific next action. Preserve approved strengths of existing copy.

## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent
reviewer for material production work. Define verification and evidence before
completion.

---

## Source: `craft-standards/CS-002-web-product-design.md`

---
id: CS-002
title: Web and Product Design Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Web and Product Design Standard


Design for the audience, task, trust requirement, and desired action.

Before changing an existing design, capture desktop and mobile baselines and preserve
approved strengths.

Reject unrequested chat layouts, dashboards, command centers, neon AI styling, excessive
cards, fake activity feeds, generic SaaS heroes, internal workflow language, and visual
regressions.

Review the rendered product and primary user journey. Source inspection is not enough.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-003-production-artifact-review.md`

---
id: CS-003
title: Production Artifact Review Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Production Artifact Review Standard


Every material artifact requires a brief, baseline, creator, domain reviewer, outcome
reviewer, verification, comparison, approval, release evidence, and rollback path.

Do not ship when the artifact is worse than the approved version, unsupported, untested,
visually unreviewed, or missing required Principal approval.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-004-research-intelligence.md`

---
id: CS-004
title: Research and Intelligence Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Research and Intelligence Standard


Begin with the decision or uncertainty the research must improve.

Use primary sources when available. Evaluate credibility, recency, independence,
methodology, incentives, and corroboration.

Separate observation, sourced fact, inference, forecast, and speculation.

Search for disconfirming evidence. Do not summarize obvious news when weak signals,
mechanisms, or implications are required.

Outputs must include sources, findings, contradictions, uncertainty, implications, and
what evidence would change the conclusion.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-005-strategy-decisions.md`

---
id: CS-005
title: Strategy and Decision Quality Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Strategy and Decision Quality Standard


Define the decision, objective, constraints, time horizon, reversibility, and decision
owner.

Generate real alternatives, including doing nothing. Evaluate value, cost, risk,
optionality, dependencies, second-order effects, and evidence.

Do not confuse ambition with strategy, activity with progress, or a roadmap with a
decision.

Recommendations must state the chosen option, why it wins, what would invalidate it,
and the next decision point.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-006-product-management.md`

---
id: CS-006
title: Product Management Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Product Management Standard


Start with a validated user problem and desired behavior change.

Define user, job, context, pain, current workaround, outcome, evidence, constraints, and
success metric.

Reject feature lists without a problem, speculative personas, vanity metrics, roadmap
theater, and requirements that expose internal implementation.

Prioritize based on user value, strategic fit, evidence, effort, risk, and learning.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-007-software-engineering.md`

---
id: CS-007
title: Software Engineering Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Software Engineering Standard


Inspect the repository and runtime before designing.

Define behavior, interfaces, constraints, failure modes, security boundaries, tests, and
migration.

Prefer simple, maintainable, observable solutions. Preserve working behavior. Avoid
invented APIs, unnecessary abstractions, placeholder success, and broad rewrites without
evidence.

Completion requires implementation, tests, real execution, error handling,
documentation, and rollback where material.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-008-quality-testing.md`

---
id: CS-008
title: Quality Assurance and Testing Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Quality Assurance and Testing Standard


Test the real behavior, not only the implementation's claims.

Cover happy paths, edge cases, failure paths, regression risk, permissions, data
integrity, usability, and recovery.

A green unit test suite is not sufficient when the real workflow, interface, delivery,
or rendered output is unverified.

Report reproducible evidence, severity, impact, and release recommendation.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-009-security-privacy.md`

---
id: CS-009
title: Security and Privacy Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Security and Privacy Standard


Use least authority, explicit trust boundaries, secure defaults, data minimization,
defense in depth, and auditable actions.

Identify assets, actors, entry points, threats, likelihood, impact, controls, residual
risk, and response.

Never place secrets in prompts, repositories, logs, or the Principal Model. Never weaken
a security boundary to make a demo work.

Security recommendations must be practical and proportionate.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-010-finance-economics.md`

---
id: CS-010
title: Finance and Economics Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Finance and Economics Standard


State the decision, time horizon, currency, baseline, assumptions, data sources, and
uncertainty.

Separate actuals, estimates, forecasts, and scenarios.

Use ranges and sensitivity analysis when uncertainty is meaningful. Do not fabricate
precision, count unrelated revenue, hide cash timing, or present gross revenue as value.

Recommendations must show economics, downside, break-even logic, and validation.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-011-legal-compliance.md`

---
id: CS-011
title: Legal and Compliance Analysis Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Legal and Compliance Analysis Standard


State jurisdiction, facts, assumptions, issue, authority, uncertainty, and whether
licensed counsel is required.

Distinguish law, contract language, policy, risk, and business preference.

Do not present incomplete legal research as definitive advice. Cite controlling or
authoritative sources when available. Identify missing facts and material ambiguity.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-012-data-analytics.md`

---
id: CS-012
title: Data and Analytics Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Data and Analytics Standard


Define the question, decision, metric, unit, population, period, source, lineage, and
quality limitations.

Separate descriptive findings, correlation, causal claims, forecasts, and recommendations.

Check completeness, consistency, freshness, selection bias, leakage, duplication, and
denominator errors.

Use the simplest analysis that answers the question. Never make a chart or metric merely
because data exists.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-013-operations-automation.md`

---
id: CS-013
title: Operations and Automation Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Operations and Automation Standard


Define mission, trigger, inputs, outputs, owner, authority, dependencies, idempotency,
retries, timeout, recovery, observability, pause control, and success evidence.

Automate stable repeatable work, not unresolved policy.

Do not claim success from configuration alone. Run the real job, inspect delivery, verify
state, and preserve manual recovery.

Minimize notification noise and duplicate operations.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-014-executive-communication.md`

---
id: CS-014
title: Executive Communication Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Executive Communication Standard


Prioritize decisions, evidence, material risk, opportunity, preparation, and next action.

Order by leverage, not chronology. Remove routine status that changes nothing.

A briefing must let the Principal understand what matters, why it matters, and what to do
without additional research.

Use concise direct language. No em dashes. Do not narrate agent activity.

The four tests and banned structures of CS-001 apply to briefings and reports.
Numbers in a briefing carry decision weight or they are cut. The Principal
reads words a person would say.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-015-relationship-customer.md`

---
id: CS-015
title: Relationship and Customer Intelligence Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Relationship and Customer Intelligence Standard


Use verified identity and relationship context.

Separate facts from inference. Respect privacy, consent, communication history, and
channel expectations.

Do not invent familiarity, motives, authority, or relationship strength.

Recommendations must identify the relationship objective, evidence, risk, timing, and
appropriate next action.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-016-planning-execution.md`

---
id: CS-016
title: Planning and Execution Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Planning and Execution Standard


Translate approved outcomes into milestones, dependencies, owners, completion criteria,
risks, contingencies, and evidence.

Activity is not progress. A plan is not completion.

Keep plans executable and adaptive. Surface blockers early. Verify completion against
the original outcome, not task count.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-017-model-provider-evaluation.md`

---
id: CS-017
title: Model and Provider Evaluation Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Model and Provider Evaluation Standard


Evaluate providers against the required capability using representative tasks.

Measure quality, reliability, latency, cost, privacy, context handling, tool use,
failure behavior, and operational fit.

Do not route based on popularity, benchmark marketing, or one anecdotal result.

Preserve provider independence and document fallback behavior.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-018-knowledge-documentation.md`

---
id: CS-018
title: Knowledge and Documentation Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Knowledge and Documentation Standard


Create one authoritative source for each important concept.

Documentation must be accurate, current, discoverable, structured, versioned, and useful
to its intended reader.

Reject duplicated definitions, stale instructions, unexplained jargon, generated filler,
and documentation that describes plans rather than actual behavior.

Verify links, commands, examples, and ownership.

Documentation states facts plainly and may use counts freely; documentation is
inventory. The CS-001 tests apply the moment text faces a customer or reader
who is being persuaded rather than informed.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-019-innovation-experiments.md`

---
id: CS-019
title: Innovation and Experiments Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Innovation and Experiments Standard


Define a falsifiable hypothesis, smallest useful experiment, success and stop criteria,
cost, risk, duration, owner, and evidence.

Prefer cheap learning before expensive implementation.

Reject innovation theater, vague pilots, uncontrolled scope, and experiments that cannot
change a decision.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.


---

## Source: `craft-standards/CS-020-platform-infrastructure.md`

---
id: CS-020
title: Platform and Infrastructure Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

# Platform and Infrastructure Standard


Define service boundaries, reliability targets, capacity, dependencies, observability,
security, recovery, ownership, and cost.

Prefer boring reliable infrastructure unless a new approach has a material verified
advantage.

Do not infer hosting from DNS, confuse configuration with deployment, or call a service
healthy without real checks.


## Required review

Apply LPOS-026 and LPOS-027. Preserve approved strengths. Use an independent reviewer
for material production work. Define verification and evidence before completion.
