# COE Implementation Evidence

Status: shipped
Recorded: 2026-07-28

## Merged implementation

- LPOS release branch: `release/4.5.0`
- LPOS implementation and operating repairs merged through PR 13.
- Chip service main branch commit: `64dec157367b2d3be6cbd0440b950af4d9e4c2d1`
- Chip service implementation merged through PR 8.

## Final artifact and deployment

- Release version: `4.5.0`
- Artifact SHA-256: `20f6fa6529afab8a103d01f988d7cc8f06a26102230a13c77f5a92d7b771a432`
- Cloud Build: `56c26524-26a0-4f1f-b33a-1b0b41998f3b`
- Image digest: `sha256:541dffd50e0c9211d6961bf0ba2b8999fa46c1b9529cc69193e512e736fca6f7`
- Cloud Run revision: `chip-api-coe-v45-20f6-v3`
- Traffic: 100 percent
- Rollback revision: `chip-api-gateway-whole-site-prod`

## Final audit

- Audit ID: `audit-1785261466341-679ee503a3f8037f`
- Decision: `pass`
- All nine mandatory gates: `pass`
- Application manifest: 484 files, 2,485,291 bytes
- Report delivery: `delivered`
- Provider message ID: `34c5e9af-52e3-4adb-97a5-20b8d1a6247f`

## Schedule

- Hermes job: `ce51f7aeb7f1`
- Schedule: `0 3 * * *`
- Timezone: `America/Chicago`
- Runner: deterministic no-model script `coe-daily.sh`
- Next scheduled run: 2026-07-29 03:00 Central

## Published documentation

- GitHub: `https://github.com/listeningpost-dsteele/lposv3/blob/release/4.5.0/docs/passoff/LPOS-v4.5.0-COE.md`
- User-guide wiki: `https://chip.listeningpost.ai/wiki/administration/continuous-operational-excellence/`
- Google Drive: `https://drive.google.com/file/d/1lTLPzVUySUhbIeKe5hpAxLoxjeLdHy9p/view`

## Live proof

- Dashboard: `https://chip.listeningpost.ai/dashboard/coe`
- Unauthenticated dashboard probe: HTTP 401
- Authenticated dashboard probe: HTTP 200 with all 18 required labels
- Summary API: HTTP 200, final audit ID, readiness pass, delivery status delivered
- Release gate API: HTTP 200, release status pass, exact artifact SHA-256
- Final probe timestamp: `2026-07-28T18:00:37.182451Z`

## Compatibility boundary

Legacy `/Users/dan/lpos-state` remains read-only and tracked as `TD-LEGACY-LPOS-STATE`. No legacy migration or deletion occurred.