# LPOS First-Run Onboarding (run once, immediately after installation)

Email is not set up yet, so every question here is asked in the current session
(desktop/chat), never by email. Keep it to two short question rounds: this is
onboarding, not an interview.

## 1. Name the office

Ask: "Your executive office is named **Chip** by default. Keep Chip, or pick another
name?" Accept any reasonable name; default to Chip if the Principal shrugs or skips.
Record it in `confirmed.office.name`. From this point forward, use the chosen name
everywhere: self-reference, email display name, templates, briefs.

## 2. Choose the sending address

Ask which email address the office will send from and check for replies on. Offer
the realistic options:

- a dedicated address on the Principal's domain (like chip@theirdomain.com): best;
- an existing mailbox the Principal controls;
- "skip for now": LPOS runs without the email loop until they return to this step.

## 3. Verify real access, never assume it

Whatever the runtime provides (Gmail API, OAuth, SMTP/IMAP, a mail tool), verify
BOTH directions before declaring the channel live: send one test email from the
chosen address to the Principal's own address, and confirm the mailbox can be read
by the collector. Configuration alone is not verification (CS-013). If credentials
are missing, tell the Principal exactly what to create or authorize (one concise
checklist for their provider), then pause this step: do not half-enable the loop.
Record `email`, `email_provider`, `outbound_verified_at`, and
`inbox_read_verified_at` in `confirmed.office`. These two checks prove the system
can send and read; they do not yet prove the Principal loop works.

## 4. Verified reply addresses

Ask which of the Principal's addresses count as verified senders (the addresses
they will reply from). Seed `confirmed.verified_reply_addresses` with them. These
are the ONLY addresses the feedback loop will ever execute instructions from.

## 5. Channel map

Ask which channels exist in this environment (email, desktop, Telegram, Slack,
other). Fill `confirmed.channels.available` and `routing_preferences`. Any intent
whose preferred channel doesn't exist routes to the session (desktop) by default.

## 6. Choose your model routing

LPOS never pins work to a vendor (LPOS-019). Work is routed through **classes**, and
the classes point at whatever models the Principal actually has. Most people start
with one license and add models later; the flow handles both.

1. **Discover, don't assume.** List the providers and models actually configured in
   this runtime. Show the Principal what they have, with plain-language labels
   ("your OpenAI subscription", "a local model on this machine").
2. **One provider?** One question: "Everything will run on <provider>. OK?" On yes,
   write all classes to it and move on. Adding a second model later is one short
   conversation, not a redesign.
3. **More than one?** Ask at most three questions:
   - Which model handles **executive work** (briefs, strategy, material writing,
     decisions)? Default: the most capable configured model.
   - Which handles **routine work** (scheduled collectors, status runs,
     formatting)? Default: the cheapest reliable one.
   - Reviews: if two or more models exist, default **independent review** to a
     different model than the one that created the work, and say why in one line
     (a different model catches different mistakes). Let the Principal override.
4. Write the choices to `lpos-state/model-routing.yaml` (schema in LEDGERS.md),
   including the fallback order (remaining models, most capable first; local
   models last unless the Principal prefers otherwise).
5. State the three standing policies out loud so the Principal knows them:
   fallback use is always visible in evidence records; a provider in a known
   quota outage gets temporarily rerouted with a decision record; and new models
   are benchmarked (SO-016) before they take over a class.
6. Record the routing choices as a decision record.

Scheduled jobs and specialists reference classes, never providers. When the
Principal adds a license later, they just say "add <provider> to my model
routing": the runtime benchmarks it, proposes where it fits, and updates the one
file on approval.

## 7. Activate the feedback loop

Only after steps 3 and 4 verify: enable the SO-021 schedule (every 10 minutes),
send the standard round-trip test question (`[LPOS-Q-0001] Email loop test`, asking
the Principal to reply "confirmed"), detect the reply, and record the evidence. On success record
`principal_round_trip_verified_at` and `loop_activated_at`. SO-021 activates only
when outbound, inbox-read, and round-trip timestamps all exist.
Until email verifies, SO-021 stays dormant and questions fall back to the session : 
blocked-on-consent work waits in the question registry rather than being emailed.

## 8. Wire the Standing Operations

Create scheduled jobs for the Standing Operations, every job pointing at the
canonical install path. Suggested defaults (adjust to the Principal's day; local
time):

| SO | Schedule | Condition |
|----|----------|-----------|
| SO-001 Executive Brief | 0 7 * * 1-5 |: |
| SO-003 Calendar Review | 30 6 * * 1-5 | calendar connected |
| SO-004 Inbox Review | 0 8,16 * * 1-5 | mailbox readable |
| SO-005 Meeting Preparation | */15 7-18 * * 1-5 (event-driven check) | calendar connected |
| SO-002 Opportunity Intelligence | 0 9,13,16 * * 1-5 |: |
| SO-010 Technology Signals | 0 10 * * 1-5 |: |
| SO-011 Daily Execution Review | 45 16 * * 1-5 |: |
| SO-006 Weekly Review | 0 16 * * 5 |: |
| SO-007 Evidence Review | 0 15 * * 5 |: |
| SO-008 Standing Operation Health | 0 6 * * * |: |
| SO-009 Relationship Review | 0 11 * * 2,4 |: |
| SO-014 Security Review | 30 8 * * 1 |: |
| SO-020 Platform Health Review | 0 7 * * 0 |: |
| SO-015 Provider Review | 0 9 1 * * |: |
| SO-016 Model Benchmark Review | 30 9 1 * * |: |
| SO-017 Knowledge Review | 0 10 1 * * |: |
| SO-018 Monthly Effectiveness Review | 30 10 1 * * |: |
| SO-019 Decision Retrospective | 0 11 1 * * |: |
| SO-012 Pipeline Review | 0 9 * * 1 | only if a pipeline/CRM data source exists |
| SO-013 Customer Review | 0 9 * * 2 | only if customer account data exists |
| SO-021 Principal Feedback Loop | */10 * * * * | after step 7 verifies |

Wire where the data source exists; defer where it doesn't and record each deferral
in the decision ledger with its revisit condition. Anti-noise rule (CS-013): if a
wired SO returns [SILENT] or near-empty output for 4 consecutive runs, SO-008 flags
it with a recommendation to retune or pause.

## 9. Record and report

Seed the decision ledger with the onboarding decisions (office name, email choice,
wiring and deferrals). Append evidence for the email round trip. Then return the
installation completion report from INSTALL-LPOS-COMPACT.md.
