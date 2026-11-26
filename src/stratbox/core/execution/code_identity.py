"""Content identities of trusted callable code and its reachable helpers."""
from types import CodeType, FunctionType, ModuleType
import inspect

from stratbox.shared.data.values import fingerprint


def _code(code):
    constants = tuple(_code(item) if isinstance(item, CodeType) else item
        for index, item in enumerate(code.co_consts) if not (index == 0 and isinstance(item, str)))
    return code.co_code, constants, code.co_names, code.co_varnames, code.co_freevars


def code_identity(method):
    method = method.resolve() if hasattr(method, "resolve") else method
    root = getattr(method, "__module__", "").split(".")[0]
    seen, records = set(), []
    def visit(function):
        if not isinstance(function, FunctionType) or id(function) in seen: return
        seen.add(id(function))
        closure = []
        for cell in function.__closure__ or ():
            try:
                value = cell.cell_contents
                if not isinstance(value, FunctionType): closure.append(value)
            except ValueError: pass
        records.append((function.__module__, function.__qualname__, _code(function.__code__),
            fingerprint((function.__defaults__, function.__kwdefaults__, tuple(closure)))))
        for name in function.__code__.co_names:
            dependency = function.__globals__.get(name)
            if isinstance(dependency, FunctionType) and dependency.__module__.split(".")[0] in {"stratbox", root}:
                visit(dependency)
            elif isinstance(dependency, ModuleType) and dependency.__name__.split(".")[0] in {"stratbox", root}:
                for attribute in function.__code__.co_names:
                    visit(vars(dependency).get(attribute))
        wrapped = getattr(function, "__wrapped__", None)
        visit(wrapped)
        for cell in function.__closure__ or ():
            try: visit(cell.cell_contents)
            except ValueError: pass
    visit(method)
    return fingerprint(tuple(sorted(records))) if records else fingerprint((getattr(method,"__module__",""), getattr(method,"__qualname__",type(method).__qualname__)))
