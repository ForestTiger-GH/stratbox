"""
registries — встроенные справочники/реестры, поставляемые вместе с пакетом.

Цель:
- хранить "сырьё" прямо в репозитории (внутри пакета), чтобы оно было доступно после pip install
- дать простой API чтения (DataFrame) без внешних ссылок и без сетевых скачиваний
"""

from stratbox.registries import cbr_banks, rosstat_okved2

__all__ = ["cbr_banks", "rosstat_okved2"]
