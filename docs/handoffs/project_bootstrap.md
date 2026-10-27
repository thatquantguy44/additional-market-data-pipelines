# Master handoff and current pickup point

Last updated: 2026-10-26.

The user requested a sister repository named
`additional-market-data-pipelines`, beside `fred-bronze-to-gold-pipeline`.
They selected positioning and market structure as the main spec, requested the
same general repository format, and retained disclosures/insider activity and a
broader alternative-data mix for later.

Completed: independent local repository scaffold, Spec 001, official-source
catalog, future-theme roadmap, proposed architecture/data contracts, development
guidance, and pinned workflow library. Application code is not implemented.

The user also requested that every additional source discussed be retained in
the handoff and roadmap. The [master roadmap](../roadmap.md) is the canonical
source backlog, with official references, proposed access methods, research
uses, limitations, and stable backlog IDs for all 13 additions.

## Retained source inventory

Existing Spec 001 sequence: CFTC positioning → FINRA short-sale volume → OFR
Short-term Funding Monitor. SEC fails-to-deliver remains a candidate extension.
See the [source catalog](../catalog/README.md) for those original four sources.

Additional positioning and market-structure candidates:

- `nyfed-primary-dealers`: NY Fed Primary Dealer Statistics.
- `ofr-hedge-fund-monitor`: OFR Hedge Fund Monitor, distinct from STFM.
- `finra-otc-transparency`: FINRA ATS/non-ATS activity, distinct from short-sale
  volume.
- `sec-nmfp`: SEC money-market-fund portfolio holdings.
- `dtcc-public-swaps`: DTCC public swap/security-based-swap dissemination.
- `sec-midas`: SEC Market Structure Analytics / MIDAS published datasets.

Later company/holdings candidates:

- `sec-nport`: SEC fund portfolio holdings, derivatives, and securities lending.
- `fdic-bankfind`: FDIC bank financials, deposits, branches, and history.

Later alternative-data candidates:

- `usda-mymarketnews`: USDA agricultural reports and prices.
- `stb-rail-service`: Surface Transportation Board rail performance.
- `epa-clean-air-markets`: EPA plant emissions and operating data.
- `usace-corps-locks`: USACE vessel movements, lockage times, and delays.
- `usaspending`: Federal awards, recipients, and award transactions.

Company insider filings and filing-event metadata also remain future themes.
The new candidates are a research backlog; connector access and functionality
have not been validated by live extraction.

## Next work

Next: review Spec 001's CFTC-first scope, local SQLite target, availability and
revision semantics, and acceptance criteria. Then follow the pinned workflow's
Plan → Tasks → Implement phases. Keep planned functionality distinct from tested
runtime behavior. No GitHub remote or deployment has been created.

After the initial pipeline slice, the recommended order for the new additions
is NY Fed Primary Dealer Statistics → SEC N-MFP → FINRA ATS/non-ATS → OFR Hedge
Fund Monitor. Keep DTCC and MIDAS queued for later evaluation. This ordering does
not replace Spec 001's CFTC-first sequence.

Use the roadmap's promotion checklist before implementing each candidate:
verify access/terms, coverage and schema, publication/revision semantics, then
capture fixtures and specify acceptance criteria. Preserve provider-specific
grains and original availability timestamps. Update this handoff and the
roadmap when status or priorities change so the same inventory stays visible.
