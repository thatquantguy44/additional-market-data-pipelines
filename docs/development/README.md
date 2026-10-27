# Development

This repository currently contains specifications and a directory scaffold.
There is no installable Python package, test suite, or active CI workflow yet.
Do not run the planned install/CLI commands in Spec 001 until implemented.

Read the pinned workflow library and review Spec 001 first. After specification
approval, write `tasks/plan.md` and `tasks/todo.md`, then implement small vertical
slices. Pin dependencies and add packaging only with the first executable slice.

Verification for implementation must include offline unit tests, a local
Bronze/Silver/Gold/audit integration test, idempotent reruns, revision timing,
failure isolation, and Bronze replay. Live provider checks are separate,
explicitly requested, bounded smoke runs; never make unit tests require network.

The reserved directories mirror `fred-bronze-to-gold-pipeline`. No code, runtime
configuration, warehouse files, or credentials have been copied from it.
