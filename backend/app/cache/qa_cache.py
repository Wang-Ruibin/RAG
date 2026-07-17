"""问答缓存 - Redis 缓存核心逻辑"""

import hashlib
import json
from datetime import datetime

from app.config import settings
from app.redis_client import redis_client

PREFIX = settings.CACHE_KEY_PREFIX


class QACache:
    """问答缓存服务"""

    @staticmethod
    def _make_qa_key(user_id: int, question: str) -> str:
        """生成问答缓存 key: campus:qa:qa:{user_id}:{question_short}:{hash_short}"""
        q_hash = hashlib.md5(question.encode("utf-8")).hexdigest()
        question_short = question[:30].replace(":", "_")
        q_hash_short = q_hash[:8]
        return f"{PREFIX}qa:{user_id}:{question_short}:{q_hash_short}"

    @staticmethod
    def _make_session_key(session_id: str) -> str:
        """生成会话缓存 key: campus:qa:session:{session_id}"""
        return f"{PREFIX}session:{session_id}"

    @staticmethod
    def _make_hot_key() -> str:
        """生成热数据统计 key"""
        return f"{PREFIX}hot:questions"

    @staticmethod
    def get_cached_answer(user_id: int, question: str) -> str | None:
        """获取缓存的问答结果"""
        try:
            key = QACache._make_qa_key(user_id, question)
            data = redis_client.get(key)
            if data:
                return data
        except Exception:
            pass
        return None

    @staticmethod
    def set_cached_answer(user_id: int, question: str, answer: str) -> None:
        """缓存问答结果"""
        try:
            key = QACache._make_qa_key(user_id, question)
            redis_client.setex(key, settings.CACHE_EXPIRE_SECONDS, answer)
        except Exception:
            pass

    @staticmethod
    def get_session_history(session_id: str) -> list[dict] | None:
        """获取缓存的会话历史"""
        try:
            key = QACache._make_session_key(session_id)
            data = redis_client.lrange(key, 0, -1)
            if data:
                return [json.loads(item) for item in data]
        except Exception:
            pass
        return None

    @staticmethod
    def append_to_session(
        session_id: str, question: str, answer: str
    ) -> None:
        """追加记录到会话缓存"""
        try:
            key = QACache._make_session_key(session_id)
            entry = json.dumps(
                {
                    "question": question,
                    "answer": answer,
                    "timestamp": datetime.now().isoformat(),
                },
                ensure_ascii=False,
            )
            redis_client.rpush(key, entry)
            # 设置会话缓存过期时间（7天）
            redis_client.expire(key, 604800)
        except Exception:
            pass

    @staticmethod
    def clear_session(session_id: str) -> None:
        """清除会话缓存"""
        try:
            key = QACache._make_session_key(session_id)
            redis_client.delete(key)
        except Exception:
            pass

    @staticmethod
    def increment_hot_count(question: str) -> None:
        """增加问题的热门计数"""
        try:
            key = QACache._make_hot_key()
            redis_client.zincrby(key, 1, question)
            # 热数据统计保留 7 天
            redis_client.expire(key, 604800)
        except Exception:
            pass

    @staticmethod
    def get_hot_questions(limit: int = 10) -> list[dict]:
        """获取热门问题列表"""
        try:
            key = QACache._make_hot_key()
            results = redis_client.zrevrange(key, 0, limit - 1, withscores=True)
            return [
                {"question": q, "count": int(c)} for q, c in results
            ]
        except Exception:
            return []
