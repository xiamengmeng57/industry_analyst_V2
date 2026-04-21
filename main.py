"""
Industry Analyst - 主协调器
集成所有agent，实现高效的多agent协作流程
"""
import os
from typing import Optional, Dict, Any
from anthropic import Anthropic

from agents import (
    PlannerAgent,
    ResearcherAgent,
    FactCheckerAgent,
    OntologyBuilderAgent,
    ReportWriterAgent
)
from utils import StateManager


class IndustryAnalyst:
    """
    智能行业分析师

    Token优化核心策略:
    1. 状态管理器集中存储，避免重复传递
    2. Agent间仅传递ID/索引而非完整数据
    3. 每个agent使用最小化prompt
    4. 批量处理减少API调用
    5. 支持检查点恢复
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
        verbose: bool = True,
        wechat_api_key: Optional[str] = None,
        twitter_bearer_token: Optional[str] = None,
        twitter_api_type: str = "official",
        zep_api_key: Optional[str] = None,
        enable_zep: bool = True,
        enable_web_search: bool = True,
        use_claude_search: bool = True
    ):
        """
        初始化分析师

        Args:
            api_key: Anthropic API key (默认从环境变量读取)
            model: 使用的模型
            verbose: 是否输出详细日志
            wechat_api_key: 微信公众号爬取 API key (可选，默认从环境变量 WECHAT_API_KEY 读取)
            twitter_bearer_token: Twitter Bearer Token (可选，默认从环境变量 TWITTER_BEARER_TOKEN 读取)
            twitter_api_type: Twitter API类型 ("official" 或 "rapidapi"，默认 "official")
            zep_api_key: Zep Cloud API key (可选，默认从环境变量 ZEP_API_KEY 读取)
            enable_zep: 是否启用 Zep Cloud 图谱存储（默认True）
            enable_web_search: 是否启用网页搜索（默认True，需配置 SERPER_API_KEY 或 BING_API_KEY）
            use_claude_search: 是否优先使用 Claude Web Search（默认True，无需额外 API key）
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("需要提供ANTHROPIC_API_KEY")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.verbose = verbose
        self.enable_zep = enable_zep
        self.enable_web_search = enable_web_search
        self.use_claude_search = use_claude_search

        # 初始化状态管理器
        self.state_manager = StateManager()

        # 微信 API key (优先使用参数，否则从环境变量读取)
        wechat_key = wechat_api_key or os.getenv("WECHAT_API_KEY")

        # Twitter Bearer Token (优先使用参数，否则从环境变量读取)
        twitter_token = twitter_bearer_token or os.getenv("TWITTER_BEARER_TOKEN")

        # Zep API key (优先使用参数，否则从环境变量读取)
        zep_key = zep_api_key or os.getenv("ZEP_API_KEY")

        # 初始化所有agent
        self.planner = PlannerAgent(self.client, self.model)
        self.researcher = ResearcherAgent(
            self.client,
            self.model,
            wechat_api_key=wechat_key,
            twitter_bearer_token=twitter_token,
            twitter_api_type=twitter_api_type,
            enable_web_search=enable_web_search,
            use_claude_search=use_claude_search
        )
        self.fact_checker = FactCheckerAgent(self.client, self.model)
        self.ontology_builder = OntologyBuilderAgent(
            self.client,
            self.model,
            zep_api_key=zep_key,
            enable_zep=enable_zep
        )
        self.report_writer = ReportWriterAgent(
            self.client,
            self.model,
            zep_api_key=zep_key,
            enable_zep=enable_zep
        )

        self._log("✓ Industry Analyst initialized")

    def analyze(
        self,
        query: str,
        save_checkpoint: bool = False,
        wechat_accounts: Optional[list] = None,
        twitter_accounts: Optional[list] = None,
        date_range: Optional[str] = None,
        session_id: Optional[str] = None,
        interactive_plan: bool = True,
        interactive_search: bool = True,
        user_documents: Optional[list] = None,
        user_doc_titles: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        执行完整的行业分析流程

        Args:
            query: 用户查询
            save_checkpoint: 是否保存检查点
            wechat_accounts: 要爬取的微信公众号列表（可选）
            twitter_accounts: 要爬取的 Twitter 账号列表（可选，不带@）
            date_range: 信息时间范围 "YYYY-MM-DD到YYYY-MM-DD"（可选）
            session_id: 会话ID（用于Zep图谱存储，可选，默认自动生成）
            interactive_plan: 是否在生成计划后让用户确认/修改（默认True）
            interactive_search: 是否在生成检索策略后让用户确认/修改（默认True）
            user_documents: 用户上传的文档路径列表（可选）
            user_doc_titles: 用户文档的标题列表（可选，需与 user_documents 长度一致）

        Returns:
            包含报告和元数据的结果字典
        """
        import uuid
        from datetime import datetime

        # 生成或使用提供的 session_id
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        self._log(f"\n{'='*60}")
        self._log(f"开始分析: {query}")
        if self.enable_zep:
            self._log(f"Session ID: {session_id}")
        self._log(f"{'='*60}\n")

        # 1. Planning阶段
        self._log("📋 [1/5] Planning...")
        self.state_manager.update(query=query)
        plan = self.planner.plan(query)

        # 交互式确认计划（如果启用）
        if interactive_plan:
            plan = self._get_user_confirmation_for_plan(plan)

        self.state_manager.update(plan=plan)

        # 输出研究计划
        time_range = plan.get('time_range', '当前')
        region = plan.get('region', '中国')
        subjects = plan.get('subjects', [])
        industry_areas = plan.get('industry_areas', [])

        self._log(f"  ✓ 时间范围: {time_range}")
        self._log(f"  ✓ 地区范围: {region}")
        self._log(f"  ✓ 行业领域: {', '.join(industry_areas) if industry_areas else '通用'}")
        self._log(f"  ✓ 研究主体: {len(subjects)} 个")
        if subjects and self.verbose:
            self._log("  \n  📌 研究主体:")
            for i, subj in enumerate(subjects[:5], 1):
                self._log(f"     {i}. {subj}")
            if len(subjects) > 5:
                self._log(f"     ... (共 {len(subjects)} 个)")

        # 输出关键问题
        questions = plan.get('research_questions', [])
        if questions and self.verbose:
            self._log(f"  \n  ❓ 研究问题 ({len(questions)} 个):")
            for i, q in enumerate(questions[:3], 1):
                self._log(f"     {i}. {q}")
            if len(questions) > 3:
                self._log(f"     ... (共 {len(questions)} 个)")

        # 2. Research阶段
        self._log("\n🔍 [2/5] Researching...")
        if date_range:
            self._log(f"  📅 时间范围: {date_range}")
        if twitter_accounts:
            self._log(f"  🐦 Twitter 账号: {', '.join(f'@{acc}' for acc in twitter_accounts)}")

        # 生成检索策略
        self._log("  📝 生成检索策略...")
        search_strategy = self.researcher.generate_search_strategy(
            plan,
            wechat_accounts=wechat_accounts,
            twitter_accounts=twitter_accounts,
            date_range=date_range
        )

        search_terms = search_strategy.get("search_terms", [])
        search_queries = search_strategy.get("search_queries", [])

        # 交互式确认检索策略（如果启用）
        if interactive_search:
            search_terms, search_queries = self._get_user_confirmation_for_search(
                search_terms,
                search_queries
            )

        # 执行实际检索
        self._log("\n  🔍 执行检索...")
        search_results = self.researcher.execute_search(
            search_terms,
            search_queries,
            wechat_accounts=wechat_accounts,
            twitter_accounts=twitter_accounts,
            date_range=date_range
        )

        # 整合研究结果
        research_result = {
            "findings": search_results.get("findings", []),
            "search_terms": search_terms,
            "search_queries": search_queries,
            "search_stats": search_results.get("search_stats", {})
        }

        # 如果返回的是字典（包含检索信息），提取findings和metadata
        if isinstance(research_result, dict):
            findings = research_result.get('findings', [])
            search_terms = research_result.get('search_terms', [])
            search_queries = research_result.get('search_queries', [])
            search_stats = research_result.get('search_stats', {})

            # 输出检索关键词（完整）
            if search_terms and self.verbose:
                self._log(f"  \n  🔍 检索关键词 ({len(search_terms)} 组):")
                for i, term_group in enumerate(search_terms, 1):
                    # 新格式：term_group 是字符串 "词1,词2,词3"
                    self._log(f"     {i}. {term_group}")

            # 输出检索式（完整）
            if search_queries and self.verbose:
                self._log(f"  \n  🔎 检索式 ({len(search_queries)} 个):")
                for i, query_item in enumerate(search_queries, 1):
                    self._log(f"     {i}. {query_item}")

            # 输出搜索统计（新增）
            if search_stats and self.verbose:
                self._log(f"  \n  📊 数据来源统计:")
                if search_stats.get('wechat', 0) > 0:
                    self._log(f"     • 微信公众号: {search_stats['wechat']} 条")
                if search_stats.get('twitter', 0) > 0:
                    self._log(f"     • Twitter: {search_stats['twitter']} 条")
                if search_stats.get('claude_web', 0) > 0:
                    self._log(f"     • Claude Web Search: {search_stats['claude_web']} 条")
                if search_stats.get('traditional_web', 0) > 0:
                    self._log(f"     • 传统网页搜索: {search_stats['traditional_web']} 条")
                self._log(f"     • 总计: {search_stats.get('total', len(findings))} 条")
        else:
            # 兼容旧版本返回格式（直接返回findings列表）
            findings = research_result

        self.state_manager.update(findings=findings)
        self._log(f"  \n  ✓ 收集 {len(findings)} 条研究发现")

        # 按数据源分类和输出 findings（新增）
        if self.verbose and findings:
            findings_by_source = self._classify_findings_by_source(findings)
            self._output_findings_by_source(findings_by_source)

            # 保存 findings 到文件
            findings_file = self._save_findings_to_file(findings_by_source, session_id)
            if findings_file:
                self._log(f"\n  💾 Findings 已保存: {findings_file}")

        # 3. Fact Checking阶段
        self._log("✅ [3/5] Fact Checking...")

        # 处理用户上传的文档（如果有）
        user_doc_findings = None
        if user_documents:
            self._log(f"  📄 处理用户上传的文档: {len(user_documents)} 个")
            try:
                from utils import DocumentParser
                user_doc_findings = DocumentParser.batch_convert_to_findings(
                    user_documents,
                    user_doc_titles,
                    extract_time=True,  # 启用时间提取
                    anthropic_client=self.client  # 传递 client
                )
                self._log(f"  ✓ 成功解析 {len(user_doc_findings)} 个文档")

                # 统计提取的时间事实
                total_time_facts = sum(len(f.get('time_facts', [])) for f in user_doc_findings)
                if total_time_facts > 0:
                    self._log(f"  ✓ 提取 {total_time_facts} 个时间-事实对")
            except Exception as e:
                self._log(f"  ⚠️  文档解析失败: {e}")
                user_doc_findings = None

        # 验证事实（包含用户文档）
        verification_result = self.fact_checker.verify(
            findings,
            user_documents=user_doc_findings
        )
        self.state_manager.update(
            verified_facts=verification_result["verified"],
            unverified_facts=verification_result["unverified"]
        )
        verified_count = len(verification_result["verified"])
        unverified_count = len(verification_result["unverified"])

        # 如果有用户文档，显示统计
        if user_doc_findings:
            user_doc_count = len(user_doc_findings)
            self._log(f"  ✓ 验证通过: {verified_count} (包含 {user_doc_count} 个用户文档), 待确认: {unverified_count}")
        else:
            self._log(f"  ✓ 验证通过: {verified_count}, 待确认: {unverified_count}")

        # 4. Ontology Building阶段
        self._log("🕸️  [4/5] Building Ontology...")
        ontology = self.ontology_builder.build_ontology(
            verification_result["verified"],
            session_id=session_id,
            use_existing_graph=True
        )
        self.state_manager.update(ontology=ontology)
        entities_count = len(ontology.get("entities", []))
        relations_count = len(ontology.get("relations", []))
        insights_count = len(ontology.get("insights", []))
        self._log(f"  ✓ 构建本体: {entities_count}实体, {relations_count}关系, {insights_count}洞察")

        # 5. Report Writing阶段
        self._log("📝 [5/5] Writing Report...")
        report = self.report_writer.write_report(
            ontology,
            verification_result["verified"],
            query,
            session_id=session_id,
            use_historical_knowledge=True
        )
        self.state_manager.update(report=report)
        self._log(f"  ✓ 生成报告 ({len(report)} 字符)")

        # 保存检查点
        if save_checkpoint:
            checkpoint_path = "analysis_checkpoint.json"
            self.state_manager.save_checkpoint(checkpoint_path)
            self._log(f"\n💾 检查点已保存: {checkpoint_path}")

        self._log(f"\n{'='*60}")
        self._log("✅ 分析完成")
        self._log(f"{'='*60}\n")

        # 返回结果
        return {
            "report": report,
            "ontology": ontology,
            "plan": plan,
            "research": research_result if isinstance(research_result, dict) else {"findings": research_result},
            "verified_facts": verification_result["verified"],
            "unverified_facts": verification_result["unverified"],
            "verified_facts_count": verified_count,
            "unverified_facts_count": unverified_count,
            "state": self.state_manager.get_state()
        }

    def analyze_streaming(self, query: str):
        """
        流式分析 - 边计算边输出
        适合长时间运行的分析任务
        """
        self._log(f"开始流式分析: {query}\n")

        # 前4个阶段保持不变
        self.state_manager.update(query=query)

        plan = self.planner.plan(query)
        self.state_manager.update(plan=plan)
        yield {"stage": "plan", "data": plan}

        research_result = self.researcher.research(plan)
        # 兼容新返回格式
        if isinstance(research_result, dict):
            findings = research_result.get('findings', [])
        else:
            findings = research_result
        self.state_manager.update(findings=findings)
        yield {"stage": "research", "data": {"count": len(findings)}}

        verification = self.fact_checker.verify(findings)
        self.state_manager.update(
            verified_facts=verification["verified"],
            unverified_facts=verification["unverified"]
        )
        yield {"stage": "verification", "data": {
            "verified": len(verification["verified"]),
            "unverified": len(verification["unverified"])
        }}

        ontology = self.ontology_builder.build_ontology(verification["verified"])
        self.state_manager.update(ontology=ontology)
        yield {"stage": "ontology", "data": ontology}

        # 流式输出报告
        yield {"stage": "report_start", "data": None}
        for chunk in self.report_writer.write_report_streaming(
            ontology,
            verification["verified"],
            query
        ):
            yield {"stage": "report_chunk", "data": chunk}

        yield {"stage": "complete", "data": None}

    def get_state_summary(self) -> str:
        """获取当前状态摘要"""
        return self.state_manager.get_state().get_summary()

    def load_checkpoint(self, filepath: str):
        """从检查点恢复"""
        self.state_manager.load_checkpoint(filepath)
        self._log(f"✓ 从检查点恢复: {filepath}")

    def _log(self, message: str):
        """内部日志"""
        if self.verbose:
            print(message)

    def _get_user_confirmation_for_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        显示研究计划并获取用户确认/修改

        Args:
            plan: AI生成的研究计划

        Returns:
            用户确认或修改后的计划
        """
        import json

        print("\n" + "="*70)
        print("📋 研究计划已生成，请确认或修改")
        print("="*70)
        print("\n当前计划:")
        print(json.dumps(plan, ensure_ascii=False, indent=2))

        print("\n" + "-"*70)
        print("请选择操作:")
        print("  1. 确认并继续")
        print("  2. 修改计划（输入修改后的完整JSON）")
        print("  3. 取消分析")
        print("-"*70)

        while True:
            choice = input("\n请输入选项 (1/2/3): ").strip()

            if choice == "1":
                print("\n✓ 计划已确认，继续分析...")
                return plan

            elif choice == "2":
                print("\n请输入修改后的计划（JSON格式）:")
                print("（输入 'end' 结束输入）\n")

                lines = []
                while True:
                    line = input()
                    if line.strip().lower() == 'end':
                        break
                    lines.append(line)

                modified_json = '\n'.join(lines)
                try:
                    modified_plan = json.loads(modified_json)
                    print("\n✓ 计划已更新")
                    return modified_plan
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON格式错误: {e}")
                    print("请重新选择操作")
                    continue

            elif choice == "3":
                print("\n分析已取消")
                raise KeyboardInterrupt("用户取消分析")

            else:
                print("❌ 无效选项，请输入 1, 2 或 3")

    def _get_user_confirmation_for_search(
        self,
        search_terms: list,
        search_queries: list
    ) -> tuple:
        """
        显示检索策略并获取用户确认/修改

        Args:
            search_terms: AI生成的检索词列表
            search_queries: AI生成的检索式列表

        Returns:
            (用户确认或修改后的search_terms, search_queries)
        """
        import json

        print("\n" + "="*70)
        print("🔍 检索策略已生成，请确认或修改")
        print("="*70)

        print("\n检索词组:")
        for i, term in enumerate(search_terms, 1):
            print(f"  {i}. {term}")

        print("\n检索式:")
        for i, query in enumerate(search_queries, 1):
            print(f"  {i}. {query}")

        print("\n" + "-"*70)
        print("请选择操作:")
        print("  1. 确认并继续检索")
        print("  2. 修改检索词组（输入JSON数组）")
        print("  3. 修改检索式（输入JSON数组）")
        print("  4. 同时修改检索词组和检索式（输入JSON对象）")
        print("  5. 取消分析")
        print("-"*70)

        current_terms = search_terms
        current_queries = search_queries

        while True:
            choice = input("\n请输入选项 (1/2/3/4/5): ").strip()

            if choice == "1":
                print("\n✓ 检索策略已确认，开始检索...")
                return current_terms, current_queries

            elif choice == "2":
                print("\n请输入修改后的检索词组（JSON数组格式）:")
                print('例: ["词1,词2", "词3,词4"]')
                print("（输入 'end' 结束输入）\n")

                lines = []
                while True:
                    line = input()
                    if line.strip().lower() == 'end':
                        break
                    lines.append(line)

                modified_json = '\n'.join(lines)
                try:
                    current_terms = json.loads(modified_json)
                    print(f"\n✓ 检索词组已更新: {len(current_terms)} 组")
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON格式错误: {e}")
                    continue

            elif choice == "3":
                print("\n请输入修改后的检索式（JSON数组格式）:")
                print('例: ["查询1", "查询2"]')
                print("（输入 'end' 结束输入）\n")

                lines = []
                while True:
                    line = input()
                    if line.strip().lower() == 'end':
                        break
                    lines.append(line)

                modified_json = '\n'.join(lines)
                try:
                    current_queries = json.loads(modified_json)
                    print(f"\n✓ 检索式已更新: {len(current_queries)} 个")
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON格式错误: {e}")
                    continue

            elif choice == "4":
                print("\n请输入修改后的检索策略（JSON对象格式）:")
                print('例: {"search_terms": ["词1,词2"], "search_queries": ["查询1"]}')
                print("（输入 'end' 结束输入）\n")

                lines = []
                while True:
                    line = input()
                    if line.strip().lower() == 'end':
                        break
                    lines.append(line)

                modified_json = '\n'.join(lines)
                try:
                    modified_strategy = json.loads(modified_json)
                    current_terms = modified_strategy.get("search_terms", current_terms)
                    current_queries = modified_strategy.get("search_queries", current_queries)
                    print(f"\n✓ 检索策略已更新")
                    print(f"  - 检索词组: {len(current_terms)} 组")
                    print(f"  - 检索式: {len(current_queries)} 个")
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON格式错误: {e}")
                    continue

            elif choice == "5":
                print("\n分析已取消")
                raise KeyboardInterrupt("用户取消分析")

            else:
                print("❌ 无效选项，请输入 1, 2, 3, 4 或 5")

    def _classify_findings_by_source(self, findings: list) -> Dict[str, list]:
        """
        按数据源分类 findings

        Args:
            findings: 所有 findings 列表

        Returns:
            按来源分类的字典 {"wechat": [...], "twitter": [...], "claude_web": [...], ...}
        """
        classified = {
            "wechat": [],
            "twitter": [],
            "claude_web": [],
            "traditional_web": [],
            "other": []
        }

        for finding in findings:
            source_type = finding.get("metadata", {}).get("source_type", "other")
            if source_type in classified:
                classified[source_type].append(finding)
            else:
                classified["other"].append(finding)

        return classified

    def _output_findings_by_source(self, findings_by_source: Dict[str, list]):
        """
        输出各数据源的 findings 详情

        Args:
            findings_by_source: 按来源分类的 findings
        """
        self._log(f"\n  📑 各数据源 Findings 详情:")
        self._log(f"  {'-' * 60}")

        source_names = {
            "wechat": "📱 微信公众号",
            "twitter": "🐦 Twitter",
            "claude_web": "🤖 Claude Web Search",
            "traditional_web": "🌐 传统网页搜索",
            "other": "📝 其他来源"
        }

        for source_type, findings in findings_by_source.items():
            if not findings:
                continue

            source_name = source_names.get(source_type, source_type)
            self._log(f"\n  {source_name} ({len(findings)} 条):")

            for i, finding in enumerate(findings[:5], 1):  # 显示前5条
                title = finding.get("topic", "无标题")
                data_preview = finding.get("data", "")[:100]
                source = finding.get("source", "未知来源")
                date = finding.get("date", "")

                self._log(f"    {i}. {title}")
                if date:
                    self._log(f"       日期: {date}")
                self._log(f"       来源: {source}")
                self._log(f"       内容: {data_preview}...")

            if len(findings) > 5:
                self._log(f"    ... (还有 {len(findings) - 5} 条)")

        self._log(f"  {'-' * 60}")

    def _save_findings_to_file(
        self,
        findings_by_source: Dict[str, list],
        session_id: str
    ) -> Optional[str]:
        """
        保存 findings 到文件（JSON 和 Markdown）

        Args:
            findings_by_source: 按来源分类的 findings
            session_id: 会话 ID

        Returns:
            保存的文件路径（JSON）
        """
        import json
        from datetime import datetime
        import os

        try:
            # 创建输出目录
            output_dir = "findings_output"
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"findings_{timestamp}.json"
            md_filename = f"findings_{timestamp}.md"
            json_filepath = os.path.join(output_dir, json_filename)
            md_filepath = os.path.join(output_dir, md_filename)

            # 准备保存数据
            output_data = {
                "session_id": session_id,
                "timestamp": timestamp,
                "summary": {
                    "total": sum(len(findings) for findings in findings_by_source.values()),
                    "by_source": {
                        source: len(findings)
                        for source, findings in findings_by_source.items()
                        if findings
                    }
                },
                "findings_by_source": findings_by_source
            }

            # 1. 保存为 JSON
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            # 2. 保存为 Markdown（更易读）
            self._save_findings_markdown(findings_by_source, md_filepath, session_id, timestamp)

            self._log(f"  📄 Markdown: {md_filepath}")
            return json_filepath

        except Exception as e:
            self._log(f"  ⚠️  保存 findings 失败: {e}")
            return None

    def _save_findings_markdown(
        self,
        findings_by_source: Dict[str, list],
        filepath: str,
        session_id: str,
        timestamp: str
    ):
        """保存 Markdown 格式的 findings"""
        source_names = {
            "wechat": "📱 微信公众号",
            "twitter": "🐦 Twitter",
            "claude_web": "🤖 Claude Web Search",
            "traditional_web": "🌐 传统网页搜索",
            "other": "📝 其他来源"
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            # 标题
            f.write(f"# Research Findings Report\n\n")
            f.write(f"**Session ID**: {session_id}  \n")
            f.write(f"**Generated**: {timestamp}  \n\n")

            # 统计摘要
            total = sum(len(findings) for findings in findings_by_source.values())
            f.write(f"## 📊 Summary\n\n")
            f.write(f"**Total Findings**: {total}\n\n")
            f.write(f"| Source | Count |\n")
            f.write(f"|--------|-------|\n")
            for source, findings in findings_by_source.items():
                if findings:
                    source_name = source_names.get(source, source)
                    f.write(f"| {source_name} | {len(findings)} |\n")
            f.write(f"\n---\n\n")

            # 各来源详情
            for source_type, findings in findings_by_source.items():
                if not findings:
                    continue

                source_name = source_names.get(source_type, source_type)
                f.write(f"## {source_name}\n\n")
                f.write(f"共 **{len(findings)}** 条\n\n")

                for i, finding in enumerate(findings, 1):
                    title = finding.get("topic", "无标题")
                    data = finding.get("data", "")
                    source = finding.get("source", "未知来源")
                    date = finding.get("date", "")

                    f.write(f"### {i}. {title}\n\n")
                    if date:
                        f.write(f"**日期**: {date}  \n")
                    f.write(f"**来源**: {source}  \n\n")
                    f.write(f"**内容**:\n\n")
                    f.write(f"{data}\n\n")
                    f.write(f"---\n\n")


def main():
    """示例使用"""
    # 从环境变量读取API key
    analyst = IndustryAnalyst(
        model="claude-sonnet-4-6",
        verbose=True
    )

    # 执行分析
    result = analyst.analyze(
        query="分析2026年中国新能源汽车产业的发展趋势和主要挑战",
        save_checkpoint=True
    )

    # 输出报告
    print("\n" + "="*60)
    print("最终报告")
    print("="*60)
    print(result["report"])
    print("\n")
    print(f"验证事实数: {result['verified_facts_count']}")
    print(f"待确认事实数: {result['unverified_facts_count']}")


if __name__ == "__main__":
    main()
