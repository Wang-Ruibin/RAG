"""
LLM generator for the RAG engine.

Provides a ``Generator`` class that wraps the DeepSeek API (via OpenAI-compatible
interface) with retry logic, streaming support, and context-aware generation.
"""

import logging
import os
import sys
import time
from typing import Generator

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOTENV_PATH = os.path.join(_BASE_DIR, ".env")

# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class Generator:
    """DeepSeek-powered text generator for RAG pipelines.

    Parameters
    ----------
    api_key : str, optional
        DeepSeek API key. Falls back to ``DEEPSEEK_API_KEY`` env var.
    base_url : str, optional
        API base URL (default ``https://api.deepseek.com``).
    model : str, optional
        Model name (default ``deepseek-chat``).
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-chat"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        load_dotenv(_DOTENV_PATH)

        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", self.DEFAULT_BASE_URL)
        self.model = model or os.getenv("DEEPSEEK_MODEL", self.DEFAULT_MODEL)

        if not self.api_key:
            logger.error("DEEPSEEK_API_KEY not found in environment or .env")
            sys.exit(1)

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(
            "Generator initialised (model=%s, base_url=%s)", self.model, self.base_url
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Send a completion request and return the response text.

        Retries up to 3 times with exponential backoff (1 s, 2 s, 4 s).

        Parameters
        ----------
        system_prompt : str
            System-level instruction.
        user_prompt : str
            User query / context.
        temperature : float, optional
            Sampling temperature (default ``0.3``).
        max_tokens : int, optional
            Maximum tokens in the response (default ``1024``).

        Returns
        -------
        str
            Generated answer text.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30,
                )
                return resp.choices[0].message.content.strip()
            except Exception as exc:
                if attempt < max_retries - 1:
                    wait = 2**attempt  # 1, 2, 4
                    logger.warning(
                        "API request failed (attempt %d/%d): %s — retrying in %ds",
                        attempt + 1,
                        max_retries,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "API request failed after %d attempts: %s",
                        max_retries,
                        exc,
                    )
                    return f"[API Error] {exc}. Please check API key and network connection."

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Generator[str, None, None]:
        """Stream a completion, yielding tokens as they arrive.

        Parameters
        ----------
        system_prompt : str
            System-level instruction.
        user_prompt : str
            User query / context.
        temperature : float, optional
            Sampling temperature (default ``0.3``).
        max_tokens : int, optional
            Maximum tokens in the response (default ``1024``).

        Yields
        ------
        str
            Content delta from each streaming chunk.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                stream = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    timeout=30,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
                return  # successfully finished streaming
            except Exception as exc:
                if attempt < max_retries - 1:
                    wait = 2**attempt
                    logger.warning(
                        "Stream request failed (attempt %d/%d): %s — retrying in %ds",
                        attempt + 1,
                        max_retries,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "Stream request failed after %d attempts: %s",
                        max_retries,
                        exc,
                    )
                    yield f"[API Error] {exc}. Please check API key and network connection."

    def generate_with_context(
        self,
        query: str,
        context_chunks: list[dict],
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Generate an answer grounded in retrieved context chunks.

        Parameters
        ----------
        query : str
            User's question.
        context_chunks : list[dict]
            Retrieved chunks, each expected to have at least a ``"text"`` key
            (and optionally ``"source"``).
        system_prompt : str, optional
            Custom system prompt. Falls back to a default instruction if omitted.
        temperature : float, optional
            Sampling temperature (default ``0.3``).
        max_tokens : int, optional
            Maximum tokens in the response (default ``1024``).

        Returns
        -------
        str
            Generated answer with source markers ``[1]``, ``[2]``, etc.
        """
        # Build context string with source markers
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            text = chunk.get("text", "")
            source = chunk.get("source", "未知来源")
            context_parts.append(f"[{i}] {text}\n（来源：{source}）")
        context_str = "\n\n".join(context_parts)

        user_prompt = f"参考资料：\n{context_str}\n\n问题：{query}"

        if system_prompt is None:
            system_prompt = (
                "你是一个基于知识库的智能问答助手。"
                "请根据以下提供的参考资料回答用户的问题。"
                "在回答中标注引用来源，如 [1][2][3]。"
                "如果参考资料不足以回答问题，请如实说明，不要编造信息。"
                "请用中文回答，保持简洁准确。"
            )

        return self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def test(self) -> None:
        """Send a simple query to verify the API key and network work."""
        print("🧪 Testing DeepSeek API connection …", flush=True)
        try:
            reply = self.generate(
                system_prompt="You are a helpful assistant.",
                user_prompt="请用一句话介绍你自己。",
            )
            print(f"✅ Response: {reply}")
        except Exception as exc:
            print(f"❌ Test failed: {exc}")
