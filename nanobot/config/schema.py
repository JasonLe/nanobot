"""配置Schema定义 - 使用Pydantic定义配置数据结构。

该模块定义了nanobot的所有配置结构:
- 渠道配置: WhatsApp, Telegram, Discord, 飞书, 钉钉, Email, Slack, QQ, Matrix等
- Agent配置: 工作目录、模型、token限制等
- Provider配置: 各LLM提供者的API配置
- 工具配置: Web工具、Shell执行、MCP服务器等
- 网关配置: 服务端口、心跳等

使用Pydantic进行配置验证和类型转换，
支持环境变量和别名(如camelCase/snake_case)。
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings


class Base(BaseModel):
    """基类模型，接受camelCase和snake_case两种键名。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WhatsAppConfig(Base):
    """WhatsApp渠道配置。"""

    enabled: bool = False
    bridge_url: str = "ws://localhost:3001"
    bridge_token: str = ""  # Bridge认证的共享token (可选，推荐设置)
    allow_from: list[str] = Field(default_factory=list)  # 允许的 phone numbers


class TelegramConfig(Base):
    """Telegram渠道配置。"""

    enabled: bool = False
    token: str = ""  # 从 @BotFather 获取的Bot Token
    allow_from: list[str] = Field(default_factory=list)  # 允许的 user IDs 或 usernames
    proxy: str | None = (
        None  # HTTP/SOCKS5 代理URL，如 "http://127.0.0.1:7890" 或 "socks5://127.0.0.1:1080"
    )
    reply_to_message: bool = False  # 是否引用回复原消息
    group_policy: Literal["open", "mention"] = "mention"  # "mention" 只在@提及或回复时响应，"open"响应所有


class FeishuConfig(Base):
    """飞书/钉钉渠道配置 (使用WebSocket长连接)。"""

    enabled: bool = False
    app_id: str = ""  # 飞书开放平台的应用ID
    app_secret: str = ""  # 飞书开放平台的应用密钥
    encrypt_key: str = ""  # 事件订阅的加密密钥 (可选)
    verification_token: str = ""  # 事件订阅的验证Token (可选)
    allow_from: list[str] = Field(default_factory=list)  # 允许的 user open_ids
    react_emoji: str = (
        "THUMBSUP"  # 消息回复的emoji类型 (如 THUMBSUP, OK, DONE, SMILE)
    )


class DingTalkConfig(Base):
    """钉钉渠道配置 (使用Stream模式)。"""

    enabled: bool = False
    client_id: str = ""  # AppKey
    client_secret: str = ""  # AppSecret
    allow_from: list[str] = Field(default_factory=list)  # 允许的 staff_ids


class DiscordConfig(Base):
    """Discord渠道配置。"""

    enabled: bool = False
    token: str = ""  # Discord开发者门户的Bot Token
    allow_from: list[str] = Field(default_factory=list)  # 允许的 user IDs
    gateway_url: str = "wss://gateway.discord.gg/?v=10&encoding=json"
    intents: int = 37377  # GUILDS + GUILD_MESSAGES + DIRECT_MESSAGES + MESSAGE_CONTENT
    group_policy: Literal["mention", "open"] = "mention"


class MatrixConfig(Base):
    """Matrix (Element) 渠道配置。"""

    enabled: bool = False
    homeserver: str = "https://matrix.org"
    access_token: str = ""
    user_id: str = ""  # @bot:matrix.org
    device_id: str = ""
    e2ee_enabled: bool = True  # 启用Matrix端到端加密支持
    sync_stop_grace_seconds: int = (
        2  # 等待sync_forever优雅停止的最大秒数
    )
    max_media_bytes: int = (
        20 * 1024 * 1024
    )  # Matrix媒体处理接受的最大附件大小 (字节)
    allow_from: list[str] = Field(default_factory=list)
    group_policy: Literal["open", "mention", "allowlist"] = "open"
    group_allow_from: list[str] = Field(default_factory=list)
    allow_room_mentions: bool = False


class EmailConfig(Base):
    """Email渠道配置 (IMAP接收 + SMTP发送)。"""

    enabled: bool = False
    consent_granted: bool = False  # 明确获得所有者许可访问邮箱数据

    # IMAP (接收)
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_mailbox: str = "INBOX"
    imap_use_ssl: bool = True

    # SMTP (发送)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    from_address: str = ""

    # 行为配置
    auto_reply_enabled: bool = (
        True  # 如果为false，入站邮件会被读取但不会自动回复
    )
    poll_interval_seconds: int = 30
    mark_seen: bool = True
    max_body_chars: int = 12000
    subject_prefix: str = "Re: "
    allow_from: list[str] = Field(default_factory=list)  # 允许的 sender email addresses


class MochatMentionConfig(Base):
    """Mochat @提及行为配置。"""

    require_in_groups: bool = False


class MochatGroupRule(Base):
    """Mochat每个群的@提及要求。"""

    require_mention: bool = False


class MochatConfig(Base):
    """Mochat渠道配置。"""

    enabled: bool = False
    base_url: str = "https://mochat.io"
    socket_url: str = ""
    socket_path: str = "/socket.io"
    socket_disable_msgpack: bool = False
    socket_reconnect_delay_ms: int = 1000
    socket_max_reconnect_delay_ms: int = 10000
    socket_connect_timeout_ms: int = 10000
    refresh_interval_ms: int = 30000
    watch_timeout_ms: int = 25000
    watch_limit: int = 100
    retry_delay_ms: int = 500
    max_retry_attempts: int = 0  # 0 表示无限重试
    claw_token: str = ""
    agent_user_id: str = ""
    sessions: list[str] = Field(default_factory=list)
    panels: list[str] = Field(default_factory=list)
    allow_from: list[str] = Field(default_factory=list)
    mention: MochatMentionConfig = Field(default_factory=MochatMentionConfig)
    groups: dict[str, MochatGroupRule] = Field(default_factory=dict)
    reply_delay_mode: str = "non-mention"  # off | non-mention
    reply_delay_ms: int = 120000


class SlackDMConfig(Base):
    """Slack DM策略配置。"""

    enabled: bool = True
    policy: str = "open"  # "open" 或 "allowlist"
    allow_from: list[str] = Field(default_factory=list)  # 允许的 Slack user IDs


class SlackConfig(Base):
    """Slack渠道配置。"""

    enabled: bool = False
    mode: str = "socket"  # 支持 "socket"
    webhook_path: str = "/slack/events"
    bot_token: str = ""  # xoxb-...
    app_token: str = ""  # xapp-...
    user_token_read_only: bool = True
    reply_in_thread: bool = True
    react_emoji: str = "eyes"
    allow_from: list[str] = Field(default_factory=list)  # 允许的 Slack user IDs (发送者级别)
    group_policy: str = "mention"  # "mention", "open", "allowlist"
    group_allow_from: list[str] = Field(default_factory=list)  # allowlist模式下的允许 channel IDs
    dm: SlackDMConfig = Field(default_factory=SlackDMConfig)


class QQConfig(Base):
    """QQ渠道配置 (使用botpy SDK)。"""

    enabled: bool = False
    app_id: str = ""  # 机器人 ID (AppID) from q.qq.com
    secret: str = ""  # 机器人密钥 (AppSecret) from q.qq.com
    allow_from: list[str] = Field(
        default_factory=list
    )  # 允许的 user openids (空=公共访问)



class ChannelsConfig(Base):
    """聊天渠道配置。"""

    send_progress: bool = True  # 向渠道流式传输Agent的文本进度
    send_tool_hints: bool = False  # 流式传输工具调用提示 (如 read_file("…"))
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    mochat: MochatConfig = Field(default_factory=MochatConfig)
    dingtalk: DingTalkConfig = Field(default_factory=DingTalkConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    qq: QQConfig = Field(default_factory=QQConfig)
    matrix: MatrixConfig = Field(default_factory=MatrixConfig)


class AgentDefaults(Base):
    """默认Agent配置。"""

    workspace: str = "~/.nanobot/workspace"
    model: str = "anthropic/claude-opus-4-5"
    provider: str = (
        "auto"  # 提供者名称 (如 "anthropic", "openrouter") 或 "auto" 自动检测
    )
    max_tokens: int = 8192
    temperature: float = 0.1
    max_tool_iterations: int = 40
    memory_window: int = 100
    reasoning_effort: str | None = None  # low / medium / high — 启用LLM思考模式


class AgentsConfig(Base):
    """Agent配置。"""

    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class ProviderConfig(Base):
    """LLM提供者配置。"""

    api_key: str = ""
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None  # 自定义headers (如 AiHubMix的 APP-Code)


class ProvidersConfig(Base):
    """LLM提供者配置集合。"""

    custom: ProviderConfig = Field(default_factory=ProviderConfig)  # 任意OpenAI兼容端点
    azure_openai: ProviderConfig = Field(default_factory=ProviderConfig)  # Azure OpenAI (model = deployment name)
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)
    groq: ProviderConfig = Field(default_factory=ProviderConfig)
    zhipu: ProviderConfig = Field(default_factory=ProviderConfig)
    dashscope: ProviderConfig = Field(default_factory=ProviderConfig)  # 阿里云通义千问
    vllm: ProviderConfig = Field(default_factory=ProviderConfig)
    gemini: ProviderConfig = Field(default_factory=ProviderConfig)
    moonshot: ProviderConfig = Field(default_factory=ProviderConfig)
    minimax: ProviderConfig = Field(default_factory=ProviderConfig)
    aihubmix: ProviderConfig = Field(default_factory=ProviderConfig)  # AiHubMix API网关
    siliconflow: ProviderConfig = Field(default_factory=ProviderConfig)  # SiliconFlow (硅基流动)
    volcengine: ProviderConfig = Field(default_factory=ProviderConfig)  # VolcEngine (火山引擎)
    openai_codex: ProviderConfig = Field(default_factory=ProviderConfig)  # OpenAI Codex (OAuth)
    github_copilot: ProviderConfig = Field(default_factory=ProviderConfig)  # Github Copilot (OAuth)


class HeartbeatConfig(Base):
    """心跳服务配置。"""

    enabled: bool = True
    interval_s: int = 30 * 60  # 30分钟


class GatewayConfig(Base):
    """网关/服务器配置。"""

    host: str = "0.0.0.0"
    port: int = 18790
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)


class WebSearchConfig(Base):
    """Web搜索工具配置。"""

    api_key: str = ""  # Brave Search API key
    max_results: int = 5


class WebToolsConfig(Base):
    """Web工具配置。"""

    proxy: str | None = (
        None  # HTTP/SOCKS5 代理URL，如 "http://127.0.0.1:7890" 或 "socks5://127.0.0.1:1080"
    )
    search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class ExecToolConfig(Base):
    """Shell执行工具配置。"""

    timeout: int = 60
    path_append: str = ""


class MCPServerConfig(Base):
    """MCP服务器连接配置 (stdio或HTTP)。"""

    type: Literal["stdio", "sse", "streamableHttp"] | None = None  # 省略时自动检测
    command: str = ""  # Stdio: 要运行的命令 (如 "npx")
    args: list[str] = Field(default_factory=list)  # Stdio: 命令参数
    env: dict[str, str] = Field(default_factory=dict) # Stdio: 额外环境变量
    url: str = ""  # HTTP/SSE: 端点URL
    headers: dict[str, str] = Field(default_factory=dict)  # HTTP/SSE: 自定义headers
    tool_timeout: int = 30  # 工具调用超时取消的秒数


class ToolsConfig(Base):
    """工具配置。"""

    web: WebToolsConfig = Field(default_factory=WebToolsConfig)
    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)
    restrict_to_workspace: bool = False  # 如果为true，限制所有工具访问到workspace目录
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)


class Config(BaseSettings):
    """nanobot根配置。"""

    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)

    @property
    def workspace_path(self) -> Path:
        """获取展开的工作目录路径。

        Returns:
            展开后的Path对象
        """
        return Path(self.agents.defaults.workspace).expanduser()

    def _match_provider(
        self, model: str | None = None
    ) -> tuple["ProviderConfig | None", str | None]:
        """匹配提供者配置及其注册名称。返回 (config, spec_name)。

        Args:
            model: 模型名称

        Returns:
            (提供者配置, 注册名称) 元组
        """
        from nanobot.providers.registry import PROVIDERS

        forced = self.agents.defaults.provider
        if forced != "auto":
            p = getattr(self.providers, forced, None)
            return (p, forced) if p else (None, None)

        model_lower = (model or self.agents.defaults.model).lower()
        model_normalized = model_lower.replace("-", "_")
        model_prefix = model_lower.split("/", 1)[0] if "/" in model_lower else ""
        normalized_prefix = model_prefix.replace("-", "_")

        def _kw_matches(kw: str) -> bool:
            kw = kw.lower()
            return kw in model_lower or kw.replace("-", "_") in model_normalized

        # 显式提供者前缀优先 — 防止 `github-copilot/...codex` 匹配 openai_codex
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and model_prefix and normalized_prefix == spec.name:
                if spec.is_oauth or p.api_key:
                    return p, spec.name

        # 按关键字匹配 (顺序遵循PROVIDERS注册表)
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and any(_kw_matches(kw) for kw in spec.keywords):
                if spec.is_oauth or p.api_key:
                    return p, spec.name

        # 回退: 网关优先，然后是其他 (遵循注册表顺序)
        # OAuth提供者不是有效的回退 — 需要显式模型选择
        for spec in PROVIDERS:
            if spec.is_oauth:
                continue
            p = getattr(self.providers, spec.name, None)
            if p and p.api_key:
                return p, spec.name
        return None, None

    def get_provider(self, model: str | None = None) -> ProviderConfig | None:
        """获取匹配的配置 (api_key, api_base, extra_headers)。回退到第一个可用的。

        Args:
            model: 模型名称

        Returns:
            ProviderConfig对象
        """
        p, _ = self._match_provider(model)
        return p

    def get_provider_name(self, model: str | None = None) -> str | None:
        """获取匹配提供者的注册名称 (如 "deepseek", "openrouter")。

        Args:
            model: 模型名称

        Returns:
            提供者注册名称
        """
        _, name = self._match_provider(model)
        return name

    def get_api_key(self, model: str | None = None) -> str | None:
        """获取给定模型的API密钥。回退到第一个可用的。

        Args:
            model: 模型名称

        Returns:
            API密钥字符串
        """
        p = self.get_provider(model)
        return p.api_key if p else None

    def get_api_base(self, model: str | None = None) -> str | None:
        """获取给定模型的API基础URL。为已知网关应用默认URL。

        Args:
            model: 模型名称

        Returns:
            API基础URL字符串
        """
        from nanobot.providers.registry import find_by_name

        p, name = self._match_provider(model)
        if p and p.api_base:
            return p.api_base
        # 只有网关在这里获取默认api_base。标准提供者
        # (如Moonshot)通过env vars在_setup_env中设置base URL
        # 以避免污染全局litellm.api_base。
        if name:
            spec = find_by_name(name)
            if spec and spec.is_gateway and spec.default_api_base:
                return spec.default_api_base
        return None

    model_config = ConfigDict(env_prefix="NANOBOT_", env_nested_delimiter="__")
