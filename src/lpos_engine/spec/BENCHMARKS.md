# LPOS v4 Fixed Benchmark Corpus

This corpus is the readable form of the 53 immutable benchmark fixtures packaged under
`lpos_engine.evals`. Each fixture has explicit inputs, expected behavior, success and
failure criteria, an evaluation method, and required evidence. The deterministic core
evaluator runs every fixture with `lpos evals`; deployment model adapters may consume the
same fixtures for model-quality scoring without changing the cases.

Coverage: 32 specialist fixtures (`BENCH-S001` through `BENCH-S032`) and 21 Standing
Operation fixtures (`BENCH-O001` through `BENCH-O021`).

## BENCH-S001 — SPECIALIST-001

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Strategic Planner work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Strategic Planner deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Executive",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S001",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S001: produce the Strategic Planner analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "executive_coordination",
    "strategy",
    "strategic_planning",
    "scenario_planning",
    "planning",
    "objectives"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-005",
    "CS-014",
    "CS-016"
  ],
  "lead_guild": "Executive",
  "lead_specialist": "SPECIALIST-001",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-001.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S002 — SPECIALIST-002

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Decision Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Decision Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Executive",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S002",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S002: produce the Decision Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "decision_support",
    "decision_analysis",
    "tradeoff_analysis",
    "recommendations",
    "confidence_assessment"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-005",
    "CS-014",
    "CS-016"
  ],
  "lead_guild": "Executive",
  "lead_specialist": "SPECIALIST-002",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-002.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S003 — SPECIALIST-003

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Evidence Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Evidence Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Executive",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S003",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S003: produce the Evidence Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "evidence_synthesis",
    "measurement",
    "outcome_evaluation",
    "evidence_management",
    "fact_checking"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-005",
    "CS-014",
    "CS-016"
  ],
  "lead_guild": "Executive",
  "lead_specialist": "SPECIALIST-003",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-003.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S004 — SPECIALIST-004

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Risk Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Risk Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Executive",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S004",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S004: produce the Risk Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "risk_triage",
    "risk_analysis",
    "scenario_analysis",
    "mitigation_planning"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-005",
    "CS-014",
    "CS-016"
  ],
  "lead_guild": "Executive",
  "lead_specialist": "SPECIALIST-004",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-004.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S005 — SPECIALIST-005

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Initiative Manager work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Initiative Manager deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Executive",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S005",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "routine",
  "principal_instruction": "Fixture BENCH-S005: produce the Initiative Manager analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "initiative_management",
    "dependency_tracking",
    "execution_planning",
    "portfolio_tracking"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-005",
    "CS-014",
    "CS-016"
  ],
  "lead_guild": "Executive",
  "lead_specialist": "SPECIALIST-005",
  "missing_capabilities": [],
  "model_class": "routine"
}
```

### Success criteria

- Lead specialist is SPECIALIST-005.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S006 — SPECIALIST-006

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Research Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Research Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Research",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S006",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S006: produce the Research Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "research",
    "evidence_synthesis",
    "source_evaluation",
    "fact_checking",
    "literature_review"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-004"
  ],
  "lead_guild": "Research",
  "lead_specialist": "SPECIALIST-006",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-006.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S007 — SPECIALIST-007

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Technology Scout work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Technology Scout deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Research",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S007",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S007: produce the Technology Scout analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "technology_scouting",
    "technology_research",
    "weak_signal_detection",
    "innovation_research"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-004"
  ],
  "lead_guild": "Research",
  "lead_specialist": "SPECIALIST-007",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-007.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S008 — SPECIALIST-008

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Source Validator work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Source Validator deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Research",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S008",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "review",
  "principal_instruction": "Fixture BENCH-S008: produce the Source Validator analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "source_evaluation",
    "source_validation",
    "fact_checking",
    "recency_analysis",
    "independence_analysis"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-004"
  ],
  "lead_guild": "Research",
  "lead_specialist": "SPECIALIST-008",
  "missing_capabilities": [],
  "model_class": "review"
}
```

### Success criteria

- Lead specialist is SPECIALIST-008.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S009 — SPECIALIST-009

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Competitive Intelligence Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Competitive Intelligence Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Research",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S009",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S009: produce the Competitive Intelligence Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "competitive_intelligence",
    "market_positioning",
    "competitor_research",
    "evidence_synthesis"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-004"
  ],
  "lead_guild": "Research",
  "lead_specialist": "SPECIALIST-009",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-009.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S010 — SPECIALIST-010

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Market Research Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Market Research Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Research",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S010",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S010: produce the Market Research Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "market_research",
    "demand_analysis",
    "segmentation",
    "customer_research",
    "evidence_synthesis"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-004"
  ],
  "lead_guild": "Research",
  "lead_specialist": "SPECIALIST-010",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-010.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S011 — SPECIALIST-011

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Software Architect work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Software Architect deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Engineering",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S011",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S011: produce the Software Architect analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "software_architecture",
    "system_design",
    "data_modeling",
    "integration_architecture",
    "security_review"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-007",
    "CS-008"
  ],
  "lead_guild": "Engineering",
  "lead_specialist": "SPECIALIST-011",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-011.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S012 — SPECIALIST-012

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Software Engineer work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Software Engineer deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Engineering",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S012",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S012: produce the Software Engineer analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "software_implementation",
    "automation",
    "integration",
    "code_generation",
    "data_modeling"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-007",
    "CS-008"
  ],
  "lead_guild": "Engineering",
  "lead_specialist": "SPECIALIST-012",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-012.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S013 — SPECIALIST-013

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Code Reviewer work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Code Reviewer deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Engineering",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S013",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "review",
  "principal_instruction": "Fixture BENCH-S013: produce the Code Reviewer analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "code_review",
    "security_review",
    "quality_assurance",
    "regression_detection",
    "policy_audit",
    "independent_review"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-007",
    "CS-008"
  ],
  "lead_guild": "Engineering",
  "lead_specialist": "SPECIALIST-013",
  "missing_capabilities": [],
  "model_class": "review"
}
```

### Success criteria

- Lead specialist is SPECIALIST-013.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S014 — SPECIALIST-014

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Test Engineer work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Test Engineer deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Engineering",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S014",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "review",
  "principal_instruction": "Fixture BENCH-S014: produce the Test Engineer analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "testing",
    "test_design",
    "quality_assurance",
    "regression_detection",
    "failure_injection"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-007",
    "CS-008"
  ],
  "lead_guild": "Engineering",
  "lead_specialist": "SPECIALIST-014",
  "missing_capabilities": [],
  "model_class": "review"
}
```

### Success criteria

- Lead specialist is SPECIALIST-014.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S015 — SPECIALIST-015

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Debugging Specialist work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Debugging Specialist deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Engineering",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S015",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S015: produce the Debugging Specialist analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "debugging",
    "root_cause_analysis",
    "incident_diagnosis",
    "corrective_action"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-007",
    "CS-008"
  ],
  "lead_guild": "Engineering",
  "lead_specialist": "SPECIALIST-015",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-015.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S016 — SPECIALIST-016

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Operations Manager work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Operations Manager deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Operations",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S016",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "routine",
  "principal_instruction": "Fixture BENCH-S016: produce the Operations Manager analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "operations",
    "operational_coordination",
    "incident_response",
    "process_improvement",
    "scheduling"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-013",
    "CS-016"
  ],
  "lead_guild": "Operations",
  "lead_specialist": "SPECIALIST-016",
  "missing_capabilities": [],
  "model_class": "routine"
}
```

### Success criteria

- Lead specialist is SPECIALIST-016.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S017 — SPECIALIST-017

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Workflow Coordinator work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Workflow Coordinator deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Operations",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S017",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "routine",
  "principal_instruction": "Fixture BENCH-S017: produce the Workflow Coordinator analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "workflow_design",
    "workflow_coordination",
    "scheduling",
    "state_tracking",
    "process_improvement"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-013",
    "CS-016"
  ],
  "lead_guild": "Operations",
  "lead_specialist": "SPECIALIST-017",
  "missing_capabilities": [],
  "model_class": "routine"
}
```

### Success criteria

- Lead specialist is SPECIALIST-017.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S018 — SPECIALIST-018

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Dependency Manager work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Dependency Manager deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Operations",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S018",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "routine",
  "principal_instruction": "Fixture BENCH-S018: produce the Dependency Manager analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "dependency_management",
    "dependency_tracking",
    "execution_planning",
    "blocker_resolution"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-013",
    "CS-016"
  ],
  "lead_guild": "Operations",
  "lead_specialist": "SPECIALIST-018",
  "missing_capabilities": [],
  "model_class": "routine"
}
```

### Success criteria

- Lead specialist is SPECIALIST-018.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S019 — SPECIALIST-019

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Executive Writer work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Executive Writer deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Communications",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S019",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "routine",
  "principal_instruction": "Fixture BENCH-S019: produce the Executive Writer analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "writing",
    "executive_communication",
    "brief_writing",
    "decision_communication",
    "customer_communication"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-001",
    "CS-014",
    "CS-018"
  ],
  "lead_guild": "Communications",
  "lead_specialist": "SPECIALIST-019",
  "missing_capabilities": [],
  "model_class": "routine"
}
```

### Success criteria

- Lead specialist is SPECIALIST-019.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S020 — SPECIALIST-020

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Technical Writer work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Technical Writer deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Communications",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S020",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "routine",
  "principal_instruction": "Fixture BENCH-S020: produce the Technical Writer analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "writing",
    "technical_writing",
    "documentation",
    "developer_communication"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-001",
    "CS-014",
    "CS-018"
  ],
  "lead_guild": "Communications",
  "lead_specialist": "SPECIALIST-020",
  "missing_capabilities": [],
  "model_class": "routine"
}
```

### Success criteria

- Lead specialist is SPECIALIST-020.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S021 — SPECIALIST-021

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Editor work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Editor deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Communications",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S021",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "review",
  "principal_instruction": "Fixture BENCH-S021: produce the Editor analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "editing",
    "writing_review",
    "clarity_improvement",
    "meaning_preservation"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-001",
    "CS-014",
    "CS-018"
  ],
  "lead_guild": "Communications",
  "lead_specialist": "SPECIALIST-021",
  "missing_capabilities": [],
  "model_class": "review"
}
```

### Success criteria

- Lead specialist is SPECIALIST-021.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S022 — SPECIALIST-022

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Financial Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Financial Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Finance",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S022",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S022: produce the Financial Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "financial_analysis",
    "budgeting",
    "forecasting",
    "roi_analysis",
    "cost_analysis"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-010"
  ],
  "lead_guild": "Finance",
  "lead_specialist": "SPECIALIST-022",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-022.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S023 — SPECIALIST-023

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Pricing Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Pricing Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Finance",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S023",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S023: produce the Pricing Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "pricing",
    "packaging",
    "unit_economics",
    "revenue_analysis"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-010"
  ],
  "lead_guild": "Finance",
  "lead_specialist": "SPECIALIST-023",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-023.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S024 — SPECIALIST-024

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Security Architect work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Security Architect deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Security",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S024",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S024: produce the Security Architect analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "security_architecture",
    "security_review",
    "threat_mitigation",
    "least_privilege",
    "privacy_engineering"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-009"
  ],
  "lead_guild": "Security",
  "lead_specialist": "SPECIALIST-024",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-024.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S025 — SPECIALIST-025

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Threat Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Threat Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Security",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S025",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "review",
  "principal_instruction": "Fixture BENCH-S025: produce the Threat Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "threat_modeling",
    "attack_surface_analysis",
    "security_review",
    "risk_analysis"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-009"
  ],
  "lead_guild": "Security",
  "lead_specialist": "SPECIALIST-025",
  "missing_capabilities": [],
  "model_class": "review"
}
```

### Success criteria

- Lead specialist is SPECIALIST-025.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S026 — SPECIALIST-026

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Legal Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Legal Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Legal",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S026",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S026: produce the Legal Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "legal_analysis",
    "contract_analysis",
    "legal_risk",
    "policy_interpretation"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-011"
  ],
  "lead_guild": "Legal",
  "lead_specialist": "SPECIALIST-026",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-026.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S027 — SPECIALIST-027

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Product Manager work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Product Manager deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Product",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S027",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S027: produce the Product Manager analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "product_management",
    "requirements",
    "prioritization",
    "product_strategy",
    "outcome_definition"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-006"
  ],
  "lead_guild": "Product",
  "lead_specialist": "SPECIALIST-027",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-027.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S028 — SPECIALIST-028

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Customer Insights Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Customer Insights Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Customer Intelligence",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S028",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S028: produce the Customer Insights Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "customer_research",
    "customer_insights",
    "needs_analysis",
    "evidence_synthesis"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-015",
    "CS-006"
  ],
  "lead_guild": "Customer Intelligence",
  "lead_specialist": "SPECIALIST-028",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-028.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S029 — SPECIALIST-029

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Relationship Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Relationship Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Relationship Intelligence",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S029",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "routine",
  "principal_instruction": "Fixture BENCH-S029: produce the Relationship Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "relationship_analysis",
    "stakeholder_analysis",
    "follow_up_planning",
    "communication_context"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-015"
  ],
  "lead_guild": "Relationship Intelligence",
  "lead_specialist": "SPECIALIST-029",
  "missing_capabilities": [],
  "model_class": "routine"
}
```

### Success criteria

- Lead specialist is SPECIALIST-029.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S030 — SPECIALIST-030

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Data Analyst work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Data Analyst deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Data Intelligence",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S030",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S030: produce the Data Analyst analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "data_analysis",
    "metrics",
    "trend_analysis",
    "data_quality",
    "measurement"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-012"
  ],
  "lead_guild": "Data Intelligence",
  "lead_specialist": "SPECIALIST-030",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-030.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S031 — SPECIALIST-031

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Automation Architect work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Automation Architect deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Automation",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S031",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S031: produce the Automation Architect analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "automation",
    "workflow_design",
    "integration_architecture",
    "observability",
    "reliability_engineering"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-013"
  ],
  "lead_guild": "Automation",
  "lead_specialist": "SPECIALIST-031",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-031.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-S032 — SPECIALIST-032

**Fixture version:** 1.0.0  
**Component type:** specialist

### Objective

Verify that fixed Web & Product Designer work routes to the canonical specialist with complete capability coverage.

### Scenario

The Principal requests a bounded Web & Product Designer deliverable using the supplied fixture facts; no external action is authorized.

### Inputs

```json
{
  "facts": {
    "approved_scope": "Design",
    "external_action_authorized": false,
    "fixture_id": "BENCH-S032",
    "known_constraint": "Preserve the supplied scope and identify uncertainty."
  },
  "preferred_model_class": "executive",
  "principal_instruction": "Fixture BENCH-S032: produce the Web & Product Designer analysis from the supplied facts, state assumptions, and propose evidence without taking an external action.",
  "required_capabilities": [
    "product_design",
    "web_design",
    "interaction_design",
    "visual_design",
    "baseline_preservation"
  ]
}
```

### Expected behavior

```json
{
  "craft_standards": [
    "CS-003",
    "CS-002",
    "CS-001"
  ],
  "lead_guild": "Design",
  "lead_specialist": "SPECIALIST-032",
  "missing_capabilities": [],
  "model_class": "executive"
}
```

### Success criteria

- Lead specialist is SPECIALIST-032.
- All required capabilities are covered.
- Mapped craft standards are present.
- No external action is executed.

### Failure criteria

- A different lead specialist is selected.
- Any capability is silently omitted.
- The route names a provider instead of a model class.
- The fixture is modified during evaluation.

### Evaluation method

`deterministic_router_assertions` with assertions:
- `lead_specialist`
- `model_class`
- `no_missing_capabilities`
- `craft_standards_present`

### Evidence

- RouteDecision JSON
- selected specialist and craft-standard IDs
- missing-capability set

---

## BENCH-O001 — SO-001

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Executive Brief workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Executive Brief for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-001:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-001"
}
```

### Success criteria

- Workflow resolves as SO-001.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O002 — SO-002

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Opportunity Intelligence workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Opportunity Intelligence for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-002:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-002"
}
```

### Success criteria

- Workflow resolves as SO-002.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O003 — SO-003

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Calendar Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Calendar Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-003:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "routine",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-003"
}
```

### Success criteria

- Workflow resolves as SO-003.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O004 — SO-004

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Inbox Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Inbox Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-004:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "routine",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-004"
}
```

### Success criteria

- Workflow resolves as SO-004.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O005 — SO-005

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Meeting Preparation workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Meeting Preparation for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-005:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "routine",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-005"
}
```

### Success criteria

- Workflow resolves as SO-005.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O006 — SO-006

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Weekly Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Weekly Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-006:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-006"
}
```

### Success criteria

- Workflow resolves as SO-006.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O007 — SO-007

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Evidence Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Evidence Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-007:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "review",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-007"
}
```

### Success criteria

- Workflow resolves as SO-007.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O008 — SO-008

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Standing Operation Health workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Standing Operation Health for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-008:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "routine",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-008"
}
```

### Success criteria

- Workflow resolves as SO-008.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O009 — SO-009

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Relationship Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Relationship Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-009:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-009"
}
```

### Success criteria

- Workflow resolves as SO-009.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O010 — SO-010

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Technology Signals workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Technology Signals for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-010:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-010"
}
```

### Success criteria

- Workflow resolves as SO-010.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O011 — SO-011

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Daily Execution Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Daily Execution Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-011:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "routine",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-011"
}
```

### Success criteria

- Workflow resolves as SO-011.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O012 — SO-012

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Pipeline Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Pipeline Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-012:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-012"
}
```

### Success criteria

- Workflow resolves as SO-012.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O013 — SO-013

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Customer Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Customer Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-013:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-013"
}
```

### Success criteria

- Workflow resolves as SO-013.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O014 — SO-014

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Security Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Security Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-014:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "review",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-014"
}
```

### Success criteria

- Workflow resolves as SO-014.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O015 — SO-015

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Provider Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Provider Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-015:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-015"
}
```

### Success criteria

- Workflow resolves as SO-015.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O016 — SO-016

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Model Benchmark Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Model Benchmark Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-016:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "review",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-016"
}
```

### Success criteria

- Workflow resolves as SO-016.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O017 — SO-017

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Knowledge Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Knowledge Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-017:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "routine",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-017"
}
```

### Success criteria

- Workflow resolves as SO-017.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O018 — SO-018

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Monthly Effectiveness Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Monthly Effectiveness Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-018:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-018"
}
```

### Success criteria

- Workflow resolves as SO-018.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O019 — SO-019

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Decision Retrospective workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Decision Retrospective for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-019:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "executive",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-019"
}
```

### Success criteria

- Workflow resolves as SO-019.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O020 — SO-020

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Platform Health Review workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Platform Health Review for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-020:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "routine",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-020"
}
```

### Success criteria

- Workflow resolves as SO-020.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---

## BENCH-O021 — SO-021

**Fixture version:** 1.0.0  
**Component type:** standing_operation

### Objective

Verify the fixed Principal Feedback Loop workflow identity, model class, DAG shape, and executable step contract.

### Scenario

Run Principal Feedback Loop for the immutable scheduled fixture without live channel or consequential-action adapters.

### Inputs

```json
{
  "fixture": {
    "live_side_effects": false,
    "records": 3,
    "source": "packaged deterministic benchmark"
  },
  "idempotency_key": "SO-021:2030-01-07T12:00:00Z:fixture-1",
  "scheduled_for": "2030-01-07T12:00:00Z"
}
```

### Expected behavior

```json
{
  "evidence_record_required": true,
  "minimum_steps": 3,
  "model_class": "routine",
  "result_values": [
    "ok",
    "silent",
    "error"
  ],
  "so_id": "SO-021"
}
```

### Success criteria

- Workflow resolves as SO-021.
- Step identifiers are unique and dependencies resolve.
- The workflow declares a model class.
- The run contract requires one evidence record.

### Failure criteria

- Workflow identity or model class differs from the fixture.
- A dependency references a missing step.
- The workflow has fewer steps than the fixed fixture.
- A live side effect occurs during the core evaluation.

### Evaluation method

`workflow_definition_assertions` with assertions:
- `workflow_identity`
- `model_class`
- `minimum_steps`
- `unique_step_ids`

### Evidence

- WorkflowDefinition JSON
- step and dependency set
- catalog mapping

---
