"""
registry — реестр исходных статистических файлов Банка России.

Этот файл является главным местом пополнения списка ссылок:
- новый источник добавляется в DEFAULT_CBR_ARCHIVE_SOURCES;
- логика скачивания и сохранения при этом не меняется;
- содержимое самих Excel-файлов домен не редактирует.
"""

from __future__ import annotations

from stratbox.macrobanks.cbr_archiver.models import CbrArchiveSource


DEFAULT_ARCHIVE_BASE_NAME = "CBR Collected Files"
DEFAULT_FOLDER_NAME = "CBR Collected Files"
DEFAULT_OUTPUT_BASE_DIR = "/content"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    )
}


DEFAULT_CBR_ARCHIVE_SOURCES: tuple[CbrArchiveSource, ...] = (
    # Кредиты физлиц
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_05_Debt_ind.xlsx",
        group="retail_loans",
        code="02_05_Debt_ind",
        title="Кредиты физическим лицам: задолженность",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_14_Debt_mortgage.xlsx",
        group="retail_loans",
        code="02_14_Debt_mortgage",
        title="Ипотечная задолженность физических лиц",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_18_Debt_scpa_mortgage.xlsx",
        group="retail_loans",
        code="02_18_Debt_scpa_mortgage",
        title="Ипотечная задолженность по счетам эскроу/ДДУ",
    ),

    # Ипотека: полные ряды
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/banksector/mortgage/02_41_Mortgage_ihc.xlsx",
        group="mortgage",
        code="02_41_Mortgage_ihc",
        title="Ипотечное жилищное кредитование: полные ряды",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_02_Mortgage.xlsx",
        group="mortgage",
        code="02_02_Mortgage",
        title="Ипотека: выдачи и задолженность",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_03_Scpa_mortgage.xlsx",
        group="mortgage",
        code="02_03_Scpa_mortgage",
        title="Ипотека по договорам участия в долевом строительстве",
    ),

    # Кредиты корпорациям: полные ряды
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_A_New_loans_corp_by_activity.xlsx",
        group="corporate_loans",
        code="01_01_A_New_loans_corp_by_activity",
        title="Новые кредиты корпорациям по видам деятельности",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_C_New_loans_corp_by_activity.xlsx",
        group="corporate_loans",
        code="01_01_C_New_loans_corp_by_activity",
        title="Новые кредиты корпорациям по видам деятельности",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_A_Debt_corp_by_activity.xlsx",
        group="corporate_loans",
        code="01_02_A_Debt_corp_by_activity",
        title="Задолженность корпораций по видам деятельности",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_C_Debt_corp_by_activity.xlsx",
        group="corporate_loans",
        code="01_02_C_Debt_corp_by_activity",
        title="Задолженность корпораций по видам деятельности",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_Debt_sme.xlsx",
        group="corporate_loans",
        code="01_11_Debt_sme",
        title="Задолженность субъектов МСП",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_F_Debt_sme_by_activity.xlsx",
        group="corporate_loans",
        code="01_11_F_Debt_sme_by_activity",
        title="Задолженность субъектов МСП по видам деятельности",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_F_Debt_sme_subj.xlsx",
        group="corporate_loans",
        code="01_13_F_Debt_sme_subj",
        title="Задолженность субъектов МСП по субъектам РФ",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_I_Debt_sme_subj.xlsx",
        group="corporate_loans",
        code="01_13_I_Debt_sme_subj",
        title="Задолженность субъектов МСП по субъектам РФ",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_05_D_Debt_subj.xlsx",
        group="corporate_loans",
        code="01_05_D_Debt_subj",
        title="Задолженность по субъектам РФ",
    ),
    CbrArchiveSource(
        url="https://cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/02_03_Debt_structure_by_benchmark_interest_rate_type.xlsx",
        group="corporate_loans",
        code="02_03_Debt_structure_by_benchmark_interest_rate_type",
        title="Структура задолженности по типу процентной ставки",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/banksector/loans_to_corporations/02_02_SME_Borrowers_info.xlsx",
        group="corporate_loans",
        code="02_02_SME_Borrowers_info",
        title="Информация по заемщикам МСП",
    ),

    # Долговые бумаги
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/debt_securities/66-debt_securities.xlsx",
        group="debt_securities",
        code="66-debt_securities",
        title="Долговые ценные бумаги",
    ),

    # Средства клиентов и бюджета
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_01_Funds_all.xlsx",
        group="funds",
        code="02_01_Funds_all",
        title="Средства клиентов: всего",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_02_Funds_clients.xlsx",
        group="funds",
        code="02_02_Funds_clients",
        title="Средства клиентов",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_04_Funds_org.xlsx",
        group="funds",
        code="02_04_Funds_org",
        title="Средства организаций",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_05_Dep_corp.xlsx",
        group="funds",
        code="02_05_Dep_corp",
        title="Депозиты юридических лиц",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_06_Dep_ind.xlsx",
        group="funds",
        code="02_06_Dep_ind",
        title="Депозиты физических лиц",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_27_Dep_ind_excluding_escrow.xlsx",
        group="funds",
        code="02_27_Dep_ind_excluding_escrow",
        title="Депозиты физических лиц без счетов эскроу",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_07_Dep_enterpreneur.xlsx",
        group="funds",
        code="02_07_Dep_enterpreneur",
        title="Депозиты индивидуальных предпринимателей",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_28_Escrow_accounts.xlsx",
        group="funds",
        code="02_28_Escrow_accounts",
        title="Счета эскроу",
    ),
    CbrArchiveSource(
        url="https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_29_Budget_all.xlsx",
        group="funds",
        code="02_29_Budget_all",
        title="Средства бюджетов",
    ),

    # Домашние хозяйства
    CbrArchiveSource(
        url="https://cbr.ru/vfs/statistics/households/households_bm.xlsx",
        group="households",
        code="households_bm",
        title="Домашние хозяйства: банковские счета/операции",
    ),
    CbrArchiveSource(
        url="https://cbr.ru/vfs/statistics/households/households_om.xlsx",
        group="households",
        code="households_om",
        title="Домашние хозяйства: прочие операции",
    ),

    # Прочие файлы
    CbrArchiveSource(
        url="https://www.cbr.ru/Content/Document/File/115862/obs_tabl20%D1%81.xlsx",
        group="other",
        code="obs_tabl20c",
        title="Обследования: таблица 20с",
        file_name="obs_tabl20с_new.xlsx",
        note="Имя задано явно, чтобы отличать файл от одноименных/старых вариантов.",
    ),
)


__all__ = [
    "DEFAULT_ARCHIVE_BASE_NAME",
    "DEFAULT_CBR_ARCHIVE_SOURCES",
    "DEFAULT_FOLDER_NAME",
    "DEFAULT_HEADERS",
    "DEFAULT_OUTPUT_BASE_DIR",
]
