# Strategy Box — единая архитектура кастомизации и наборов стилей артефактов

**Research branch:** вторая ветка исследований Strategy Box / 02-base-study  
**Дата:** 2026-10-07  
**Scope:** stratbox core, stratbox-windows surface, будущий stratbox-android, generic plugin boundary, artifact/report generation  
**Статус:** Research Result — целевая архитектура кастомизации; обратная совместимость с текущими style/preset contracts не требуется  
**Важно:** документ описывает только нейтральные публичные контракты и не содержит сведений о реализации какого-либо закрытого корпоративного расширения.

---

# 0. Краткий вывод

Кастомизацию Strategy Box стоит разделить на несколько независимых сущностей, а затем свести их через один понятный resolution path.

Главное архитектурное разведение:

~~~text
Plugin
    ≠
ArtifactStyleSet
    ≠
InterfaceTheme
    ≠
ArtifactMetadata
~~~

Плагин — контейнер возможностей. Он может добавлять источники, infrastructure capabilities, операции, настройки, форматы и, опционально, один набор стилей артефактов. Набор стилей при этом является самостоятельным декларативным ресурсом и может существовать вообще без плагина: как встроенный набор Strategy Box, отдельный устанавливаемый style-package, пользовательский импортированный набор или управляемый набор среды.

Для артефактов нужен **ровно один эффективный ArtifactStyleSet**. Не комбинация шрифта из одного профиля, палитры из второго и таблиц из третьего. Внутри одного набора разрешена вариативность, но только как заранее определённая и структурированная система semantic roles, variants и format projections. Она является частью версии набора и проходит валидацию до использования.

Целевая модель:

~~~text
Style provider
    ↓
ArtifactStyleSet registry
    ↓
выбран один style_set_id + version
    ↓
compile / validate
    ↓
ResolvedArtifactStyleSet
    ↓
единые semantic tokens
    ↓
XLSX adapter
DOCX adapter
PPTX adapter
PDF adapter
other adapters
    ↓
артефакты с общей визуальной идентичностью
~~~

При этом UI Strategy Box живёт отдельно:

~~~text
InterfaceTheme
    theme_mode = system / light / dark
    accent = strategy / system / custom
~~~

ArtifactStyleSet не перекрашивает shell, не подменяет QSS, не меняет навигацию и не определяет UI typography. Это сохраняет единый Windows/Android продукт и одновременно даёт глубокую кастомизацию создаваемых файлов.

Основной принцип для артефактов:

> **Один набор стилей — один визуальный язык — несколько форматных проекций.**

Если один и тот же run формирует XLSX, DOCX и PPTX, они должны использовать один и тот же основной шрифт, одну semantic palette, одинаковую логику заголовков, акцентов, предупреждений, источников, числовых ролей и chart series там, где соответствующий формат это поддерживает.

Текущий Excel-style layer уже доказывает полезность styles-as-data, но его модель слишком узкая и format-specific. Текущие Excel presets и style addons логично заменить общим ArtifactStyleSet contract, а Excel StyleSpec оставить лишь внутренней проекцией XLSX renderer.

---

# 1. Что именно понимается под кастомизацией

В Strategy Box слово «кастомизация» сейчас может означать слишком разные вещи. Их необходимо развести.

## 1.1. Кастомизация интерфейса приложения

Относится к stratbox-windows / будущему stratbox-android:

- системная / светлая / тёмная тема;
- минимальный выбор акцентного цвета;
- системные accessibility preferences;
- автоматически сохраняемое состояние layout.

Это surface concern.

## 1.2. Кастомизация создаваемых артефактов

Относится к stratbox/reporting layer:

- шрифты;
- палитра;
- semantic text roles;
- таблицы;
- границы и заливки;
- числовые форматы;
- chart colors;
- document styles;
- presentation master semantics;
- PDF presentation rules;
- approved templates;
- branding assets;
- часть статических metadata defaults.

Это ArtifactStyleSet.

## 1.3. Кастомизация metadata

Отдельный слой:

- creator/author display label;
- company/application metadata;
- title/subject/category;
- automatic artifact/run/source identifiers;
- provenance.

Авторство файла не является стилем и не должно прятаться внутри палитры или template.

## 1.4. Кастомизация возможностей

Это plugin/capability layer:

- storage;
- network;
- sources;
- operations;
- import/export capabilities;
- reporting resources;
- settings schema;
- health.

Плагин может поставлять ArtifactStyleSet, но от этого ArtifactStyleSet не становится «плагином».

---

# 2. Главный термин: ArtifactStyleSet

Предлагаемый canonical термин:

**ArtifactStyleSet** — версионированная, декларативная, целостная спецификация визуального языка создаваемых Strategy Box артефактов.

Свойства:

~~~text
single
versioned
immutable after publication
declarative
semantic
cross-format
validated
reproducible
provider-independent
~~~

Не следует использовать как основные публичные термины одновременно:

- profile;
- theme;
- preset;
- skin;
- template pack;
- Excel style addon.

Они пересекаются и создают неоднозначность.

Для UI остаётся InterfaceTheme.  
Для артефактов — ArtifactStyleSet.  
Для документов-шаблонов — ArtifactTemplate.  
Для расширений — Plugin.

---

# 3. Один эффективный набор, а не merge нескольких

Это центральный invariant.

В конкретном execution context действует:

~~~text
effective_artifact_style_set = exactly one
~~~

Запрещена runtime-модель:

~~~text
font      ← Set A
colors    ← Set B
charts    ← Set C
xlsx      ← Set D
pptx      ← Set E
~~~

Она быстро приводит к:

- визуальной несогласованности;
- трудно воспроизводимым результатам;
- конфликтам при обновлении;
- невозможности нормально тестировать output;
- сложной provenance;
- неожиданным format-specific отличиям;
- бесконечным пользовательским controls.

Правильная модель:

~~~text
ArtifactStyleSet "A"
    typography
    colors
    semantic roles
    number formats
    charts
    xlsx projection
    docx projection
    pptx projection
    pdf projection
~~~

Все элементы принадлежат одной identity/version.

---

# 4. Наследование допустимо только до runtime

Полезно различать authoring-time inheritance и runtime composition.

## 4.1. Допустимо при разработке набора

Например:

~~~text
corp.standard v3
extends strategy.standard v2
overrides:
    typography.primary_family
    brand.primary
    table.header.primary
~~~

Это удобно для автора style set.

## 4.2. Перед использованием набор обязан быть скомпилирован

Resolver превращает inheritance chain в:

~~~text
ResolvedArtifactStyleSet
    complete values
    no unresolved inheritance
    no missing required tokens
    one version
    one digest
~~~

После этого renderer не знает о base/overlay.

## 4.3. Почему это важно

Старый результат должен точно отвечать:

~~~text
style_set_id
style_set_version
resolved_style_digest
~~~

а не:

~~~text
base X + addon Y + user overrides Z + plugin defaults Q
~~~

---

# 5. Plugin и ArtifactStyleSet — разные жизненные циклы

## 5.1. Plugin

Plugin:

- устанавливается как extension package;
- проходит activation;
- объявляет capabilities;
- имеет health/readiness;
- может быть required/optional;
- может содержать runtime code.

## 5.2. ArtifactStyleSet

ArtifactStyleSet:

- является пассивной спецификацией;
- имеет stable ID/version;
- валидируется;
- может быть сериализован;
- не обязан иметь executable code;
- может жить дольше конкретного plugin runtime;
- может быть сохранён в provenance и artifact manifest.

## 5.3. Связь

Plugin contract может иметь optional contribution:

~~~text
artifact_style_set: ArtifactStyleSet | None
~~~

На первом контракте этого достаточно.

Если в будущем появится реальная потребность в нескольких независимых branding systems, лучше регистрировать несколько самостоятельных ArtifactStyleSet resources, а не превращать один набор в скрытый каталог разных брендов.

## 5.4. Standalone style package

Должен быть возможен пакет, который вообще ничего не делает кроме поставки одного ArtifactStyleSet.

Это особенно полезно для:

- branded deployments;
- клиентов;
- отдельных команд;
- публичных theme packages;
- managed organizational policy.

Такой пакет не следует называть business plugin.

---

# 6. Где должен жить contract

Canonical модели ArtifactStyleSet должны жить в публичном stratbox.

Причины:

- generated artifacts принадлежат бизнес/core слою;
- Windows и Android являются consumers;
- headless execution тоже должен уметь формировать тот же output;
- remote host обязан применять ту же style identity;
- plugin providers должны зависеть от neutral public contract.

Концептуально:

~~~text
stratbox/
    artifact_styles/
        models
        registry
        resolver
        validation
        semantic_roles
        adapters/
            xlsx
            docx
            pptx
            pdf
~~~

Материализовать все каталоги заранее необязательно. Важна граница.

stratbox-windows хранит только пользовательский выбор style_set_id и показывает каталог.

---

# 7. Структура ArtifactStyleSet

Минимальная верхнеуровневая модель:

~~~text
ArtifactStyleSet
    identity
    compatibility
    foundation
    semantic_styles
    approved_variants
    format_policies
    template_bindings
    static_metadata
    assets
~~~

## 7.1. Identity

~~~text
style_set_id
version
title
description
provider_id
schema_version
revision/digest
~~~

style_set_id стабилен.

Изменение смысла опубликованного style set создаёт новую version.

## 7.2. Compatibility

~~~text
supported_artifact_kinds
supported_formats
min_style_api_version
required_renderer_capabilities
required_fonts
optional_fonts
~~~

Нельзя считать любой style set автоматически применимым к любому writer.

## 7.3. Foundation

Базовые design decisions:

~~~text
typography
colors
spacing
borders
radii where applicable
effects where applicable
number_format_roles
chart_palette
~~~

Foundation не используется domain code напрямую. Domain работает с semantic roles.

---

# 8. Typography

Цель — максимальная согласованность разных formats.

Пример:

~~~text
typography:
    primary_family: Arial
    mono_family: Cascadia Mono
    fallback_families:
        - Liberation Sans
        - sans-serif

    roles:
        title
        subtitle
        heading_1
        heading_2
        body
        body_emphasis
        note
        source
        table_header
        table_body
        chart_title
        chart_axis
~~~

Главный принцип:

> Один основной font family применяется ко всем форматам, где это имеет смысл.

Размеры и веса могут различаться по semantic role. Формат не получает право сам выбирать другой «любимый» font.

## 8.1. Допустимые исключения

- monospace для code/path/technical blocks;
- symbol font только если writer реально требует его;
- форматный fallback, если основной font невозможно применить.

Каждое исключение должно быть частью style set, а не случайной логикой writer-а.

## 8.2. Font availability

Style set должен разделять:

~~~text
font declared
font available on execution node
font embeddable
font actually embedded
~~~

При отсутствии обязательного font:

- strict style set → render readiness failure;
- style set с approved fallback → использовать заранее объявленный fallback;
- выбранный fallback фиксируется в provenance.

Нельзя молча перейти на произвольный системный font.

---

# 9. Semantic color system

Цвета должны описываться по смыслу.

Пример:

~~~text
color.brand.primary
color.brand.secondary

color.text.primary
color.text.secondary
color.text.muted
color.text.inverse

color.surface.default
color.surface.subtle
color.surface.strong

color.border.subtle
color.border.default
color.border.strong

color.table.header.primary
color.table.header.secondary
color.table.total
color.table.subtotal

color.data.positive
color.data.negative
color.data.neutral
color.data.forecast
color.data.plan
color.data.actual

color.chart.series.1
...
color.chart.series.12
~~~

XLSX/PPTX/DOCX adapters преобразуют эти roles в конкретные механизмы формата.

Hex/RGB значения не должны дублироваться по domain exporters.

---

# 10. Semantic text/document roles

Вместо format-specific «ячейка A1 bold green»:

~~~text
document.title
document.subtitle
document.heading_1
document.heading_2
document.body
document.note
document.source
document.caption
document.warning
document.emphasis
~~~

Для таблиц:

~~~text
table.header.primary
table.header.secondary
table.row.normal
table.row.alternate
table.row.total
table.row.subtotal
table.row.forecast
table.row.warning
table.column.label
table.corner
~~~

Для диаграмм:

~~~text
chart.title
chart.subtitle
chart.axis
chart.grid
chart.series.primary
chart.series.secondary
chart.series.N
chart.annotation
chart.forecast
~~~

Domain знает только semantic role.

---

# 11. Number/date formats

Числовое представление является частью оформления, но business units остаются в domain layer.

Style set может задавать presentation roles:

~~~text
number.integer
number.decimal_1
number.decimal_2
number.percent_0
number.percent_1
number.ratio_1
number.currency
number.accounting
date.day
date.month
date.quarter
date.year
missing_value
~~~

Operation должна сказать:

~~~text
value role = percent
precision intent = 1
unit = %
~~~

а renderer выбирает соответствующий format.

Style set не должен решать, является ли конкретный показатель процентом или млрд рублей. Это domain truth.

---

# 12. Approved variants внутри одного набора

Внутренняя вариативность разрешена, если:

1. она объявлена заранее;
2. имеет semantic name;
3. принадлежит той же identity/version;
4. не образует второй независимый visual system;
5. renderer выбирает её по явной semantic причине.

Хорошие варианты:

~~~text
table.density.standard
table.density.compact

table.header.primary
table.header.secondary

document.cover.default
document.cover.minimal

chart.series.default
chart.series.monochrome_print

page.orientation.portrait
page.orientation.landscape
~~~

Плохая модель:

~~~text
Green Theme
Yellow Theme
Dark Green Theme
Fancy Theme
Minimal Theme
~~~

внутри одного style set.

Если различия меняют brand identity и основной visual language — это уже другой ArtifactStyleSet.

---

# 13. Варианты не должны превращаться в конструктор

UI не должен показывать:

~~~text
шрифт A/B/C
palette 1/2/3
table style 1/2/3
chart style 1/2/3
template 1/2/3
~~~

и давать собрать комбинацию.

Лучший UX:

~~~text
Набор стилей
[ Strategy Box Standard ]
~~~

Дополнительно operation может иметь semantic параметр:

~~~text
Представление
[ Стандартное / Компактное ]
~~~

только если текущий style set объявляет обе approved variants.

Параметр выбирает ветку внутри одного набора, а не новый набор.

---

# 14. Cross-format consistency

Если один run формирует несколько representations:

~~~text
report.xlsx
report.docx
report.pptx
report.pdf
~~~

они получают один ResolvedArtifactStyleSet.

Общие решения:

- font family;
- brand colors;
- text hierarchy;
- source/note appearance;
- table semantics;
- positive/negative/forecast semantics;
- chart series ordering;
- document metadata style identity.

Различаться может реализация.

Например:

~~~text
semantic role: document.heading_1

DOCX → paragraph style Heading 1
PPTX → title placeholder style
XLSX → merged title row / named cell style
PDF  → text style in PDF renderer
~~~

Это не четыре независимых стиля, а четыре projections одной роли.

---

# 15. Format capability model

Не каждый формат способен выразить всё.

Нужны outcomes:

~~~text
SUPPORTED
DEGRADED
NOT_APPLICABLE
UNSUPPORTED
~~~

Примеры:

- CSV: typography NOT_APPLICABLE;
- XLSX: page master может быть DEGRADED;
- PPTX: spreadsheet number format NOT_APPLICABLE;
- PDF: editable named styles могут быть UNSUPPORTED после serialization.

Важно:

> Отсутствие capability не означает переход к другому style set.

Renderer использует deterministic degradation, объявленную тем же набором.

---

# 16. Никаких скрытых cross-set fallback

Если пользователь выбрал style set X, а X не поддерживает PPTX:

Плохое поведение:

~~~text
XLSX → X
PPTX → Strategy Box Standard
~~~

Получится один run с двумя visual identities.

Правильные варианты:

1. не разрешить выбрать X для операции, требующей PPTX;
2. завершить validation до execution;
3. использовать explicit managed fallback policy только если она заранее задана;
4. в таком случае provenance обязана зафиксировать fallback.

Default product behavior лучше делать strict.

---

# 17. Templates — отдельные ресурсы внутри style set

Template и style set не равны.

ArtifactTemplate определяет структуру конкретного документа:

- slide master/layout;
- Word section arrangement;
- workbook sheet structure;
- cover page;
- placeholders.

ArtifactStyleSet определяет visual language.

Однако style set может содержать bindings:

~~~text
template_bindings:
    presentation.default → template:presentation.standard
    memo.default         → template:document.memo
    workbook.report      → template:workbook.report
~~~

Templates должны быть совместимы с semantic roles style set.

Это позволяет:

~~~text
один style set
    +
несколько approved templates
~~~

без превращения templates в независимые стили.

---

# 18. Assets

Style set может ссылаться на:

- logos;
- icons;
- watermark assets;
- document theme parts;
- approved template files;
- chart assets.

Все assets:

- versioned;
- hashed;
- лицензированно допустимы;
- доступны renderer-у;
- входят в digest/resolution identity.

Font files по умолчанию лучше не встраивать в style package. Набор может объявить required font family и deployment requirement. Встраивание разрешается только при явной license/format policy.

---

# 19. Metadata — отдельный context

Не стоит складывать всё в ArtifactStyleSet.

Нужен отдельный:

~~~text
ArtifactMetadataContext
    creator_label
    title
    subject
    category
    keywords
    created_at
    artifact_id
    run_id
    provenance_ref
~~~

Sources:

~~~text
creator_label     ← user/workspace/managed setting
title/subject     ← operation
artifact_id       ← artifact layer
run_id            ← execution
provenance_ref    ← provenance
~~~

Style set может иметь только безопасные статические branding defaults, например:

~~~text
company_label
template_identity
producer_label
~~~

и только если формат это поддерживает.

Office Author остаётся display metadata и не заменяет фактического actor provenance.

---

# 20. UI customization остаётся отдельной системой

ArtifactStyleSet не участвует в Qt/QSS/Android shell rendering.

Целевая surface model:

~~~text
AppearanceSettings
    theme_mode
    accent_mode
    custom_accent?
~~~

Этого достаточно.

Плагин и ArtifactStyleSet не получают право:

- менять shell font;
- подмешивать QSS/CSS;
- менять icons приложения;
- менять navigation;
- добавлять skin;
- менять component spacing/radius;
- внедрять platform-specific widgets.

Это особенно важно для Android reuse.

---

# 21. Можно ли сделать палитры UI и артефактов похожими

Да, но через намеренное продуктовое решение, а не через наследование.

Например built-in Strategy Box style set может использовать brand blue, совпадающий с InterfaceTheme Strategy accent.

Но это два самостоятельных contract-а:

~~~text
InterfaceTheme
ArtifactStyleSet
~~~

Изменение пользовательского UI accent не должно автоматически перекрашивать отчёты.

И наоборот, корпоративный ArtifactStyleSet не должен перекрашивать приложение.

---

# 22. Registry

Нужен единый ArtifactStyleSetRegistry.

Он собирает style sets из разрешённых providers:

~~~text
builtin provider
standalone style provider
active plugin contribution
managed deployment provider
future validated user import
~~~

Каждый registry entry:

~~~text
style_set_id
version
title
provider_type
provider_id
availability
compatibility
health/validation
digest
~~~

Catalog не смешивает contents sets.

---

# 23. Provider model

Полезный нейтральный protocol:

~~~python
class ArtifactStyleSetProvider(Protocol):
    def list_style_sets(self) -> Sequence[ArtifactStyleSetDescriptor]: ...
    def load_style_set(self, style_set_id: str, version: str) -> ArtifactStyleSet: ...
~~~

Однако в v1 можно сделать ещё проще:

- builtin provider;
- package entry point, который возвращает один ArtifactStyleSet;
- plugin capability, которая возвращает один ArtifactStyleSet.

Главное — все sources попадают в **один registry path**.

---

# 24. Style package ≠ plugin

Standalone style package лучше сделать декларативным.

Например:

~~~text
style-package/
    manifest.json
    style.json
    assets/
    templates/
~~~

Python code не требуется, если resolver может прочитать пакет как data resource.

Плюсы:

- меньше attack surface;
- проще validation;
- легче cross-platform;
- проще AppDock install;
- можно подписывать/hash-ить;
- можно использовать на Windows и Android;
- можно архивировать рядом с artifact provenance.

---

# 25. Resolution precedence

Нужно различать selection и provider priority.

Provider priority не должен решать пользовательский выбор.

Selection chain:

~~~text
managed forced style_set
        ↓ if absent
workspace default
        ↓ if absent
user default
        ↓ if absent
Strategy Box built-in default
~~~

Run может передать explicit style set только если policy разрешает override.

Результат:

~~~text
RequestedStyle
ResolvedStyle
ResolutionReason
~~~

Пример:

~~~text
requested = corp.standard
resolved  = corp.standard@3.2
reason    = workspace_default
~~~

---

# 26. Unavailable selected style set

Если previously selected style set исчез:

Нельзя молча выбрать другой и сделать вид, что ничего не произошло.

State:

~~~text
selected_style_set = unavailable
effective_style_set = unresolved
~~~

UI:

~~~text
Набор стилей недоступен
[Выбрать другой]
~~~

Для non-interactive execution policy может явно разрешить fallback.

Если fallback использован:

~~~text
requested_style_set
resolved_style_set
fallback_reason
~~~

попадают в provenance.

---

# 27. Run-time StyleContext

Перед exporter-ом создаётся immutable context:

~~~text
ArtifactStyleContext
    style_set_id
    style_set_version
    style_set_digest
    resolved_tokens
    selected_approved_variants
    format
    renderer_version
    font_resolution
    template_refs
~~~

Handler не читает Settings напрямую.

Цепочка:

~~~text
Settings / Workspace / Managed policy
        ↓
ArtifactStyleResolver
        ↓
ArtifactStyleContext
        ↓
operation/export request
        ↓
format renderer
~~~

Это одинаково работает:

- desktop;
- host;
- background;
- remote;
- AI-triggered run;
- Android.

---

# 28. Provenance

Каждый styled artifact должен фиксировать:

~~~text
style_set_id
style_set_version
style_set_digest
renderer_id
renderer_version
selected approved variants
font resolution
template identities
fallback/degradation events
~~~

Не обязательно помещать всё в visible Office properties. Это canonical provenance/artifact manifest.

В самом файле можно дополнительно записать custom properties, если формат это позволяет.

---

# 29. Artifact manifest linkage

ArtifactDescriptor из отдельной artifact architecture не нужно перегружать style details.

Лучше:

~~~text
ArtifactDescriptor
    ...
    provenance_ref
~~~

Provenance:

~~~text
rendering:
    style_set_ref
    renderer_ref
    template_refs
    metadata_context_digest
~~~

Так artifact identity остаётся компактной, а rendering воспроизводим.

---

# 30. Что делать с current Excel style system

Текущий stratbox.base.styles.excel имеет полезные идеи:

- FontTheme;
- BlockStyle;
- StyleSpec;
- builtin registry;
- apply layer;
- plugin-discovered addon.

Но архитектурно это format-first model.

Целевая перестройка:

~~~text
сейчас
Excel preset
    fonts
    fills
    borders
    number format
    freeze

будущее
ArtifactStyleSet
    semantic design system
        ↓
XlsxStyleProjection
        ↓
openpyxl application
~~~

StyleSpec можно оставить как внутреннюю compiled XLSX model либо заменить более точной моделью renderer-а.

---

# 31. Что убрать из текущего Excel model

Поскольку backward compatibility не нужна:

1. Убрать notion, что Excel presets являются верхнеуровневым публичным style contract.
2. Убрать format-specific style addon entry point как конечную архитектуру.
3. Убрать поведение «несколько addons подмешиваются по порядку».
4. Убрать implicit default, который меняется просто из-за discovery внешнего package.
5. Убрать произвольное overwrite preset names.
6. Не хранить font registry отдельно от style-set identity.

Главная причина: эти механизмы допускают runtime mixing.

---

# 32. Что сохранить из Excel model

Стоит сохранить идеи:

- style as data;
- immutable dataclasses/specs;
- semantic overlays внутри одного compiled projection;
- central application engine;
- format adapter вне domain;
- no hardcoded styles in business parser.

---

# 33. XLSX projection

ArtifactStyleSet → XlsxStyleProjection может включать:

~~~text
workbook:
    default font
    theme colors
    properties

worksheet:
    gridline policy
    default row/column presentation
    freeze policy by semantic layout role

cells:
    title
    heading
    header
    values
    total
    subtotal
    warning
    forecast
    source

number formats:
    semantic role → Excel pattern

charts:
    semantic series → colors/fonts/line styles
~~~

Freeze panes стоит считать presentation policy, а не brand token. Она может иметь sensible defaults, но operation/layout может выбирать семантически нужный режим.

---

# 34. DOCX projection

Использовать named semantic paragraph/character/table styles.

Пример:

~~~text
document.title       → StrategyTitle
document.heading_1   → StrategyHeading1
document.body        → StrategyBody
document.source      → StrategySource
table.header.primary → StrategyTableHeader
table.row.total      → StrategyTableTotal
~~~

Основной font и palette берутся из ArtifactStyleSet.

Word theme может использоваться как один из механизмов реализации, но canonical Strategy Box contract не должен зависеть от OOXML theme format.

---

# 35. PPTX projection

Style set определяет:

- theme font;
- theme color scheme;
- title/body text roles;
- table roles;
- chart palette;
- shape fills/lines;
- source/note role;
- approved master/template binding.

Layout slide-а остаётся задачей template/presentation builder.

---

# 36. PDF projection

PDF renderer получает тот же semantic context.

Style set может управлять:

- fonts;
- colors;
- hierarchy;
- table styles;
- chart colors;
- margins/presentation defaults;
- metadata branding.

PDF ограничен финальной serialization model, поэтому renderer фиксирует все degradation events.

---

# 37. CSV, JSON, Parquet и другие data artifacts

Не каждый artifact обязан визуально стилизоваться.

Для:

~~~text
CSV
JSON
JSONL
Parquet
raw source
archive
~~~

style applicability обычно:

~~~text
NOT_APPLICABLE
~~~

Но artifact provenance всё равно может ссылаться на run style context, если тот же run создаёт рядом human-facing report.

Не надо вставлять styling metadata внутрь canonical datasets без предметной причины.

---

# 38. Design tokens как reference

Design Tokens Community Group в 2025 году выпустила первую stable 2025.10 спецификацию формата design tokens. Она полезна как внешний reference для:

- typed token values;
- aliases;
- groups;
- portable serialization;
- resolution.

Strategy Box не обязан копировать DTCG schema полностью.

Artifact styles имеют дополнительные предметные concepts:

- tables;
- number formats;
- Office document roles;
- chart semantics;
- templates;
- format degradation.

Поэтому лучше небольшой собственный versioned schema, при этом terminology primitive/semantic/resolved tokens можно выровнять с индустриальной практикой.

---

# 39. Office Open XML как подтверждение cross-format модели

Open XML Theme уже показывает, что единая тема документа естественно состоит из:

- color scheme;
- font scheme;
- format/effects scheme.

Такая Theme part применяется в WordprocessingML, SpreadsheetML и PresentationML. Это подтверждает саму архитектурную идею общего визуального языка поверх нескольких Office formats.

Strategy Box ArtifactStyleSet должен быть выше OOXML Theme:

~~~text
ArtifactStyleSet
        ↓
OOXML theme / styles / masters / cell formats
~~~

Потому что:

- PDF не OOXML;
- semantic number/table roles шире generic Office Theme;
- templates и provenance имеют отдельный lifecycle;
- некоторые Office formats требуют дополнительных style structures.

---

# 40. Validation

ArtifactStyleSet загружается только после validation.

Минимальные проверки:

## Identity

- valid stable ID;
- semantic version;
- schema version;
- immutable digest.

## Completeness

- все required semantic roles разрешены;
- нет unresolved aliases;
- inheritance chain closed;
- нет циклов.

## Typography

- primary font задан;
- approved fallbacks валидны;
- font requirement policy определена.

## Colors

- valid values;
- required contrast pairs проходят policy;
- chart series различимы;
- text/background combinations допустимы.

## Formats

- declared support соответствует adapters;
- нет ссылок на отсутствующий template;
- required writer capability существует.

## Assets

- hash matches;
- file type allowed;
- size bounded;
- path traversal impossible.

---

# 41. Conformance suite

Style set должен иметь автоматическую certification matrix.

Примеры:

~~~text
compile style set
resolve all tokens
render sample XLSX
render sample DOCX
render sample PPTX
render sample PDF
inspect fonts/colors/metadata
check required semantic roles
check deterministic digest
check no undeclared fallback
check template references
check font resolution
~~~

Golden outputs могут проверяться структурно, а не pixel-perfect.

---

# 42. Security

ArtifactStyleSet по умолчанию должен быть data, а не code.

Запрещать в declarative style resource:

- arbitrary Python;
- scripts/macros;
- external executable commands;
- unbounded remote resource fetch;
- template macros;
- post-render hooks.

Если когда-нибудь нужен executable renderer extension, это отдельная plugin capability с отдельной trust model.

Style set не должен незаметно становиться каналом выполнения кода.

---

# 43. Managed policy

Организация или deployment может:

- установить style set;
- сделать его default;
- сделать его обязательным;
- запретить user imports;
- запретить overrides;
- требовать specific author/company metadata;
- запретить render при missing font/template.

UI при этом показывает:

~~~text
Набор стилей: Corporate Standard
Управляется организацией
~~~

но не даёт менять значение.

---

# 44. User settings

Раздел Артефакты и отчёты должен оставаться маленьким.

Целевая форма:

~~~text
Артефакты и отчёты

Набор стилей
[ Strategy Box Standard ▼ ]

Автор файлов
[ Strategy Box ]
~~~

Опционально:

~~~text
[Подробнее о наборе]
~~~

В Details:

- title;
- version;
- provider;
- supported formats;
- primary font;
- preview;
- validation status.

Не нужны sliders/pickers внутренних tokens.

---

# 45. Style preview

Полезна deterministic preview surface:

~~~text
Typography
Table
Chart
Document
Presentation
~~~

Preview строится из sample semantic document, а не из реального business data.

Это позволяет сравнивать approved style sets, не превращая Settings в редактор.

---

# 46. User import

В будущем можно разрешить:

~~~text
Импортировать набор стилей
~~~

Но импортированный объект:

1. валидируется;
2. получает/проверяет identity;
3. компилируется;
4. проходит compatibility;
5. становится отдельным ArtifactStyleSet;
6. только после этого может быть выбран.

Нельзя импортировать «palette.json» и подмешать её к текущему набору.

---

# 47. Versioning

Правило:

- изменение display title без смысла может быть metadata revision;
- изменение любого token/role/template, влияющего на output, требует новой version или revision digest;
- published version immutable;
- old style set сохраняется, пока нужен для воспроизводимости historical artifacts.

Пользователь может выбрать latest compatible, но каждый run фиксирует конкретную version.

---

# 48. Update style set

Update package:

~~~text
corp.standard 3.1 → 3.2
~~~

не должен retroactively менять старые artifacts.

Для future run:

- managed policy может auto-advance;
- user preference может следовать latest;
- строгий environment может pin version.

В любом случае resolved version пишется в run provenance.

---

# 49. Renderer version

Воспроизводимость зависит не только от style set.

Нужно хранить:

~~~text
style_set
renderer
template
format library
~~~

Минимум:

~~~text
renderer_id
renderer_version
~~~

Потому что одинаковый style set при изменении writer implementation может дать отличающийся файл.

---

# 50. Current domain exporters

Домены не должны:

- hardcode Arial/Calibri сами;
- выбирать RGB;
- создавать private header styles;
- задавать chart colors;
- самостоятельно искать plugin styles;
- читать user settings.

Domain exporter описывает semantic structure:

~~~text
title
table header
value
subtotal
source
warning
forecast
chart series
~~~

Rendering layer применяет style set.

Текущие hardcoded styles в отдельных exporters следует постепенно удалить по мере перевода на общий layer.

---

# 51. Связь с Artifact architecture

Artifact layer отвечает:

- identity;
- storage;
- manifest;
- commit;
- immutability;
- lineage;
- provenance.

ArtifactStyleSet отвечает:

- presentation semantics.

Связь:

~~~text
Operation
    ↓ canonical result
Renderer + ArtifactStyleContext
    ↓ bytes
Artifact draft
    ↓ commit
Artifact + provenance(style_set_ref)
~~~

Стиль не владеет artifact lifecycle.

---

# 52. Связь с Operation/Scenario architecture

Operation descriptor может объявлять:

~~~text
artifact_kinds
required_style_capabilities
supported approved variants
style_override_allowed
~~~

Пример:

~~~text
operation = export.board_presentation
requires:
    pptx
    presentation.template
    chart_palette
style_override_allowed = false
~~~

До запуска UI может отфильтровать несовместимые style sets.

---

# 53. Remote execution

Client не отправляет renderer-у «текущие colors».

Он отправляет:

~~~text
style_set_ref
approved variant selection
metadata context
~~~

Execution node:

1. разрешает exact style set;
2. проверяет digest/version;
3. проверяет assets/fonts;
4. рендерит;
5. фиксирует фактическое разрешение.

Это предотвращает расхождение client/host.

---

# 54. Android

Android surface должен видеть тот же catalog:

~~~text
style_set_id
title
version
availability
managed
preview metadata
~~~

Но сам style set может фактически применяться на remote host.

Android не должен импортировать desktop QSS или openpyxl models.

---

# 55. AI

AI может:

- запросить доступные style sets;
- использовать effective default;
- выбрать approved style set при наличии разрешения;
- выбрать approved variant operation-а.

AI не должен:

- создавать arbitrary colors;
- менять persistent default без отдельного permission;
- импортировать непроверенный style resource;
- обходить managed policy.

---

# 56. AppDock boundary

AppDock отвечает за deployment concerns:

- установка package/resource;
- version availability;
- managed policy delivery;
- node environment;
- required font/resource provisioning;
- package update.

Strategy Box отвечает за:

- style schema;
- validation;
- registry;
- selection semantics;
- rendering;
- provenance.

AppDock не нужно знать смысл table.header.primary.

---

# 57. Предлагаемый manifest

Пример направления, не финальная схема:

~~~yaml
schema: stratbox.artifact-style-set/v1

identity:
  id: strategy.standard
  version: 1.0.0
  title: Strategy Box Standard

compatibility:
  formats:
    - xlsx
    - docx
    - pptx
    - pdf

foundation:
  typography:
    primary_family: Arial
    fallback_families:
      - Liberation Sans

  colors:
    brand.primary: "#316BE5"
    text.primary: "#20242B"
    text.secondary: "#5E6673"
    surface.default: "#FFFFFF"
    border.default: "#D4DAE3"

semantic_styles:
  document.title:
    font_role: title
    color: text.primary

  table.header.primary:
    font_role: table_header
    background: brand.primary
    foreground: text.inverse

  table.row.total:
    font_role: body_emphasis

number_formats:
  integer: ...
  decimal_1: ...
  percent_1: ...

approved_variants:
  table_density:
    - standard
    - compact

format_policies:
  xlsx: ...
  docx: ...
  pptx: ...
  pdf: ...

template_bindings:
  presentation.default: presentation.standard
~~~

В production schema лучше использовать machine-validatable JSON либо YAML с canonical JSON normalization для digest.

---

# 58. Структура внутренних variants

Variants лучше делать namespaced и ограниченными.

~~~text
approved_variants:
    table_density:
        default: standard
        allowed:
            standard
            compact

    presentation_tone:
        default: standard
        allowed:
            standard
            executive

    print_mode:
        default: color
        allowed:
            color
            monochrome
~~~

Важно:

- variant не меняет style_set_id;
- variant не может заменить primary font arbitrary value;
- список фиксирован в version;
- combination matrix может быть ограничена.

Если executive начинает иметь другой brand/font/palette — это отдельный style set.

---

# 59. Решение по «один набор на всё»

Рекомендуемый invariant для Strategy Box v1:

> **Один execution context использует один ArtifactStyleSet для всех human-facing artifacts.**

Исключения:

- data-only artifacts → style NOT_APPLICABLE;
- raw source → style NOT_APPLICABLE;
- external user-provided template → либо становится частью validated style/template resource, либо считается отдельным explicit export mode.

Не следует разрешать:

~~~text
xlsx_style_set = A
pptx_style_set = B
docx_style_set = C
~~~

в одном стандартном run.

---

# 60. Что делать, если нужен специальный regulatory format

Если внешний регулятор требует фиксированный внешний шаблон, это не «пользовательский стиль».

Operation объявляет:

~~~text
presentation_contract = external_fixed
~~~

Тогда:

- ArtifactStyleSet может применяться только к разрешённым zones;
- либо styling полностью NOT_APPLICABLE;
- внешний template identity фиксируется отдельно.

Так compliance format не конфликтует с branding settings.

---

# 61. Что делать с chart palette

Chart palette принадлежит style set.

Нужна стабильная sequence:

~~~text
chart.series.1
chart.series.2
...
chart.series.N
~~~

Дополнительно semantic roles:

~~~text
chart.actual
chart.plan
chart.forecast
chart.benchmark
chart.highlight
~~~

Renderer должен предпочитать semantic role, а generic series sequence использовать как fallback внутри **того же** style set.

---

# 62. Accessibility

ArtifactStyleSet validation должна учитывать:

- контраст текста;
- различимость chart series;
- недопустимость color-only differentiation там, где renderer умеет pattern/marker;
- readable font sizes;
- print/PDF behavior;
- dark-filled header readability.

Accessibility rules являются частью conformance, а не ручной настройки пользователя.

---

# 63. Localization

Style set не должен хранить локализованный business text.

Допустимо:

- locale-specific number/date format mappings;
- font fallback по writing system;
- page typography adaptation.

Domain/content layer предоставляет:

- labels;
- units;
- language.

Style set предоставляет presentation.

---

# 64. Naming

Рекомендуемые IDs:

~~~text
strategy.standard
example.corporate
client.brand
team.research
~~~

Version отдельно.

Не стоит кодировать version в ID.

Пользователь видит title, а не technical ID.

---

# 65. Source/provider identity

Style set знает provider только ради provenance/management:

~~~text
provider_type:
    builtin
    style_package
    plugin
    managed

provider_id
~~~

Rendering semantics не должны ветвиться по provider_type.

Все sets равноправны после validation.

---

# 66. Пересмотр plugin contract

Generic plugin capability taxonomy лучше изменить с абстрактного reporting_theme на:

~~~text
artifact_style_set
~~~

и определить его как passive contribution.

Plugin:

- может иметь zero or one ArtifactStyleSet contribution в v1;
- не меняет registry merge semantics;
- не задаёт global default сам;
- не получает automatic priority только потому, что установлен;
- не изменяет UI theme.

Default выбирает settings/managed policy.

---

# 67. Пересмотр Settings research

Предыдущую модель ReportProfile стоит уточнить.

Заменить:

~~~text
ReportProfile
overridable_tokens
plugin profile
~~~

на:

~~~text
ArtifactStyleSet
approved_variants
provider-independent
single effective set
~~~

Особенно важно убрать default UX с font/color overrides.

Если business потребность в override появится позже, лучше вводить новую approved variant или новый style set, чем разрешать arbitrary mutation.

---

# 68. Пользовательские controls: итог

## Внешний вид

~~~text
Тема
  Как в системе / Светлая / Тёмная

Акцент
  Strategy Box / Windows / Свой
~~~

## Артефакты и отчёты

~~~text
Набор стилей
  Strategy Box Standard

Автор файлов
  Strategy Box
~~~

## Плагины

Отдельная surface:

- installed;
- active;
- compatibility;
- health;
- config.

Если plugin поставляет style set, в plugin details можно показать:

~~~text
Предоставляет набор стилей: Example Corporate
~~~

Но выбирать этот набор пользователь идёт в «Артефакты и отчёты».

---

# 69. Каталог style sets

Каждый item:

~~~text
title
version
source/provider
status
supported formats
primary font
small palette preview
managed badge
~~~

Actions:

~~~text
Выбрать
Подробнее
Проверить
Удалить / Управлять в AppDock
~~~

если policy разрешает.

---

# 70. Migration path

## Этап A — terminology/contracts

1. Ввести ArtifactStyleSet.
2. Ввести ArtifactStyleSetRef.
3. Ввести ResolvedArtifactStyleSet.
4. Ввести ArtifactStyleContext.
5. Ввести registry/resolver.

## Этап B — built-in set

6. Перенести текущий разумный Excel visual language в strategy.standard.
7. Сформировать common typography/palette.
8. Добавить XLSX projection.

## Этап C — убрать format-first public contract

9. Сделать Excel StyleSpec internal renderer model.
10. Удалить public Excel addon entry point.
11. Убрать automatic addon merge/default override.

## Этап D — domain migration

12. Убрать hardcoded formatting из exporters.
13. Перевести exporters на semantic roles.
14. Добавить style context в artifact/export contracts.

## Этап E — cross-format

15. DOCX projection.
16. PPTX projection.
17. PDF projection.
18. template bindings.

## Этап F — providers

19. standalone style package provider.
20. generic plugin optional contribution.
21. managed provider.

## Этап G — surface

22. one style-set selector.
23. author field.
24. preview/details.
25. managed lock state.

---

# 71. Tests

## Resolver

- builtin default;
- user selection;
- workspace selection;
- managed forced selection;
- explicit run override;
- missing selected set;
- duplicate IDs;
- incompatible version;
- digest mismatch.

## Compilation

- inheritance;
- cycle;
- missing token;
- invalid alias;
- invalid asset;
- unsupported format.

## Cross-format

- same primary font across XLSX/DOCX/PPTX;
- same semantic primary color;
- same chart series order;
- same document heading hierarchy;
- deterministic number format mapping.

## Strictness

- no cross-set fallback;
- no runtime merge;
- no arbitrary override;
- plugin installation does not change default automatically.

## Provenance

- exact style set ID/version/digest;
- renderer version;
- template IDs;
- font fallback recorded;
- degradation recorded.

---

# 72. Acceptance criteria

Архитектура кастомизации считается выровненной, если:

1. Plugin, ArtifactStyleSet и InterfaceTheme являются разными concepts.
2. ArtifactStyleSet существует без plugin.
3. Plugin может опционально поставлять ArtifactStyleSet через общий provider path.
4. В execution context действует один effective ArtifactStyleSet.
5. Runtime не смешивает tokens из нескольких sets.
6. Authoring-time inheritance компилируется до complete resolved set.
7. Style set имеет stable ID, version и digest.
8. Один primary font применяется cross-format где применимо.
9. Одна semantic palette используется cross-format.
10. XLSX/DOCX/PPTX/PDF являются adapters одного semantic model.
11. Approved variants заранее перечислены и versioned.
12. Arbitrary font/color override отсутствует в default UX.
13. Templates отделены от style set, но могут быть bound к нему.
14. Artifact metadata отделена от styling.
15. UI theme отделена от artifact styling.
16. Plugin не может менять shell visual system.
17. Missing selected style set не вызывает silent fallback.
18. Unsupported format не приводит к подстановке другого style set.
19. Provenance фиксирует exact resolved style identity.
20. Current Excel preset layer больше не является верхнеуровневым public style API.
21. Domain exporters не hardcode colors/fonts.
22. Windows, host, Android и AI используют один style reference contract.

---

# 73. Ключевые архитектурные решения

В максимально короткой форме:

~~~text
UI
  InterfaceTheme
  system/light/dark + accent
  app-owned

Artifacts
  ArtifactStyleSet
  exactly one effective set
  cross-format
  versioned
  declarative

Metadata
  ArtifactMetadataContext
  author/title/run/provenance
  separate from style

Plugins
  capability containers
  may contribute ArtifactStyleSet
  style set remains independent resource

Templates
  structure/layout resources
  may be bound by ArtifactStyleSet
  not equivalent to style set
~~~

---

# 74. Итоговый тезис

Strategy Box не нужен «конструктор оформления».

Ему нужна **система утверждённых визуальных языков**, где каждый язык представлен одной атомарной сущностью ArtifactStyleSet.

Пользователь выбирает набор целиком. Организация может его зафиксировать. Плагин может его привезти. Отдельный package может привезти только его. Но после resolution происхождение перестаёт влиять на rendering: остаётся один validated style set, один semantic vocabulary и набор format adapters.

Это даёт одновременно:

- целостность;
- воспроизводимость;
- cross-format consistency;
- переносимость Windows → Android → host;
- безопасную plugin architecture;
- понятные Settings;
- минимум пользовательского шума;
- возможность branded deployments;
- нормальную provenance;
- отсутствие скрытого style spaghetti.

Именно такой уровень абстракции выглядит достаточным для будущего Strategy Box: **не Excel preset, не plugin theme и не UI skin, а единый ArtifactStyleSet над всеми human-facing артефактами.**

---

# 75. Проверенные внутренние материалы

Использованы:

- stratbox_base_study_current_state_2026-10-06.md;
- stratbox-windows_current_state_full_research_2026-10-06.md;
- stratbox_file_artifact_layer_research_2026-10-06.md;
- strategy_box_interface_visual_system_research_2026-10-07.md;
- strategy_box_system_settings_research_2026-10-07.md;
- stratbox_corporate_plugin_contract_research_2026-10-07.md;
- актуальный public Excel style layer stratbox.base.styles.excel на main.

Этот документ уточняет предыдущие исследования в двух местах:

1. ReportProfile заменяется более строгим ArtifactStyleSet.
2. Plugin и ArtifactStyleSet окончательно разводятся как разные сущности и lifecycle.

---

# 76. Внешняя техническая сверка

Использованы как reference:

1. W3C Design Tokens Community Group — Design Tokens Format/Color/Resolver 2025.10:  
   https://www.w3.org/community/design-tokens/

2. Microsoft Learn — Open XML Theme structure / replacement in WordprocessingML:  
   https://learn.microsoft.com/en-us/office/open-xml/general/how-to-replace-the-theme-part-in-a-word-processing-document

3. Microsoft Learn — PresentationML structure / Theme Part:  
   https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document

4. Microsoft Learn — Apply a theme to a presentation:  
   https://learn.microsoft.com/en-us/office/open-xml/presentation/how-to-apply-a-theme-to-a-presentation

Open XML используется как подтверждение того, что color/font/format scheme естественно может быть общей темой нескольких Office formats. ArtifactStyleSet намеренно располагается выше OOXML Theme, потому что должен охватывать также PDF, semantic table/number roles, templates, provenance и будущие renderers.

---

**Конец исследования.**
