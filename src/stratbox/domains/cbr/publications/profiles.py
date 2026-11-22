"""Official acquisition defaults, separate from logical publication identities."""
from .contracts import AcquisitionProfile, ProcessingProfile

_PROFILES = (
    AcquisitionProfile('cbr.route.mortgage_debt_ind', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_05_Debt_ind.xlsx', None),
    AcquisitionProfile('cbr.route.mortgage_debt', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_14_Debt_mortgage.xlsx', None),
    AcquisitionProfile('cbr.route.mortgage_scpa_debt', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_18_Debt_scpa_mortgage.xlsx', None),
    AcquisitionProfile('cbr.route.mortgage_ihc', 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/mortgage/02_41_Mortgage_ihc.xlsx', None),
    AcquisitionProfile('cbr.route.mortgage_full', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_02_Mortgage.xlsx', None),
    AcquisitionProfile('cbr.route.mortgage_scpa_full', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_03_Scpa_mortgage.xlsx', None),
    AcquisitionProfile('cbr.route.corp_new_loans_a', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_A_New_loans_corp_by_activity.xlsx', None),
    AcquisitionProfile('cbr.route.corp_new_loans_c', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_C_New_loans_corp_by_activity.xlsx', None),
    AcquisitionProfile('cbr.route.corp_debt_a', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_A_Debt_corp_by_activity.xlsx', None),
    AcquisitionProfile('cbr.route.corp_debt_c', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_C_Debt_corp_by_activity.xlsx', None),
    AcquisitionProfile('cbr.route.sme_debt', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_Debt_sme.xlsx', None),
    AcquisitionProfile('cbr.route.sme_debt_activity', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_F_Debt_sme_by_activity.xlsx', None),
    AcquisitionProfile('cbr.route.sme_debt_subj_f', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_F_Debt_sme_subj.xlsx', None),
    AcquisitionProfile('cbr.route.sme_debt_subj_i', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_I_Debt_sme_subj.xlsx', None),
    AcquisitionProfile('cbr.route.corp_debt_subj', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_05_D_Debt_subj.xlsx', None),
    AcquisitionProfile('cbr.route.structure_by_benchmark_interest_rate_type', 'fixed', 'https://cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/02_03_Debt_structure_by_benchmark_interest_rate_type.xlsx', None),
    AcquisitionProfile('cbr.route.sme_borrowers_info', 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/loans_to_corporations/02_02_SME_Borrowers_info.xlsx', None),
    AcquisitionProfile('cbr.route.sme_by_activity', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_10_F_New_loans_sme_by_activity.xlsx', None),
    AcquisitionProfile('cbr.route.debt_securities', 'fixed', 'https://www.cbr.ru/vfs/statistics/debt_securities/66-debt_securities.xlsx', None),
    AcquisitionProfile('cbr.route.funds_all', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_01_Funds_all.xlsx', None),
    AcquisitionProfile('cbr.route.funds_clients', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_02_Funds_clients.xlsx', None),
    AcquisitionProfile('cbr.route.funds_org', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_04_Funds_org.xlsx', None),
    AcquisitionProfile('cbr.route.dep_corp', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_05_Dep_corp.xlsx', None),
    AcquisitionProfile('cbr.route.dep_ind', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_06_Dep_ind.xlsx', None),
    AcquisitionProfile('cbr.route.dep_ind_no_escrow', 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_27_Dep_ind_excluding_escrow.xlsx', None),
    AcquisitionProfile('cbr.route.dep_entrepreneur', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_07_Dep_enterpreneur.xlsx', None),
    AcquisitionProfile('cbr.route.escrow_accounts', 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_28_Escrow_accounts.xlsx', None),
    AcquisitionProfile('cbr.route.budget_all', 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_29_Budget_all.xlsx', None),
    AcquisitionProfile('cbr.route.households_bm', 'fixed', 'https://cbr.ru/vfs/statistics/households/households_bm.xlsx', None),
    AcquisitionProfile('cbr.route.households_om', 'fixed', 'https://cbr.ru/vfs/statistics/households/households_om.xlsx', None),
    AcquisitionProfile('cbr.route.monetary_agg', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/monetary_agg.xlsx', None),
    AcquisitionProfile('cbr.route.survey_cb', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/survey_cb.xlsx', None),
    AcquisitionProfile('cbr.route.balance_odc', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/balance_odc.xlsx', None),
    AcquisitionProfile('cbr.route.survey_odc', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/survey_odc.xlsx', None),
    AcquisitionProfile('cbr.route.survey_dc_new', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/survey_dc_new.xlsx', None),
    AcquisitionProfile('cbr.route.annex_survey_dc', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/annex_survey_dc.xlsx', None),
    AcquisitionProfile('cbr.route.debt_new', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_new.xlsx', None),
    AcquisitionProfile('cbr.route.debt_maturity', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_maturity.xlsx', None),
    AcquisitionProfile('cbr.route.debt_cur-mat_new', 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_cur-mat_new.xlsx', None),
    AcquisitionProfile('cbr.route.obs_table_20s', 'fixed', 'https://www.cbr.ru/Content/Document/File/115862/obs_tabl20%D1%81.xlsx', None),
    AcquisitionProfile('cbr.route.exchange_rate', 'fixed', 'https://cbr.ru/vfs/statistics/credit_statistics/ex_rate_ind/exchange_rate.xlsx', None),
    AcquisitionProfile('cbr.route.sme_ie_debt_activity', 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_I_Debt_ie_by_activity.xlsx', None),
    AcquisitionProfile('cbr.route.debt_0105a', 'index', 'https://www.cbr.ru/statistics/bank_sector/sors/', '01_05_A_Debt_corp_(?P<date>\\d{8})\\.xlsx'),
    AcquisitionProfile('cbr.route.issuance_0104a', 'index', 'https://www.cbr.ru/statistics/bank_sector/sors/', '01_04_A_New_loans_corp_(?P<date>\\d{8})\\.xlsx'),
    AcquisitionProfile('cbr.route.fd_okved2', 'index', 'https://www.cbr.ru/statistics/bank_sector/sors/', '01_03_C_Loans_corp_by_fd_activity_(?P<date>\\d{8})\\.xlsx'),
    AcquisitionProfile('cbr.route.sme_fd_okved2', 'index', 'https://www.cbr.ru/statistics/bank_sector/sors/', '01_12_A_Loans_sme_by_fd_activity_(?P<date>\\d{8})\\.xlsx'),
    AcquisitionProfile('cbr.route.form101', 'index', 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/', '101-(?P<date>\\d{8})\\.(?:rar|zip)'),
    AcquisitionProfile('cbr.route.form102', 'index', 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/', '102-(?P<date>\\d{8})\\.(?:rar|zip)'),
    AcquisitionProfile('cbr.route.form123', 'index', 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/', '123-(?P<date>\\d{8})\\.(?:rar|zip)'),
    AcquisitionProfile('cbr.route.form134', 'index', 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/', '134-(?P<date>\\d{8})\\.(?:rar|zip)'),
    AcquisitionProfile('cbr.route.form135', 'index', 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/', '135-(?P<date>\\d{8})\\.(?:rar|zip)'),
    AcquisitionProfile('cbr.route.form802', 'index', 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/', '802-(?P<date>\\d{8})\\.(?:rar|zip)'),
    AcquisitionProfile('cbr.route.form803', 'index', 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/', '803-(?P<date>\\d{8})\\.(?:rar|zip)'),
    AcquisitionProfile('cbr.route.form805', 'index', 'https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/', '805-(?P<date>\\d{8})\\.(?:rar|zip)'),
    AcquisitionProfile('cbr.route.escrow', 'escrow_index', 'https://www.cbr.ru/statistics/bank_sector/equity_const_financing/', None),
    AcquisitionProfile('cbr.route.bank_offices', 'page', 'https://www.cbr.ru/banking_sector/credit/cstat/', None),
    AcquisitionProfile('cbr.route.territorial_offices', 'territorial_index', 'https://www.cbr.ru/statistics/bank_sector/lic/', None),
)
_BY_ID = {item.profile_id: item for item in _PROFILES}


def acquisition_profile(profile_id):
    try:
        return _BY_ID[profile_id]
    except (KeyError, TypeError):
        raise ValueError("cbr.profile.acquisition_unknown") from None


_PROCESSING = (
    ProcessingProfile("cbr.forms.dbf_flakes.v1", "cbr.forms.extract", ("rar", "zip", "dbf"),
                      "All regular members are retained; classic text DBF dialects are decoded explicitly."),
    ProcessingProfile("cbr.escrow.flake.v1", "cbr.escrow.parse", ("xlsx",),
                      "Reviewed regional workbook layouts; historical HTML remains an original-only variant.", 3),
    ProcessingProfile("cbr.industries.debt.flake.v1", "cbr.industries.0105a.parse", ("xlsx",),
                      "Regional corporate debt and overdue debt at the publication reference date.", 3),
    ProcessingProfile("cbr.industries.issuance.flake.v1", "cbr.industries.0104a.parse", ("xlsx",),
                      "Monthly loan issuance with distinct publication and observation periods.", 3),
    ProcessingProfile("cbr.offices.flake.v1", "cbr.offices.parse", ("html",),
                      "Bank-by-region office counts with separate capture and official reference dates."),
    ProcessingProfile("cbr.territorial_offices.flake.v1", "cbr.offices_reg.parse", ("xlsx",),
                      "Explicitly selected territorial blocks with ambiguity and formula evidence.", 3),
) + tuple(ProcessingProfile(f"cbr.forms.f{code}.normalization.v1", "cbr.forms.normalize", ("rar", "zip", "dbf"),
                            f"Modeled form {code}; physical field selection and financial normalization are explicit.")
          for code in ("101", "102", "123", "135", "802", "805"))
_PROCESSING_BY_ID = {item.profile_id: item for item in _PROCESSING}


def processing_profile(profile_id):
    try:
        return _PROCESSING_BY_ID[profile_id]
    except (KeyError, TypeError):
        raise ValueError("cbr.profile.processing_unknown") from None
