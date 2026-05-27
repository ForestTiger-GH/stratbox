"""
Примеры запуска cbr_archiver.

Файл является примером использования, а не частью доменной логики.
"""

from stratbox.macrobanks.cbr_archiver import run_cbr_archiver


# ZIP в базовой папке Colab/Jupyter.
result_zip = run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
)
print("ZIP output:", result_zip.output_path)
print("Downloaded:", result_zip.downloaded_count)
print("Failed:", result_zip.failed_count)


# Пачка файлов в базовой папке Colab/Jupyter.
# Раскомментировать при необходимости.
# result_files = run_cbr_archiver(
#     out_path="/content",
#     output_mode="files",
# )
# print("Files output:", result_files.output_path)
# print("Downloaded:", result_files.downloaded_count)
# print("Failed:", result_files.failed_count)


# Пример сохранения ZIP на сетевой диск через активный FileStore.
# Путь нужно заменить на фактический каталог пользователя.
# result_network = run_cbr_archiver(
#     out_path="DSR/ЦМиРАП/CBR",
#     output_mode="zip",
# )
# print("Network output:", result_network.output_path)
