# Current HOW — аналитическое ядро: runtime и сетевой транспорт

**Статус:** ограниченная реконструкция по исходным файлам; **не** полная модель core.  
**Implementation owner:** `ForestTiger-GH/stratbox`. **Source Baseline:** `8459dc58922b7e8df853cf1d9e8131fa9e132580`; diff до исполнения `5cff9157460c2035aa42758b505cce65b7c53f47` не затронул `src/`, `tests/` и `scripts/`.  
**Метод доказательства:** чтение конкретных исходных файлов целиком, без запуска, network calls, проверки установленного пакета или среды.

## Назначение и граница

Ядро предоставляет предметным обработчикам инфраструктурные абстракции `FileStore`, `SecretProvider` и сетевую операцию скачивания байтов. Выбор внешнего runtime provider изолирован в `base.runtime`; предметным модулям доступны `get_filestore()` и `get_secrets()`. Точные среды установки и фактические backend-поставщики **не установлены** данным статическим срезом.

## Загрузка runtime providers

В `base.runtime` определена неизменяемая запись `Providers(filestore, secrets, source)` и процессный кэш `_PROVIDERS`. При первом запросе выбирается обнаруженный совместимый provider bundle либо встроенная локальная композиция; в последующих вызовах используется кэш. `force_reload` инициирует пересборку. В локальной композиции `LocalFileStore` получает опциональный корень из окружения, а чтение секретов выстроено через цепочку окружения и интерактивного ввода. В полном неинтерактивном запуске поведение интерактивного fallback требует отдельной проверки. [Прямая реализация](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/runtime.py).

**Предел достоверности:** статическая ветвящаяся реализация не доказывает наличие, корректность, доступность или выбранное состояние какого-либо стороннего provider в реальной установке. Не следует интерпретировать его как гарантированную возможность.

## HTTP download

`download_bytes` сначала передаёт исходную строку в общий URL-normalizer, при ошибке предварительной нормализации сохраняет исходную строку. Затем выполняет до `retries + 1` HTTP-запросов через `requests.get`, применяя `timeout` и линейный backoff `backoff*(attempt+1)`. Успех требует код 200 и содержимое не меньше `min_bytes_ok` байтов. Возвращает структурированный `DownloadResult(ok, status_code, content, error, final_url, headers)` с `content=None` при окончательном отказе. [Прямая реализация](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py).

**Наблюдаемая граница ошибки:** функция перехватывает исключение URL-нормализации и продолжает с исходным URL. Это часть действительного control flow, но не универсально правильная политика для управляемой среды. Статический анализ не подтверждает сетевой тест и не доказывает конкретные схемы внешних источников. Переписывание URL как общий extension seam остаётся *неизвестным в части выбранного deployment*; текущая реальная реализация принадлежит указанному коду, а не описанию будущего сетевого слоя.

## Репрезентативные пути и ограничения

1. Локальный caller запрашивает `get_filestore()`: создаётся либо возвращается закэшированный локальный runtime context.
2. Предметный downloader вызывает `download_bytes()`: URL normalization → HTTP attempt(s) → `DownloadResult`.
3. При неприемлемом ответе может быть несколько сетевых попыток; caller получает `ok=False` и последний error/status, но не полный trace каждой попытки.
4. В этом срезе **нет** доказанного сквозного run identity, общего operation admission, authoritative source snapshot registry или durable failure journal поверх данного downloader. Это граница исследованного файла, а не доказательство отсутствия таких механизмов во всём продукте.

**Что подлежит пересмотру:** изменение `base/runtime.py`, `base/net/http.py`, соответствующих tests, packaging, deployment configuration или внешних API. Исторические проектные мотивы здесь не реконструируются.

## Pinned neutral runtime, secret and byte IO scope — 2026-10-12

**Source-first, static-only:** Seven frozen core files were read end-to-end and checked against the census Git blob identities. [Runtime provider composition](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/runtime.py) (`SB-SRC-0129`); generic [SecretProvider protocol](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/secrets/base.py), [environment lookup](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/secrets/env.py), [interactive prompt](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/secrets/prompt.py) (`0131–0133`); [byte-oriented FileStore IO](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/ioapi/bytes.py) (`0110`); [provider test](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/tests/unit/test_runtime_providers.py) (`0338`) and [import smoke](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/tests/smoke/test_core_imports.py) (`0331`). This note covers **public-neutral extension contracts only** and no non-public implementation.

The runtime uses a process-level cached provider bundle. In its **local fallback profile**, environment secret lookup is followed by interactive `PromptSecretProvider.get_secret` on missing values. This calls **`getpass.getpass`** and may cache a nonempty reply in memory. The generic `SecretProvider` protocol offers `str | None` but no unattended policy or timeout. A future headless host accidentally taking that interactive path may block or fail where a terminal is absent; this is a *static risk*, not a demonstrated deployed incident. Interactive notebook use is a separate acceptable context. A global provider cache is not proof of per-principal hosted authorization or secret rotation.

The byte IO wrapper delegates `read_bytes/write_bytes` to a supplied FileStore or the resolved default and does not issue any verified published-Artifact receipt. Both inspected smoke tests are narrow: they establish importability or a non-null provider bundle, not noninteractive secret failure handling, credential isolation, authoritative Job outcome or deployment security.

**Verification limit:** no actual secret, installed provider, terminal, network, GUI or host ran; read statuses alone do not close 566 source material-unit dispositions. See [target host HOW](../how/hosting/host-and-client-deployment.md) for the conditional remedy.
