"""
Web搜索模块 - 支持多搜索引擎
"""

import os
from typing import List, Dict, Any
import requests


class WebSearcher:
    """网页搜索引擎包装器"""

    def __init__(self):
        """初始化Web搜索器"""
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.bing_api_key = os.getenv("BING_API_KEY")
        self.timeout = 30

    def search(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        在网络上搜索信息

        Args:
            query: 搜索查询（已由 RESEARCHER_PROMPT 生成，包含布尔逻辑等）
            num_results: 返回结果数量

        Returns:
            包含 title, url, snippet 的搜索结果列表
        """
        print(f"  🌐 搜索: {query}")

        results = []

        # 优先尝试 Serper API
        if self.serper_api_key:
            try:
                results = self._search_serper(query, num_results)
            except Exception as e:
                print(f"  ⚠️  Serper API 失败: {e}")

        # 备选：Bing API
        if not results and self.bing_api_key:
            try:
                results = self._search_bing(query, num_results)
            except Exception as e:
                print(f"  ⚠️  Bing API 失败: {e}")

        if not results:
            print(f"  ⚠️  所有搜索引擎均失败")
            return []

        print(f"  ✓ 找到 {len(results)} 个结果")
        return results

    def _search_serper(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """使用 Serper API 搜索"""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results,
            "gl": "cn",
            "hl": "zh-cn"
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get('organic', [])[:num_results]:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'source': 'serper'
            })

        return results

    def _search_bing(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """使用 Bing Search API 搜索"""
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": self.bing_api_key
        }
        params = {
            "q": query,
            "count": num_results,
            "mkt": "zh-CN"
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get('webPages', {}).get('value', [])[:num_results]:
            results.append({
                'title': item.get('name', ''),
                'url': item.get('url', ''),
                'snippet': item.get('snippet', ''),
                'source': 'bing'
            })

        return results
