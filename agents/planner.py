"""
Planner Agent - 理解用户请求，设计研究内容
"""
import json
from typing import Dict, Any
from anthropic import Anthropic


class PlannerAgent:
    """规划Agent - 最小token设计"""

    def __init__(self, client: Anthropic, model: str = "claude-sonnet-4-6"):
        self.client = client
        self.model = model

    def plan(self, query: str) -> Dict[str, Any]:
        """
        生成研究计划
        Token优化:
        - 简洁prompt - JSON结构化输出 - 限制输出长度
        """
        from prompts.templates import PLANNER_PROMPT

        prompt = PLANNER_PROMPT.format(query=query)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,  # 限制输出
            temperature=0.8,  # 降低随机性
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # 解析JSON输出（处理 ThinkingBlock）
        content = self._extract_text_from_response(response)
        try:
            plan = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            # 降级处理 - 使用新的五维度格式
            plan = {
                "time_range": "当前",
                "region": "中国",
                "subjects": [query],
                "research_questions": [query],
                "industry_areas": [""]
            }

        return plan

    @staticmethod
    def _extract_text_from_response(response) -> str:
        """从响应中提取文本内容（跳过 ThinkingBlock）"""
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        return '\n'.join(text_parts)

    @staticmethod
    def _extract_json(text: str) -> str:
        """提取JSON内容"""
        # 尝试找到JSON块
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return text[start:end]
        return text
