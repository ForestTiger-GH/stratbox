"""
registry — жёсткий встроенный реестр исходных статистических файлов Банка России.

Новые источники добавляются сюда как отдельные элементы реестра. Домен скачивает
их как есть и не занимается предобработкой содержимого файлов.
"""

from __future__ import annotations

from stratbox.macrobanks.cbr_archiver.contracts import CbrRegistryItem


DEFAULT_CBR_TARGET_ARCHIVE_NAME = "CBR Collected Files.zip"
DEFAULT_CBR_TARGET_DIRECTORY_NAME = "CBR Collected Files"
DEFAULT_OUTPUT_BASE_DIR = "/content"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    )
}


DEFAULT_CBR_SOURCES: tuple[CbrRegistryItem, ...] = (
    # Кредиты физлиц
    CbrRegistryItem("mortgage_debt_ind", "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_05_Debt_ind.xlsx", "Кредиты физлиц: задолженность"),
    CbrRegistryItem("mortgage_debt", "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_14_Debt_mortgage.xlsx", "Ипотека: задолженность"),
    CbrRegistryItem("mortgage_scpa_debt", "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_18_Debt_scpa_mortgage.xlsx", "Ипотека: задолженность по ДДУ"),

    # Ипотека (полные ряды)
    CbrRegistryItem("mortgage_ihc", "https://www.cbr.ru/vfs/statistics/banksector/mortgage/02_41_Mortgage_ihc.xlsx", "Ипотека: жильё в строящихся домах"),
    CbrRegistryItem("mortgage_full", "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_02_Mortgage.xlsx", "Ипотека: полный ряд"),
    CbrRegistryItem("mortgage_scpa_full", "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_03_Scpa_mortgage.xlsx", "Ипотека: ДДУ полный ряд"),

    # Кредиты корпорациям (полные ряды)
    CbrRegistryItem("corp_new_loans_a", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_A_New_loans_corp_by_activity.xlsx", "Корпорации: новые кредиты A"),
    CbrRegistryItem("corp_new_loans_c", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_C_New_loans_corp_by_activity.xlsx", "Корпорации: новые кредиты C"),
    CbrRegistryItem("corp_debt_a", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_A_Debt_corp_by_activity.xlsx", "Корпорации: долг A"),
    CbrRegistryItem("corp_debt_c", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_C_Debt_corp_by_activity.xlsx", "Корпорации: долг C"),
    CbrRegistryItem("sme_debt", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_Debt_sme.xlsx", "МСП: долг"),
    CbrRegistryItem("sme_debt_activity", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_F_Debt_sme_by_activity.xlsx", "МСП: долг по видам деятельности"),
    CbrRegistryItem("sme_debt_subj_f", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_F_Debt_sme_subj.xlsx", "МСП: долг по субъектам F"),
    CbrRegistryItem("sme_debt_subj_i", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_I_Debt_sme_subj.xlsx", "МСП: долг по субъектам I"),
    CbrRegistryItem("corp_debt_subj", "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_05_D_Debt_subj.xlsx", "Корпорации: долг по субъектам"),
    CbrRegistryItem("debt_structure_benchmark_rate", "https://cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/02_03_Debt_structure_by_benchmark_interest_rate_type.xlsx", "Структура долга по типу бенчмарк-ставки"),
    CbrRegistryItem("sme_borrowers_info", "https://www.cbr.ru/vfs/statistics/banksector/loans_to_corporations/02_02_SME_Borrowers_info.xlsx", "МСП: сведения о заёмщиках"),

    # Долговые бумаги
    CbrRegistryItem("debt_securities", "https://www.cbr.ru/vfs/statistics/debt_securities/66-debt_securities.xlsx", "Долговые ценные бумаги"),

    # Средства совокупные
    CbrRegistryItem("funds_all", "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_01_Funds_all.xlsx", "Средства совокупные"),
    CbrRegistryItem("funds_clients", "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_02_Funds_clients.xlsx", "Средства клиентов"),
    CbrRegistryItem("funds_org", "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_04_Funds_org.xlsx", "Средства организаций"),
    CbrRegistryItem("dep_corp", "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_05_Dep_corp.xlsx", "Депозиты корпораций"),
    CbrRegistryItem("dep_ind", "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_06_Dep_ind.xlsx", "Депозиты физлиц"),
    CbrRegistryItem("dep_ind_no_escrow", "https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_27_Dep_ind_excluding_escrow.xlsx", "Депозиты физлиц без escrow"),
    CbrRegistryItem("dep_entrepreneur", "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_07_Dep_enterpreneur.xlsx", "Депозиты ИП"),
    CbrRegistryItem("escrow_accounts", "https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_28_Escrow_accounts.xlsx", "Счета эскроу"),
    CbrRegistryItem("budget_all", "https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_29_Budget_all.xlsx", "Средства бюджетов"),

    # Домашние хозяйства
    CbrRegistryItem("households_bm", "https://cbr.ru/vfs/statistics/households/households_bm.xlsx", "Домохозяйства BM"),
    CbrRegistryItem("households_om", "https://cbr.ru/vfs/statistics/households/households_om.xlsx", "Домохозяйства OM"),

    # Прочие файлы
    CbrRegistryItem("obs_table_20s", "https://www.cbr.ru/Content/Document/File/115862/obs_tabl20%D1%81.xlsx", "Таблица obs_tabl20с"),
    CbrRegistryItem("exchange_rate", "https://cbr.ru/vfs/statistics/credit_statistics/ex_rate_ind/exchange_rate.xlsx", "Курс валют"),
)


__all__ = [
    "DEFAULT_CBR_SOURCES",
    "DEFAULT_CBR_TARGET_ARCHIVE_NAME",
    "DEFAULT_CBR_TARGET_DIRECTORY_NAME",
    "DEFAULT_HEADERS",
    "DEFAULT_OUTPUT_BASE_DIR",
]
