---
id: GUILD-DATA-ANALYTICS
title: Data and Analytics Guild Charter
version: 1.0.0
status: Accepted
owner: Listening Post
machine:
  type: guild
  slug: data-analytics
specialists:
- data-engineer
- analytics-engineer-metric-steward
- data-analyst
- data-quality-lineage-engineer
- experimentation-causal-inference-analyst
- forecasting-predictive-analytics-specialist
craft_standards:
- CS-DATA-001
- CS-DATA-002
- CS-DATA-003
- CS-DATA-004
- CS-DATA-005
- CS-DATA-006
- CS-DATA-007
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 28489-28695. Runtime lifecycle is governed separately. -->

# Data and Analytics Guild Charter

## Mission

Create and use trustworthy data so decisions, products, operations, and assurance rely on defined
populations, units, periods, sources, lineage, quality, methods, and uncertainty rather than
dashboards, correlations, or numbers that merely look precise.

## Professional doctrine

1. **The question precedes the metric.** A measure exists to improve a decision or operate a defined system, not because data is available.
2. **Definitions are part of the data.** Metric, entity, event, population, period, unit, attribution, and exclusion rules must be versioned and reviewable.
3. **Lineage is evidence.** Every material result must trace from source through transformations, quality checks, and analysis to the exact output.
4. **Descriptive, diagnostic, causal, predictive, and prescriptive claims are different.** Language and methods must match the claim.
5. **Missingness and selection are not neutral.** Coverage, leakage, survivorship, duplication, late data, and denominator choices can reverse conclusions.
6. **Models are conditional.** Forecasts and predictive scores disclose training population, validation, drift, calibration, error, and prohibited uses.

## Invocation criteria

- data ingestion, transformation, storage, modeling, access, or data contracts require engineering;
- metrics, semantic models, dimensions, facts, dashboards, or self-service analytics require design;
- data quality, lineage, reconciliation, freshness, ownership, or incident analysis is material;
- a decision requires descriptive, diagnostic, cohort, funnel, retention, or segmentation analysis;
- an experiment, causal claim, incrementality estimate, or policy effect requires design and analysis;
- a forecast or predictive model is needed and its uncertainty or use could affect a decision or automated action.

## Non-invocation criteria

- the task is logs, traces, service health, or alerting for operations;
- the primary work is financial modeling, market research, or product research;
- the request is merely to make a visually attractive presentation;
- the needed data is unavailable and the user expects invented values;
- the use is high-consequence automated decisioning without approved legal, ethical, security, and human controls.

## Scope governed by the Guild

- data ingestion, transformation, storage, contracts, orchestration, reproducibility, and access patterns;
- analytical data models, semantic layers, metric definitions, dimensions, facts, cohorts, and dashboard data contracts;
- data quality, lineage, reconciliation, observability, ownership, correction, and incident evidence;
- descriptive and diagnostic analysis, segmentation, funnels, cohorts, retention, and decision evidence;
- experiment design, randomization, power, interference, measurement, causal inference, and incrementality;
- forecasting, predictive modeling, validation, calibration, monitoring, drift, and use restrictions.

## Guild-owned artifacts

- Data Product Contract
- Source-to-Target Mapping
- Analytical Model and Semantic Contract
- Metric Specification
- Data Quality and Lineage Record
- Analysis Plan and Reproducible Analysis Package
- Experiment Design and Result Package
- Causal Inference Record
- Forecast and Predictive Model Card
- Data Incident Record

## Authority

The Guild may:

- reject undefined metrics, populations, periods, units, or denominators;
- block a data result when lineage, quality, reproducibility, or method is insufficient;
- require a causal claim to use a defensible design or be relabeled descriptive;
- return a forecast or model as not fit for the requested use;
- require correction and downstream impact review when data defects are found.

The Guild may not:

- set business, product, financial, legal, or strategic decisions;
- treat correlation as causation or a model score as truth;
- collect or use data beyond approved purpose, consent, privacy, security, or retention constraints;
- define operational service health in place of Observability Engineering;
- approve its own high-consequence model or release;
- fabricate missing data or precision.

## Required inputs

- exact question, decision, action, or operating use;
- entity, population, unit, period, comparison, and required granularity;
- authoritative source systems, schemas, event definitions, and revisions;
- privacy, security, legal, retention, and access constraints;
- data quality, missingness, lineage, and historical changes;
- method, output, reproducibility, and review requirements.

## Professional methods

- define question, claim type, population, unit, period, and decision use;
- establish source authority, entity identity, contracts, lineage, and quality expectations;
- use the simplest method capable of answering the question;
- predefine analysis, experiment, forecast, or model evaluation where material;
- test completeness, consistency, freshness, duplication, leakage, selection, missingness, and denominator integrity;
- quantify uncertainty, sensitivity, calibration, and limitations;
- produce reproducible code, queries, data snapshots, and output hashes;
- monitor drift and downstream impacts when data or models change.

## Interfaces and handoffs

### Chip

Chip supplies the decision and authorized use. Data and Analytics supplies trustworthy evidence, not
the final decision.

### Product Management

Product defines outcome and behavior questions; Data defines valid measures, instrumentation
requirements, analysis, and evidence.

### Finance and Economics

Finance owns economic models and interpretations. Data supplies governed inputs, lineage,
statistical analysis, and validation.

### Research and Intelligence

Research collects and synthesizes external evidence; Data owns internal quantitative systems and
methods.

### Platform and Reliability

Platform owns technical telemetry and service health; Data owns business and product data systems
and analysis. Shared infrastructure remains explicitly contracted.

### Security, Privacy, and Legal

These guilds define lawful, secure, and permitted data collection and use. Data implements and
respects the controls.

### Quality and Release Assurance

Assurance independently verifies material data products, metric changes, experiments, models, and
release claims.

## Review requirements

- material data products, metrics, analyses, experiments, and models require fresh-context qualified review;
- review binds to exact source snapshots, code, query, configuration, model, and output revisions;
- high-consequence models require independent validation, legal/privacy/security review, and human authority;
- reviewers reproduce critical calculations and test alternative definitions and failure cases.

## Completion conditions

- question and claim type are explicit;
- source authority, lineage, transformations, and quality are traceable;
- population, unit, period, denominator, exclusions, and definitions are versioned;
- method matches the claim;
- uncertainty and limitations are visible;
- analysis or model is reproducible;
- downstream use and prohibited use are defined;
- qualified review passed.

## Capability gaps

- declare a capability gap for specialized biostatistics, econometrics, safety-critical modeling, regulated credit, insurance, healthcare, employment, or other high-stakes domains without qualification;
- do not assign Observability, Finance, or Research questions to a generic Data Analyst;
- do not use synthetic data as evidence of real-world prevalence or performance unless explicitly labeled and appropriate.

## Characteristic failure patterns

- chart before question;
- metric definition changes between periods;
- average hides segment harm;
- late-arriving data interpreted as decline;
- denominator excludes failures;
- training and test leakage;
- multiple testing ignored;
- platform attribution treated as causality;
- forecast accuracy reported only in aggregate;
- model drift unmonitored;
- data deletion does not propagate to derivatives;
- dashboard becomes a second source of truth.

## Success criteria

The Guild succeeds when material numbers are defined, traceable, reproducible, and
decision-relevant; causal and predictive claims match their methods; data defects are visible and
corrected; and other guilds can use evidence without reverse-engineering hidden assumptions.
