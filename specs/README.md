# Specification index

Updated: 2026-10-30. Numbers identify documents, not automatic build priority.

| Spec | Capability ID | Contract and status |
| --- | --- | --- |
| [001](spec001/README.md) | positioning-market-structure | Original broader design; CFTC, FINRA and OFR remain planned. |
| [002](spec002/README.md) | aaii-initial-slice | Existing AAII ingestion contract; see the current handoffs for verification status. |
| [003](spec003/README.md) | aaii-completion | AAII local completion implemented and verified; recurring acquisition and production deployment remain gated. |
| [004](spec004/README.md) | fx-reference-rates | Initial scope accepted 2026-10-30: ECB daily reference rates, nine quote currencies and confirmed backfill start 1999-01-01 where available. Connector not implemented. |
| [005](spec005/README.md) | company-web-traffic | New draft: company/competitor visit estimates, free-first feasibility, optional paid Similarweb access. No connector implemented. |

## Capability boundaries and proposed sequence

Specs 004 and 005 are independent source capabilities. Both depend on the
existing Bronze, source-specific Silver/Gold, audit, replay, Parquet and
warehouse boundaries described in [architecture](../docs/deployment/architecture.md).
Neither pipeline depends on the other. Neither changes AAII semantics.

Suggested sequence for these additions: FX offline slice → bounded ECB
verification → FX operational readiness. Web traffic source feasibility can
proceed independently; acquisition waits for a source with suitable access and
retention rights. There is no new shared-platform rebuild prerequisite.

The user selected **daily official reference rates**, **company/competitor
traffic estimates**, and **prefer free sources; document paid option** on
2026-10-30. The user subsequently confirmed Spec 004's proposed initial FX
scope covers the need; its acceptance record distinguishes settled coverage
from remaining engineering and operational choices. Spec 005's provider/universe
choices remain proposals. No purchase, live acquisition or schedule enablement
is authorized by these documents; no implementation was requested in the scope
confirmation exchange. These future specs do not change the AAII completion scope or
silently reprioritize the existing CFTC/FINRA/OFR backlog.

## Picking up a build

Read the root [agent guidance](../AGENTS.md), [master handoff](../docs/handoffs/project_bootstrap.md)
and the selected numbered spec. Reconcile the current working tree and handoff
before creating a source-specific implementation plan. Keep active AAII tasks in
`tasks/plan.md` and `tasks/todo.md` intact. Use a separate branch/worktree and
source-scoped task files when implementation is authorized; reserve new spec
numbers by checking this directory first.

The [roadmap](../docs/roadmap.md) retains the original source backlog. Its
historical count of 14 additions refers to that original inventory; these two
new research capabilities are additional proposals.
