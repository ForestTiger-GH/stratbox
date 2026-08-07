from __future__ import annotations

PRIMARY_PORTFOLIO_SCOPE = 'CORPORATE_TOTAL'
PORTFOLIO_SCOPES = (
    PRIMARY_PORTFOLIO_SCOPE,
    'SME',
    'SME_IE',
)
PORTFOLIO_SCOPE_ORDER = {scope: index for index, scope in enumerate(PORTFOLIO_SCOPES)}
PORTFOLIO_PARENT_SCOPE = {
    'SME': PRIMARY_PORTFOLIO_SCOPE,
    'SME_IE': 'SME',
}


def validate_portfolio_scopes(scopes: tuple[str, ...] | list[str] | set[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({str(scope) for scope in scopes}, key=PORTFOLIO_SCOPE_ORDER.get))
    unknown = sorted(set(normalized) - set(PORTFOLIO_SCOPES))
    if unknown:
        raise ValueError(f'Unsupported SORS portfolio scopes: {unknown}')
    missing = tuple(scope for scope in PORTFOLIO_SCOPES if scope not in normalized)
    if missing:
        raise ValueError(
            'SORS restoration requires the complete nested portfolio system '
            f'{PORTFOLIO_SCOPES}; missing {missing}'
        )
    return normalized
