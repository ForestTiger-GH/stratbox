"""The explicit Bank of Russia catalog: source facts, methods and numerical purposes."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import DomainSpec
from stratbox.domains.cbr.common.access import CBR_ACCESS
from stratbox.domains.cbr.calculations.sors import SORS
from stratbox.domains.cbr.calculations.sors.catalog import SORS_WORKBOOK, SORS_CROSSWALK
from stratbox.domains.cbr.calculations.catalog import DEBT_APK, ISSUANCE_APK, FORM_101, FORM_102, FORM_123, FORM_134, FORM_135, FORM_802, FORM_803, FORM_805
from stratbox.domains.cbr.products.specifications import ESCROW_HISTORY, FORM_WORKBOOK, INDUSTRY_WORKBOOK, OFFICE_TABLE, STATISTICAL_TABLE
from stratbox.domains.cbr.series.banking_sector_structure import OBS_TABLE_20S
from stratbox.domains.cbr.series.corporate_lending import CORP_DEBT_A, CORP_DEBT_C, CORP_DEBT_SUBJ, CORP_NEW_LOANS_A, CORP_NEW_LOANS_C, DEBT_0105A, FD_OKVED2, ISSUANCE_0104A, SME_BORROWERS_INFO, SME_BY_ACTIVITY, SME_DEBT, SME_DEBT_ACTIVITY, SME_DEBT_SUBJ_F, SME_DEBT_SUBJ_I, SME_FD_OKVED2, SME_IE_DEBT_ACTIVITY, STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE
from stratbox.domains.cbr.series.exchange_rates import EXCHANGE_RATE
from stratbox.domains.cbr.series.external_debt import DEBT_CUR_MAT_NEW, DEBT_MATURITY, DEBT_NEW
from stratbox.domains.cbr.series.funding import BUDGET_ALL, DEP_CORP, DEP_ENTREPRENEUR, DEP_IND, DEP_IND_NO_ESCROW, ESCROW_ACCOUNTS, FUNDS_ALL, FUNDS_CLIENTS, FUNDS_ORG
from stratbox.domains.cbr.series.household_finance import HOUSEHOLDS_BM, HOUSEHOLDS_OM
from stratbox.domains.cbr.series.household_lending import MORTGAGE_DEBT, MORTGAGE_DEBT_IND, MORTGAGE_FULL, MORTGAGE_IHC, MORTGAGE_SCPA_DEBT, MORTGAGE_SCPA_FULL
from stratbox.domains.cbr.series.monetary_statistics import ANNEX_SURVEY_DC, BALANCE_ODC, MONETARY_AGG, SURVEY_CB, SURVEY_DC_NEW, SURVEY_ODC
from stratbox.domains.cbr.series.project_finance import ESCROW
from stratbox.domains.cbr.series.reporting_forms import F101, F102, F123, F134, F135, F802, F803, F805
from stratbox.domains.cbr.series.securities import DEBT_SECURITIES
from stratbox.domains.cbr.series.service_network import BANK_OFFICES, TERRITORIAL_OFFICES

DOMAIN = DomainSpec(
    id="cbr",
    common=MappingProxyType({"access": CBR_ACCESS}),
    series=MappingProxyType({
        OBS_TABLE_20S.id: OBS_TABLE_20S,
        CORP_DEBT_A.id: CORP_DEBT_A,
        CORP_DEBT_C.id: CORP_DEBT_C,
        CORP_DEBT_SUBJ.id: CORP_DEBT_SUBJ,
        CORP_NEW_LOANS_A.id: CORP_NEW_LOANS_A,
        CORP_NEW_LOANS_C.id: CORP_NEW_LOANS_C,
        DEBT_0105A.id: DEBT_0105A,
        FD_OKVED2.id: FD_OKVED2,
        ISSUANCE_0104A.id: ISSUANCE_0104A,
        SME_BORROWERS_INFO.id: SME_BORROWERS_INFO,
        SME_BY_ACTIVITY.id: SME_BY_ACTIVITY,
        SME_DEBT.id: SME_DEBT,
        SME_DEBT_ACTIVITY.id: SME_DEBT_ACTIVITY,
        SME_DEBT_SUBJ_F.id: SME_DEBT_SUBJ_F,
        SME_DEBT_SUBJ_I.id: SME_DEBT_SUBJ_I,
        SME_FD_OKVED2.id: SME_FD_OKVED2,
        SME_IE_DEBT_ACTIVITY.id: SME_IE_DEBT_ACTIVITY,
        STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE.id: STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE,
        EXCHANGE_RATE.id: EXCHANGE_RATE,
        DEBT_CUR_MAT_NEW.id: DEBT_CUR_MAT_NEW,
        DEBT_MATURITY.id: DEBT_MATURITY,
        DEBT_NEW.id: DEBT_NEW,
        BUDGET_ALL.id: BUDGET_ALL,
        DEP_CORP.id: DEP_CORP,
        DEP_ENTREPRENEUR.id: DEP_ENTREPRENEUR,
        DEP_IND.id: DEP_IND,
        DEP_IND_NO_ESCROW.id: DEP_IND_NO_ESCROW,
        ESCROW_ACCOUNTS.id: ESCROW_ACCOUNTS,
        FUNDS_ALL.id: FUNDS_ALL,
        FUNDS_CLIENTS.id: FUNDS_CLIENTS,
        FUNDS_ORG.id: FUNDS_ORG,
        HOUSEHOLDS_BM.id: HOUSEHOLDS_BM,
        HOUSEHOLDS_OM.id: HOUSEHOLDS_OM,
        MORTGAGE_DEBT.id: MORTGAGE_DEBT,
        MORTGAGE_DEBT_IND.id: MORTGAGE_DEBT_IND,
        MORTGAGE_FULL.id: MORTGAGE_FULL,
        MORTGAGE_IHC.id: MORTGAGE_IHC,
        MORTGAGE_SCPA_DEBT.id: MORTGAGE_SCPA_DEBT,
        MORTGAGE_SCPA_FULL.id: MORTGAGE_SCPA_FULL,
        ANNEX_SURVEY_DC.id: ANNEX_SURVEY_DC,
        BALANCE_ODC.id: BALANCE_ODC,
        MONETARY_AGG.id: MONETARY_AGG,
        SURVEY_CB.id: SURVEY_CB,
        SURVEY_DC_NEW.id: SURVEY_DC_NEW,
        SURVEY_ODC.id: SURVEY_ODC,
        ESCROW.id: ESCROW,
        F101.id: F101,
        F102.id: F102,
        F123.id: F123,
        F134.id: F134,
        F135.id: F135,
        F802.id: F802,
        F803.id: F803,
        F805.id: F805,
        DEBT_SECURITIES.id: DEBT_SECURITIES,
        BANK_OFFICES.id: BANK_OFFICES,
        TERRITORIAL_OFFICES.id: TERRITORIAL_OFFICES,
    }),
    calculations=MappingProxyType({
        SORS.id: SORS,
        SORS_CROSSWALK.id: SORS_CROSSWALK,
        DEBT_APK.id: DEBT_APK, ISSUANCE_APK.id: ISSUANCE_APK,
        FORM_101.id: FORM_101, FORM_102.id: FORM_102, FORM_123.id: FORM_123,
        FORM_134.id: FORM_134, FORM_135.id: FORM_135, FORM_802.id: FORM_802,
        FORM_803.id: FORM_803, FORM_805.id: FORM_805,
    }),
    products=MappingProxyType({
        SORS_WORKBOOK.id: SORS_WORKBOOK,
        ESCROW_HISTORY.id: ESCROW_HISTORY, FORM_WORKBOOK.id: FORM_WORKBOOK,
        INDUSTRY_WORKBOOK.id: INDUSTRY_WORKBOOK, OFFICE_TABLE.id: OFFICE_TABLE,
        STATISTICAL_TABLE.id: STATISTICAL_TABLE,
    }),
)
