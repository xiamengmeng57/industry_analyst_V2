"""
状态管理器 - 集中式数据存储，避免重复传递
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List
import json


@dataclass
class AnalysisState:
    """分析状态 - 所有agent共享"""
    query: str = ""
    plan: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict] = field(default_factory=list)
    verified_facts: List[Dict] = field(default_factory=list)
    unverified_facts: List[Dict] = field(default_factory=list)
    ontology: Dict[str, Any] = field(default_factory=dict)
    report: str = ""

    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "plan": self.plan,
            "findings": self.findings,
            "verified_facts": self.verified_facts,
            "unverified_facts": self.unverified_facts,
            "ontology": self.ontology,
            "report": self.report
        }

    def get_summary(self) -> str:
        """获取当前状态摘要 - 用于日志"""
        subjects = self.plan.get('subjects', [])
        return f"""
State Summary:
- Query: {self.query[:50]}...
- Plan subjects: {len(subjects)}
- Findings: {len(self.findings)}
- Verified facts: {len(self.verified_facts)}
- Entities: {len(self.ontology.get('entities', []))}
- Report length: {len(self.report)} chars
"""


class StateManager:
    """轻量级状态管理"""

    def __init__(self):
        self.state = AnalysisState()
        self.history: List[Dict] = []

    def update(self, **kwargs):
        """更新状态"""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
                self.history.append({
                    "action": f"update_{key}",
                    "timestamp": self._get_timestamp()
                })

    def get(self, key: str) -> Any:
        """获取状态值"""
        return getattr(self.state, key, None)

    def get_state(self) -> AnalysisState:
        """获取完整状态"""
        return self.state

    def save_checkpoint(self, filepath: str):
        """保存检查点"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)

    def load_checkpoint(self, filepath: str):
        """加载检查点"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for key, value in data.items():
                self.update(**{key: value})

    @staticmethod
    def _get_timestamp() -> str:
        from datetime import datetime
        return datetime.now().isoformat()
