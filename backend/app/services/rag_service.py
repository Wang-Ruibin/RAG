"""RAG 问答服务 — ai_service HTTP 客户端"""

import httpx

AI_SERVICE_URL = "http://localhost:8003"


class RAGService:
    """封装与 ai_service 的 HTTP 通信"""

    @staticmethod
    async def query(question: str, top_k: int = 5) -> dict:
        """调用 ai_service /query 端点获取 RAG 问答结果"""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{AI_SERVICE_URL}/query",
                json={"question": question, "top_k": top_k},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def query_stream(question: str, top_k: int = 5):
        """调用 ai_service /query/stream 端点，逐行 yield SSE 事件"""
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "GET",
                f"{AI_SERVICE_URL}/query/stream",
                params={"question": question, "top_k": top_k},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield line[6:]

    @staticmethod
    async def reindex() -> dict:
        """触发 ai_service 全量重新索引"""
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.get(f"{AI_SERVICE_URL}/reindex")
            return resp.json()

    @staticmethod
    async def stats() -> dict:
        """获取知识库统计信息"""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{AI_SERVICE_URL}/stats")
            return resp.json()

    @staticmethod
    async def process_file(file_path: str) -> dict:
        """提交文件路径给 ai_service 处理"""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{AI_SERVICE_URL}/process",
                json={"file_path": file_path},
            )
            return resp.json()
