# Proposed architecture

Status: design; runtime components are not implemented.

Use the sister project's manifest-driven medallion pattern. Source clients own
transport and provider addressing. Pure transforms own normalization and feature
math. Storage adapters own engine-specific persistence. The orchestrator connects
these pieces and writes audit results throughout.

Bronze stores response bytes and extraction metadata. Silver uses dataset-specific
schemas and immutable observed revisions. Gold exposes current research views
and observed-as-of features with explicit lineage. Shared metadata contracts do
not imply shared numeric grains across positions, trading volume, and rates.

SQLite is the initial warehouse because it enables a full local integration test
without cloud credentials. Engine adapters are deferred. No Databricks bundle,
Docker service, production database, or scheduler is configured.

Replay rebuilds derived layers from Bronze, retaining original availability
timestamps. A full historical download establishes current historical coverage;
it does not establish what the provider published on each past date.

See [Spec 001](../../specs/spec001/README.md) for the executable interface proposed
for implementation and its acceptance criteria.
