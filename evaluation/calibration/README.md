# Human benchmark workspace

This directory contains benchmark lifecycle configuration, not human approval.

- `cohort.yml` declares the required sampling strata and the current lifecycle state.
- Reviewer submissions and adjudications must be created through the blinded workflow and bound to immutable answer, context, target-input, schema, and rubric digests.
- No reviewer identities, approvals, or adjudicated labels are recorded here until real domain reviewers submit them.
- Benchmark agreement is descriptive provenance. It does not approve canonical testing-case oracles, adopt experiment candidates, determine metric eligibility, or set a release/confidence gate.

The checked-in cohort remains `NOT_FROZEN` until reproducible outputs and Effective Context Snapshots exist and real two-reviewer plus distinct-adjudicator sign-off is complete.
