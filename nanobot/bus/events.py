"""事件类型定义 - 定义消息总线中使用的数据结构。

该模块包含:
- InboundMessage: 从聊天渠道接收的入站消息
- OutboundMessage: 发送到聊天渠道的出站消息
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InboundMessage:
    """从聊天平台接收的入站消息。

    属性:
        channel: 消息来源的渠道名称 (如 telegram, discord, slack)
        sender_id: 发送者标识符
        chat_id: 聊天/群组标识符
        content: 消息文本内容
        timestamp: 消息时间戳
        media: 媒体URL列表 (图片、视频等)
        metadata: 渠道特定的元数据
        session_key_override: 可选的会话键覆盖 (用于线程作用域会话)
    """

    channel: str  # telegram, discord, slack, whatsapp
    sender_id: str  # User identifier
    chat_id: str  # Chat/channel identifier
    content: str  # Message text
    timestamp: datetime = field(default_factory=datetime.now)
    media: list[str] = field(default_factory=list)  # Media URLs
    metadata: dict[str, Any] = field(default_factory=dict)  # Channel-specific data
    session_key_override: str | None = None  # Optional override for thread-scoped sessions

    @property
    def session_key(self) -> str:
        """获取会话唯一标识键。

        返回格式: "channel:chat_id"
        如果有session_key_override则使用覆盖值。
        """
        return self.session_key_override or f"{self.channel}:{self.chat_id}"


@dataclass
class OutboundMessage:
    """发送到聊天平台的出站消息。

    属性:
        channel: 目标渠道名称
        chat_id: 目标聊天/群组标识符
        content: 消息文本内容
        reply_to: 可选的回复消息ID
        media: 媒体URL列表
        metadata: 额外的元数据 (如进度标记等)
    """

    channel: str
    chat_id: str
    content: str
    reply_to: str | None = None
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


