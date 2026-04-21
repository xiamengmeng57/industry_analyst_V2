"""
Report Writer Agent - 基于本体和核对结果撰写报告
集成 Zep Cloud 读取历史知识图谱
"""
import json
from typing import Dict, List, Any, Optional
from anthropic import Anthropic


class ReportWriterAgent:
    """报告撰写Agent"""

    def __init__(
        self,
        client: Anthropic,
        model: str = "claude-sonnet-4-6",
        zep_api_key: Optional[str] = None,
        enable_zep: bool = True
    ):
        self.client = client
        self.model = model
        self.enable_zep = enable_zep

        # 初始化 Zep Graph Manager
        self.zep_manager = None
        if enable_zep:
            try:
                from utils.zep_graph_manager import ZepGraphManager
                self.zep_manager = ZepGraphManager(zep_api_key=zep_api_key)
            except ImportError:
                print("  ⚠️ Zep Graph Manager 未找到，禁用 Zep 功能")
            except Exception as e:
                print(f"  ⚠️ Zep Graph Manager 初始化失败: {str(e)}")

    def write_report(
        self,
        ontology: Dict[str, Any],
        verified_facts: List[Dict],
        query: str,
        session_id: Optional[str] = None,
        use_historical_knowledge: bool = True
    ) -> str:
        """
        撰写最终报告

        Token优化:
        - 仅传递关键洞察而非完整本体
        - 压缩事实列表
        - 流式输出（如需要）

        Args:
            ontology: 当前构建的知识图谱
            verified_facts: 验证过的事实列表
            query: 原始查询
            session_id: 会话ID（用于从Zep读取历史图谱）
            use_historical_knowledge: 是否使用历史知识增强报告

        Returns:
            分析报告
        """
        from prompts.templates import REPORT_WRITER_PROMPT

        # 1. 尝试从 Zep 读取历史图谱（用于增强报告）
        historical_context = ""
        if use_historical_knowledge and self.zep_manager and session_id:
            print("  📥 从 Zep Cloud 读取历史知识图谱...")
            historical_ontology = self.zep_manager.retrieve_ontology(session_id)

            if historical_ontology:
                hist_entities = len(historical_ontology.get("entities", []))
                hist_relations = len(historical_ontology.get("relations", []))
                hist_insights = historical_ontology.get("insights", [])[:3]

                historical_context = f"""

历史知识图谱（来自Zep Cloud）:
- 已知实体数: {hist_entities}
- 已知关系数: {hist_relations}
- 历史洞察: {json.dumps([i.get('description', '') for i in hist_insights], ensure_ascii=False)}

请结合历史知识和当前发现撰写报告。"""
                print(f"  ✓ 读取历史图谱: {hist_entities}实体, {hist_relations}关系")

        # 2. 提取当前图谱的关键信息
        key_insights = ontology.get("insights", [])[:5]
        top_entities = [
            e.get("name", "")
            for e in ontology.get("entities", [])[:10]
        ]

        # 3. 构建紧凑context
        context = {
            "insights": key_insights,
            "entities": top_entities,
            "fact_count": len(verified_facts)
        }

        prompt = REPORT_WRITER_PROMPT.format(
            ontology=json.dumps(context, ensure_ascii=False),
            verified_facts=f"{len(verified_facts)} verified facts",
            historical_context=historical_context
        )

        # 添加原始query作为指导
        full_prompt = f"原始需求: {query}\n\n{prompt}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=3072,  # 报告可以稍长
            temperature=0.7,  # 提高创造性
            messages=[{
                "role": "user",
                "content": full_prompt
            }]
        )

        report = self._extract_text_from_response(response)
        return report

    def write_report_streaming(
        self,
        ontology: Dict[str, Any],
        verified_facts: List[Dict],
        query: str
    ):
        """流式写入报告 - 进一步节省内存"""
        from prompts.templates import REPORT_WRITER_PROMPT

        key_insights = ontology.get("insights", [])[:5]
        top_entities = [e.get("name", "") for e in ontology.get("entities", [])[:10]]

        context = {
            "insights": key_insights,
            "entities": top_entities,
            "fact_count": len(verified_facts)
        }

        prompt = REPORT_WRITER_PROMPT.format(
            ontology=json.dumps(context, ensure_ascii=False),
            verified_facts=f"{len(verified_facts)} verified facts"
        )

        full_prompt = f"原始需求: {query}\n\n{prompt}"

        # 流式API
        with self.client.messages.stream(
            model=self.model,
            max_tokens=3072,
            temperature=0.7,
            messages=[{"role": "user", "content": full_prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text

    @staticmethod
    def _extract_text_from_response(response) -> str:
        """从响应中提取文本内容（跳过 ThinkingBlock）"""
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        return '\n'.join(text_parts)
