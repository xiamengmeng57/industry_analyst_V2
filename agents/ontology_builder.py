"""
Ontology Builder Agent - 构建事实本体和分析关联
集成 Zep Cloud 进行知识图谱存储和更新
"""
import json
from typing import Dict, List, Any, Optional
from anthropic import Anthropic


class OntologyBuilderAgent:
    """本体构建Agent - 知识图谱"""

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

    def build_ontology(
        self,
        verified_facts: List[Dict],
        session_id: Optional[str] = None,
        use_existing_graph: bool = True
    ) -> Dict[str, Any]:
        """
        构建知识本体

        Token优化:
        - 仅处理验证过的事实
        - 图结构紧凑表示
        - 聚焦高价值关系

        Args:
            verified_facts: 验证过的事实列表
            session_id: 会话ID（用于Zep存储）
            use_existing_graph: 是否从Zep读取现有图谱并增量更新

        Returns:
            知识图谱
        """
        from prompts.templates import ONTOLOGY_BUILDER_PROMPT

        # 1. 尝试从 Zep 读取现有图谱
        existing_ontology = None
        if use_existing_graph and self.zep_manager and session_id:
            print("  📥 尝试从 Zep Cloud 读取现有图谱...")
            existing_ontology = self.zep_manager.retrieve_ontology(session_id)

        # 2. 构建新的图谱
        # 超精简事实表示
        compact_facts = [
            {
                "fact": f.get("fact", str(f)),
                "confidence": f.get("confidence", 0)
            }
            for f in verified_facts  # 限制数量
            # if f.get("confidence", 0) >= 0.7  # 只使用高置信度事实
        ]

        # 如果有现有图谱，在 Prompt 中提供上下文
        existing_context = ""
        if existing_ontology:
            entity_count = len(existing_ontology.get("entities", []))
            relation_count = len(existing_ontology.get("relations", []))
            existing_context = f"\n现有图谱: {entity_count}个实体, {relation_count}个关系"

        prompt = ONTOLOGY_BUILDER_PROMPT.format(
            verified_facts=json.dumps(compact_facts, ensure_ascii=False)
        ) + existing_context

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.4,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        content = self._extract_text_from_response(response)
        try:
            new_ontology = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            new_ontology = {
                "entities": [],
                "relations": [],
                "insights": [{"description": content[:200], "confidence": 0.5}]
            }

        # 3. 如果启用 Zep，更新或存储图谱
        if self.zep_manager and session_id:
            if existing_ontology:
                # 增量更新
                print("  🔄 增量更新知识图谱到 Zep Cloud...")
                self.zep_manager.update_ontology(
                    new_ontology,
                    session_id,
                    incremental=True
                )
            else:
                # 首次存储
                print("  💾 存储知识图谱到 Zep Cloud...")
                self.zep_manager.store_ontology(
                    new_ontology,
                    session_id
                )

        return new_ontology

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

    def get_graph_summary(self, ontology: Dict[str, Any]) -> str:
        """获取图摘要 - 节省token"""
        entities = len(ontology.get("entities", []))
        relations = len(ontology.get("relations", []))
        insights = len(ontology.get("insights", []))

        return f"Graph: {entities}E, {relations}R, {insights}I"
