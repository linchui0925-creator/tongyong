"""
ToolRegistry - 工具注册中心

每个工具模块在模块级调用 registry.register() 自注册。
registry 自动发现 implementations/ 下的工具模块。
"""

import ast
import importlib
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

logger = logging.getLogger(__name__)

_TOOLS_DIR = Path(__file__).resolve().parent / "implementations"


class ToolEntry:
    """单个工具的元数据"""

    __slots__ = (
        "name", "description", "schema", "handler", "check_fn",
        "is_async", "emoji", "max_result_size_chars", "parallel_mode",
    )

    def __init__(
        self,
        name: str,
        description: str,
        schema: dict,
        handler: Callable,
        check_fn: Optional[Callable] = None,
        is_async: bool = True,
        emoji: str = "",
        max_result_size_chars: Optional[int] = None,
        parallel_mode: str = "never",
    ):
        self.name = name
        self.description = description
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.is_async = is_async
        self.emoji = emoji
        self.max_result_size_chars = max_result_size_chars
        self.parallel_mode = parallel_mode  # "never" | "safe" | "path_scoped"


class ToolRegistry:
    """工具注册中心（单例）"""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}

    # ── 注册 ──────────────────────────────────────────────

    def register(
        self,
        name: str,
        description: str,
        schema: dict,
        handler: Callable,
        check_fn: Optional[Callable] = None,
        is_async: bool = True,
        emoji: str = "",
        max_result_size_chars: Optional[int] = None,
        parallel_mode: str = "never",
    ):
        if name in self._tools:
            logger.warning(f"工具 '{name}' 重复注册，覆盖")
        self._tools[name] = ToolEntry(
            name=name,
            description=description,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            is_async=is_async,
            emoji=emoji,
            max_result_size_chars=max_result_size_chars,
            parallel_mode=parallel_mode,
        )

    def deregister(self, name: str):
        self._tools.pop(name, None)

    # ── 查询 ──────────────────────────────────────────────

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """返回所有可用工具的 OpenAI function calling schema"""
        result = []
        for entry in self._tools.values():
            if entry.check_fn:
                try:
                    if not entry.check_fn():
                        continue
                except Exception:
                    continue
            result.append({
                "type": "function",
                "function": {
                    "name": entry.name,
                    "description": entry.description,
                    "parameters": entry.schema,
                }
            })
        return result

    # ── 执行 ──────────────────────────────────────────────

    async def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        entry = self._tools.get(name)
        if not entry:
            logger.warning(f"工具 '{name}' 未注册，当前已注册工具: {list(self._tools.keys())}")
            return f"未知工具: {name}"
        try:
            if entry.is_async:
                result = await entry.handler(**arguments)
            else:
                result = entry.handler(**arguments)

            max_chars = entry.max_result_size_chars
            if max_chars and isinstance(result, str) and len(result) > max_chars:
                result = result[:max_chars] + f"\n...（结果过长，已截断至 {max_chars} 字符）"
            return str(result)
        except Exception as e:
            logger.error(f"工具 '{name}' 执行失败: {e}", exc_info=True)
            return f"工具执行失败: {e}"

    def get_emoji(self, name: str, default: str = "⚡") -> str:
        """获取工具 emoji"""
        entry = self._tools.get(name)
        return entry.emoji if entry and entry.emoji else default

    def get_parallel_mode(self, name: str) -> str:
        """获取工具的并行模式：never | safe | path_scoped"""
        entry = self._tools.get(name)
        return entry.parallel_mode if entry else "never"

    def classify_tool_calls(self, tool_calls: List[Dict]) -> Dict[str, List[Dict]]:
        """按并行模式对工具调用进行分组

        Returns:
            {"never": [...], "safe": [...], "path_scoped": [...]}
        """
        groups: Dict[str, List[Dict]] = {"never": [], "safe": [], "path_scoped": []}
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name") or tc.get("name", "")
            mode = self.get_parallel_mode(tool_name)
            if mode not in groups:
                mode = "never"
            groups[mode].append(tc)
        return groups

    def clear(self):
        self._tools.clear()


# 全局单例
registry = ToolRegistry()


def _module_has_register_call(module_path: Path) -> bool:
    """检查模块文件是否包含 registry.register() 调用"""
    try:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(module_path))
    except (OSError, SyntaxError):
        return False
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute) and func.attr == "register":
                if isinstance(func.value, ast.Name) and func.value.id == "registry":
                    return True
    return False


def discover_and_import_tools():
    """自动发现并导入所有工具模块"""
    if not _TOOLS_DIR.exists():
        logger.warning(f"工具目录不存在: {_TOOLS_DIR}")
        return

    imported = []
    for py_file in sorted(_TOOLS_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        if not _module_has_register_call(py_file):
            continue
        mod_name = f"app.tools.implementations.{py_file.stem}"
        try:
            importlib.import_module(mod_name)
            imported.append(py_file.stem)
        except Exception as e:
            logger.warning(f"导入工具模块失败 {mod_name}: {e}")

    if imported:
        logger.info(f"已加载工具模块: {', '.join(imported)}")
