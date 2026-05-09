"""
env_capabilities - 运行时环境能力检测

启动时检测实际安装了哪些工具/依赖，注入到 system prompt，
让 Agent 知道自己的真实环境能力，而不是靠静态文本。
"""

import logging
import shutil
import subprocess
import sys
from typing import Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


def _check_package(package: str) -> str | None:
    """检查 Python 包是否安装，返回版本号"""
    try:
        import importlib.metadata
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        # fallback
        try:
            __import__(package.replace("-", "_"))
            return "installed"
        except ImportError:
            return None
    except Exception:
        return None


def _check_cli(name: str) -> str | None:
    """检查 CLI 工具是否存在，返回版本信息"""
    path = shutil.which(name)
    if not path:
        return None
    try:
        result = subprocess.run(
            [name, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or result.stderr.strip() or path
    except Exception:
        return path


def _check_playwright_browsers() -> list[str]:
    """检查 Playwright 已安装哪些浏览器"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run"],
            capture_output=True, text=True, timeout=10,
        )
        browsers = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("browser:"):
                name = line.split("browser:")[1].strip().split()[0]
                if name not in browsers:
                    browsers.append(name)
        return browsers
    except Exception:
        return []


@lru_cache(maxsize=1)
def detect() -> Dict[str, Any]:
    """检测环境能力，结果缓存避免重复执行"""
    result: Dict[str, Any] = {
        "python": sys.version.split()[0],
        "packages": {},
        "cli_tools": {},
    }

    # Python 包检测
    for pkg in ["playwright", "httpx", "chromadb"]:
        ver = _check_package(pkg)
        if ver:
            result["packages"][pkg] = ver

    # 如果 playwright 装了，检测浏览器
    if "playwright" in result["packages"]:
        browsers = _check_playwright_browsers()
        if browsers:
            result["playwright_browsers"] = browsers

    # CLI 工具检测
    for cmd in ["git", "node", "npm", "curl", "docker", "sqlite3"]:
        ver = _check_cli(cmd)
        if ver:
            result["cli_tools"][cmd] = ver

    return result


def format_env_prompt() -> str:
    """将环境能力格式化为 system prompt 文本"""
    env = detect()
    lines = ["## 当前环境能力（自动检测）\n"]

    lines.append(f"- Python {env['python']}")

    for pkg, ver in env.get("packages", {}).items():
        lines.append(f"- {pkg}=={ver}")

    browsers = env.get("playwright_browsers", [])
    if browsers:
        lines.append(f"- Playwright 浏览器: {', '.join(browsers)}")
        lines.append("  你可以使用 browser 工具打开网页、截图、点击元素等。")

    for cmd, ver in env.get("cli_tools", {}).items():
        short = ver.split("\n")[0] if "\n" in ver else ver
        lines.append(f"- {cmd}: {short}")

    if not browsers:
        lines.append("")

    return "\n".join(lines)


# 模块加载时预热缓存（不阻塞）
_detected: str | None = None


def get_env_prompt() -> str:
    """获取环境能力提示词（延迟初始化 + 缓存）"""
    global _detected
    if _detected is None:
        try:
            _detected = format_env_prompt()
            logger.info(f"环境能力检测完成")
        except Exception as e:
            logger.warning(f"环境能力检测失败: {e}")
            _detected = ""
    return _detected


def refresh():
    """强制重新检测（例如安装新包后）"""
    global _detected
    detect.cache_clear()
    _detected = None
    return get_env_prompt()
