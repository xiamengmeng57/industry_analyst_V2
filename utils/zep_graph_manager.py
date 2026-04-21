"""
Zep Cloud 知识图谱管理器
使用 Zep Cloud 和 Graphiti 进行知识图谱的存储、更新和查询
"""
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class ZepGraphManager:
    """
    Zep Cloud 知识图谱管理器

    整合 Zep Cloud 和 Graphiti 用于：
    - 存储知识图谱（实体和关系）
    - 增量更新图谱
    - 查询相关知识
    """

    def __init__(
        self,
        zep_api_key: Optional[str] = None,
        graph_uri: Optional[str] = None,
        use_graphiti: bool = True
    ):
        """
        初始化图谱管理器

        Args:
            zep_api_key: Zep Cloud API Key（优先从环境变量读取）
            graph_uri: Graphiti 图数据库URI（可选，使用 Neo4j/FalkorDB等）
            use_graphiti: 是否使用 Graphiti 本地图谱（默认True）
        """
        self.zep_api_key = zep_api_key or os.getenv("ZEP_API_KEY")
        self.graph_uri = graph_uri
        self.use_graphiti = use_graphiti

        # 初始化 Zep Cloud 客户端
        self.zep_client = None
        if self.zep_api_key:
            try:
                from zep_cloud.client import Zep
                self.zep_client = Zep(api_key=self.zep_api_key)
                print("  ✓ Zep Cloud 客户端初始化成功")
            except ImportError:
                print("  ⚠️ zep-cloud 未安装，请运行: pip install zep-cloud")
            except Exception as e:
                print(f"  ⚠️ Zep Cloud 初始化失败: {str(e)}")

        # 初始化 Graphiti（可选）
        self.graphiti = None
        if self.use_graphiti and self.graph_uri:
            try:
                from graphiti_core import Graphiti
                self.graphiti = Graphiti(uri=self.graph_uri)
                print("  ✓ Graphiti 本地图谱初始化成功")
            except ImportError:
                print("  ⚠️ graphiti-core 未安装，请运行: pip install graphiti-core")
            except Exception as e:
                print(f"  ⚠️ Graphiti 初始化失败: {str(e)}")

    def store_ontology(
        self,
        ontology: Dict[str, Any],
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        存储知识图谱到 Zep Cloud

        Args:
            ontology: 知识图谱数据（包含 entities, relations, insights）
            session_id: 会话ID（用于关联分析任务）
            metadata: 额外的元数据（可选）

        Returns:
            是否存储成功
        """
        if not self.zep_client:
            print("  ⚠️ Zep Cloud 未配置，跳过存储")
            return False

        try:
            # 将图谱转换为 Zep 的事实格式
            facts = self._ontology_to_facts(ontology)

            # 添加元数据
            if metadata:
                facts["metadata"] = metadata

            facts["timestamp"] = datetime.now().isoformat()
            facts["session_id"] = session_id

            # 确保图谱存在
            try:
                self.zep_client.graph.create(
                    graph_id=session_id,
                    name=f"Industry Analysis - {session_id}",
                    description="Knowledge graph for industry analysis"
                )
                print(f"  ✓ 创建新图谱: {session_id}")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    pass  # 图谱已存在，继续
                else:
                    raise

            # 使用 Zep Cloud Graph API 存储
            message_content = json.dumps(facts, ensure_ascii=False)

            print(f"  📊 存储知识图谱到 Zep Cloud (graph_id: {session_id})")
            print(f"     - 实体数: {len(ontology.get('entities', []))}")
            print(f"     - 关系数: {len(ontology.get('relations', []))}")
            print(f"     - 洞察数: {len(ontology.get('insights', []))}")

            # 使用 graph.add() 添加数据
            episode = self.zep_client.graph.add(
                graph_id=session_id,
                data=message_content,
                type='json',
                metadata=metadata
            )

            print(f"  ✅ 存储成功")
            return True

        except Exception as e:
            print(f"  ❌ 存储到 Zep Cloud 失败: {str(e)}")
            return False

    def update_ontology(
        self,
        ontology: Dict[str, Any],
        session_id: str,
        incremental: bool = True
    ) -> bool:
        """
        增量更新知识图谱

        Args:
            ontology: 新的知识图谱数据
            session_id: 会话ID
            incremental: 是否增量更新（True）还是完全替换（False）

        Returns:
            是否更新成功
        """
        if not self.zep_client:
            print("  ⚠️ Zep Cloud 未配置，跳过更新")
            return False

        try:
            if incremental:
                # 增量更新：合并新旧数据
                print(f"  🔄 增量更新知识图谱 (session: {session_id})")

                # 获取现有图谱
                existing_ontology = self.retrieve_ontology(session_id)

                if existing_ontology:
                    # 合并实体
                    merged_entities = self._merge_entities(
                        existing_ontology.get("entities", []),
                        ontology.get("entities", [])
                    )

                    # 合并关系
                    merged_relations = self._merge_relations(
                        existing_ontology.get("relations", []),
                        ontology.get("relations", [])
                    )

                    # 合并洞察
                    merged_insights = self._merge_insights(
                        existing_ontology.get("insights", []),
                        ontology.get("insights", [])
                    )

                    # 构建合并后的图谱
                    merged_ontology = {
                        "entities": merged_entities,
                        "relations": merged_relations,
                        "insights": merged_insights
                    }

                    # 存储合并后的图谱
                    return self.store_ontology(
                        merged_ontology,
                        session_id,
                        metadata={"update_type": "incremental"}
                    )
                else:
                    # 首次存储
                    return self.store_ontology(ontology, session_id)
            else:
                # 完全替换
                print(f"  🔄 完全替换知识图谱 (session: {session_id})")
                return self.store_ontology(
                    ontology,
                    session_id,
                    metadata={"update_type": "replace"}
                )

        except Exception as e:
            print(f"  ❌ 更新知识图谱失败: {str(e)}")
            return False

    def retrieve_ontology(
        self,
        session_id: str,
        query: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        从 Zep Cloud 读取知识图谱

        Args:
            session_id: 会话ID
            query: 可选的查询条件（用于过滤相关知识）

        Returns:
            知识图谱数据，如果不存在则返回 None
        """
        if not self.zep_client:
            print("  ⚠️ Zep Cloud 未配置，无法读取")
            return None

        try:
            print(f"  📥 从 Zep Cloud 读取知识图谱 (graph_id: {session_id})")

            # 检查图谱是否存在
            try:
                graph = self.zep_client.graph.get(session_id)
            except Exception as e:
                if 'not found' in str(e).lower():
                    print(f"  ⚠️ 图谱不存在: {session_id}")
                    return None
                else:
                    raise

            # 使用 search 从图谱中读取所有数据
            search_query = query if query else "*"

            # 分别搜索节点和边
            # 1. 搜索节点（实体）
            node_results = self.zep_client.graph.search(
                graph_id=session_id,
                query=search_query,
                scope='nodes',
                limit=50  # Zep Cloud 最大限制为 50
            )

            # 2. 搜索边（关系）
            edge_results = self.zep_client.graph.search(
                graph_id=session_id,
                query=search_query,
                scope='edges',
                limit=50
            )

            # 解析搜索结果
            ontology = {
                "entities": [],
                "relations": [],
                "insights": []
            }

            # 从节点中提取实体
            if hasattr(node_results, 'nodes') and node_results.nodes:
                print(f"  ✓ 找到 {len(node_results.nodes)} 个节点")
                for node in node_results.nodes:
                    entity = {
                        "id": str(node.uuid_) if hasattr(node, 'uuid_') else str(hash(node.name)),
                        "name": node.name if hasattr(node, 'name') else "未知",
                        "type": node.labels[0] if hasattr(node, 'labels') and node.labels else "实体",
                        "attributes": {},
                        "confidence": 0.9
                    }
                    ontology["entities"].append(entity)

            # 从边中提取关系
            if hasattr(edge_results, 'edges') and edge_results.edges:
                print(f"  ✓ 找到 {len(edge_results.edges)} 条边")
                for edge in edge_results.edges:
                    relation = {
                        "from": str(edge.source_node_uuid) if hasattr(edge, 'source_node_uuid') else "",
                        "to": str(edge.target_node_uuid) if hasattr(edge, 'target_node_uuid') else "",
                        "type": edge.name if hasattr(edge, 'name') else "关系",
                        "fact": edge.fact if hasattr(edge, 'fact') else "",
                        "confidence": 0.9,
                        "attributes": {}
                    }
                    ontology["relations"].append(relation)

            if ontology["entities"] or ontology["relations"]:
                print(f"  ✅ 读取成功")
                return ontology
            else:
                print(f"  ⚠️ 图谱为空")
                return None

        except Exception as e:
            print(f"  ❌ 从 Zep Cloud 读取失败: {str(e)}")
            return None

    def search_related_knowledge(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索相关知识（实体、关系或洞察）

        Args:
            query: 搜索查询
            session_id: 可选的会话ID（限定搜索范围）
            top_k: 返回前K个结果

        Returns:
            相关知识列表
        """
        if not self.zep_client:
            print("  ⚠️ Zep Cloud 未配置，无法搜索")
            return []

        try:
            print(f"  🔍 搜索相关知识: {query}")

            if not session_id:
                print("  ⚠️ 需要提供 session_id")
                return []

            # 使用 Zep Cloud 的搜索 API (最大限制 50)
            results = self.zep_client.graph.search(
                graph_id=session_id,
                query=query,
                limit=min(top_k, 50)
            )

            knowledge_list = []

            # 处理节点（实体）
            if hasattr(results, 'nodes') and results.nodes:
                for node in results.nodes[:top_k]:
                    knowledge_list.append({
                        "type": "entity",
                        "name": node.name if hasattr(node, 'name') else "未知",
                        "labels": node.labels if hasattr(node, 'labels') else [],
                        "uuid": str(node.uuid) if hasattr(node, 'uuid') else None
                    })

            # 处理边（关系）
            if hasattr(results, 'edges') and results.edges:
                for edge in results.edges[:top_k]:
                    knowledge_list.append({
                        "type": "relation",
                        "name": edge.name if hasattr(edge, 'name') else "关系",
                        "source": str(edge.source_node_uuid) if hasattr(edge, 'source_node_uuid') else None,
                        "target": str(edge.target_node_uuid) if hasattr(edge, 'target_node_uuid') else None
                    })

            print(f"  ✅ 找到 {len(knowledge_list)} 条相关知识")
            return knowledge_list

        except Exception as e:
            print(f"  ❌ 搜索知识失败: {str(e)}")
            return []

    def _ontology_to_facts(self, ontology: Dict[str, Any]) -> Dict[str, Any]:
        """将图谱结构转换为 Zep 的事实格式"""
        return {
            "entities": ontology.get("entities", []),
            "relations": ontology.get("relations", []),
            "insights": ontology.get("insights", []),
            "metadata": ontology.get("metadata", {})
        }

    def _facts_to_ontology(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        """将 Zep 的事实格式转换为图谱结构"""
        return {
            "entities": facts.get("entities", []),
            "relations": facts.get("relations", []),
            "insights": facts.get("insights", []),
            "metadata": facts.get("metadata", {})
        }

    def _merge_entities(
        self,
        old_entities: List[Dict[str, Any]],
        new_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并实体列表（去重，更新属性）"""
        entity_map = {e["id"]: e for e in old_entities}

        for new_entity in new_entities:
            entity_id = new_entity["id"]
            if entity_id in entity_map:
                # 更新现有实体（合并属性）
                entity_map[entity_id]["attributes"].update(
                    new_entity.get("attributes", {})
                )
                # 更新置信度（取较高值）
                entity_map[entity_id]["confidence"] = max(
                    entity_map[entity_id].get("confidence", 0),
                    new_entity.get("confidence", 0)
                )
            else:
                # 添加新实体
                entity_map[entity_id] = new_entity

        return list(entity_map.values())

    def _merge_relations(
        self,
        old_relations: List[Dict[str, Any]],
        new_relations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并关系列表（去重）"""
        # 使用 (from, to, type) 作为唯一键
        relation_map = {}

        for rel in old_relations:
            key = (rel["from"], rel["to"], rel["type"])
            relation_map[key] = rel

        for rel in new_relations:
            key = (rel["from"], rel["to"], rel["type"])
            if key not in relation_map:
                relation_map[key] = rel
            else:
                # 更新置信度
                relation_map[key]["confidence"] = max(
                    relation_map[key].get("confidence", 0),
                    rel.get("confidence", 0)
                )

        return list(relation_map.values())

    def _merge_insights(
        self,
        old_insights: List[Dict[str, Any]],
        new_insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并洞察列表（去重，保留最新）"""
        # 按描述去重
        insight_map = {i["description"]: i for i in old_insights}

        for insight in new_insights:
            desc = insight["description"]
            if desc not in insight_map:
                insight_map[desc] = insight
            else:
                # 更新置信度
                insight_map[desc]["confidence"] = max(
                    insight_map[desc].get("confidence", 0),
                    insight.get("confidence", 0)
                )

        return list(insight_map.values())


# 测试代码
if __name__ == "__main__":
    # 测试 Zep Graph Manager
    manager = ZepGraphManager()

    # 测试存储
    test_ontology = {
        "entities": [
            {
                "id": "e1",
                "name": "OpenAI",
                "type": "公司",
                "attributes": {"industry": "AI"},
                "confidence": 0.9
            }
        ],
        "relations": [
            {
                "from": "e1",
                "to": "e2",
                "type": "竞争",
                "confidence": 0.8
            }
        ],
        "insights": [
            {
                "type": "趋势",
                "description": "AI大模型竞争加剧",
                "confidence": 0.85
            }
        ]
    }

    manager.store_ontology(test_ontology, session_id="test_session_001")
    print("\n测试完成")
