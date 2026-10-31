from datetime import UTC, date, datetime


def features(versions: list[dict], as_of: str | None = None) -> list[dict]:
    """Select available versions first, then calculate changes across survey dates."""
    if as_of is not None:
        cutoff = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("as-of cutoff requires a timezone")
        as_of = cutoff.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    latest = {}
    for row in sorted(versions, key=lambda r: (r["first_seen_at"], r["version_id"])):
        if as_of is None or row["first_seen_at"] <= as_of:
            latest[row["survey_date"]] = row
    output = []
    prior = None
    for key in sorted(latest):
        row = latest[key]
        spread = (row["bullish"] - row["bearish"]) * 100
        output.append(
            {
                **row,
                "bull_bear_spread_pp": spread,
                "previous_survey_date": prior["survey_date"] if prior else None,
                "gap_days": (
                    date.fromisoformat(key) - date.fromisoformat(prior["survey_date"])
                ).days
                if prior
                else None,
                "spread_change_pp": spread - (prior["bullish"] - prior["bearish"]) * 100
                if prior
                else None,
                "previous_version_id": prior["version_id"] if prior else None,
            }
        )
        prior = row
    return output
