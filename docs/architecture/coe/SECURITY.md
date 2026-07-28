# COE Security

Release: LPOS 4.5.0

## Private surfaces

The dashboard and COE APIs require an operator bearer credential or the deployed service's equivalent operator authorization. Authentication is mandatory even when no audit exists. Sensitive responses use private, no-store caching, deny framing, disable MIME sniffing, and apply a restrictive content security policy.

## Process safety

Gate execution uses direct executable and argument arrays. Shell interpolation is not used. Child environments are restricted. Gate duration and output are bounded. Context and evidence files are stored outside the release.

## Evidence safety

Evidence excerpts are redacted before persistence. Authorization headers, passwords, tokens, cookies, API keys, private keys, and user-home paths are removed. Full outputs are represented by hashes. Generated evidence and reports are scanned before delivery.

## Fail-closed rules

Missing configuration, evidence, schema validity, chain integrity, artifact identity, source provenance, dependency audit, authenticated security tests, or fresh restore evidence is not a pass. Network unavailability is recorded as unknown or failed according to policy.

Failure injection and restore checks use isolated temporary resources. Production state is never used as a failure-injection target.
