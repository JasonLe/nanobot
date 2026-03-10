"""渠道基类 - 定义聊天平台渠道的统一接口。

该模块提供:
- BaseChannel: 抽象基类，所有聊天渠道(Telegram、Discord等)需继承实现

每个渠道需要实现以下方法:
- start(): 启动渠道并开始监听消息
- stop(): 停止渠道并清理资源
- send(): 发送消息到聊天平台

还包括权限控制功能(is_allowed)用于限制访问。
"""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus


class BaseChannel(ABC):
    """
    聊天渠道实现的抽象基类。

    每个渠道(如Telegram、Discord等)应实现此接口
    以集成到nanobot消息总线。
    """

    name: str = "base"

    def __init__(self, config: Any, bus: MessageBus):
        """初始化渠道。

        Args:
            config: 渠道特定配置
            bus: 用于通信的消息总线
        """
        self.config = config
        self.bus = bus
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """启动渠道并开始监听消息。

        这应该是一个长期运行的异步任务:
        1. 连接到聊天平台
        2. 监听传入消息
        3. 通过_handle_message()转发消息到总线
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止渠道并清理资源。"""
        pass

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """通过此渠道发送消息。

        Args:
            msg: 要发送的消息
        """
        pass

    def is_allowed(self, sender_id: str) -> bool:
        """检查发送者是否被允许。

        权限规则:
        - allow_from为空列表 → 拒绝所有访问
        - allow_from包含"*" → 允许所有访问
        - 否则只允许列表中的用户ID

        Args:
            sender_id: 发送者标识符

        Returns:
            允许返回True，拒绝返回False
        """
        allow_list = getattr(self.config, "allow_from", [])
        if not allow_list:
            logger.warning("{}: allow_from is empty — all access denied", self.name)
            return False
        if "*" in allow_list:
            return True
        return str(sender_id) in allow_list

    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        session_key: str | None = None,
    ) -> None:
        """处理来自聊天平台的传入消息。

        此方法检查权限并将消息转发到总线。

        Args:
            sender_id: 发送者标识符
            chat_id: 聊天/频道标识符
            content: 消息文本内容
            media: 可选的媒体URL列表
            metadata: 可选的渠道特定元数据
            session_key: 可选的会话键覆盖 (如线程作用域会话)
        """
        if not self.is_allowed(sender_id):
            logger.warning(
                "Access denied for sender {} on channel {}. "
                "Add them to allowFrom list in config to grant access.",
                sender_id, self.name,
            )
            return

        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media or [],
            metadata=metadata or {},
            session_key_override=session_key,
        )

        await self.bus.publish_inbound(msg)

    @property
    def is_running(self) -> bool:
        """检查渠道是否正在运行。

        Returns:
            运行中返回True，否则返回False
        """
        return self._running
