# Specialist Index (lookup table: load charters from SPECIALISTS.md only when needed)

| ID | Specialist | Guild | Mission (one line) | Craft standards |
|----|-----------|-------|--------------------|-----------------|
| 001 | Strategic Planner | Executive | Objectives → strategic options and plans | CS-005, CS-014, CS-016 |
| 002 | Decision Analyst | Executive | Prepare decisions: options, tradeoffs, confidence | CS-005, CS-014, CS-016 |
| 003 | Evidence Analyst | Executive | Measure outcomes; maintain evidence records | CS-005, CS-014, CS-016 |
| 004 | Risk Analyst | Executive | Identify operational and strategic risks | CS-005, CS-014, CS-016 |
| 005 | Initiative Manager | Executive | Track initiatives, dependencies, next decisions | CS-005, CS-014, CS-016 |
| 006 | Research Analyst | Research | Broad evidence-based research | CS-004 |
| 007 | Technology Scout | Research | Emerging technologies and weak signals | CS-004 |
| 008 | Source Validator | Research | Source credibility, recency, independence | CS-004 |
| 009 | Competitive Intelligence Analyst | Research | Competitors and market positioning | CS-004 |
| 010 | Market Research Analyst | Research | Markets, demand, customer segments | CS-004 |
| 011 | Software Architect | Engineering | Design implementation architecture | CS-007, CS-008 |
| 012 | Software Engineer | Engineering | Implement approved specifications | CS-007, CS-008 |
| 013 | Code Reviewer | Engineering | Review correctness, maintainability, compliance | CS-007, CS-008 |
| 014 | Test Engineer | Engineering | Design and execute testing strategies | CS-007, CS-008 |
| 015 | Debugging Specialist | Engineering | Root causes and corrective actions | CS-007, CS-008 |
| 016 | Operations Manager | Operations | Coordinate operational execution | CS-013, CS-016 |
| 017 | Workflow Coordinator | Operations | Sequence work; track workflow state | CS-013, CS-016 |
| 018 | Dependency Manager | Operations | Track and resolve execution dependencies | CS-013, CS-016 |
| 019 | Executive Writer | Communications | Concise executive communications | CS-001, CS-014, CS-018 |
| 020 | Technical Writer | Communications | Accurate technical documentation | CS-001, CS-014, CS-018 |
| 021 | Editor | Communications | Improve clarity without changing meaning | CS-001, CS-014, CS-018 |
| 022 | Financial Analyst | Finance | Budgets, ROI, cost, revenue, forecasts | CS-010 |
| 023 | Pricing Analyst | Finance | Pricing and packaging | CS-010 |
| 024 | Security Architect | Security | Least authority; defense in depth | CS-009 |
| 025 | Threat Analyst | Security | Threats, attack surfaces, mitigations | CS-009 |
| 026 | Legal Analyst | Legal | Legal/contractual issues, stated limitations | CS-011 |
| 027 | Product Manager | Product | Product outcomes, requirements, priorities | CS-006 |
| 028 | Customer Insights Analyst | Customer Intelligence | Customer needs and evidence | CS-015, CS-006 |
| 029 | Relationship Analyst | Relationship Intelligence | Relationship context and follow-ups | CS-015 |
| 030 | Data Analyst | Data Intelligence | Metrics, trends, data quality | CS-012 |
| 031 | Automation Architect | Automation | Reliable, observable workflows | CS-013 |
| 032 | Web & Product Designer | Design | Audience-fit web/product design; baseline-preserving changes | CS-002, CS-001, CS-003 |
| 033 | Bug Triage Analyst | Support Engineering | Reproduce, classify, localize, and package user-reported defects | CS-007, CS-008, CS-014 |

## Fallback map for unstaffed guilds

Personal Office → 016 + 029 · Revenue Operations → 022 + 028 · Knowledge Management → 020 ·
Intelligence → 001 + 006 · Platform / Infrastructure / Runtime → 011 + 031 ·
Innovation → 007 + 027 · Quality Assurance → 014 · Learning and Improvement → 003 ·
Integration → 012 · Observability → 030 · AI Strategy / Ecosystem → 007 + 001 ·
Governance → 020 + 013 · Model Intelligence / Provider Intelligence → 030 + 007 ·
Principal Success / Principal Intelligence → 003 + 029 · Execution / Planning → 005 + 001 ·
Capability Engineering → 011 · Decision Intelligence → 002 · Support Engineering → 033

## Staffing policy

Specialists are compiled roles the model assumes at routing time (LPOS-020), not
resident agents; fallback-mapped guilds are by design. A guild earns a dedicated
skill or agent only when the evidence ledger shows 3+ fallback-routed tasks in its
domain within 30 days. Record staffing changes in the decision ledger.
