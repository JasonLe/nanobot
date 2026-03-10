"""渠道管理器 - 协调和管理多个聊天渠道。

主要功能:
- 根据配置初始化已启用的渠道 (Telegram、WhatsApp、Discord等)
- 启动/停止所有渠道
- 路由出站消息到相应渠道
- 提供渠道状态查询

该模块是nanobot的核心组件之一，负责将不同的聊天平台
与Agent核心连接起来。
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import Config


class ChannelManager:
    """管理和协调聊天渠道的类。

    职责:
    - 初始化已启用的渠道 (Telegram、WhatsApp、Discord等)
    - 启动/停止渠道
    - 路由出站消息
    """

    def __init__(self, config: Config, bus: MessageBus):
        """初始化渠道管理器。

        Args:
            config: 全局配置对象
            bus: 消息总线
        """
        self.config = config
        self.bus = bus
        self.channels: dict[str, BaseChannel] = {}
        self._dispatch_task: asyncio.Task | None = None

        self._init_channels()

    def _init_channels(self) -> None:
        """根据配置初始化渠道。"""
        # Telegram 渠道
        if self.config.channels.telegram.enabled:
            try:
                from nanobot.channels.telegram import TelegramChannel
                self.channels["telegram"] = TelegramChannel(
                    self.config.channels.telegram,
                    self.bus,
                    groq_api_key=self.config.providers.groq.api_key,
                )
                logger.info("Telegram channel enabled")
            except ImportError as e:
                logger.warning("Telegram channel not available: {}", e)

        # WhatsApp 渠道
        if self.config.channels.whatsapp.enabled:
            try:
                from nanobot.channels.whatsapp import WhatsAppChannel
                self.channels["whatsapp"] = WhatsAppChannel(
                    self.config.channels.whatsapp, self.bus
                )
                logger.info("WhatsApp channel enabled")
            except ImportError as e:
                logger.warning("WhatsApp channel not available: {}", e)

        # Discord 渠道
        if self.config.channels.discord.enabled:
            try:
                from nanobot.channels.discord import DiscordChannel
                self.channels["discord"] = DiscordChannel(
                    self.config.channels.discord, self.bus
                )
                logger.info("Discord channel enabled")
            except ImportError as e:
                logger.warning("Discord channel not available: {}", e)

        # 飞书渠道
        if self.config.channels.feishu.enabled:
            try:
                from nanobot.channels.feishu import FeishuChannel
                self.channels["feishu"] = FeishuChannel(
                    self.config.channels.feishu, self.bus,
                    groq_api_key=self.config.providers.groq.api_key,
                )
                logger.info("Feishu channel enabled")
            except ImportError as e:
                logger.warning("Feishu channel not available: {}", e)

        # Mochat 渠道
        if self.config.channels.mochat.enabled:
            try:
                from nanobot.channels.mochat import MochatChannel

                self.channels["mochat"] = MochatChannel(
                    self.config.channels.mochat, self.bus
                )
                logger.info("Mochat channel enabled")
            except ImportError as e:
                logger.warning("Mochat channel not available: {}", e)

        # 钉钉渠道
        if self.config.channels.dingtalk.enabled:
            try:
                from nanobot.channels.dingtalk import DingTalkChannel
                self.channels["dingtalk"] = DingTalkChannel(
                    self.config.channels.dingtalk, self.bus
                )
                logger.info("DingTalk channel enabled")
            except ImportError as e:
                logger.warning("DingTalk channel not available: {}", e)

        # Email 渠道
        if self.config.channels.email.enabled:
            try:
                from nanobot.channels.email import EmailChannel
                self.channels["email"] = EmailChannel(
                    self.config.channels.email, self.bus
                )
                logger.info("Email channel enabled")
            except ImportError as e:
                logger.warning("Email channel not available: {}", e)

        # Slack 渠道
        if self.config.channels.slack.enabled:
            try:
                from nanobot.channels.slack import SlackChannel
                self.channels["slack"] = SlackChannel(
                    self.config.channels.slack, self.bus
                )
                logger.info("Slack channel enabled")
            except ImportError as e:
                logger.warning("Slack channel not available: {}", e)

        # QQ 渠道
        if self.config.channels.qq.enabled:
            try:
                from nanobot.channels.qq import QQChannel
                self.channels["qq"] = QQChannel(
                    self.config.channels.qq,
                    self.bus,
                )
                logger.info("QQ channel enabled")
            except ImportError as e:
                logger.warning("QQ channel not available: {}", e)

        # Matrix 渠道
        if self.config.channels.matrix.enabled:
            try:
                from nanobot.channels.matrix import MatrixChannel
                self.channels["matrix"] = MatrixChannel(
                    self.config.channels.matrix,
                    self.bus,
                )
                logger.info("Matrix channel enabled")
            except ImportError as e:
                logger.warning("Matrix channel not available: {}", e)

        self._validate_allow_from()

    def _validate_allow_from(self) -> None:
        """验证所有渠道的allow_from配置是否有效。"""
        for name, ch in self.channels.items():
            if getattr(ch.config, "allow_from", None) == []:
                raise SystemExit(
                    f'Error: "{name}" has empty allowFrom (denies all). '
                    f'Set ["*"] to allow everyone, or add specific user IDs.'
                )

    async def _start_channel(self, name: str, channel: BaseChannel) -> None:
        """启动单个渠道并记录异常。

        Args:
            name: 渠道名称
            channel: 渠道实例
        """
        try:
            await channel.start()
        except Exception as e:
            logger.error("Failed to start channel {}: {}", name, e)

    async def start_all(self) -> None:
        """启动所有渠道和出站消息分发器。"""
        if not self.channels:
            logger.warning("No channels enabled")
            return

        # 启动出站消息分发器
        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())

        # 启动所有渠道
        tasks = []
        for name, channel in self.channels.items():
            logger.info("Starting {} channel...", name)
            tasks.append(asyncio.create_task(self._start_channel(name, channel)))

        # 等待所有渠道启动完成 (它们应该永久运行)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self) -> None:
        """停止所有渠道和分发器。"""
        logger.info("Stopping all channels...")

        # 停止分发器
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        # 停止所有渠道
        for name, channel in self.channels.items():
            try:
                await channel.stop()
                logger.info("Stopped {} channel", name)
            except Exception as e:
                logger.error("Error stopping {}: {}", name, e)

    async def _dispatch_outbound(self) -> None:
        """分发出站消息到相应渠道。

        此方法持续从outbound队列消费消息，
        并根据消息的channel字段发送到对应渠道。
        """
        logger.info("Outbound dispatcher started")

        while True:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_outbound(),
                    timeout=1.0
                )

                # 处理进度消息
                if msg.metadata.get("_progress"):
                    if msg.metadata.get("_tool_hint") and not self.config.channels.send_tool_hints:
                        continue
                    if not msg.metadata.get("_tool_hint") and not self.config.channels.send_progress:
                        continue

                channel = self.channels.get(msg.channel)
                if channel:
                    try:
                        await channel.send(msg)
                    except Exception as e:
                        logger.error("Error sending to {}: {}", msg.channel, e)
                else:
                    logger.warning("Unknown channel: {}", msg.channel)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    def get_channel(self, name: str) -> BaseChannel | None:
        """根据名称获取渠道。

        Args:
            name: 渠道名称

        Returns:
            渠道实例，如果不存在则返回None
        """
        return self.channels.get(name)

    def get_status(self) -> dict[str, Any]:
        """获取所有渠道的状态。

        Returns:
            渠道状态字典 {渠道名: {enabled: bool, running: bool}}
        """
        return {
            name: {
                "enabled": True,
                "running": channel.is_running
            }
            for name, channel in self.channels.items()
        }

    @property
    def enabled_channels(self) -> list[str]:
        """获取已启用的渠道名称列表。

        Returns:
            渠道名称列表
        """
        return list(self.channels.keys())
