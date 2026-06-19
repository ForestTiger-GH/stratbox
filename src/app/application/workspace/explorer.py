from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.runtime.context import AppContext


@dataclass(frozen=True, slots=True)
class WorkspaceExplorerSection:
    id: str
    title: str
    path: Path
    description: str = ''
    show_children: bool = True


def build_workspace_explorer_sections(context: AppContext) -> tuple[WorkspaceExplorerSection, ...]:
    root = context.workspace_root_path
    if root is None:
        return tuple()
    sections: list[WorkspaceExplorerSection] = [
        WorkspaceExplorerSection('workspace_root', 'Рабочий каталог', root, 'Корень пользовательских данных Strategy Box.', True),
    ]
    for name in context.workspace_schema.required_dirs:
        title = {'input': 'Входные данные', 'output': 'Результаты'}.get(name, name)
        sections.append(WorkspaceExplorerSection(name, title, root / name, f'Обязательный раздел workspace: {name}', True))
    return tuple(sections)
