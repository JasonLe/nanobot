"""工具注册表 - 动态管理Agent工具的类。

功能:
- 注册/注销工具
- 获取工具定义
- 执行工具调用
- 参数验证和类型转换

该模块是Agent工具系统的核心，负责管理所有可用工具
并处理工具执行过程中的参数验证和错误处理。
"""

from typing import Any

from nanobot.agent.tools.base import Tool


class ToolRegistry:
    """Agent工具的注册表。

    允许动态注册和执行工具。
    支持参数验证、类型转换和错误处理。
    """

    def __init__(self):
        """初始化工具注册表。"""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具。

        Args:
            tool: 工具实例
        """
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """根据名称注销工具。

        Args:
            name: 工具名称
        """
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """根据名称获取工具。

        Args:
            name: 工具名称

        Returns:
            工具实例，如果不存在则返回None
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """检查工具是否已注册。

        Args:
            name: 工具名称

        Returns:
            已注册返回True，否则返回False
        """
        return name in self._tools

    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具的OpenAI格式定义。

        用于LLM调用工具时传递工具schema。

        Returns:
            工具定义列表
        """
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """根据名称和参数执行工具。

        执行流程:
        1. 查找工具
        2. 参数类型转换
        3. 参数验证
        4. 执行工具
        5. 错误处理

        Args:
            name: 工具名称
            params: 工具参数

        Returns:
            工具执行结果字符串，错误时返回错误信息
        """
        _HINT = "\n\n[Analyze the error above and try a different approach.]"

        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found. Available: {', '.join(self.tool_names)}"

        try:
            # 尝试将参数转换为匹配schema的类型
            params = tool.cast_params(params)
            
            # 验证参数
            errors = tool.validate_params(params)
            if errors:
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors) + _HINT
            result = await tool.execute(**params)
            if isinstance(result, str) and result.startswith("Error"):
                return result + _HINT
            return result
        except Exception as e:
            return f"Error executing {name}: {str(e)}" + _HINT

    @property
    def tool_names(self) -> list[str]:
        """获取已注册工具名称列表。

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def __len__(self) -> int:
        """获取已注册工具数量。

        Returns:
            工具数量
        """
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """检查工具是否已注册 (支持in操作符)。

        Args:
            name: 工具名称

        Returns:
            已注册返回True，否则返回False
        """
        return name in self._tools
