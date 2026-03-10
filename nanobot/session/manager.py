"""会话管理 - 管理对话历史记录。

功能:
- Session: 单个对话会话的数据结构
- SessionManager: 会话管理器，负责会话的创建、加载、保存

会话以JSONL格式存储，每行是一条JSON记录:
- 元数据行: 包含会话创建时间、最后整合位置等
- 消息行: 包含角色、内容、时间戳等

特性:
- 内存缓存: 常用会话缓存在内存中提高性能
- 自动迁移: 从旧版本目录自动迁移会话文件
- 只追加模式: 消息只增不减，保证LLM缓存效率
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.config.paths import get_legacy_sessions_dir
from nanobot.utils.helpers import ensure_dir, safe_filename


@dataclass
class Session:
    """一个对话会话。

    以JSONL格式存储消息，便于阅读和持久化。

    注意: 消息只增不减以保证LLM缓存效率。
    整合过程会将摘要写入MEMORY.md/HISTORY.md，
    但不会修改messages列表或get_history()输出。

    属性:
        key: 会话键 (格式: channel:chat_id)
        messages: 消息列表
        created_at: 创建时间
        updated_at: 更新时间
        metadata: 元数据
        last_consolidated: 已整合到文件的消息数量
    """

    key: str  # channel:chat_id
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_consolidated: int = 0  # Number of messages already consolidated to files

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """向会话添加一条消息。

        Args:
            role: 消息角色 (user/assistant/system/tool)
            content: 消息内容
            **kwargs: 其他消息字段
        """
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.messages.append(msg)
        self.updated_at = datetime.now()

    def get_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
        """返回未整合的消息用于LLM输入，对齐到用户轮次。

        Args:
            max_messages: 最大返回消息数

        Returns:
            消息列表
        """
        unconsolidated = self.messages[self.last_consolidated:]
        sliced = unconsolidated[-max_messages:]

        # 丢弃开头的非用户消息，避免孤立的tool_result块
        for i, m in enumerate(sliced):
            if m.get("role") == "user":
                sliced = sliced[i:]
                break

        out: list[dict[str, Any]] = []
        for m in sliced:
            entry: dict[str, Any] = {"role": m["role"], "content": m.get("content", "")}
            for k in ("tool_calls", "tool_call_id", "name"):
                if k in m:
                    entry[k] = m[k]
            out.append(entry)
        return out

    def clear(self) -> None:
        """清除所有消息并将会话重置为初始状态。"""
        self.messages = []
        self.last_consolidated = 0
        self.updated_at = datetime.now()


class SessionManager:
    """管理对话会话的类。

    会话以JSONL文件形式存储在sessions目录中。
    """

    def __init__(self, workspace: Path):
        """初始化会话管理器。

        Args:
            workspace: 工作目录路径
        """
        self.workspace = workspace
        self.sessions_dir = ensure_dir(self.workspace / "sessions")
        self.legacy_sessions_dir = get_legacy_sessions_dir()
        self._cache: dict[str, Session] = {}

    def _get_session_path(self, key: str) -> Path:
        """获取会话文件路径。

        Args:
            key: 会话键

        Returns:
            会话文件路径
        """
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"

    def _get_legacy_session_path(self, key: str) -> Path:
        """获取旧版全局会话路径 (~/.nanobot/sessions/)。

        Args:
            key: 会话键

        Returns:
            旧版会话文件路径
        """
        safe_key = safe_filename(key.replace(":", "_"))
        return self.legacy_sessions_dir / f"{safe_key}.jsonl"

    def get_or_create(self, key: str) -> Session:
        """获取现有会话或创建新会话。

        Args:
            key: 会话键 (通常为 channel:chat_id)

        Returns:
            会话对象
        """
        if key in self._cache:
            return self._cache[key]

        session = self._load(key)
        if session is None:
            session = Session(key=key)

        self._cache[key] = session
        return session

    def _load(self, key: str) -> Session | None:
        """从磁盘加载会话。

        Args:
            key: 会话键

        Returns:
            会话对象，如果不存在则返回None
        """
        path = self._get_session_path(key)
        if not path.exists():
            legacy_path = self._get_legacy_session_path(key)
            if legacy_path.exists():
                try:
                    shutil.move(str(legacy_path), str(path))
                    logger.info("Migrated session {} from legacy path", key)
                except Exception:
                    logger.exception("Failed to migrate session {}", key)

        if not path.exists():
            return None

        try:
            messages = []
            metadata = {}
            created_at = None
            last_consolidated = 0

            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)

                    if data.get("_type") == "metadata":
                        metadata = data.get("metadata", {})
                        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                        last_consolidated = data.get("last_consolidated", 0)
                    else:
                        messages.append(data)

            return Session(
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                metadata=metadata,
                last_consolidated=last_consolidated
            )
        except Exception as e:
            logger.warning("Failed to load session {}: {}", key, e)
            return None

    def save(self, session: Session) -> None:
        """将会话保存到磁盘。

        Args:
            session: 要保存的会话对象
        """
        path = self._get_session_path(session.key)

        with open(path, "w", encoding="utf-8") as f:
            metadata_line = {
                "_type": "metadata",
                "key": session.key,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata,
                "last_consolidated": session.last_consolidated
            }
            f.write(json.dumps(metadata_line, ensure_ascii=False) + "\n")
            for msg in session.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        self._cache[session.key] = session

    def invalidate(self, key: str) -> None:
        """从内存缓存中移除会话。

        Args:
            key: 会话键
        """
        self._cache.pop(key, None)

    def list_sessions(self) -> list[dict[str, Any]]:
        """列出所有会话。

        Returns:
            会话信息字典列表
        """
        sessions = []

        for path in self.sessions_dir.glob("*.jsonl"):
            try:
                # 只读取元数据行
                with open(path, encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("_type") == "metadata":
                            key = data.get("key") or path.stem.replace("_", ":", 1)
                            sessions.append({
                                "key": key,
                                "created_at": data.get("created_at"),
                                "updated_at": data.get("updated_at"),
                                "path": str(path)
                            })
            except Exception:
                continue

        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)
