"""异步消息队列 - 用于解耦渠道与Agent核心的消息通信。

核心组件:
- MessageBus: 异步消息总线，实现发布/订阅模式
  - inbound: 入站队列，渠道推送消息到此处
  - outbound: 出站队列，Agent处理后发送响应到此处

使用场景:
- 渠道(如Telegram)接收到消息后，通过publish_inbound发布到队列
- Agent从inbound队列消费消息，处理后通过publish_outbound发布响应
- 渠道管理器从outbound队列消费响应，发送给用户
"""

import asyncio

from nanobot.bus.events import InboundMessage, OutboundMessage


class MessageBus:
    """
    异步消息总线，解耦聊天渠道与Agent核心。

    渠道推送消息到入站队列，Agent处理后
    将响应推送至出站队列。
    """

    def __init__(self):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """发布来自渠道的消息到Agent。

        Args:
            msg: 入站消息对象
        """
        await self.inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """消费下一条入站消息 (阻塞直到有消息可用)。

        Returns:
            入站消息对象
        """
        return await self.inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """发布Agent的响应到渠道。

        Args:
            msg: 出站消息对象
        """
        await self.outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """消费下一条出站消息 (阻塞直到有消息可用)。

        Returns:
            出站消息对象
        """
        return await self.outbound.get()

    @property
    def inbound_size(self) -> int:
        """获取待处理入站消息数量。

        Returns:
            队列中的消息数量
        """
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        """获取待处理出站消息数量。

        Returns:
            队列中的消息数量
        """
        return self.outbound.qsize()
