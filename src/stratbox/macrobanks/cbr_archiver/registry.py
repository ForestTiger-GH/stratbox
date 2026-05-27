"""
registry — плоский список исходных статистических файлов Банка России.

Этот файл является главным местом ручного пополнения списка ссылок:
- новый источник добавляется в DEFAULT_CBR_ARCHIVE_URLS обычной строкой;
- логика скачивания и сохранения при этом не меняется;
- содержимое самих Excel-файлов домен не редактирует и не переименовывает вручную.
"""

from __future__ import annotations


DEFAULT_ARCHIVE_BASE_NAME = "CBR Collected Files"
DEFAULT_FOLDER_NAME = "CBR Collected Files"
DEFAULT_OUTPUT_BASE_DIR = "/content"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    )
}


DEFAULT_CBR_ARCHIVE_URLS: tuple[str, ...] = (
    # Кредиты физлиц
    "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_05_Debt_ind.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_14_Debt_mortgage.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_18_Debt_scpa_mortgage.xlsx",

    # Ипотека (полные ряды)
    "https://www.cbr.ru/vfs/statistics/banksector/mortgage/02_41_Mortgage_ihc.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_02_Mortgage.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_03_Scpa_mortgage.xlsx",

    # Кредиты корпорациям (полные ряды)
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_A_New_loans_corp_by_activity.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_C_New_loans_corp_by_activity.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_A_Debt_corp_by_activity.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_C_Debt_corp_by_activity.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_Debt_sme.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_F_Debt_sme_by_activity.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_F_Debt_sme_subj.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_I_Debt_sme_subj.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_05_D_Debt_subj.xlsx",
    "https://cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/02_03_Debt_structure_by_benchmark_interest_rate_type.xlsx",
    "https://www.cbr.ru/vfs/statistics/banksector/loans_to_corporations/02_02_SME_Borrowers_info.xlsx",

    # Долговые бумаги
    "https://www.cbr.ru/vfs/statistics/debt_securities/66-debt_securities.xlsx",

    # Средства совокупные
    "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_01_Funds_all.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_02_Funds_clients.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_04_Funds_org.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_05_Dep_corp.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_06_Dep_ind.xlsx",
    "https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_27_Dep_ind_excluding_escrow.xlsx",
    "https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_07_Dep_enterpreneur.xlsx",
    "https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_28_Escrow_accounts.xlsx",
    "https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_29_Budget_all.xlsx",

    # Домашние хозяйства
    "https://cbr.ru/vfs/statistics/households/households_bm.xlsx",
    "https://cbr.ru/vfs/statistics/households/households_om.xlsx",

    # Прочие файлы
    "https://www.cbr.ru/Content/Document/File/115862/obs_tabl20%D1%81.xlsx",
)

# Совместимое старое имя: теперь это тоже простой плоский список строк-URL.
DEFAULT_CBR_ARCHIVE_SOURCES = DEFAULT_CBR_ARCHIVE_URLS


__all__ = [
    "DEFAULT_ARCHIVE_BASE_NAME",
    "DEFAULT_CBR_ARCHIVE_SOURCES",
    "DEFAULT_CBR_ARCHIVE_URLS",
    "DEFAULT_FOLDER_NAME",
    "DEFAULT_HEADERS",
    "DEFAULT_OUTPUT_BASE_DIR",
]
