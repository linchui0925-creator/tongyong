"""
browser - Playwright 浏览器控制工具

支持打开网页、点击、输入、截图、获取文本等操作。
使用实例池管理浏览器，支持多会话隔离。
"""

import logging
import os
import threading
from typing import Optional

from app.tools.registry import registry

logger = logging.getLogger(__name__)

# ── 实例池（替代全局单例） ────────────────────────────

_lock = threading.Lock()
_instances: dict = {}
"""结构:
{
  instance_key: {
    "playwright": PlaywrightContextManager,
    "browser": Browser,
    "page": Page,
  }
}
"""


def _get_instance_key(session_id: str = "") -> str:
    """获取实例键。有 session_id 则按会话隔离，否则共享 default"""
    return session_id if session_id else "default"


async def _ensure_browser(instance_key: str = "default"):
    with _lock:
        inst = _instances.get(instance_key)
        if inst is not None and inst["page"] is not None:
            return inst["page"]

    # 在锁外创建，避免阻塞
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()

    with _lock:
        # 关闭旧实例（如果有）
        old = _instances.get(instance_key)
        if old is not None:
            try:
                await old["browser"].close()
            except Exception:
                pass
            try:
                await old["playwright"].stop()
            except Exception:
                pass
        _instances[instance_key] = {
            "playwright": pw,
            "browser": browser,
            "page": page,
        }

    logger.info(f"Playwright 浏览器已启动（实例: {instance_key}）")
    return page


def _get_page(instance_key: str):
    """获取实例的 page 对象（不创建）"""
    with _lock:
        inst = _instances.get(instance_key)
        if inst is None:
            return None
        return inst.get("page")


async def _close_instance(instance_key: str) -> bool:
    """关闭指定实例，返回是否有关闭"""
    with _lock:
        inst = _instances.pop(instance_key, None)
    if inst is None:
        return False
    try:
        await inst["browser"].close()
    except Exception:
        pass
    try:
        await inst["playwright"].stop()
    except Exception:
        pass
    logger.info(f"浏览器实例已关闭: {instance_key}")
    return True


async def _close_all():
    """关闭所有浏览器实例（进程退出时调用）"""
    with _lock:
        keys = list(_instances.keys())
    for key in keys:
        await _close_instance(key)


# ── 工具入口 ──────────────────────────────────────────


async def browser_execute(
    action: str,
    url: str = "",
    selector: str = "",
    text: str = "",
    path: str = "screenshot.png",
    session_id: str = "",
) -> str:
    instance_key = _get_instance_key(session_id)

    try:
        if action == "close":
            closed = await _close_instance(instance_key)
            return "浏览器已关闭" if closed else "浏览器未启动"

        if action == "close_all":
            await _close_all()
            return "所有浏览器实例已关闭"

        page = await _ensure_browser(instance_key)

        if action == "navigate":
            return await _navigate(page, url)
        elif action == "click":
            return await _click(page, selector)
        elif action == "type":
            return await _type(page, selector, text)
        elif action == "screenshot":
            return await _screenshot(page, path)
        elif action == "get_text":
            return await _get_text(page, selector)
        elif action == "get_page_content":
            return await _get_page_content(page)
        elif action == "scroll":
            return await _scroll(page, selector)
        else:
            return f"未知操作: {action}"
    except Exception as e:
        logger.error(f"浏览器操作失败: {e}", exc_info=True)
        return f"浏览器操作失败: {e}"


# ── 操作函数 ──────────────────────────────────────────


async def _navigate(page, url: str) -> str:
    if not url:
        return "navigate 操作需要提供 url 参数"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    title = await page.title()
    return f"已打开: {url}\n页面标题: {title}"


async def _click(page, selector: str) -> str:
    if not selector:
        return "click 操作需要提供 selector 参数"
    await page.click(selector, timeout=10000)
    return f"已点击: {selector}"


async def _type(page, selector: str, text: str) -> str:
    if not selector:
        return "type 操作需要提供 selector 参数"
    await page.fill(selector, text, timeout=10000)
    return f"已在 {selector} 输入: {text}"


async def _screenshot(page, path: str) -> str:
    await page.screenshot(path=path, full_page=False)
    abs_path = os.path.abspath(path)
    return f"截图已保存: {abs_path}"


async def _get_text(page, selector: str) -> str:
    if not selector:
        return "get_text 操作需要提供 selector 参数"
    element = await page.query_selector(selector)
    if not element:
        return f"未找到元素: {selector}"
    content = await element.inner_text()
    if len(content) > 5000:
        content = content[:5000] + "\n...（内容过长，已截断）"
    return content


async def _get_page_content(page) -> str:
    content = await page.inner_text("body")
    if len(content) > 8000:
        content = content[:8000] + "\n...（内容过长，已截断）"
    return content


async def _scroll(page, selector: str = "") -> str:
    if selector:
        await page.evaluate(f'document.querySelector("{selector}")?.scrollIntoView()')
        return f"已滚动到: {selector}"
    await page.evaluate("window.scrollBy(0, window.innerHeight)")
    return "已向下滚动一屏"


def _check_browser() -> bool:
    """检查 Playwright 是否可用"""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


BROWSER_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "操作类型",
            "enum": ["navigate", "click", "type", "screenshot", "get_text", "get_page_content", "scroll", "close", "close_all"],
        },
        "url": {
            "type": "string",
            "description": "navigate 时必填，要打开的网页 URL（需包含 http:// 或 https://）",
        },
        "selector": {
            "type": "string",
            "description": "click/type/get_text/scroll 时可选，CSS 选择器（如 '#id'、'.class'、'button'）",
        },
        "text": {
            "type": "string",
            "description": "type 时必填，要输入的文字",
        },
        "path": {
            "type": "string",
            "description": "screenshot 时可选，截图保存路径，默认 'screenshot.png'",
        },
        "session_id": {
            "type": "string",
            "description": "会话标识，同一会话共享浏览器实例",
        },
    },
    "required": ["action"],
}

registry.register(
    name="browser",
    description="【浏览器自动化 — 首选用此工具】打开网页、点击、输入、截图、获取文本等。支持操作: navigate(打开URL), click(点击元素), type(输入文字), screenshot(截图保存), get_text(获取元素文本), get_page_content(获取全部文本), scroll(滚动), close(关闭浏览器)。每个会话使用独立浏览器实例。注意：这是浏览器操作的唯一工具，不要用 terminal 或 Python 脚本替代。",
    schema=BROWSER_SCHEMA,
    handler=browser_execute,
    check_fn=_check_browser,
    emoji="🌐",
    parallel_mode="never",
)
