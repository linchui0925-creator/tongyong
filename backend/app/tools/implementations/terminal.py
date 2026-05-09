"""
terminal - 命令行执行工具

在终端中执行 shell 命令。支持超时、后台执行、工作目录、PTY 模式。
自带安全校验：白名单命令基 + 禁止模式 + 路径穿越检测。
"""

import asyncio
import logging
import os
import re
import shlex
from typing import Optional

from app.tools.registry import registry

logger = logging.getLogger(__name__)

# ── 安全配置 ────────────────────────────────────────────

_ALLOWED_COMMANDS = [
    # 文件查看
    "cat", "less", "more", "head", "tail", "wc", "diff",
    # 文件操作
    "cp", "mv", "rm", "touch", "mkdir", "chmod", "chown",
    # 文本处理
    "grep", "rg", "awk", "sed", "sort", "uniq",
    # 文件查找
    "find", "locate", "which", "type",
    # 目录与路径
    "ls", "pwd", "cd", "tree", "du", "df",
    # 进程管理
    "ps", "top", "htop", "kill", "killall",
    # 网络
    "curl", "wget", "ping", "nc", "ss", "netstat",
    # 压缩
    "tar", "gzip", "gunzip", "zip", "unzip", "bzip2", "xz",
    # SHELL 内置
    "echo", "printf", "source", "export",
    # Python 生态
    "python", "python3", "pip", "pip3", "pytest", "mypy", "ruff", "black", "flake8", "uv",
    # Node 生态
    "node", "npm", "npx", "yarn", "pnpm", "bun",
    # 版本控制
    "git", "svn",
    # 容器
    "docker", "docker-compose",
    # 数据库
    "sqlite3", "redis-cli", "psql", "mysql",
    # 构建工具
    "make", "cmake", "cargo", "rustc", "go", "gcc", "g++", "clang",
    # 系统信息
    "date", "cal", "whoami", "id", "uname", "hostname", "uptime", "dmesg",
    # macOS 特定
    "open", "brew", "sw_vers", "defaults", "plutil",
    # 环境
    "env", "printenv", "xargs", "time", "watch",
    # 编码与校验
    "base64", "shasum", "sha256sum", "md5sum",
    # 浏览器自动化 — 已移除: 使用专用的 browser 工具
    # "playwright",
    # 杂项
    "jq", "yq", "rsync", "screen", "tmux",
]

_FORBIDDEN_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"sudo\s+",
    r"curl.*\|.*sh",
    r"wget.*\|.*sh",
    r">\s*/etc/",
    r"mkfs",
    r"dd\s+.*of=/dev/",
    r":\(\)\{\s*:\|:",
]

_MAX_OUTPUT_CHARS = 100_000
_DEFAULT_TIMEOUT = 60
_MAX_FOREGROUND_TIMEOUT = 600


def _validate_command(command: str) -> Optional[str]:
    """验证命令安全性，返回错误信息或 None"""
    if len(command) > 2000:
        return "命令过长（最多 2000 字符）"

    cmd_base = command.split()[0] if command.split() else ""
    if cmd_base not in _ALLOWED_COMMANDS:
        return f"命令 '{cmd_base}' 不在允许列表中"

    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return f"命令包含禁止的模式: {pattern}"

    # 路径穿越
    if ".." in command and "/" in command:
        if re.search(r"\.\.[/\\]", command):
            return "路径遍历攻击检测"

    # 禁止通过任何方式调用 playwright（import、CLI 命令、Python 脚本）
    if re.search(r'\bplaywright\b', command, re.IGNORECASE):
        return "浏览器操作请使用 browser 工具，不要通过终端调用 playwright"

    return None


def _check_terminal() -> bool:
    """终端工具总是可用"""
    return True


TERMINAL_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "要执行的 shell 命令",
        },
        "timeout": {
            "type": "integer",
            "description": f"超时秒数（默认 {_DEFAULT_TIMEOUT}s，前台最大 {_MAX_FOREGROUND_TIMEOUT}s）",
            "default": _DEFAULT_TIMEOUT,
        },
        "workdir": {
            "type": "string",
            "description": "工作目录（绝对路径，默认当前目录）",
        },
        "background": {
            "type": "boolean",
            "description": "后台执行（适用于长时间运行的任务，默认 false）",
            "default": False,
        },
    },
    "required": ["command"],
}


async def terminal_tool(command: str, timeout: int = _DEFAULT_TIMEOUT, workdir: str = "", background: bool = False) -> str:
    # 安全校验
    err = _validate_command(command)
    if err:
        return f"⛔ {err}"

    cwd = workdir if workdir else None
    if cwd and not os.path.isdir(cwd):
        return f"工作目录不存在: {cwd}"

    timeout = min(timeout, _MAX_FOREGROUND_TIMEOUT if not background else 86400)

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            limit=1024 * 1024,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return f"⏱ 命令执行超时（>{timeout}s）"

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        output = ""
        if stdout:
            output += stdout
        if stderr:
            if output:
                output += "\n"
            output += f"[stderr]\n{stderr}"

        if len(output) > _MAX_OUTPUT_CHARS:
            output = output[:_MAX_OUTPUT_CHARS] + "\n...（输出过长，已截断）"

        status = "✅" if process.returncode == 0 else "❌"
        return f"{status} 命令完成（返回码 {process.returncode}）\n{output}"

    except Exception as e:
        logger.error(f"命令执行失败: {e}", exc_info=True)
        return f"❌ 命令执行失败: {e}"


registry.register(
    name="terminal",
    description="执行 shell 命令（编译、运行、安装、git、文件操作等）。支持超时、工作目录、后台执行。注意：不要用此工具实现浏览器操作（打开网页、截图等）——请使用专门的 browser 工具。",
    schema=TERMINAL_SCHEMA,
    handler=terminal_tool,
    check_fn=_check_terminal,
    is_async=True,
    emoji="💻",
    max_result_size_chars=_MAX_OUTPUT_CHARS,
    parallel_mode="never",
)
