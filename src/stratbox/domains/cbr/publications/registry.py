"""Logical CBR publication families; physical routes live in profiles."""
from .contracts import SourceSeries

_SOURCES = (
    SourceSeries('cbr.household_lending.mortgage_debt_ind', 'cbr.household_lending', 'Household loan debt', 'rolling', ('xlsx',), 'cbr.route.mortgage_debt_ind', None, None),
    SourceSeries('cbr.household_lending.mortgage_debt', 'cbr.household_lending', 'Mortgage debt', 'rolling', ('xlsx',), 'cbr.route.mortgage_debt', None, None),
    SourceSeries('cbr.household_lending.mortgage_scpa_debt', 'cbr.household_lending', 'Mortgage debt under shared construction agreements', 'rolling', ('xlsx',), 'cbr.route.mortgage_scpa_debt', None, None),
    SourceSeries('cbr.household_lending.mortgage_ihc', 'cbr.household_lending', 'Mortgages for individual housing construction', 'rolling', ('xlsx',), 'cbr.route.mortgage_ihc', None, None),
    SourceSeries('cbr.household_lending.mortgage_full', 'cbr.household_lending', 'Mortgage lending history', 'rolling', ('xlsx',), 'cbr.route.mortgage_full', None, None),
    SourceSeries('cbr.household_lending.mortgage_scpa_full', 'cbr.household_lending', 'Mortgages under shared construction agreements', 'rolling', ('xlsx',), 'cbr.route.mortgage_scpa_full', None, None),
    SourceSeries('cbr.corporate_lending.corp_new_loans_a', 'cbr.corporate_lending', 'Corporate lending by published activity categories', 'rolling', ('xlsx',), 'cbr.route.corp_new_loans_a', None, None),
    SourceSeries('cbr.corporate_lending.corp_new_loans_c', 'cbr.corporate_lending', 'Corporate lending by OKVED2 classes', 'rolling', ('xlsx',), 'cbr.route.corp_new_loans_c', None, None),
    SourceSeries('cbr.corporate_lending.corp_debt_a', 'cbr.corporate_lending', 'Corporate debt by published activity categories', 'rolling', ('xlsx',), 'cbr.route.corp_debt_a', None, None),
    SourceSeries('cbr.corporate_lending.corp_debt_c', 'cbr.corporate_lending', 'Corporate debt by OKVED2 classes', 'rolling', ('xlsx',), 'cbr.route.corp_debt_c', None, None),
    SourceSeries('cbr.corporate_lending.sme_debt', 'cbr.corporate_lending', 'SME loan debt', 'rolling', ('xlsx',), 'cbr.route.sme_debt', None, None),
    SourceSeries('cbr.corporate_lending.sme_debt_activity', 'cbr.corporate_lending', 'SME debt by OKVED2 classes', 'rolling', ('xlsx',), 'cbr.route.sme_debt_activity', None, None),
    SourceSeries('cbr.corporate_lending.sme_debt_subj_f', 'cbr.corporate_lending', 'SME debt by region', 'rolling', ('xlsx',), 'cbr.route.sme_debt_subj_f', None, None),
    SourceSeries('cbr.corporate_lending.sme_debt_subj_i', 'cbr.corporate_lending', 'SME individual entrepreneur debt by region', 'rolling', ('xlsx',), 'cbr.route.sme_debt_subj_i', None, None),
    SourceSeries('cbr.corporate_lending.corp_debt_subj', 'cbr.corporate_lending', 'Corporate debt by region over time', 'rolling', ('xlsx',), 'cbr.route.corp_debt_subj', None, None),
    SourceSeries('cbr.corporate_lending.structure_by_benchmark_interest_rate_type', 'cbr.corporate_lending', 'Corporate debt by benchmark interest rate type', 'rolling', ('xlsx',), 'cbr.route.structure_by_benchmark_interest_rate_type', None, None),
    SourceSeries('cbr.corporate_lending.sme_borrowers_info', 'cbr.corporate_lending', 'SME borrowers and loans', 'rolling', ('xlsx',), 'cbr.route.sme_borrowers_info', None, None),
    SourceSeries('cbr.corporate_lending.sme_by_activity', 'cbr.corporate_lending', 'SME lending by OKVED2 classes', 'rolling', ('xlsx',), 'cbr.route.sme_by_activity', None, None),
    SourceSeries('cbr.securities.debt_securities', 'cbr.securities', 'Debt securities', 'rolling', ('xlsx',), 'cbr.route.debt_securities', None, None),
    SourceSeries('cbr.borrowings.funds_all', 'cbr.borrowings', 'Total borrowed funds', 'rolling', ('xlsx',), 'cbr.route.funds_all', None, None),
    SourceSeries('cbr.borrowings.funds_clients', 'cbr.borrowings', 'Client funds', 'rolling', ('xlsx',), 'cbr.route.funds_clients', None, None),
    SourceSeries('cbr.borrowings.funds_org', 'cbr.borrowings', 'Organization funds', 'rolling', ('xlsx',), 'cbr.route.funds_org', None, None),
    SourceSeries('cbr.borrowings.dep_corp', 'cbr.borrowings', 'Corporate deposits', 'rolling', ('xlsx',), 'cbr.route.dep_corp', None, None),
    SourceSeries('cbr.borrowings.dep_ind', 'cbr.borrowings', 'Household deposits', 'rolling', ('xlsx',), 'cbr.route.dep_ind', None, None),
    SourceSeries('cbr.borrowings.dep_ind_no_escrow', 'cbr.borrowings', 'Household deposits excluding escrow', 'rolling', ('xlsx',), 'cbr.route.dep_ind_no_escrow', None, None),
    SourceSeries('cbr.borrowings.dep_entrepreneur', 'cbr.borrowings', 'Individual entrepreneur deposits', 'rolling', ('xlsx',), 'cbr.route.dep_entrepreneur', None, None),
    SourceSeries('cbr.borrowings.escrow_accounts', 'cbr.borrowings', 'Escrow account balances', 'rolling', ('xlsx',), 'cbr.route.escrow_accounts', None, None),
    SourceSeries('cbr.borrowings.budget_all', 'cbr.borrowings', 'Budget funds', 'rolling', ('xlsx',), 'cbr.route.budget_all', None, None),
    SourceSeries('cbr.household_assets.households_bm', 'cbr.household_assets', 'Household statistics BM', 'rolling', ('xlsx',), 'cbr.route.households_bm', None, None),
    SourceSeries('cbr.household_assets.households_om', 'cbr.household_assets', 'Household statistics OM', 'rolling', ('xlsx',), 'cbr.route.households_om', None, None),
    SourceSeries('cbr.monetary_statistics.monetary_agg', 'cbr.monetary_statistics', 'Monetary aggregates', 'rolling', ('xlsx',), 'cbr.route.monetary_agg', None, None),
    SourceSeries('cbr.monetary_statistics.survey_cb', 'cbr.monetary_statistics', 'Central bank survey', 'rolling', ('xlsx',), 'cbr.route.survey_cb', None, None),
    SourceSeries('cbr.monetary_statistics.balance_odc', 'cbr.monetary_statistics', 'Credit institution balance sheet', 'rolling', ('xlsx',), 'cbr.route.balance_odc', None, None),
    SourceSeries('cbr.monetary_statistics.survey_odc', 'cbr.monetary_statistics', 'Credit institution survey', 'rolling', ('xlsx',), 'cbr.route.survey_odc', None, None),
    SourceSeries('cbr.monetary_statistics.survey_dc_new', 'cbr.monetary_statistics', 'Banking system survey', 'rolling', ('xlsx',), 'cbr.route.survey_dc_new', None, None),
    SourceSeries('cbr.monetary_statistics.annex_survey_dc', 'cbr.monetary_statistics', 'Banking system survey annex', 'rolling', ('xlsx',), 'cbr.route.annex_survey_dc', None, None),
    SourceSeries('cbr.external_debt.debt_new', 'cbr.external_debt', 'External debt', 'rolling', ('xlsx',), 'cbr.route.debt_new', None, None),
    SourceSeries('cbr.external_debt.debt_maturity', 'cbr.external_debt', 'External debt by maturity and instrument', 'rolling', ('xlsx',), 'cbr.route.debt_maturity', None, None),
    SourceSeries('cbr.external_debt.debt_cur-mat_new', 'cbr.external_debt', 'External debt by currency', 'rolling', ('xlsx',), 'cbr.route.debt_cur-mat_new', None, None),
    SourceSeries('cbr.other_statistics.obs_table_20s', 'cbr.other_statistics', 'Publication obs_tabl20s', 'rolling', ('xlsx',), 'cbr.route.obs_table_20s', None, None),
    SourceSeries('cbr.other_statistics.exchange_rate', 'cbr.other_statistics', 'Exchange rate indices', 'rolling', ('xlsx',), 'cbr.route.exchange_rate', None, None),
    SourceSeries('cbr.corporate_lending.sme_ie_debt_activity', 'cbr.corporate_lending', 'SME individual entrepreneur debt by OKVED2 classes', 'rolling', ('xlsx',), 'cbr.route.sme_ie_debt_activity', None, None),
    SourceSeries('cbr.corporate_lending.debt_0105a', 'cbr.corporate_lending', 'Regional corporate debt by activity', 'dated', ('xlsx',), 'cbr.route.debt_0105a', 'cbr.industries.debt.flake.v1', None),
    SourceSeries('cbr.corporate_lending.issuance_0104a', 'cbr.corporate_lending', 'Monthly regional corporate lending by activity', 'dated', ('xlsx',), 'cbr.route.issuance_0104a', 'cbr.industries.issuance.flake.v1', None),
    SourceSeries('cbr.corporate_lending.fd_okved2', 'cbr.corporate_lending', 'Corporate loans by federal district and OKVED2 section', 'dated', ('xlsx',), 'cbr.route.fd_okved2', None, None),
    SourceSeries('cbr.corporate_lending.sme_fd_okved2', 'cbr.corporate_lending', 'SME loans by federal district and OKVED2 section', 'dated', ('xlsx',), 'cbr.route.sme_fd_okved2', None, None),
    SourceSeries('cbr.reporting_forms.f101', 'cbr.reporting_forms', 'Credit institution reporting form 101', 'dated', ('rar', 'zip', 'dbf'), 'cbr.route.form101', 'cbr.forms.dbf_flakes.v1', 'cbr.forms.f101.normalization.v1'),
    SourceSeries('cbr.reporting_forms.f102', 'cbr.reporting_forms', 'Credit institution reporting form 102', 'dated', ('rar', 'zip', 'dbf'), 'cbr.route.form102', 'cbr.forms.dbf_flakes.v1', 'cbr.forms.f102.normalization.v1'),
    SourceSeries('cbr.reporting_forms.f123', 'cbr.reporting_forms', 'Credit institution reporting form 123', 'dated', ('rar', 'zip', 'dbf'), 'cbr.route.form123', 'cbr.forms.dbf_flakes.v1', 'cbr.forms.f123.normalization.v1'),
    SourceSeries('cbr.reporting_forms.f134', 'cbr.reporting_forms', 'Credit institution reporting form 134', 'dated', ('rar', 'zip', 'dbf'), 'cbr.route.form134', 'cbr.forms.dbf_flakes.v1', None),
    SourceSeries('cbr.reporting_forms.f135', 'cbr.reporting_forms', 'Credit institution reporting form 135', 'dated', ('rar', 'zip', 'dbf'), 'cbr.route.form135', 'cbr.forms.dbf_flakes.v1', 'cbr.forms.f135.normalization.v1'),
    SourceSeries('cbr.reporting_forms.f802', 'cbr.reporting_forms', 'Credit institution reporting form 802', 'dated', ('rar', 'zip', 'dbf'), 'cbr.route.form802', 'cbr.forms.dbf_flakes.v1', 'cbr.forms.f802.normalization.v1'),
    SourceSeries('cbr.reporting_forms.f803', 'cbr.reporting_forms', 'Credit institution reporting form 803', 'dated', ('rar', 'zip', 'dbf'), 'cbr.route.form803', 'cbr.forms.dbf_flakes.v1', None),
    SourceSeries('cbr.reporting_forms.f805', 'cbr.reporting_forms', 'Credit institution reporting form 805', 'dated', ('rar', 'zip', 'dbf'), 'cbr.route.form805', 'cbr.forms.dbf_flakes.v1', 'cbr.forms.f805.normalization.v1'),
    SourceSeries('cbr.project_finance.escrow', 'cbr.project_finance', 'Housing project finance and escrow', 'dated', ('xlsx', 'html'), 'cbr.route.escrow', 'cbr.escrow.flake.v1', None),
    SourceSeries('cbr.service_network.bank_offices', 'cbr.service_network', 'Credit institution offices by bank and region', 'capture', ('html',), 'cbr.route.bank_offices', 'cbr.offices.flake.v1', None),
    SourceSeries('cbr.service_network.territorial_offices', 'cbr.service_network', 'Credit institution offices by territory', 'dated', ('xlsx',), 'cbr.route.territorial_offices', 'cbr.territorial_offices.flake.v1', None),
)
_BY_ID = {item.series_id: item for item in _SOURCES}
if len(_BY_ID) != len(_SOURCES):
    raise ValueError("cbr.registry.duplicate_series")

CATALOG_SERIES = {'mortgage_debt_ind': 'cbr.household_lending.mortgage_debt_ind', 'mortgage_debt': 'cbr.household_lending.mortgage_debt', 'mortgage_scpa_debt': 'cbr.household_lending.mortgage_scpa_debt', 'mortgage_ihc': 'cbr.household_lending.mortgage_ihc', 'mortgage_full': 'cbr.household_lending.mortgage_full', 'mortgage_scpa_full': 'cbr.household_lending.mortgage_scpa_full', 'corp_new_loans_a': 'cbr.corporate_lending.corp_new_loans_a', 'corp_new_loans_c': 'cbr.corporate_lending.corp_new_loans_c', 'corp_debt_a': 'cbr.corporate_lending.corp_debt_a', 'corp_debt_c': 'cbr.corporate_lending.corp_debt_c', 'sme_debt': 'cbr.corporate_lending.sme_debt', 'sme_debt_activity': 'cbr.corporate_lending.sme_debt_activity', 'sme_debt_subj_f': 'cbr.corporate_lending.sme_debt_subj_f', 'sme_debt_subj_i': 'cbr.corporate_lending.sme_debt_subj_i', 'corp_debt_subj': 'cbr.corporate_lending.corp_debt_subj', 'structure_by_benchmark_interest_rate_type': 'cbr.corporate_lending.structure_by_benchmark_interest_rate_type', 'sme_borrowers_info': 'cbr.corporate_lending.sme_borrowers_info', 'sme_by_activity': 'cbr.corporate_lending.sme_by_activity', 'debt_securities': 'cbr.securities.debt_securities', 'funds_all': 'cbr.borrowings.funds_all', 'funds_clients': 'cbr.borrowings.funds_clients', 'funds_org': 'cbr.borrowings.funds_org', 'dep_corp': 'cbr.borrowings.dep_corp', 'dep_ind': 'cbr.borrowings.dep_ind', 'dep_ind_no_escrow': 'cbr.borrowings.dep_ind_no_escrow', 'dep_entrepreneur': 'cbr.borrowings.dep_entrepreneur', 'escrow_accounts': 'cbr.borrowings.escrow_accounts', 'budget_all': 'cbr.borrowings.budget_all', 'households_bm': 'cbr.household_assets.households_bm', 'households_om': 'cbr.household_assets.households_om', 'monetary_agg': 'cbr.monetary_statistics.monetary_agg', 'survey_cb': 'cbr.monetary_statistics.survey_cb', 'balance_odc': 'cbr.monetary_statistics.balance_odc', 'survey_odc': 'cbr.monetary_statistics.survey_odc', 'survey_dc_new': 'cbr.monetary_statistics.survey_dc_new', 'annex_survey_dc': 'cbr.monetary_statistics.annex_survey_dc', 'debt_new': 'cbr.external_debt.debt_new', 'debt_maturity': 'cbr.external_debt.debt_maturity', 'debt_cur-mat_new': 'cbr.external_debt.debt_cur-mat_new', 'obs_table_20s': 'cbr.other_statistics.obs_table_20s', 'exchange_rate': 'cbr.other_statistics.exchange_rate', 'sme_ie_debt_activity': 'cbr.corporate_lending.sme_ie_debt_activity'}
DEFAULT_COLLECTION_KEYS = ('mortgage_debt_ind', 'mortgage_debt', 'mortgage_scpa_debt', 'mortgage_ihc', 'mortgage_full', 'mortgage_scpa_full', 'corp_new_loans_a', 'corp_new_loans_c', 'corp_debt_a', 'corp_debt_c', 'sme_debt', 'sme_debt_activity', 'sme_debt_subj_f', 'sme_debt_subj_i', 'corp_debt_subj', 'structure_by_benchmark_interest_rate_type', 'sme_borrowers_info', 'sme_by_activity', 'debt_securities', 'funds_all', 'funds_clients', 'funds_org', 'dep_corp', 'dep_ind', 'dep_ind_no_escrow', 'dep_entrepreneur', 'escrow_accounts', 'budget_all', 'households_bm', 'households_om', 'monetary_agg', 'survey_cb', 'balance_odc', 'survey_odc', 'survey_dc_new', 'annex_survey_dc', 'debt_new', 'debt_maturity', 'debt_cur-mat_new', 'obs_table_20s', 'exchange_rate')
FORM_CODES = ("101", "102", "123", "134", "135", "802", "803", "805")


def all_sources(family_id=None):
    if family_id is not None and family_id not in families():
        raise ValueError("cbr.registry.family_unknown")
    return tuple(item for item in _SOURCES if family_id is None or item.family_id == family_id)


def families():
    return tuple(dict.fromkeys(item.family_id for item in _SOURCES))


def source(series_id):
    try:
        return _BY_ID[series_id]
    except (KeyError, TypeError):
        raise ValueError("cbr.registry.series_unknown") from None


def validate_profiles():
    from .profiles import acquisition_profile, processing_profile
    for item in _SOURCES:
        acquisition_profile(item.acquisition_profile)
        for profile_id in (item.extraction_profile, item.normalization_profile):
            if profile_id is not None:
                profile = processing_profile(profile_id)
                if not set(profile.formats) <= set(item.formats):
                    raise ValueError("cbr.profile.formats_incompatible")
    return True
