"""Named convenience selections; a collection is not a statistical family."""
from dataclasses import dataclass
from .catalog import source


@dataclass(frozen=True, slots=True)
class CollectionProfile:
    profile_id: str
    series_ids: tuple[str, ...]
    description: str


CATALOG_SERIES = {'mortgage_debt_ind': 'cbr.household_lending.mortgage_debt_ind',
 'mortgage_debt': 'cbr.household_lending.mortgage_debt',
 'mortgage_scpa_debt': 'cbr.household_lending.mortgage_scpa_debt',
 'mortgage_ihc': 'cbr.household_lending.mortgage_ihc',
 'mortgage_full': 'cbr.household_lending.mortgage_full',
 'mortgage_scpa_full': 'cbr.household_lending.mortgage_scpa_full',
 'corp_new_loans_a': 'cbr.corporate_lending.corp_new_loans_a',
 'corp_new_loans_c': 'cbr.corporate_lending.corp_new_loans_c',
 'corp_debt_a': 'cbr.corporate_lending.corp_debt_a',
 'corp_debt_c': 'cbr.corporate_lending.corp_debt_c',
 'sme_debt': 'cbr.corporate_lending.sme_debt',
 'sme_debt_activity': 'cbr.corporate_lending.sme_debt_activity',
 'sme_debt_subj_f': 'cbr.corporate_lending.sme_debt_subj_f',
 'sme_debt_subj_i': 'cbr.corporate_lending.sme_debt_subj_i',
 'corp_debt_subj': 'cbr.corporate_lending.corp_debt_subj',
 'structure_by_benchmark_interest_rate_type': 'cbr.corporate_lending.structure_by_benchmark_interest_rate_type',
 'sme_borrowers_info': 'cbr.corporate_lending.sme_borrowers_info',
 'sme_by_activity': 'cbr.corporate_lending.sme_by_activity',
 'debt_securities': 'cbr.securities.debt_securities',
 'funds_all': 'cbr.funding.funds_all',
 'funds_clients': 'cbr.funding.funds_clients',
 'funds_org': 'cbr.funding.funds_org',
 'dep_corp': 'cbr.funding.dep_corp',
 'dep_ind': 'cbr.funding.dep_ind',
 'dep_ind_no_escrow': 'cbr.funding.dep_ind_no_escrow',
 'dep_entrepreneur': 'cbr.funding.dep_entrepreneur',
 'escrow_accounts': 'cbr.funding.escrow_accounts',
 'budget_all': 'cbr.funding.budget_all',
 'households_bm': 'cbr.household_finance.households_bm',
 'households_om': 'cbr.household_finance.households_om',
 'monetary_agg': 'cbr.monetary_statistics.monetary_agg',
 'survey_cb': 'cbr.monetary_statistics.survey_cb',
 'balance_odc': 'cbr.monetary_statistics.balance_odc',
 'survey_odc': 'cbr.monetary_statistics.survey_odc',
 'survey_dc_new': 'cbr.monetary_statistics.survey_dc_new',
 'annex_survey_dc': 'cbr.monetary_statistics.annex_survey_dc',
 'debt_new': 'cbr.external_debt.debt_new',
 'debt_maturity': 'cbr.external_debt.debt_maturity',
 'debt_cur-mat_new': 'cbr.external_debt.debt_cur-mat_new',
 'obs_table_20s': 'cbr.banking_sector_structure.obs_table_20s',
 'exchange_rate': 'cbr.exchange_rates.exchange_rate',
 'sme_ie_debt_activity': 'cbr.corporate_lending.sme_ie_debt_activity'}
DEFAULT_COLLECTION_KEYS = ('mortgage_debt_ind',
 'mortgage_debt',
 'mortgage_scpa_debt',
 'mortgage_ihc',
 'mortgage_full',
 'mortgage_scpa_full',
 'corp_new_loans_a',
 'corp_new_loans_c',
 'corp_debt_a',
 'corp_debt_c',
 'sme_debt',
 'sme_debt_activity',
 'sme_debt_subj_f',
 'sme_debt_subj_i',
 'corp_debt_subj',
 'structure_by_benchmark_interest_rate_type',
 'sme_borrowers_info',
 'sme_by_activity',
 'debt_securities',
 'funds_all',
 'funds_clients',
 'funds_org',
 'dep_corp',
 'dep_ind',
 'dep_ind_no_escrow',
 'dep_entrepreneur',
 'escrow_accounts',
 'budget_all',
 'households_bm',
 'households_om',
 'monetary_agg',
 'survey_cb',
 'balance_odc',
 'survey_odc',
 'survey_dc_new',
 'annex_survey_dc',
 'debt_new',
 'debt_maturity',
 'debt_cur-mat_new',
 'obs_table_20s',
 'exchange_rate')
DEFAULT_COLLECTION = CollectionProfile("cbr.selection.statistical_workbooks.v1",
    tuple(CATALOG_SERIES[key] for key in DEFAULT_COLLECTION_KEYS),
    "The selected rolling statistical workbooks; publication coverage is explicit and bounded.")


def collection_profile(profile_id=DEFAULT_COLLECTION.profile_id):
    if profile_id != DEFAULT_COLLECTION.profile_id:
        raise ValueError("cbr.selection.profile_unknown")
    return DEFAULT_COLLECTION


def resolve_series(selection):
    """Resolve an explicit logical series or the short key of a named selection."""
    return source(CATALOG_SERIES.get(selection, selection))


def select_publication(request):
    """Require one logical candidate and one physical route without guessing."""
    from dataclasses import replace
    candidates = tuple(item for item in request.inventory.assets
        if (request.issue_id is None or item.issue_id == request.issue_id)
        and (request.format is None or item.format == request.format) and item.asset_id == request.asset_id)
    if request.url is not None:
        candidates = tuple(replace(item, url=request.url, alternative_urls=()) for item in candidates
                           if request.url in (item.url, *item.alternative_urls))
    if not candidates:
        raise ValueError("cbr.selection.publication_missing")
    if len(candidates) != 1 or candidates[0].alternative_urls:
        raise ValueError("cbr.selection.publication_ambiguous")
    selected = candidates[0]
    if selected.series_id != request.inventory.series_id:
        raise ValueError("cbr.selection.series_mismatch")
    return selected
