"""会话管理模块"""

import time
import uuid
from typing import Optional

import config


class DialogueManager:
    """对话会话管理器。

    维护多轮对话的会话状态，支持会话创建、轮次记录、历史查询和过期清理。
    每个会话存储最近 N 轮的用户-助手对话历史。
    """

    def __init__(self, ttl: Optional[int] = None, max_rounds: Optional[int] = None):
        """初始化会话管理器。

        Args:
            ttl: 会话过期时间（秒），默认使用 config.SESSION_TTL_SECONDS
            max_rounds: 每会话最大保留轮次，默认使用 config.MAX_HISTORY_ROUNDS
        """
        self.ttl = ttl or config.SESSION_TTL_SECONDS
        self.max_rounds = max_rounds or config.MAX_HISTORY_ROUNDS
        self._sessions: dict[str, dict] = {}  # session_id -> {turns, last_active}

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """获取已有会话或创建新会话。

        Args:
            session_id: 可选的现有会话 ID；为 None 时自动生成

        Returns:
            会话 ID 字符串
        """
        if session_id and session_id in self._sessions:
            self._sessions[session_id]["last_active"] = time.time()
            return session_id

        new_id = session_id or str(uuid.uuid4())
        self._sessions[new_id] = {
            "turns": [],
            "last_active": time.time(),
            "created_at": time.time(),
        }
        return new_id

    def add_turn(self, session_id: str, question: str, answer: str):
        """向会话中添加一轮对话记录。

        Args:
            session_id: 会话 ID
            question: 用户提问
            answer: 助手回答
        """
        if session_id not in self._sessions:
            # 自动创建会话
            self.get_or_create_session(session_id)

        session = self._sessions[session_id]
        session["turns"].append({
            "role": "user",
            "content": question,
            "timestamp": time.time(),
        })
        session["turns"].append({
            "role": "assistant",
            "content": answer,
            "timestamp": time.time(),
        })
        session["last_active"] = time.time()

        # 限制保留轮次（截断较早的记录，保留最近 max_rounds 轮）
        # 每轮是 2 条记录（user + assistant）
        max_records = self.max_rounds * 2
        if len(session["turns"]) > max_records:
            session["turns"] = session["turns"][-max_records:]

    def get_history(self, session_id: str) -> list[dict]:
        """获取会话的对话历史。

        返回 OpenAIChat-compatible 的消息列表，每项含 role 和 content。

        Args:
            session_id: 会话 ID

        Returns:
            历史消息列表，格式为 [{"role": "user"/"assistant", "content": "..."}]
        """
        if session_id not in self._sessions:
            return []

        session = self._sessions[session_id]
        history = []
        for turn in session["turns"]:
            history.append({
                "role": turn["role"],
                "content": turn["content"],
            })

        return history

    def cleanup_expired(self):
        """清理所有超过 TTL 的过期会话。"""
        now = time.time()
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if now - session["last_active"] > self.ttl
        ]
        for sid in expired_ids:
            del self._sessions[sid]

        if expired_ids:
            print(f"[DialogueManager] Cleaned up {len(expired_ids)} expired sessions.")

    def get_session_count(self) -> int:
        """获取当前活跃会话数。

        Returns:
            会话数量
        """
        return len(self._sessions)
