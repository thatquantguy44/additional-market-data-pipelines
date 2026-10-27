# additional-market-data-pipelines

A sister project to `fred-bronze-to-gold-pipeline` for free market data on
positioning, trading activity, and funding conditions. The proposed pipeline uses
the same manifest-driven **Bronze → Silver → Gold** architecture and local-first
development approach.

**Status: specification and repository scaffold. No ingestion code, warehouse,
scheduled jobs, or deployed infrastructure exist yet.**

## Start here

- [Spec 001: Positioning and market structure](specs/spec001/README.md)
- [Source catalog and access considerations](docs/catalog/README.md)
- [Master roadmap and source backlog](docs/roadmap.md)
- [Master handoff and current pickup point](docs/handoffs/project_bootstrap.md)
- [Architecture](docs/deployment/architecture.md)
- [Development and verification](docs/development/README.md)
- [Pinned engineering workflow library](docs/development/agent_library.md)

## Initial scope

Start with CFTC Commitments of Traders positioning. Extend the same pipeline to
FINRA short-sale volume and OFR funding data after the first source is verified.
Company disclosures and insider activity, then a broader mix of free alternative
data, are future phases. Source selection is a research priority; no claim is
made that these datasets have measured low adoption or predictive value.

## Repository layout

```text
additional-market-data-pipelines/
├── config/                  # runtime and feature configuration (reserved)
├── manifests/               # source-specific dataset manifests (reserved)
├── src/market_data_pipeline/ # Python package (reserved)
├── sql/                     # warehouse DDL and research views (reserved)
├── tests/                   # offline unit and integration tests (reserved)
├── resources/               # deployment job definitions (reserved)
├── notebooks/               # platform entrypoints and exploration (reserved)
├── .github/workflows/       # CI workflows (reserved)
├── specs/spec001/           # main pipeline specification
├── docs/
│   ├── catalog/             # source research
│   ├── deployment/          # architecture and future runbooks
│   ├── development/         # workflow and verification
│   ├── dictionary/          # proposed data contracts
│   └── handoffs/            # current pickup point
└── vendor/agent-skills/     # pinned engineering workflow submodule
```

## Getting started

Review Spec 001 before implementation. Reserved directories contain `.gitkeep`
files, not working pipeline components. Planned CLI commands are explicitly
labeled in the spec and are not executable yet.

Initialize the engineering workflow library after cloning:

```bash
git submodule update --init --recursive
```

The repository is independent of the FRED project: no runtime imports, shared
databases, credentials, or deployment configuration are inherited from it.
