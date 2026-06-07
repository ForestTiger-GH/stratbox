"""
Примеры запуска домена загрузки исходных файлов Банка России.

Файл является примером использования, а не частью доменной логики.
"""

from stratbox.macrobanks.cbr_file_collector import CbrFileCollectRequest, collect_cbr_files


# ZIP в базовой папке Colab/Jupyter.
result_zip = collect_cbr_files(
    CbrFileCollectRequest(
        target_path="/content/CBR Collected Files.zip",
        save_mode="zip",
        overwrite=True,
        continue_on_error=True,
        retry_attempts=3,
    )
)
print("ZIP output:", result_zip.target_path)
print("Downloaded:", result_zip.success_count)
print("Failed:", result_zip.failure_count)


# Пачка файлов в базовой папке Colab/Jupyter.
# Раскомментировать при необходимости.
# result_files = collect_cbr_files(
#     CbrFileCollectRequest(
#         target_path="/content/CBR Collected Files",
#         save_mode="files",
#         overwrite=True,
#         continue_on_error=True,
#     )
# )
# print("Files output:", result_files.target_path)
# print("Downloaded:", result_files.success_count)
# print("Failed:", result_files.failure_count)
