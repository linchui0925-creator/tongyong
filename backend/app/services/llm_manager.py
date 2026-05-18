"""
LLMManager - 全局 LLM 管理器

职责：
1. 统一管理所有 LLM 提供商的 API 密钥和配置
2. 支持动态切换模型并同步到 AgentEngine
3. 配置持久化（保存/加载到 JSON 文件）
4. 管理多组已保存的模型配置
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Optional, Any, List

from app.llm.base import BaseLLM
from app.llm.factory import get_llm, get_available_providers, get_provider_info

logger = logging.getLogger(__name__)

_CONFIG_FILE = Path("data/llm_config.json")


class LLMManager:
    """全局 LLM 管理器，支持动态切换模型"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _init(self):
        """延迟初始化"""
        if self._initialized:
            return
        self._initialized = True
        self._current_llm: Optional[BaseLLM] = None
        self._current_provider: str = "tongyi"
        self._current_model: Optional[str] = None
        self._current_config: Dict[str, Any] = {}
        self._agent_engine_ref = None  # 弱引用方式持有 AgentEngine
        # 已保存的 API 密钥（内存缓存）
        self._api_keys: Dict[str, str] = {}
        # 已保存的多组模型配置
        self._saved_models: List[Dict[str, Any]] = []
        self._load_config()

    # ── AgentEngine 绑定 ──────────────────────────────────

    def bind_agent_engine(self, engine) -> None:
        """绑定 AgentEngine 实例，切换模型时自动同步"""
        self._init()
        self._agent_engine_ref = engine
        # 绑定后将当前 LLM 同步过去（确保 try_restore_saved_provider 恢复的 LLM 生效）
        if self._current_llm is not None:
            self._sync_to_agent()
        logger.info(f"LLMManager 已绑定 AgentEngine，_current_llm={type(self._current_llm).__name__ if self._current_llm else None}")

    def _seed_initial_llm(self, llm: BaseLLM, provider: str) -> None:
        """在启动时注入已有的 LLM 实例（避免重复创建）"""
        self._init()
        self._current_llm = llm
        self._current_provider = provider
        logger.info(f"LLMManager 已接收初始 LLM: {provider} / {llm.model}")

    def try_restore_saved_provider(self) -> bool:
        """
        尝试从已保存的配置中恢复上次使用的 provider。
        如果保存的 provider 与当前不同且 API key 存在，则重建 LLM 实例。
        同时恢复自定义 api_endpoint。
        返回 True 表示已恢复，False 表示无变化。
        """
        self._init()
        saved_provider = None
        saved_model = None
        saved_endpoint = None
        try:
            if _CONFIG_FILE.exists():
                data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
                saved_provider = data.get("provider")
                saved_model = data.get("model")
                # 从 saved_models 中查找匹配的 api_endpoint
                saved_provider_cfg = data.get("saved_models", [])
                if saved_provider and saved_model:
                    for entry in saved_provider_cfg:
                        if entry.get("provider") == saved_provider and entry.get("model") == saved_model:
                            saved_endpoint = entry.get("api_endpoint")
                            break
        except Exception as e:
            logger.warning(f"读取保存的配置失败: {e}")
            return False

        if not saved_provider:
            logger.info("没有保存的 provider")
            return False
        if saved_provider == self._current_provider and self._current_llm is not None:
            logger.info(f"保存的 provider 与当前相同且 LLM 已存在，跳过重复恢复: {saved_provider}")
            return True  # 视为恢复成功，无需重建 LLM

        api_key = self.get_api_key(saved_provider)
        if not api_key:
            logger.warning(f"已保存的 provider {saved_provider} 无 API key，跳过恢复")
            return False

        try:
            from app.llm.factory import get_llm
            llm = get_llm(saved_provider, api_key)
            if saved_model:
                llm.model = saved_model
            if saved_endpoint and hasattr(llm, 'api_base'):
                llm.api_base = saved_endpoint
            self._current_llm = llm
            self._current_provider = saved_provider
            self._current_model = saved_model
            self._sync_to_agent()
            logger.info(
                f"已从保存的配置恢复 LLM: {saved_provider} / {saved_model or llm.model}"
                + (f" (endpoint: {saved_endpoint})" if saved_endpoint else "")
            )
            return True
        except Exception as e:
            logger.warning(f"恢复保存的 LLM 失败: {e}")
            return False

    def _sync_to_agent(self) -> None:
        """将当前 LLM 同步到 AgentEngine"""
        if self._agent_engine_ref is not None:
            self._agent_engine_ref.llm = self._current_llm
            logger.debug("LLM 实例已同步到 AgentEngine")

    # ── 配置持久化 ────────────────────────────────────────

    def _load_config(self) -> None:
        """从文件加载配置"""
        try:
            if _CONFIG_FILE.exists():
                data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
                self._api_keys = data.get("api_keys", {})
                self._saved_models = data.get("saved_models", [])
                # 恢复之前使用的 provider / model
                saved_provider = data.get("provider")
                if saved_provider and saved_provider in get_available_providers():
                    self._current_provider = saved_provider
                    self._current_model = data.get("model") or self._current_model
                logger.info(
                    f"已加载 LLM 配置 ({len(self._api_keys)} 个密钥, "
                    f"{len(self._saved_models)} 个已存模型, "
                    f"上次 provider: {self._current_provider})"
                )
        except Exception as e:
            logger.warning(f"加载 LLM 配置失败: {e}")

    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "provider": self._current_provider,
                "model": self._current_model,
                "api_keys": self._api_keys,
                "saved_models": self._saved_models,
            }
            _CONFIG_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"保存 LLM 配置失败: {e}")

    # ── API 密钥管理 ──────────────────────────────────────

    def get_api_key(self, provider: str) -> Optional[str]:
        """获取指定 provider 的 API 密钥（优先内存缓存，其次 .env）"""
        self._init()
        # 先查内存缓存
        if provider in self._api_keys:
            return self._api_keys[provider]
        # 再查 .env 环境变量
        from app.llm.factory import _get_default_api_key
        key = _get_default_api_key(provider)
        if key:
            self._api_keys[provider] = key
        return key

    def set_api_key(self, provider: str, api_key: str) -> None:
        """设置并持久化指定 provider 的 API 密钥"""
        self._init()
        if api_key:
            self._api_keys[provider] = api_key
            self._save_config()

    def get_all_api_keys(self) -> Dict[str, str]:
        """获取所有已配置的 API 密钥"""
        self._init()
        # 合并内存缓存 + .env 默认值
        result = dict(self._api_keys)
        for p in get_available_providers():
            if p not in result:
                from app.llm.factory import _get_default_api_key
                key = _get_default_api_key(p)
                if key:
                    result[p] = key
        return result

    # ── 当前状态 ──────────────────────────────────────────

    def get_current_llm(self) -> Optional[BaseLLM]:
        self._init()
        return self._current_llm

    def get_current_provider(self) -> str:
        self._init()
        return self._current_provider

    def get_current_model(self) -> Optional[str]:
        self._init()
        return self._current_model

    def get_current_config(self) -> Dict[str, Any]:
        self._init()
        return {
            "provider": self._current_provider,
            "model": self._current_model,
            "api_key_configured": bool(self.get_api_key(self._current_provider)),
        }

    # ── 模型切换 ──────────────────────────────────────────

    def switch_model(
        self,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        切换模型

        1. 创建新的 LLM 实例
        2. 保存 API 密钥到内存缓存
        3. 同步到 AgentEngine
        4. 持久化配置
        """
        self._init()
        try:
            available = get_available_providers()
            if provider not in available:
                logger.error(f"提供商 {provider} 不可用，可用: {available}")
                return False

            # 确定 API 密钥
            resolved_key = api_key or self.get_api_key(provider)
            if not resolved_key:
                logger.warning(f"{provider} 未配置 API 密钥")

            # 创建新实例
            llm = get_llm(provider, resolved_key)
            if not llm:
                logger.error(f"无法创建 LLM 实例: {provider}")
                return False

            if api_endpoint and hasattr(llm, 'api_base'):
                llm.api_base = api_endpoint
            if model:
                llm.model = model

            for key, value in kwargs.items():
                if hasattr(llm, key):
                    setattr(llm, key, value)

            # 更新状态
            self._current_llm = llm
            self._current_provider = provider
            self._current_model = model

            # 保存 API 密钥
            if api_key:
                self._api_keys[provider] = api_key

            # 同步到 AgentEngine
            self._sync_to_agent()

            # 持久化
            self._save_config()

            logger.info(f"模型切换成功: {provider} / {model or llm.model}")
            return True

        except Exception as e:
            logger.error(f"模型切换失败: {e}", exc_info=True)
            return False

    async def test_connection(
        self,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """测试模型连接"""
        self._init()
        result = {"success": False, "message": "", "model": ""}
        try:
            resolved_key = api_key or self.get_api_key(provider)
            llm = get_llm(provider, resolved_key)
            if api_endpoint and hasattr(llm, 'api_base'):
                llm.api_base = api_endpoint
            if model:
                llm.model = model

            ok = await llm.initialize()
            result["success"] = ok
            result["model"] = llm.model
            result["message"] = f"{provider} 连接{'成功' if ok else '失败'}"
        except Exception as e:
            result["message"] = f"连接测试失败: {e}"
        return result

    # ── 已保存模型管理 ────────────────────────────────────

    def get_saved_models(self) -> List[Dict[str, Any]]:
        """获取所有已保存的模型配置（API 密钥脱敏）"""
        self._init()
        result = []
        for m in self._saved_models:
            entry = dict(m)
            key = entry.get("api_key", "")
            if key and len(key) > 8:
                entry["api_key"] = key[:4] + "****" + key[-4:]
            elif key:
                entry["api_key"] = "****"
            result.append(entry)
        return result

    def add_saved_model(self, entry: Dict[str, Any]) -> str:
        """添加一个已保存的模型配置，返回 id"""
        self._init()
        entry["id"] = uuid.uuid4().hex[:12]
        self._saved_models.append(entry)
        self._save_config()
        logger.info(f"已保存模型配置: {entry.get('provider')} / {entry.get('model')}")
        return entry["id"]

    def delete_saved_model(self, model_id: str) -> bool:
        """删除已保存的模型配置"""
        self._init()
        before = len(self._saved_models)
        self._saved_models = [m for m in self._saved_models if m.get("id") != model_id]
        if len(self._saved_models) < before:
            self._save_config()
            logger.info(f"已删除模型配置: {model_id}")
            return True
        return False

    def get_saved_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """根据 id 查找已保存的模型"""
        self._init()
        for m in self._saved_models:
            if m.get("id") == model_id:
                return dict(m)
        return None

    # ── 状态查询 ──────────────────────────────────────────

    def get_all_providers_status(self) -> list:
        """获取所有提供商的当前状态"""
        self._init()
        statuses = []
        for p in get_available_providers():
            info = get_provider_info(p) or {}
            is_current = p == self._current_provider
            has_key = bool(self.get_api_key(p))
            statuses.append({
                "id": p,
                "name": info.get("name", p),
                "icon": info.get("icon", ""),
                "color": info.get("color", ""),
                "is_current": is_current,
                "has_api_key": has_key,
                "model": self._current_model if is_current else None,
            })
        return statuses


# ── 全局单例 ──────────────────────────────────────────────

llm_manager = LLMManager()


def get_llm_manager() -> LLMManager:
    return llm_manager


def initialize_llm_with_config(provider: Optional[str] = None, api_key: Optional[str] = None):
    """使用配置初始化 LLM"""
    provider = provider or "tongyi"
    mgr = get_llm_manager()
    if mgr.switch_model(provider, api_key):
        return mgr.get_current_llm()
    return None
