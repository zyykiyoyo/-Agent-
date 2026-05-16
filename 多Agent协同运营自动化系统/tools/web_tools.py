from __future__ import annotations
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WebTools:
    """Web-related tools for agents to fetch and search web content."""

    @staticmethod
    async def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    logger.warning("HTTP %d for %s", resp.status, url)
                    return None
        except Exception as e:
            logger.error("Error fetching %s: %s", url, e)
            return None

    @staticmethod
    async def check_url_health(url: str, timeout: int = 10) -> dict:
        result = {"url": url, "reachable": False, "status_code": None, "response_time_ms": None}
        try:
            async with aiohttp.ClientSession() as session:
                start = __import__("time").time()
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    elapsed = (__import__("time").time() - start) * 1000
                    result["reachable"] = True
                    result["status_code"] = resp.status
                    result["response_time_ms"] = round(elapsed, 2)
        except Exception as e:
            result["error"] = str(e)
        return result

    @staticmethod
    async def check_multiple_urls(urls: list[str]) -> list[dict]:
        import asyncio
        tasks = [WebTools.check_url_health(url) for url in urls]
        return await asyncio.gather(*tasks)
