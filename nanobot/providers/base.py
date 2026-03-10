"""LLM提供者基类 - 定义与大语言模型交互的统一接口。

该模块提供了:
- ToolCallRequest: 工具调用请求数据结构
- LLMResponse: LLM响应数据结构
- LLMProvider: 抽象基类，定义LLM提供者的接口规范

各LLM提供者(如OpenAI、Anthropic、DeepSeek等)需要实现此接口，
以保持与nanobot框架的兼容性。
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class ToolCallRequest:
    """LLM发起的工具调用请求。

    属性:
        id: 工具调用唯一标识符
        name: 工具名称
        arguments: 工具参数字典
    """
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """LLM提供者的响应数据结构。

    属性:
        content: 文本内容 (当LLM直接回复时)
        tool_calls: 工具调用请求列表 (当LLM请求执行工具时)
        finish_reason: 结束原因 ("stop"=正常结束, "tool_calls"=需要工具调用, "error"=错误)
        usage: token使用量统计
        reasoning_content: 推理内容 (如Kimi、DeepSeek-R1等模型的思维链)
        thinking_blocks: 思考块列表 (如Anthropic扩展思考模式)
    """
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    reasoning_content: str | None = None  # Kimi, DeepSeek-R1 etc.
    thinking_blocks: list[dict] | None = None  # Anthropic extended thinking
    
    @property
    def has_tool_calls(self) -> bool:
        """检查响应是否包含工具调用请求。

        Returns:
            如果有工具调用返回True，否则返回False
        """
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    LLM提供者的抽象基类。

    实现类需要处理各提供者API的具体细节，
    同时保持统一的接口规范。

    主要特性:
    - 重试机制: 自动重试临时性错误 (如Rate Limit、服务器错误等)
    - 消息清洗: 处理空内容、规范化消息格式等
    """

    # 重试延迟配置 (秒)
    _CHAT_RETRY_DELAYS = (1, 2, 4)
    # 临时性错误关键词匹配
    _TRANSIENT_ERROR_MARKERS = (
        "429",
        "rate limit",
        "500",
        "502",
        "503",
        "504",
        "overloaded",
        "timeout",
        "timed out",
        "connection",
        "server error",
        "temporarily unavailable",
    )

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        """初始化LLM提供者。

        Args:
            api_key: API密钥 (可选)
            api_base: API基础URL (可选)
        """
        self.api_key = api_key
        self.api_base = api_base

    @staticmethod
    def _sanitize_empty_content(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """替换会导致提供者400错误的空内容。

        当MCP工具返回空内容时，大多数提供商会拒绝空字符串内容
        或列表内容中的空文本块。此方法清理这些无效内容。

        Args:
            messages: 消息列表

        Returns:
            清洗后的消息列表
        """
        result: list[dict[str, Any]] = []
        for msg in messages:
            content = msg.get("content")

            if isinstance(content, str) and not content:
                clean = dict(msg)
                clean["content"] = None if (msg.get("role") == "assistant" and msg.get("tool_calls")) else "(empty)"
                result.append(clean)
                continue

            if isinstance(content, list):
                filtered = [
                    item for item in content
                    if not (
                        isinstance(item, dict)
                        and item.get("type") in ("text", "input_text", "output_text")
                        and not item.get("text")
                    )
                ]
                if len(filtered) != len(content):
                    clean = dict(msg)
                    if filtered:
                        clean["content"] = filtered
                    elif msg.get("role") == "assistant" and msg.get("tool_calls"):
                        clean["content"] = None
                    else:
                        clean["content"] = "(empty)"
                    result.append(clean)
                    continue

            if isinstance(content, dict):
                clean = dict(msg)
                clean["content"] = [content]
                result.append(clean)
                continue

            result.append(msg)
        return result

    @staticmethod
    def _sanitize_request_messages(
        messages: list[dict[str, Any]],
        allowed_keys: frozenset[str],
    ) -> list[dict[str, Any]]:
        """只保留提供者安全的消息键，并规范化助手消息内容。

        Args:
            messages: 原始消息列表
            allowed_keys: 允许保留的键集合

        Returns:
            清洗后的消息列表
        """
        sanitized = []
        for msg in messages:
            clean = {k: v for k, v in msg.items() if k in allowed_keys}
            if clean.get("role") == "assistant" and "content" not in clean:
                clean["content"] = None
            sanitized.append(clean)
        return sanitized

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
    ) -> LLMResponse:
        """发送聊天完成请求。

        Args:
            messages: 消息列表，每条消息包含'role'和'content'
            tools: 可选的工具定义列表
            model: 模型标识符 (提供者特定)
            max_tokens: 响应最大token数
            temperature: 采样温度
            reasoning_effort: 推理努力程度 (可选)

        Returns:
            LLMResponse: 包含内容和/或工具调用
        """
        pass

    @classmethod
    def _is_transient_error(cls, content: str | None) -> bool:
        """判断是否为临时性错误 (可重试)。

        Args:
            content: 错误信息内容

        Returns:
            如果是临时性错误返回True
        """
        err = (content or "").lower()
        return any(marker in err for marker in cls._TRANSIENT_ERROR_MARKERS)

    async def chat_with_retry(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
    ) -> LLMResponse:
        """调用chat方法，临时错误时自动重试。

        使用指数退避策略重试，包含以下错误类型:
        - Rate limit (429)
        - 服务器错误 (500-504)
        - 超时错误
        - 连接错误

        Args:
            messages: 消息列表
            tools: 可选的工具定义
            model: 模型标识符
            max_tokens: 最大token数
            temperature: 采样温度
            reasoning_effort: 推理努力程度

        Returns:
            LLMResponse: 最终响应
        """
        for attempt, delay in enumerate(self._CHAT_RETRY_DELAYS, start=1):
            try:
                response = await self.chat(
                    messages=messages,
                    tools=tools,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    reasoning_effort=reasoning_effort,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                response = LLMResponse(
                    content=f"Error calling LLM: {exc}",
                    finish_reason="error",
                )

            if response.finish_reason != "error":
                return response
            if not self._is_transient_error(response.content):
                return response

            err = (response.content or "").lower()
            logger.warning(
                "LLM transient error (attempt {}/{}), retrying in {}s: {}",
                attempt,
                len(self._CHAT_RETRY_DELAYS),
                delay,
                err[:120],
            )
            await asyncio.sleep(delay)

        try:
            return await self.chat(
                messages=messages,
                tools=tools,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return LLMResponse(
                content=f"Error calling LLM: {exc}",
                finish_reason="error",
            )

    @abstractmethod
    def get_default_model(self) -> str:
        """获取此提供者的默认模型。

        Returns:
            默认模型名称
        """
        pass
