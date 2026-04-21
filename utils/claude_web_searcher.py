"""
Claude API Web Search - 使用 Claude 内置的 Web Search 功能
"""

import json
from typing import List, Dict, Any
from anthropic import Anthropic


class ClaudeWebSearcher:
    """使用 Claude API 内置 Web Search 功能的搜索器"""

    def __init__(self, client: Anthropic, model: str = "claude-haiku-4-5"):
        """
        初始化 Claude Web 搜索器

        Args:
            client: Anthropic 客户端实例
            model: 使用的模型
        """
        self.client = client
        self.model = model

    def search(
        self,
        query: str,
        focus_sources: List[str] = None,
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        使用 Claude 搜索网络内容

        Args:
            query: 搜索查询（可以是复杂的检索式）
            focus_sources: 重点关注的来源类型（如 ['官方文档', '行业报告', '新闻媒体']）
            num_results: 期望的结果数量

        Returns:
            搜索结果列表
        """
        print(f"  🤖 Claude Web Search: {query}")

        try:
            # 构建提示词
            sources_hint = ""
            if focus_sources:
                sources_hint = f"\n重点关注以下类型的来源：{', '.join(focus_sources)}"

            prompt = f"""请搜索关于"{query}"的最新网络内容。{sources_hint}

请提供：
1. 相关的网页、文章或报告
2. 关键信息和数据
3. 每个来源的标题、URL和摘要

请以JSON格式返回结果：
{{
  "results": [
    {{
      "title": "标题",
      "url": "URL",
      "snippet": "摘要（100-200字）",
      "source": "来源类型",
      "date": "发布日期（如果有）"
    }}
  ],
  "summary": "整体发现的简要总结"
}}

尽量提供至少{num_results}个结果。"""

            # 调用 Claude API（内置 web search）
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # 提取响应文本
            response_text = message.content[0].text.strip()

            # 解析 JSON
            data = self._extract_json(response_text)

            if data and 'results' in data:
                results = data['results']
                print(f"  ✓ Claude 找到 {len(results)} 个结果")

                # 如果有摘要，打印出来
                if 'summary' in data and data['summary']:
                    print(f"  💡 {data['summary'][:100]}...")

                return results
            else:
                print(f"  ⚠️  未找到有效的搜索结果")
                return []

        except Exception as e:
            print(f"  ⚠️  Claude Web Search 失败: {e}")
            return []

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取 JSON

        Args:
            text: 可能包含 JSON 的文本

        Returns:
            解析后的 JSON 对象
        """
        try:
            # 尝试从 markdown 代码块中提取
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_text = text[json_start:json_end].strip()
                return json.loads(json_text)
            elif "```" in text:
                json_start = text.find("```") + 3
                json_end = text.find("```", json_start)
                json_text = text[json_start:json_end].strip()
                return json.loads(json_text)
            else:
                # 尝试直接解析
                if "{" in text and "}" in text:
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    json_text = text[start:end]
                    return json.loads(json_text)
                else:
                    return {}
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON 解析失败: {e}")
            return {}

    def search_with_summary(
        self,
        query: str,
        focus_sources: List[str] = None,
        num_results: int = 10
    ) -> Dict[str, Any]:
        """
        搜索并返回结果和摘要

        Args:
            query: 搜索查询
            focus_sources: 重点关注的来源
            num_results: 期望的结果数量

        Returns:
            包含 'results' 和 'summary' 的字典
        """
        results = self.search(query, focus_sources, num_results)

        # 如果搜索成功，尝试获取摘要
        # （摘要已在 search 方法中提取）
        return {
            'results': results,
            'query': query
        }
