# Market-data source catalog

Researched against official provider pages on 2026-10-26. These are source
candidates, not implemented connectors. “Under-utilized” is a research theme;
adoption and investment usefulness have not been measured. Free access does not
establish unrestricted redistribution rights. Verify terms for each dataset.

This catalog describes the original four source candidates. The
[master roadmap and source backlog](../roadmap.md) retains all 13 additional
sources discussed, with official links, access methods, potential uses, and
implementation considerations. The [master handoff](../handoffs/project_bootstrap.md)
lists the complete inventory and current priorities. All remain unimplemented.

| Priority | Dataset | Proposed research use | Access evidence | Important limit |
| --- | --- | --- | --- | --- |
| First | CFTC Commitments of Traders, TFF and Disaggregated | Category positioning and changes | CFTC documents a public API generally usable without a token | Report families and futures-only/combined reports differ |
| Next | FINRA short-sale volume | Reported short-trading activity | Public catalog links downloads and a query API; confirm current free automated route before coding | Scope and denominators must match; short volume is not short interest |
| Funding extension | OFR Short-term Funding Monitor | Funding rates and repo conditions | Official API explicitly needs neither tokens nor registration | Review per-series provenance, units, and underlying-source terms |
| Candidate | SEC fails-to-deliver | Settlement-failure balances | Public ZIP downloads of pipe-delimited records | Outstanding balances are not daily flows or proof of abusive shorting |

## CFTC

The reports break down open interest by trader classifications. TFF covers
financial contracts; Disaggregated covers agriculture and natural resources.
Keep these universes and classifications separate. Verify actual API field names,
dataset identifiers, release timing, and corrections during implementation.

Sources: [COT documentation](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm),
[public reporting report families](https://publicreporting.cftc.gov/stories/s/r4w3-av2u),
[user guide](https://publicreporting.cftc.gov/stories/s/COT-Help/p2fg-u73y/).

## FINRA

Retain reporting-facility coverage. Avoid joining a venue-specific numerator to
market-wide volume. Current download availability, automation conditions, and
terms remain an implementation prerequisite; the website catalog alone is not a
validated extraction contract.

Sources: [short-sale volume catalog](https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data),
[interpretation guidance](https://www.finra.org/rules-guidance/notices/information-notice-051019).

## OFR

The STFM API offers metadata discovery and time-series retrieval as JSON at
`https://data.financialresearch.gov/v1`. Start from metadata rather than guessing
series mnemonics. Select measures after checking overlap with existing macro
coverage in the sister project.

Source: [official STFM API documentation](https://www.financialresearch.gov/short-term-funding-monitor/api/).

## SEC settlement failures

The SEC publishes files twice per month with a lag. Preserve both settlement
date and observed availability. Its notes explain that balances include prior
outstanding failures and that fails can arise from long or short sales. The
price field can be missing and refers to the preceding day's close.

Source: [SEC data and field definitions](https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data).

## Connector readiness checklist

Before enabling any provider: verify current endpoints, response fixtures,
pagination/archives, provider identifiers, units, null markers, release schedule,
correction behavior, HTTP limits, authentication, attribution, and usage terms.
Persist that metadata with the manifest. No dataset is production-ready solely
because it appears in this catalog.
