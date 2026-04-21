"""
Fact Checker Agent - 核对事实
"""
import json
from typing import Dict, List, Any, Optional
from anthropic import Anthropic


class FactCheckerAgent:
    """事实核查Agent"""

    def __init__(self, client: Anthropic, model: str = "claude-sonnet-4-6"):
        self.client = client
        self.model = model

    def verify(
        self,
        findings: List[Dict],
        user_documents: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        验证事实

        Args:
            findings: 从网络等来源收集的事实列表
            user_documents: 用户上传的文档列表（已转换为 findings 格式）

        Token优化:
        - 批量验证而非逐条
        - 仅传递核心字段（包含时间信息）
        - 紧凑输出格式

        Returns:
            包含 verified, unverified, time_conflicts 的字典
        """
        from prompts.templates import FACT_CHECKER_PROMPT

        # 处理用户上传的文档（直接标记为 verified）
        user_verified = []
        if user_documents:
            user_verified = self._convert_user_docs_to_verified(user_documents)

        # 精简findings - 保留关键信息和时间字段
        compact_findings = [
            {
                "topic": f.get("topic", "")[:80],
                "data": f.get("data", "")[:800],  # 增加长度以包含更多上下文
                "source": f.get("source", "")[:100],
                "publication_date": f.get("publication_date", f.get("date", "")),
                "time_facts": f.get("time_facts", []),  # 保留完整的时间-事实关联
                "source_type": f.get("metadata", {}).get("source_type", "unknown")
            }
            for f in findings  # 略微增加数量以获取更多交叉验证
        ]

        prompt = FACT_CHECKER_PROMPT.format(
            findings=json.dumps(compact_findings, ensure_ascii=False, indent=2)
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=3072,  # 增加token以适应更详细的输出
            temperature=0.2,  # 低温度确保一致性
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        content = self._extract_text_from_response(response)
        try:
            result = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            print("  ⚠️ JSON解析失败，使用默认验证结果")
            result = {
                "verified": findings,
                "unverified": [],
                "time_conflicts": []
            }

        # 合并用户文档和 AI 验证的结果
        all_verified = user_verified + result.get("verified", [])

        return {
            "verified": all_verified,
            "unverified": result.get("unverified", []),
            "time_conflicts": result.get("time_conflicts", [])  # 新增：时间冲突列表
        }

    def _convert_user_docs_to_verified(
        self,
        user_documents: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        将用户上传的文档转换为 verified 格式

        Args:
            user_documents: 用户文档列表（findings 格式）

        Returns:
            verified 格式的列表
        """
        verified_list = []

        for doc in user_documents:
            verified = {
                "fact": doc.get("data", ""),
                "time": doc.get("date", ""),
                "publication_date": doc.get("publication_date", doc.get("date", "")),
                "confidence": 0.95,  # 用户提供的文档默认高置信度
                "source": doc.get("source", "user_upload://unknown"),
                "supporting_sources": [doc.get("source", "user_upload://unknown")],
                "cross_verified": False,  # 单一来源
                "time_verified": True,  # 假设用户提供的时间准确
                "timeliness": "用户提供",
                "time_conflicts": [],
                "metadata": doc.get("metadata", {
                    "source_type": "user_upload",
                    "is_user_provided": True
                })
            }
            verified_list.append(verified)

        return verified_list

    def add_user_documents(
        self,
        file_paths: List[str],
        titles: Optional[List[str]] = None,
        extract_time: bool = True
    ) -> List[Dict[str, Any]]:
        """
        添加用户文档并转换为 findings 格式

        Args:
            file_paths: 文档文件路径列表
            titles: 可选的标题列表
            extract_time: 是否提取时间事实（默认 True）

        Returns:
            转换后的 findings 列表
        """
        from utils import DocumentParser

        return DocumentParser.batch_convert_to_findings(
            file_paths,
            titles,
            extract_time=extract_time,
            anthropic_client=self.client  # 传递 Anthropic client 用于时间提取
        )

    @staticmethod
    def _extract_json(text: str) -> str:
        """提取JSON"""
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return text[start:end]
        return text

    @staticmethod
    def _extract_text_from_response(response) -> str:
        """从响应中提取文本内容（跳过 ThinkingBlock）"""
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        return '\n'.join(text_parts)
