from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QCloseEvent, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QScrollArea,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.runtime.bootstrap import AppRuntime
from app.presentation.chat.projector import ChatProjector
from app.presentation.chat.widgets import ChatThreadView
from app.presentation.desktop.chat_scene import ChatSceneHost
from app.application.presence.models import ParticipantRecord
from app.application.product.catalog.grouping import group_operations
from app.presentation.forms.panel import OperationFormPanel
from app.application.product.catalog.models import ProductOperationSpec
from app.application.product.execution.requests import ProductResult
from app.application.system.commands import build_diagnostics_text
from app.application.timeline.models import FeedAction, FeedEntry
from app.application.workspace import run_workspace_diagnostics



def _chat_background_image_path() -> Path:
    return Path(__file__).resolve().parents[2] / 'resources' / 'images' / 'chat_history_background.png'


class ParticipantsDialog(QDialog):
    def __init__(self, participants: tuple[ParticipantRecord, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Участники')
        self.setModal(True)
        self.resize(520, 420)
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
            item.setForeground(QBrush(QColor(participant.accent_color)))
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


class SystemDialog(QDialog):
    def __init__(
        self,
        *,
        environment_text: str,
        host_text: str,
        on_refresh,
        on_show_diagnostics,
        on_copy_diagnostics,
        on_show_participants,
        on_exit,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle('Система')
        self.setModal(True)
        self.resize(620, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        layout.addWidget(self._section('Среда', environment_text))

        host_frame = self._section('Хост и участники', host_text)
        host_box = host_frame.layout()
        participants_button = QPushButton('Участники')
        participants_button.clicked.connect(on_show_participants)
        host_box.addWidget(participants_button)
        layout.addWidget(host_frame)

        actions_frame = QFrame()
        actions_frame.setObjectName('systemDialogCard')
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(16, 16, 16, 16)
        actions_layout.setSpacing(10)

        title = QLabel('Действия')
        title.setObjectName('systemDialogSectionTitle')
        actions_layout.addWidget(title)

        refresh_button = QPushButton('Обновить состояние')
        refresh_button.clicked.connect(on_refresh)
        actions_layout.addWidget(refresh_button)

        diagnostics_button = QPushButton('Диагностика')
        diagnostics_button.clicked.connect(on_show_diagnostics)
        actions_layout.addWidget(diagnostics_button)

        copy_button = QPushButton('Скопировать диагностику')
        copy_button.clicked.connect(on_copy_diagnostics)
        actions_layout.addWidget(copy_button)

        exit_button = QPushButton('Выход')
        exit_button.clicked.connect(on_exit)
        actions_layout.addWidget(exit_button)

        layout.addWidget(actions_frame)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close_button = QPushButton('Закрыть')
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _section(self, title_text: str, body_text: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName('systemDialogCard')
        box = QVBoxLayout(frame)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(8)
        title = QLabel(title_text)
        title.setObjectName('systemDialogSectionTitle')
        box.addWidget(title)
        body = QLabel(body_text)
        body.setObjectName('systemDialogBody')
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        box.addWidget(body)
        return frame


class MainWindow(QMainWindow):
    def __init__(self, runtime: AppRuntime):
        super().__init__()
        self.runtime = runtime
        self.context = runtime.context
        self._selected_operation_id: str | None = runtime.context.user_config.last_operation_id
        self._recent_artifacts: list[str] = list(self.context.session_snapshot.runtime_state.recent_artifacts) if self.context.session_snapshot and self.context.session_snapshot.runtime_state else []
        self._last_result_message = ''
        self.chat_projector = ChatProjector(context=self.context, presence_service=self.runtime.presence_service)
        self._build_ui()
        self._build_menus()
        self._populate_operation_tree()
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

        self.main_splitter.addWidget(self.left_sidebar)
        self.main_splitter.addWidget(self.center_shell)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)
        self.left_sidebar.setMinimumWidth(336)
        self.left_sidebar.setMaximumWidth(336)
        self.main_splitter.setSizes([336, 984])

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
        return box

    def _build_left_sidebar(self) -> QWidget:
        container = QWidget()
        container.setObjectName('leftSidebarShell')
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName('leftSidebarScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        box = QWidget()
        box.setObjectName('leftSidebar')
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 18, 12, 18)
        layout.setSpacing(14)

        layout.addWidget(self._section_title('Операции'))

        self.operation_tree = QTreeWidget()
        self.operation_tree.setHeaderHidden(True)
        self.operation_tree.setRootIsDecorated(False)
        self.operation_tree.setItemsExpandable(False)
        self.operation_tree.setIndentation(0)
        self.operation_tree.setObjectName('operationTree')
        self.operation_tree.itemSelectionChanged.connect(self._operation_selection_changed)
        layout.addWidget(self.operation_tree, 1)

        layout.addWidget(self._section_title('Последние артефакты'))
        self.artifact_list = QListWidget()
        self.artifact_list.setObjectName('artifactList')
        self.artifact_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.artifact_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.artifact_list.itemDoubleClicked.connect(self._open_selected_artifact)
        layout.addWidget(self.artifact_list, 0)

        layout.addStretch(1)
        scroll.setWidget(box)
        outer.addWidget(scroll, 1)

        anchor_block = QWidget()
        anchor_block.setObjectName('leftSidebarAnchor')
        anchor_layout = QVBoxLayout(anchor_block)
        anchor_layout.setContentsMargins(18, 14, 12, 14)
        anchor_layout.setSpacing(8)

        self.other_online_label = QLabel('')
        self.other_online_label.setObjectName('userOnlineNames')
        self.other_online_label.setTextFormat(Qt.RichText)
        self.other_online_label.setWordWrap(True)
        self.other_online_label.hide()
        anchor_layout.addWidget(self.other_online_label)

        self.system_side_button = QPushButton('Система')
        self.system_side_button.setObjectName('systemSideButton')
        self.system_side_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.system_side_button.clicked.connect(self._show_system_dialog)
        anchor_layout.addWidget(self.system_side_button)

        outer.addWidget(anchor_block, 0)
        return container

    def _build_center_shell(self) -> QWidget:
        scene_host = ChatSceneHost(_chat_background_image_path())

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
        scene_host.content_layout.addLayout(filters)

        self.feed_host = QWidget()
        self.feed_host.setObjectName('feedAreaHost')
        feed_layout = QVBoxLayout(self.feed_host)
        feed_layout.setContentsMargins(0, 0, 0, 0)
        feed_layout.setSpacing(0)

        self.chat_thread = ChatThreadView(on_action=self._handle_feed_action)
        self.chat_thread.setObjectName('chatThreadView')
        feed_layout.addWidget(self.chat_thread)

        scene_host.content_layout.addWidget(self.feed_host, 1)

        bottom = QWidget()
        bottom.setObjectName('composerShell')
        composer_layout = QVBoxLayout(bottom)
        composer_layout.setContentsMargins(12, 10, 12, 10)
        composer_layout.setSpacing(10)
        self.composer = OperationFormPanel(preferences=self.runtime.preferences)
        self.composer.submitted.connect(self._run_selected_operation)
        composer_layout.addWidget(self.composer, 1)

        composer_actions = QHBoxLayout()
        composer_actions.setContentsMargins(0, 0, 0, 0)
        composer_actions.setSpacing(10)
        composer_actions.addStretch(1)
        self.run_button = QPushButton('Запустить')
        self.run_button.setObjectName('primaryRunButton')
        self.run_button.clicked.connect(self._run_selected_operation)
        composer_actions.addWidget(self.run_button, 0, Qt.AlignRight)
        composer_layout.addLayout(composer_actions)

        scene_host.content_layout.addWidget(bottom)

        self._set_filter_mode('all')
        return scene_host


    def _build_menus(self) -> None:
        return

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName('sidebarSectionTitle')
        return label

    def _seed_feed(self) -> None:
        if self.context.session_snapshot and self.context.session_snapshot.runtime_state and self.context.session_snapshot.runtime_state.last_operation_title:
            title = self.context.session_snapshot.runtime_state.last_operation_title
            self._append_feed_entries([
                FeedEntry(
                    entry_id='resume:last',
                    kind='system_notice',
                    status='info',
                    title='Последняя сессия',
                    body=f'Последняя операция: {title}',
                    created_at=self._now(),
                    author_id=self.context.user_id,
                    author_label=self.context.account_name or 'Пользователь',
                    outputs=self.context.session_snapshot.runtime_state.last_outputs,
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
                    body='Выберите операцию слева. Параметры появятся внизу, запуск уйдёт в общую ленту.',
                    created_at=self._now(),
                    author_id=self.context.user_id,
                    author_label=self.context.account_name or 'Пользователь',
                    meta={'режим': self.runtime.appdock_bridge.host_mode_label()},
                )
            ])
        self._refresh_feed(force_scroll_to_bottom=True)
        self._refresh_recent_artifacts()

    def _populate_operation_tree(self) -> None:
        current = self._selected_operation_id
        self.operation_tree.clear()
        grouped = group_operations(self.runtime.product_registry)
        selected_item: QTreeWidgetItem | None = None
        for group_name, items in grouped.items():
            group_item = QTreeWidgetItem([group_name])
            group_item.setData(0, Qt.UserRole, None)
            group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
            self.operation_tree.addTopLevelItem(group_item)
            for operation in items:
                item = QTreeWidgetItem([operation.title])
                item.setData(0, Qt.UserRole, operation.id)
                item.setToolTip(0, operation.description)
                group_item.addChild(item)
                if operation.id == current:
                    selected_item = item
            group_item.setExpanded(True)
        if selected_item is not None:
            self.operation_tree.setCurrentItem(selected_item)
        elif self.operation_tree.topLevelItemCount() > 0 and self.operation_tree.topLevelItem(0).childCount() > 0:
            self.operation_tree.setCurrentItem(self.operation_tree.topLevelItem(0).child(0))

    def _operation_selection_changed(self) -> None:
        item = self.operation_tree.currentItem()
        if item is None:
            self._selected_operation_id = None
            self.composer.set_operation(None)
            return
        operation_id = item.data(0, Qt.UserRole)
        if not operation_id:
            return
        spec = self.runtime.product_registry.get(str(operation_id))
        self._selected_operation_id = spec.id
        self.composer.set_operation(spec)
        self.runtime.preferences.save(last_operation_id=spec.id)
        self.run_button.setText(spec.submit_label)

    def _selected_operation(self) -> ProductOperationSpec | None:
        if not self._selected_operation_id:
            return None
        if not self.runtime.product_registry.has(self._selected_operation_id):
            return None
        return self.runtime.product_registry.get(self._selected_operation_id)

    def _run_selected_operation(self) -> None:
        spec = self._selected_operation()
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
            last_operation_id=spec.id,
            last_operation_title=spec.title,
            recent_artifacts=tuple(self._recent_artifacts),
        )
        lifecycle = self.runtime.run_coordinator.submit(spec, params)
        self.run_button.setEnabled(False)
        self._append_feed_entries(lifecycle.timeline_entries)

    def _on_run_finished(self, payload: object) -> None:
        lifecycle = payload
        self.run_button.setEnabled(True)
        self._append_feed_entries(lifecycle.timeline_entries)
        operation_result: ProductResult | None = lifecycle.operation_result
        if operation_result is not None:
            self._last_result_message = operation_result.message
            for output in operation_result.outputs:
                if output not in self._recent_artifacts:
                    self._recent_artifacts.insert(0, output)
            self._recent_artifacts = self._recent_artifacts[:12]
            self._refresh_recent_artifacts()
            self.runtime.surface_state.update_runtime(
                active_view='timeline',
                selected_object=lifecycle.run_record.operation_id,
                active_job=None,
                last_operation_id=lifecycle.run_record.operation_id,
                last_operation_title=lifecycle.run_record.operation_title,
                last_operation_ok=operation_result.ok,
                last_outputs=operation_result.outputs,
                last_operation_log=(next((item for item in operation_result.outputs if item.endswith('.log')), None)),
                recent_artifacts=tuple(self._recent_artifacts),
            )

    def _append_feed_entries(self, entries: Iterable[FeedEntry]) -> None:
        for entry in entries:
            self.runtime.feed_store.append(entry)
            self.runtime.presence_service.register_feed_entry(entry)
        self._refresh_feed(force_scroll_to_bottom=True)
        self._refresh_context_views()

    def _refresh_feed(self, *, force_scroll_to_bottom: bool = False) -> None:
        was_near_bottom = force_scroll_to_bottom or self.chat_thread.is_near_bottom()
        messages = [self.chat_projector.project(entry) for entry in self.runtime.feed_store.visible_entries()]
        self.chat_thread.set_messages(messages)
        if was_near_bottom:
            self.chat_thread.scroll_to_bottom()

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
            self._select_operation(str(payload))

    def _select_operation(self, operation_id: str) -> None:
        matches = self.operation_tree.findItems('', Qt.MatchContains | Qt.MatchRecursive)
        for item in matches:
            if item.data(0, Qt.UserRole) == operation_id:
                self.operation_tree.setCurrentItem(item)
                self.operation_tree.scrollToItem(item)
                return

    def _set_filter_mode(self, mode: str) -> None:
        self.runtime.feed_store.set_mode(mode)
        for key, button in self.filter_buttons.items():
            button.setChecked(key == mode)
        self._refresh_feed()

    def _filter_by_participant(self, participant_id: str | None) -> None:
        self.runtime.feed_store.set_author(participant_id)
        self._refresh_feed()

    def _filter_my_messages(self) -> None:
        self.runtime.feed_store.set_author(self.context.user_id or 'local-user')
        self._set_filter_mode('mine')

    def _show_participants_dialog(self) -> None:
        dialog = ParticipantsDialog(self.runtime.presence_service.participants(), self)
        if dialog.exec() == QDialog.Accepted:
            self._filter_by_participant(dialog.selected_participant_id)

    def _refresh_recent_artifacts(self) -> None:
        self.artifact_list.clear()
        visible_artifacts = self._recent_artifacts[:3]
        for artifact in visible_artifacts:
            self.artifact_list.addItem(artifact)
        row_count = max(1, len(visible_artifacts))
        row_height = max(self.artifact_list.sizeHintForRow(0), 26) if visible_artifacts else 26
        frame = self.artifact_list.frameWidth() * 2
        self.artifact_list.setFixedHeight((row_height * row_count) + frame + 4)

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

    def _build_environment_text(self) -> str:
        mode = self.runtime.appdock_bridge.host_mode_label()
        workspace_root = str(self.context.workspace_root_path) if self.context.workspace_root_path else '—'
        selector = str(self.context.data_root_selector_path) if self.context.data_root_selector_path else '—'
        return (
            f'Workspace: {workspace_root}<br>'
            f'Selector: {selector}<br>'
            f'Режим: {mode}<br>'
            f'Node: {self.context.node_id or "-"}'
        )

    def _build_host_text(self) -> str:
        participants = self.runtime.presence_service.participants()
        if participants:
            chunks = []
            for item in participants:
                status = 'online' if item.is_online else (item.last_seen_label or 'offline')
                chunks.append(f'<span style="color:{item.accent_color};">{item.display_name}</span> · {status}')
            people = '<br>'.join(chunks)
        else:
            people = 'Участники пока отсутствуют.'
        return (
            f'Host: {self.context.host_name or "-"}<br>'
            f'Участников: {len(participants)}<br><br>'
            f'{people}'
        )

    def _refresh_context_views(self) -> None:
        mode = self.runtime.appdock_bridge.host_mode_label()
        self.mode_label.setText(f'{mode} · workspace {self.context.workspace_schema.title}')
        others_html = self.runtime.presence_service.other_online_html()
        if others_html:
            self.other_online_label.setText(others_html)
            self.other_online_label.show()
        else:
            self.other_online_label.clear()
            self.other_online_label.hide()

    def _show_system_dialog(self) -> None:
        dialog = SystemDialog(
            environment_text=self._build_environment_text(),
            host_text=self._build_host_text(),
            on_refresh=self._refresh_state,
            on_show_diagnostics=self._show_diagnostics,
            on_copy_diagnostics=self._copy_diagnostics,
            on_show_participants=self._show_participants_dialog,
            on_exit=self.close,
            parent=self,
        )
        dialog.exec()

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
            last_operation_id=self._selected_operation_id,
        )
        self.runtime.surface_state.update_runtime(
            active_view='closed',
            selected_object=self._selected_operation_id,
            active_job=None,
            recent_artifacts=tuple(self._recent_artifacts),
        )
        self.runtime.surface_state.mark_closed(clean_shutdown=True)
        super().closeEvent(event)

    @staticmethod
    def _now():
        from datetime import datetime

        return datetime.now()
