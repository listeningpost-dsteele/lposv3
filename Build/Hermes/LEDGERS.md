# LPOS Persistence Formats (implements LPOS-007, LPOS-011, LPOS-015)

All state lives under `lpos-state/` in the runtime workspace. Create on first use.
Secrets never enter these files (LPOS-018).

## evidence-ledger.jsonl: one object per line (fields from LPOS-007)

{"id":"EV-0001","recommendation":"...","owner":"SPECIALIST-003","expected_outcome":"...",
 "baseline":"...","target":"...","observed":null,"confidence":0.7,
 "measurement":"...","review_date":"YYYY-MM-DD",
 "status":"Proposed|Active|Measured|Validated|Refuted|Inconclusive"}

## decision-ledger.jsonl: append-only (fields from LPOS-015)

{"id":"DR-0001","date":"YYYY-MM-DD","context":"...","decision":"...","rationale":"...",
 "alternatives":["..."],"consequences":"...","risks":"...","references":["EV-0001"],
 "status":"Accepted|Superseded","superseded_by":null,"owner":"Principal|Chip"}

## questions.jsonl: Principal question registry (used by SO-021)

{"id":"LPOS-Q-0001","created":"YYYY-MM-DDTHH:MM","kind":"consent|clarification|approval",
 "task":"<originating task or SO id>","question":"...","options":["..."],
 "recommended":"...","sent_via":"email","status":"pending|answered|expired",
 "answer":null,"answer_source":null,"answered_at":null,"reminder_sent":false}

## principal-model.yaml: versioned (domains from LPOS-005)

version: 1
confirmed:
  identity: ...
  mission: ...
  office:
    name: Chip                      # set by onboarding; the executive office's name
    email: null                     # set by onboarding; null = email loop dormant
    email_provider: null            # gmail | smtp | runtime-tool
    email_verified_at: null         # timestamp of the successful round-trip test
  channels:
    available: []                   # set by onboarding, e.g. [email, desktop, telegram]
  priorities: []
  preferences: []
  organizations: []
  relationships: []
  active_initiatives: []
  constraints: []
  communication_preferences: []
  verified_reply_addresses: []      # ONLY these senders' instructions are executed
  routing_preferences:
    Executive Decision: <channel>
    Operational Alert: <channel>
    Evidence: <channel>
    Status: <channel>
    Collaboration: <channel>
    Conversation: <channel>
inferred: {}   # never mix with confirmed; promote only with Principal confirmation

## model-routing.yaml: model classes (set by onboarding step 6; LPOS-019)

version: 1
classes:
  executive:            # briefs, strategy, decisions, material writing
    primary: null       # e.g. openai/gpt-5.5: whatever the runtime actually has
    fallbacks: []       # ordered; most capable first, local last
  routine:              # scheduled collectors, status runs, formatting
    primary: null
    fallbacks: []
  review:               # independent review; prefer a DIFFERENT model than creator
    primary: null
    fallbacks: []
  local:                # optional offline/cheap tier
    primary: null
    fallbacks: []
policy:
  fallback_visible: true      # fallback use must appear in the run's evidence record
  review_diversity: preferred # required | preferred | off
  reroute_on_quota: true      # known quota outage => temporary reroute + decision record
  benchmark_before_promote: true  # SO-016 qualifies a model before it owns a class

Jobs and specialists reference classes, never providers. With one license, every
class points at it; adding a model later is an edit to this file plus a decision
record, never a job-by-job rewrite.

## specs/<artifact>.md: one spec per long-lived artifact (LPOS-029)

Structural decisions (for a site: page inventory, what is a page vs an anchor),
design tokens, and approved invariants. Seeded from the current approved
artifact when material work first touches it. Every Principal correction
updates the spec before the artifact. The artifact is never its own spec.

## operations/SO-###.yaml: per Standing Operation

id: SO-001
last_run: null
last_result: null            # summary + link/path to output
health: unknown              # unknown|healthy|degraded|failing
consecutive_failures: 0
evidence_ids: []

## operations/SO-021-processed.jsonl: single handled-message registry for SO-021

{"gmail_message_id":"...","processed_at":"YYYY-MM-DDTHH:MM"}

Read-only inbox collectors must exclude ids present in this registry so handled
Principal replies never resurface as new mailbox content.
