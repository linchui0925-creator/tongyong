from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """OpenAI-compatible 网关配置"""

    # API 认证
    api_key: str = Field(default="", alias="GATEWAY_API_KEY")
    """API密钥。为空时所有请求放行（仅限本地使用）。"""

    # 服务配置
    model_name: str = Field(default="tongyong-agent", alias="GATEWAY_MODEL_NAME")
    """对外暴露的模型名称"""

    # 会话
    max_tool_rounds: int = Field(default=10, alias="GATEWAY_MAX_TOOL_ROUNDS")
    """工具调用最大轮数"""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )
