# Bounded-view certification — chat_converter_seed_v2_bounded_view_certification

- service_certified: True
- probe_count: 4

## Metrics
- branch_isolation_rate: 1.0
- abstention_correctness_rate: 1.0
- flag_off_no_query_rate: 1.0
- bridge_integration_rate: 1.0

## Probes
- branch-isolation-competing-branches: pass
- abstain-missing-branch-scope: pass
- flag-off-skips-bounded-view-query: pass
- bridge-bundle-includes-bounded-view-evidence: pass
