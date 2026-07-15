# Dependency Contract: Kernel Ontology → Vocabulary Governance

**Provider:** `metaphysical-kernel-ontology`
**Consumer:** `metaphysical-vocabulary-governance`
**Status:** **Released** — Kernel G5 (`KERNEL-005`)
**Provider contract version:** `1.1.0`
**Release packet:** [`KERNEL_RELEASE_DEPENDENCY_CONTRACT.json`](../../metaphysical-kernel-ontology/derived/KERNEL_RELEASE_DEPENDENCY_CONTRACT.json)

## Provider supplies

Universal record envelope, opaque `type_id` references, provenance closure, orthogonal lifecycle axes, and profile-conformance boundaries per framework v1.1.

## Consumer obligations

- Govern type promotion and mapping without redefining kernel record semantics
- Preserve source terms and branch context in mappings
- Pin `provider_contract_version` and `release_git_revision` in consumer releases (VOCAB-005)

## Compatibility

| Change type | Policy |
|---|---|
| Additive optional fields within `1.1.x` | Consumer may adopt when ready |
| Breaking semantic change | Requires new provider version + parent decision + consumer gate regression |

## Failure / absence

- Failed profile conformance must surface violations; must not coerce kernel records
- `TypeDefinition` as first-class kernel record is deferred — vocabulary owns evolution until contract extension

## Verification consumed from provider

- [`KERNEL_CONFORMANCE_COVERAGE.json`](../../metaphysical-kernel-ontology/derived/KERNEL_CONFORMANCE_COVERAGE.json)
- Profile registry adversarial fixtures (`invalid_profile_redefines_kernel.json`)

## Known provider limits (Phase 1)

- Lifecycle transition policy not published
- Staleness propagation contract not published

Consumer acknowledgment: [`kernel-provider-acknowledgment.md`](../../metaphysical-vocabulary-governance/derived/kernel-provider-acknowledgment.md)
