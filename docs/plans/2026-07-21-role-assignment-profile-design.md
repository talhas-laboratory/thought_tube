# RoleAssignment profile design

`profile:role_assignment@1.0.0` models a participant's role in a host under a
declared scope, time interval, branch, mechanism, and provenance. Roles are
contextual assignments, never permanent intrinsic labels.

An optional `influence_assessment` supplies future weighting infrastructure. A
numeric magnitude requires a scale and unit, while every assessment declares
its basis, uncertainty, confidence, scope, time, branch, and provenance. This
profile does not calculate or aggregate weights, infer causality, or implement
cybernetic control.
