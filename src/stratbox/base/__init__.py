"""
base — нейтральный слой инфраструктуры.

Назначение:
- выбрать провайдеры (plugin или local) через runtime
- дать единый транспорт файлов (filestore)
- дать единый доступ к секретам (secrets)
- дать единый API чтения/записи форматов (ioapi)
"""

from stratbox.base import runtime  # noqa: F401