# Temporal Staleness

Status: `seeded`  
Owner: `unassigned`  
First contract: `FreshnessRecord`

## Responsibility

Track whether reused context is fresh enough to trust.

## Scope In

- source timestamp
- last verified
- last used
- conflict markers
- freshness risk
- revalidation requirement

## Scope Out

- full web crawling
- durable memory promotion

## Integration

Feeds frame preview, context policy, evaluator gates, and answer caveats.

## First Tasks

- Define freshness metadata.
- Add staleness behavior to retrieved frame blocks.
- Test that stale context is flagged before use.

## Acceptance Criteria

- Stale context is visible in previews.
- Freshness risk can reduce depth or require verification.
- Newer conflicting evidence is not hidden.
