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
 "alternatives":["..."],"consequences":"...","risks":"...","implementation_notes":"...","references":["EV-0001"],
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
    outbound_verified_at: null      # a test send from the office address succeeded
    inbox_read_verified_at: null    # the collector read the office inbox
    principal_round_trip_verified_at: null  # the Principal's reply was received and matched
    loop_activated_at: null         # set only when all three timestamps above exist
  channels:
    available: []                   # set by onboarding, e.g. [email, desktop, telegram]
  values: []
  working_style: []
  decision_history: see decision-ledger.jsonl   # single source; not duplicated here
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

Before each write, snapshot the current file to
lpos-state/principal-model-history/<timestamp>.yaml so previous versions remain
recoverable (LPOS-005).

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

{"channel":"email","provider":"gmail|imap|runtime-tool","message_id":"...",
 "question_id":"LPOS-Q-0001 or null","processed_at":"YYYY-MM-DDTHH:MM"}

Message identity is provider-neutral: channel plus provider plus message_id.
Question closure is atomic: the first verified answer closes the question in the
same operation that records it; later answers are logged, never executed
(replay protection). Non-email channels require their own verified identity
mapping in principal-model.yaml before their answers count.

Read-only inbox collectors must exclude ids present in this registry so handled
Principal replies never resurface as new mailbox content.
