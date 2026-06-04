from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap.runtime import AppRuntime
from app.presence.models import ParticipantRecord
from app.runs.models import RunRecord
from app.scenarios.catalog import group_scenarios
from app.scenarios.composer import ScenarioComposer
from app.scenarios.models import ScenarioResult, ScenarioSpec
from app.system.commands import build_diagnostics_text
from app.timeline.models import FeedAction, FeedEntry
from app.timeline.widgets import FeedCard
from app.workspace import run_workspace_diagnostics


class ParticipantsDialog(QDialog):
    def __init__(self, participants: tuple[ParticipantRecord, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Участники')
        self.setModal(True)
        self.selected_participant_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.list = QListWidget()
        for participant in participants:
            text = f"{participant.display_name}"
            if participant.is_online:
                text += ' · online'
            if participant.last_seen_label:
                text += f' · {participant.last_seen_label}'
            if participant.run_count:
                text += f' · запусков: {participant.run_count}'
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, participant.participant_id)
            self.list.addItem(item)
        self.list.itemDoubleClicked.connect(self._accept_current)
        layout.addWidget(self.list)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        filter_button = QPushButton('Фильтровать')
        filter_button.clicked.connect(self._accept_current)
        buttons.addWidget(filter_button)
        all_button = QPushButton('Показать всё')
        all_button.clicked.connect(self._accept_all)
        buttons.addWidget(all_button)
        close_button = QPushButton('Закрыть')
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _accept_current(self) -> None:
        item = self.list.currentItem()
        self.selected_participant_id = item.data(Qt.UserRole) if item is not None else None
        self.accept()

    def _accept_all(self) -> None:
        self.selected_participant_id = None
        self.accept()


class DiagnosticsDialog(QDialog):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Диагностика')
        self.resize(920, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(text)
        layout.addWidget(viewer)


class MainWindow(QMainWindow):
    def __init__(self, runtime: AppRuntime):
        super().__init__()
        self.runtime = runtime
        self.context = runtime.context
        self._selected_scenario_id: str | None = None
        self._recent_artifacts: list[str] = list(self.context.session_snapshot.app_state.recent_artifacts) if self.context.session_snapshot and self.context.session_snapshot.app_state else []
        self._last_result_message = ''
        self._build_ui()
        self._build_menus()
        self._populate_scenario_tree()
        self._seed_feed()
        self._refresh_context_views()
        self.runtime.run_coordinator.run_finished.connect(self._on_run_finished)

    def _build_ui(self) -> None:
        self.setWindowTitle('Strategy Box')
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_top_bar())

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName('mainSplitter')
        outer.addWidget(self.main_splitter, 1)

        self.left_sidebar = self._build_left_sidebar()
        self.center_shell = self._build_center_shell()
        self.right_sidebar = self._build_right_sidebar()

        self.main_splitter.addWidget(self.left_sidebar)
        self.main_splitter.addWidget(self.center_shell)
        self.main_splitter.addWidget(self.right_sidebar)
        self.main_splitter.setSizes(self.runtime.preferences.current().splitter_sizes)

    def _build_top_bar(self) -> QWidget:
        box = QWidget()
        box.setObjectName('topBar')
        layout = QHBoxLayout(box)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel('Strategy Box')
        title.setObjectName('topBarTitle')
        title_col.addWidget(title)
        self.mode_label = QLabel('')
        self.mode_label.setObjectName('topBarSubtle')
        title_col.addWidget(self.mode_label)
        layout.addLayout(title_col)
        layout.addStretch(1)

        self.online_badge = QLabel('')
        self.online_badge.setObjectName('onlineBadge')
        layout.addWidget(self.online_badge, 0, Qt.AlignVCenter)

        self.system_button = QToolButton()
        self.system_button.setText('⋯')
        self.system_button.setObjectName('topBarMenuButton')
        self.system_button.setPopupMode(QToolButton.InstantPopup)
        layout.addWidget(self.system_button, 0, Qt.AlignVCenter)
        return box

    def _build_left_sidebar(self) -> QWidget:
        box = QWidget()
        box.setObjectName('leftSidebar')
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 18, 12, 18)
        layout.setSpacing(14)

        layout.addWidget(self._section_title('Среда'))
        self.environment_label = QLabel('')
        self.environment_label.setObjectName('sidebarText')
        self.environment_label.setWordWrap(True)
        layout.addWidget(self.environment_label)

        layout.addWidget(self._section_title('Фильтры'))
        self.filter_mode_label = QLabel('Все сообщения')
        self.filter_mode_label.setObjectName('sidebarTextMuted')
        layout.addWidget(self.filter_mode_label)

        layout.addWidget(self._section_title('Последние артефакты'))
        self.artifact_list = QListWidget()
        self.artifact_list.setObjectName('artifactList')
        self.artifact_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.artifact_list.itemDoubleClicked.connect(self._open_selected_artifact)
        layout.addWidget(self.artifact_list, 1)

        layout.addWidget(self._section_title('Хост и участники'))
        self.presence_label = QLabel('')
        self.presence_label.setObjectName('sidebarText')
        self.presence_label.setWordWrap(True)
        layout.addWidget(self.presence_label)

        layout.addStretch(1)

        self.user_button = QToolButton()
        self.user_button.setObjectName('userMenuButton')
        self.user_button.setPopupMode(QToolButton.InstantPopup)
        self.user_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        layout.addWidget(self.user_button, 0, Qt.AlignLeft)
        return box

    def _build_center_shell(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(12)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.filter_buttons: dict[str, QPushButton] = {}
        for mode, title in [('all', 'Все'), ('mine', 'Мои'), ('running', 'В работе'), ('success', 'Успешные'), ('errors', 'Ошибки')]:
            button = QPushButton(title)
            button.setCheckable(True)
            button.setObjectName('filterPill')
            button.clicked.connect(lambda checked=False, value=mode: self._set_filter_mode(value))
            self.filter_buttons[mode] = button
            filters.addWidget(button)
        filters.addStretch(1)
        layout.addLayout(filters)

        self.feed_list = QListWidget()
        self.feed_list.setObjectName('feedList')
        self.feed_list.setSpacing(10)
        self.feed_list.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.feed_list, 1)

        bottom = QWidget()
        bottom.setObjectName('composerShell')
        composer_layout = QHBoxLayout(bottom)
        composer_layout.setContentsMargins(12, 10, 12, 10)
        composer_layout.setSpacing(10)
        self.composer = ScenarioComposer()
        self.composer.submitted.connect(self._run_selected_scenario)
        composer_layout.addWidget(self.composer, 1)
        self.run_button = QPushButton('Запустить')
        self.run_button.setObjectName('primaryRunButton')
        self.run_button.clicked.connect(self._run_selected_scenario)
        composer_layout.addWidget(self.run_button, 0, Qt.AlignBottom)
        layout.addWidget(bottom)

        self._set_filter_mode('all')
        return box

    def _build_right_sidebar(self) -> QWidget:
        box = QWidget()
        box.setObjectName('rightSidebar')
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 18, 18, 18)
        layout.setSpacing(12)

        title = QHBoxLayout()
        title.addWidget(self._section_title('Сценарии'))
        title.addStretch(1)
        layout.addLayout(title)

        self.scenario_search = QLineEdit()
        self.scenario_search.setObjectName('scenarioSearch')
        self.scenario_search.setPlaceholderText('Поиск сценария')
        self.scenario_search.textChanged.connect(self._populate_scenario_tree)
        layout.addWidget(self.scenario_search)

        self.scenario_tree = QTreeWidget()
        self.scenario_tree.setHeaderHidden(True)
        self.scenario_tree.setObjectName('scenarioTree')
        self.scenario_tree.itemSelectionChanged.connect(self._scenario_selection_changed)
        layout.addWidget(self.scenario_tree, 1)
        return box

    def _build_menus(self) -> None:
        system_menu = QMenu(self)
        action_refresh = QAction('Обновить состояние', self)
        action_refresh.triggered.connect(self._refresh_state)
        system_menu.addAction(action_refresh)
        action_diag = QAction('Диагностика', self)
        action_diag.triggered.connect(self._show_diagnostics)
        system_menu.addAction(action_diag)
        action_copy = QAction('Скопировать диагностику', self)
        action_copy.triggered.connect(self._copy_diagnostics)
        system_menu.addAction(action_copy)
        system_menu.addSeparator()
        action_exit = QAction('Выход', self)
        action_exit.triggered.connect(self.close)
        system_menu.addAction(action_exit)
        self.system_button.setMenu(system_menu)

        user_menu = QMenu(self)
        action_online = QAction('Кто online', self)
        action_online.triggered.connect(self._show_online_info)
        user_menu.addAction(action_online)
        action_participants = QAction('Участники', self)
        action_participants.triggered.connect(self._show_participants_dialog)
        user_menu.addAction(action_participants)
        user_menu.addSeparator()
        action_my = QAction('Показать мои сообщения', self)
        action_my.triggered.connect(self._filter_my_messages)
        user_menu.addAction(action_my)
        action_all = QAction('Показать все сообщения', self)
        action_all.triggered.connect(lambda: self._filter_by_participant(None))
        user_menu.addAction(action_all)
        self.user_button.setMenu(user_menu)

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName('sidebarSectionTitle')
        return label

    def _seed_feed(self) -> None:
        if self.context.session_snapshot and self.context.session_snapshot.app_state and self.context.session_snapshot.app_state.last_scenario_title:
            title = self.context.session_snapshot.app_state.last_scenario_title
            self._append_feed_entries([
                FeedEntry(
                    entry_id='resume:last',
                    kind='system_notice',
                    status='info',
                    title='Последняя сессия',
                    body=f'Последний сценарий: {title}',
                    created_at=self._now(),
                    author_id=self.context.user_id,
                    author_label=self.context.account_name or 'Пользователь',
                    outputs=self.context.session_snapshot.app_state.last_outputs,
                    meta={'вид': 'resume'},
                )
            ])
        else:
            self._append_feed_entries([
                FeedEntry(
                    entry_id='welcome',
                    kind='system_notice',
                    status='info',
                    title='Рабочая поверхность готова',
                    body='Выберите сценарий справа. Параметры появятся внизу, запуск уйдёт в общую ленту.',
                    created_at=self._now(),
                    author_id=self.context.user_id,
                    author_label=self.context.account_name or 'Пользователь',
                    meta={'режим': self.runtime.appdock_bridge.host_mode_label()},
                )
            ])
        self._refresh_feed()
        self._refresh_recent_artifacts()

    def _populate_scenario_tree(self) -> None:
        current = self._selected_scenario_id
        self.scenario_tree.clear()
        grouped = group_scenarios(self.runtime.scenario_registry, search=self.scenario_search.text())
        selected_item: QTreeWidgetItem | None = None
        for group_name, items in grouped.items():
            group_item = QTreeWidgetItem([group_name])
            group_item.setData(0, Qt.UserRole, None)
            self.scenario_tree.addTopLevelItem(group_item)
            for scenario in items:
                item = QTreeWidgetItem([scenario.title])
                item.setData(0, Qt.UserRole, scenario.id)
                item.setToolTip(0, scenario.description)
                group_item.addChild(item)
                if scenario.id == current:
                    selected_item = item
            group_item.setExpanded(True)
        if selected_item is not None:
            self.scenario_tree.setCurrentItem(selected_item)
        elif self.scenario_tree.topLevelItemCount() > 0 and self.scenario_tree.topLevelItem(0).childCount() > 0:
            self.scenario_tree.setCurrentItem(self.scenario_tree.topLevelItem(0).child(0))

    def _scenario_selection_changed(self) -> None:
        item = self.scenario_tree.currentItem()
        if item is None:
            self._selected_scenario_id = None
            self.composer.set_scenario(None)
            return
        scenario_id = item.data(0, Qt.UserRole)
        if not scenario_id:
            return
        spec = self.runtime.scenario_registry.get(str(scenario_id))
        self._selected_scenario_id = spec.id
        self.composer.set_scenario(spec)
        self.runtime.preferences.save(last_scenario_id=spec.id)

    def _selected_scenario(self) -> ScenarioSpec | None:
        if not self._selected_scenario_id:
            return None
        if not self.runtime.scenario_registry.has(self._selected_scenario_id):
            return None
        return self.runtime.scenario_registry.get(self._selected_scenario_id)

    def _run_selected_scenario(self) -> None:
        spec = self._selected_scenario()
        if spec is None:
            return
        if self.runtime.run_coordinator.is_busy:
            QMessageBox.information(self, 'Strategy Box', 'Сначала дождитесь завершения текущего запуска.')
            return
        try:
            params = self.composer.collect_params()
        except Exception as exc:
            QMessageBox.warning(self, 'Strategy Box', str(exc))
            return
        self.runtime.surface_state.update_runtime(
            active_view='timeline',
            selected_object=spec.id,
            active_job=spec.id,
            last_scenario_id=spec.id,
            last_scenario_title=spec.title,
            recent_artifacts=tuple(self._recent_artifacts),
        )
        lifecycle = self.runtime.run_coordinator.submit(spec, params)
        self.run_button.setEnabled(False)
        self._append_feed_entries(lifecycle.timeline_entries)

    def _on_run_finished(self, payload: object) -> None:
        lifecycle = payload
        self.run_button.setEnabled(True)
        self._append_feed_entries(lifecycle.timeline_entries)
        scenario_result: ScenarioResult | None = lifecycle.scenario_result
        if scenario_result is not None:
            self._last_result_message = scenario_result.message
            for output in scenario_result.outputs:
                if output not in self._recent_artifacts:
                    self._recent_artifacts.insert(0, output)
            self._recent_artifacts = self._recent_artifacts[:12]
            self._refresh_recent_artifacts()
            self.runtime.surface_state.update_runtime(
                active_view='timeline',
                selected_object=lifecycle.run_record.scenario_id,
                active_job=None,
                last_scenario_id=lifecycle.run_record.scenario_id,
                last_scenario_title=lifecycle.run_record.scenario_title,
                last_scenario_ok=scenario_result.ok,
                last_outputs=scenario_result.outputs,
                last_scenario_log=(next((item for item in scenario_result.outputs if item.endswith('.log')), None)),
                recent_artifacts=tuple(self._recent_artifacts),
            )

    def _append_feed_entries(self, entries: Iterable[FeedEntry]) -> None:
        for entry in entries:
            self.runtime.feed_store.append(entry)
            self.runtime.presence_service.register_feed_entry(entry)
        self._refresh_feed()
        self._refresh_context_views()

    def _refresh_feed(self) -> None:
        self.feed_list.clear()
        for entry in self.runtime.feed_store.visible_entries():
            item = QListWidgetItem()
            card = FeedCard(entry, on_action=self._handle_feed_action)
            item.setSizeHint(card.sizeHint())
            self.feed_list.addItem(item)
            self.feed_list.setItemWidget(item, card)
        self.feed_list.scrollToBottom()

    def _handle_feed_action(self, entry: FeedEntry, action: FeedAction) -> None:
        payload = action.payload
        if action.id == 'open_primary' and payload:
            self.runtime.platform.open_path(payload)
        elif action.id == 'open_folder' and payload:
            self.runtime.platform.open_path(str(Path(payload).parent))
        elif action.id == 'copy_path' and payload:
            self.runtime.platform.copy_text(payload)
            self._append_feed_entries([
                FeedEntry(
                    entry_id=f'notice:copy:{payload}',
                    kind='system_notice',
                    status='info',
                    title='Путь скопирован',
                    body=payload,
                    created_at=self._now(),
                    author_id=self.context.user_id,
                    author_label=self.context.account_name or 'Пользователь',
                )
            ])
        elif action.id == 'repeat_run' and payload:
            self._select_scenario(str(payload))

    def _select_scenario(self, scenario_id: str) -> None:
        matches = self.scenario_tree.findItems('', Qt.MatchContains | Qt.MatchRecursive)
        for item in matches:
            if item.data(0, Qt.UserRole) == scenario_id:
                self.scenario_tree.setCurrentItem(item)
                self.scenario_tree.scrollToItem(item)
                return

    def _set_filter_mode(self, mode: str) -> None:
        self.runtime.feed_store.set_mode(mode)
        for key, button in self.filter_buttons.items():
            button.setChecked(key == mode)
        titles = {
            'all': 'Все сообщения',
            'mine': 'Мои сообщения',
            'running': 'Сценарии в работе',
            'success': 'Успешные сообщения',
            'errors': 'Сообщения с ошибками',
        }
        self.filter_mode_label.setText(titles.get(mode, 'Все сообщения'))
        self._refresh_feed()

    def _filter_by_participant(self, participant_id: str | None) -> None:
        self.runtime.feed_store.set_author(participant_id)
        if participant_id:
            participant = self.runtime.presence_service.participant_by_id(participant_id)
            self.filter_mode_label.setText(f'Автор: {participant.display_name if participant else participant_id}')
        else:
            self.filter_mode_label.setText('Все сообщения')
        self._refresh_feed()

    def _filter_my_messages(self) -> None:
        self.runtime.feed_store.set_author(self.context.user_id or 'local-user')
        self._set_filter_mode('mine')

    def _show_online_info(self) -> None:
        participants = [item.display_name for item in self.runtime.presence_service.participants() if item.is_online]
        if not participants:
            QMessageBox.information(self, 'Кто online', 'Сейчас никто не отмечен как online.')
            return
        QMessageBox.information(self, 'Кто online', '\n'.join(participants))

    def _show_participants_dialog(self) -> None:
        dialog = ParticipantsDialog(self.runtime.presence_service.participants(), self)
        if dialog.exec() == QDialog.Accepted:
            self._filter_by_participant(dialog.selected_participant_id)

    def _refresh_recent_artifacts(self) -> None:
        self.artifact_list.clear()
        for artifact in self._recent_artifacts:
            self.artifact_list.addItem(artifact)

    def _refresh_state(self) -> None:
        self.runtime.presence_service.mark_refreshed()
        self._refresh_context_views()
        self._append_feed_entries([
            FeedEntry(
                entry_id=f'refresh:{self._now().timestamp()}',
                kind='system_notice',
                status='info',
                title='Состояние обновлено',
                body='Локальный срез поверхности обновлён.',
                created_at=self._now(),
                author_id=self.context.user_id,
                author_label=self.context.account_name or 'Пользователь',
            )
        ])

    def _refresh_context_views(self) -> None:
        mode = self.runtime.appdock_bridge.host_mode_label()
        workspace_root = str(self.context.workspace_root_path) if self.context.workspace_root_path else '—'
        selector = str(self.context.data_root_selector_path) if self.context.data_root_selector_path else '—'
        self.mode_label.setText(f'{mode} · workspace {self.context.workspace_schema.title}')
        self.online_badge.setText(f'● {self.runtime.presence_service.online_count()} online')
        self.environment_label.setText(
            f'Workspace: {workspace_root}\n'
            f'Selector: {selector}\n'
            f'Режим: {mode}\n'
            f'Node: {self.context.node_id or "-"}'
        )
        current_user = self.context.account_name or self.context.user_id or 'Пользователь'
        self.user_button.setText(current_user)
        participants = self.runtime.presence_service.participants()
        presence_lines = [
            f'Online: {self.runtime.presence_service.online_count()}',
            f'Host: {self.context.host_name or "-"}',
            f'Участников: {len(participants)}',
        ]
        self.presence_label.setText('\n'.join(presence_lines))

    def _show_diagnostics(self) -> None:
        dialog = DiagnosticsDialog(build_diagnostics_text(self.context), self)
        dialog.exec()

    def _copy_diagnostics(self) -> None:
        text = build_diagnostics_text(self.context)
        self.runtime.platform.copy_text(text)
        QMessageBox.information(self, 'Strategy Box', 'Диагностика скопирована в буфер обмена.')

    def _open_selected_artifact(self, *_args) -> None:
        item = self.artifact_list.currentItem()
        if item is None:
            return
        self.runtime.platform.open_path(item.text())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.runtime.preferences.save(
            width=self.width(),
            height=self.height(),
            splitter_sizes=self.main_splitter.sizes(),
            last_scenario_id=self._selected_scenario_id,
        )
        self.runtime.surface_state.update_runtime(
            active_view='closed',
            selected_object=self._selected_scenario_id,
            active_job=None,
            recent_artifacts=tuple(self._recent_artifacts),
        )
        self.runtime.surface_state.mark_closed(clean_shutdown=True)
        super().closeEvent(event)

    @staticmethod
    def _now():
        from datetime import datetime

        return datetime.now()
