"""Redis 客户端连接管理

初始化时立即尝试连接真实 Redis（超时 1s），失败则降级到 fakeredis。
"""

import redis
from app.config import settings


class _RedisClientProxy:
    """Redis 客户端代理，初始化时立即检测并确定后端"""

    def __init__(self):
        self._client = self._init_client()

    @staticmethod
    def _init_client():
        """初始化时立即尝试真实 Redis，失败则降级"""
        if settings.REDIS_FALLBACK_TO_FAKE:
            try:
                client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=2,
                    socket_keepalive=False,
                    retry_on_timeout=False,
                    health_check_interval=0,
                )
                client.ping()
                print(
                    f"Redis: connected to real Redis at "
                    f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                )
                return client
            except Exception:
                pass

        import fakeredis

        print("Redis: using fakeredis (in-memory)")
        return fakeredis.FakeRedis(decode_responses=True)

    def __getattr__(self, name):
        """透明代理：所有方法调用委托给底层客户端"""
        return getattr(self._client, name)


# 模块级单例 — 导入即初始化
redis_client = _RedisClientProxy()


def get_redis():
    """FastAPI 依赖注入：获取 Redis 客户端"""
    return redis_client
