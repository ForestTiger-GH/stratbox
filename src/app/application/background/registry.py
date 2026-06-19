from __future__ import annotations

from .models import BackgroundProcessSpec


def build_background_registry() -> tuple[BackgroundProcessSpec, ...]:
    return (
        BackgroundProcessSpec(
            id='monitor_cbr_publications',
            title='Мониторинг публикаций Банка России',
            description='Следит за появлением новых публикаций и создаёт событие в сценарном чате.',
        ),
        BackgroundProcessSpec(
            id='check_workspace_consistency',
            title='Проверка консистентности workspace',
            description='Проверяет базовую структуру рабочего каталога и доступность ключевых папок.',
        ),
        BackgroundProcessSpec(
            id='refresh_cache',
            title='Фоновое обновление кэша',
            description='Готовит данные для быстрых сценариев без ручного запуска.',
        ),
    )
