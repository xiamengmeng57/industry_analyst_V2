"""
Researcher Agent - 执行信息检索
"""
import json
from typing import Dict, List, Any, Optional
from anthropic import Anthropic


class ResearcherAgent:
    """研究Agent - 信息检索"""

    def __init__(
        self,
        client: Anthropic,
        model: str = "claude-haiku-4-6",
        wechat_api_key: Optional[str] = None,
        wechat_api_url: str = "https://down.mptext.top",
        enable_web_search: bool = True,
        use_claude_search: bool = True,
        twitter_bearer_token: Optional[str] = None,
        twitter_api_type: str = "official"  # "official" 或 "rapidapi"
    ):
        self.client = client
        self.model = model
        self.wechat_api_key = wechat_api_key
        self.wechat_api_url = wechat_api_url
        self.enable_web_search = enable_web_search
        self.use_claude_search = use_claude_search  # 优先使用 Claude Web Search
        self.twitter_bearer_token = twitter_bearer_token
        self.twitter_api_type = twitter_api_type

    def generate_search_strategy(
        self,
        plan: Dict[str, Any],
        wechat_accounts: Optional[List[str]] = None,
        twitter_accounts: Optional[List[str]] = None,
        date_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成检索策略（不执行实际检索）

        Args:
            plan: 研究计划
            wechat_accounts: 指定的微信公众号列表（可选）
            twitter_accounts: 指定的 Twitter 账号列表（可选）
            date_range: 时间范围 "YYYY-MM-DD到YYYY-MM-DD"（可选）

        Returns:
            包含 search_terms 和 search_queries 的字典
        """
        from prompts.templates import RESEARCHER_PROMPT

        # 精简计划信息
        plan_summary = {
            "time_range": plan.get("time_range", "当前"),
            "region": plan.get("region", "中国"),
            "subjects": plan.get("subjects", []),
            "research_questions": plan.get("research_questions", []),
            "industry_areas": plan.get("industry_areas", [])
        }

        # 通过 LLM 生成检索策略
        prompt = RESEARCHER_PROMPT.format(
            plan=json.dumps(plan_summary, ensure_ascii=False),
            wechat_accounts=json.dumps(wechat_accounts or [], ensure_ascii=False),
            date_range=date_range or "不限"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.8,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        content = self._extract_text_from_response(response)
        search_terms = []
        search_queries = []

        try:
            result = json.loads(self._extract_json(content))
            search_terms = result.get("search_terms", [])
            search_queries = result.get("search_queries", [])
        except json.JSONDecodeError:
            print(f"  ⚠️ JSON 解析失败，使用空检索策略")

        return {
            "search_terms": search_terms,
            "search_queries": search_queries
        }

    def execute_search(
        self,
        search_terms: List[str],
        search_queries: List[str],
        wechat_accounts: Optional[List[str]] = None,
        twitter_accounts: Optional[List[str]] = None,
        date_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行实际的检索（基于用户确认的检索策略）

        Args:
            search_terms: 检索词列表
            search_queries: 检索式列表
            wechat_accounts: 指定的微信公众号列表（可选）
            twitter_accounts: 指定的 Twitter 账号列表（可选）
            date_range: 时间范围 "YYYY-MM-DD到YYYY-MM-DD"（可选）

        Returns:
            包含 findings 和 search_stats 的字典
        """
        findings = []

        # 1. 如果指定了微信公众号，执行实际爬取
        if wechat_accounts and len(wechat_accounts) > 0:
            wechat_findings = self._crawl_wechat(
                accounts=wechat_accounts,
                keywords=self._extract_keywords(search_terms),
                date_range=date_range
            )
            findings.extend(wechat_findings)
            print(f"  ✓ 从微信公众号获取 {len(wechat_findings)} 条数据")

        # 2. 如果指定了 Twitter 账号，执行爬取
        if twitter_accounts and len(twitter_accounts) > 0:
            twitter_findings = self._crawl_twitter(
                accounts=twitter_accounts,
                keywords=self._extract_keywords(search_terms),
                date_range=date_range
            )
            findings.extend(twitter_findings)
            print(f"  ✓ 从 Twitter 获取 {len(twitter_findings)} 条数据")

        # 2. 执行网页搜索和抓取（如果启用）
        if self.enable_web_search and search_queries:
            # 限制搜索查询数量，避免过多 token 消耗
            limited_queries = search_queries[:5]
            if len(search_queries) > 5:
                print(f"  ℹ️  限制搜索查询数量：{len(search_queries)} → 5")

            web_findings = self._web_search_and_scrape(
                search_queries=limited_queries,
                num_results_per_query=10
            )
            findings.extend(web_findings)

            # 统计搜索来源
            claude_count = sum(1 for f in web_findings if f.get('metadata', {}).get('source_type') == 'claude_web')
            traditional_count = sum(1 for f in web_findings if f.get('metadata', {}).get('source_type') == 'web')

            if claude_count > 0:
                print(f"  ✓ Claude Web Search 获取 {claude_count} 条数据")
            if traditional_count > 0:
                print(f"  ✓ 传统网页搜索获取 {traditional_count} 条数据")
            if claude_count == 0 and traditional_count == 0:
                print(f"  ⚠️  网页搜索未获取到有效数据")

        # 统计数据来源
        search_stats = {
            "total": len(findings),
            "llm_knowledge": 0,
            "wechat": sum(1 for f in findings if f.get('metadata', {}).get('source_type') == 'wechat'),
            "twitter": sum(1 for f in findings if f.get('metadata', {}).get('source_type') == 'twitter'),
            "claude_web": sum(1 for f in findings if f.get('metadata', {}).get('source_type') == 'claude_web'),
            "traditional_web": sum(1 for f in findings if f.get('metadata', {}).get('source_type') == 'web')
        }

        return {
            "findings": findings,
            "search_stats": search_stats
        }

    def research(
        self,
        plan: Dict[str, Any],
        wechat_accounts: Optional[List[str]] = None,
        twitter_accounts: Optional[List[str]] = None,
        date_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行完整研究（向后兼容的接口）

        Token优化:
        - 仅传递计划摘要而非完整计划
        - 结构化输出
        - 批量处理问题

        Args:
            plan: 研究计划
            wechat_accounts: 指定的微信公众号列表（可选）
            twitter_accounts: 指定的 Twitter 账号列表（可选）
            date_range: 时间范围 "YYYY-MM-DD到YYYY-MM-DD"（可选）

        Returns:
            包含 findings、search_terms、search_queries 的字典
        """
        # 1. 生成检索策略
        strategy = self.generate_search_strategy(plan, wechat_accounts, twitter_accounts, date_range)

        # 2. 执行检索
        results = self.execute_search(
            strategy["search_terms"],
            strategy["search_queries"],
            wechat_accounts,
            twitter_accounts,
            date_range
        )

        # 3. 合并返回
        return {
            "findings": results["findings"],
            "search_terms": strategy["search_terms"],
            "search_queries": strategy["search_queries"],
            "search_stats": results["search_stats"]
        }

    def _extract_time_facts(self, content: str, source_url: str = "") -> Dict[str, Any]:
        """
        使用大模型提取文本中的时间和关联事实

        Args:
            content: 文本内容
            source_url: 来源URL（用于日志）

        Returns:
            包含 publication_date, time_facts 的字典
            time_facts 格式: [{"fact": "事实描述", "time": "时间", "time_type": "具体/提及"}]
        """
        if not content or len(content.strip()) < 20:
            return {"publication_date": None, "time_facts": []}

        try:
            prompt = f"""请从以下文本中提取**所有**时间信息和关联事实：

1. **发布时间**：这篇内容的发布/创建时间（如果文中有提到）
2. **时间-事实对**：文中提到的**每个**具体事实及其对应时间

要求：
- 提取所有事件和时间对，一个文本中可能有多个事件和多个时间
- 时间格式：保持原文格式（如：2024年3月、2024-03-15、2024Q1、近期）
- 事实描述：简洁准确，一句话概括每个独立事件
- 时间类型：
  - "publication"：内容发布时间
  - "mentioned"：文中明确提到的时间
- 只提取明确的信息，不要推测
- 如果一个事件关联多个时间，创建多个条目
- 如果一个时间关联多个事件，创建多个条目

返回JSON格式：
{{
  "publication_date": "发布时间或null",
  "time_facts": [
    {{"fact": "事件1描述", "time": "2024年3月", "time_type": "mentioned"}},
    {{"fact": "事件2描述", "time": "2024年Q1", "time_type": "mentioned"}},
    {{"fact": "事件3描述", "time": "2024-03-15", "time_type": "mentioned"}}
  ]
}}

文本内容（前800字）：
{content[:800]}

请返回JSON格式的结果，确保提取所有事件-时间对。"""

            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",  # 使用快速模型降低成本
                max_tokens=512,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = self._extract_text_from_response(response)
            result = json.loads(self._extract_json(result_text))

            return {
                "publication_date": result.get("publication_date"),
                "time_facts": result.get("time_facts", [])
            }

        except Exception as e:
            print(f"  ⚠️ 提取时间事实失败 ({source_url[:50]}...): {str(e)}")
            return {"publication_date": None, "time_facts": []}

    def _web_search_and_scrape(
        self,
        search_queries: List[str],
        num_results_per_query: int = 10
    ) -> List[Dict[str, Any]]:
        """
        执行网页搜索和内容抓取

        Args:
            search_queries: 检索式列表
            num_results_per_query: 每个查询返回的结果数量

        Returns:
            网页内容数据（符合 findings 格式）
        """
        # 优先使用 Claude Web Search
        if self.use_claude_search:
            try:
                from utils.claude_web_searcher import ClaudeWebSearcher

                print(f"  🤖 使用 Claude Web Search (共 {len(search_queries)} 个检索式)")
                searcher = ClaudeWebSearcher(client=self.client, model=self.model)
                all_findings = []

                for query in search_queries:
                    # 使用 Claude 搜索（内置 web search）
                    search_results = searcher.search(
                        query=query,
                        focus_sources=['官方报告', '行业媒体', '学术论文'],
                        num_results=num_results_per_query
                    )

                    # 格式化为 findings 格式
                    for result in search_results:
                        content = result.get('snippet', '')
                        url = result.get('url', '')

                        # 提取时间和事实关联
                        time_info = self._extract_time_facts(content, url)

                        all_findings.append({
                            "topic": result.get('title', 'Web Search Result'),
                            "data": content,
                            "source": url,
                            "date": result.get('date', ''),  # 原始发布时间
                            "publication_date": time_info.get('publication_date') or result.get('date', ''),  # 标准化发布时间
                            "time_facts": time_info.get('time_facts', []),  # 时间-事实关联
                            "metadata": {
                                "title": result.get('title', ''),
                                "source_type": "claude_web",
                                "search_engine": "claude"
                            }
                        })

                # 检查是否有有效结果
                if len(all_findings) > 0:
                    print(f"  ✓ Claude Web Search 总计获取 {len(all_findings)} 条结果")
                    return all_findings
                else:
                    # 无结果，回退到传统搜索
                    print(f"  ⚠️  Claude Web Search 未获取到结果，回退到传统搜索")

            except ImportError:
                print(f"  ⚠️ Claude Web Search 模块未找到，回退到传统搜索")
            except Exception as e:
                print(f"  ⚠️ Claude Web Search 失败: {str(e)}，回退到传统搜索")

        # 回退到传统搜索方式（Serper/Bing + 爬虫）
        print(f"  🌐 使用传统搜索 + 爬虫 (共 {len(search_queries)} 个检索式)")
        try:
            from utils.web_searcher import WebSearcher
            from utils.web_scraper import WebScraper

            # 初始化搜索器和抓取器
            searcher = WebSearcher()
            scraper = WebScraper()

            all_findings = []

            for query in search_queries:
                # 搜索（query 已由 RESEARCHER_PROMPT 扩展和优化）
                search_results = searcher.search(
                    query=query,
                    num_results=num_results_per_query
                )

                # 抓取前 10 个结果的内容
                urls_to_scrape = [r['url'] for r in search_results]
                scraped_contents = scraper.scrape_multiple(urls_to_scrape)

                # 格式化为 findings 格式
                for content in scraped_contents:
                    if content.get('status') == 'success' and content.get('content'):
                        article_content = content['content']
                        url = content['url']

                        # 提取时间和事实关联
                        time_info = self._extract_time_facts(article_content, url)

                        all_findings.append({
                            "topic": content.get('title', 'Web Article'),
                            "data": article_content,
                            "source": url,
                            "date": content.get('metadata', {}).get('published_date', ''),  # 原始发布时间
                            "publication_date": time_info.get('publication_date') or content.get('metadata', {}).get('published_date', ''),  # 标准化发布时间
                            "time_facts": time_info.get('time_facts', []),  # 时间-事实关联
                            "metadata": {
                                "title": content.get('title', ''),
                                "domain": content.get('metadata', {}).get('domain', ''),
                                "source_type": "web"
                            }
                        })

            return all_findings

        except ImportError as e:
            print(f"  ⚠️ Web搜索模块未找到: {str(e)}")
            return []
        except Exception as e:
            print(f"  ⚠️ Web搜索失败: {str(e)}")
            return []

    def _crawl_wechat(
        self,
        accounts: List[str],
        keywords: List[str],
        date_range: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        执行微信公众号爬取

        Args:
            accounts: 公众号列表
            search_queries: 检索式列表
            keywords: 关键词列表
            date_range: 时间范围 "YYYY-MM-DD到YYYY-MM-DD"（可选）

        Returns:
            微信文章数据（符合 findings 格式）
        """
        try:
            from utils.wechat_crawler import WeChatCrawler

            if not self.wechat_api_key:
                print("  ⚠️ 未配置微信 API 密钥，跳过微信爬取")
                return []

            crawler = WeChatCrawler(
                api_key=self.wechat_api_key,
                api_base_url=self.wechat_api_url
            )

            # 爬取文章
            articles = crawler.crawl_accounts(
                accounts=accounts,
                keywords=keywords if keywords else None,
                date_range=date_range,  # 传递时间范围
                limit_per_account=20
            )

            # 格式化为研究格式
            findings = crawler.format_for_research(articles, use_full_content=True)

            # 为每条 finding 添加时间-事实关联
            for finding in findings:
                content = finding.get('data', '')
                url = finding.get('source', '')
                time_info = self._extract_time_facts(content, url)

                # 添加时间字段
                finding['publication_date'] = time_info.get('publication_date') or finding.get('date', '')
                finding['time_facts'] = time_info.get('time_facts', [])

            return findings

        except ImportError:
            print("  ⚠️ wechat_crawler 模块未找到，跳过微信爬取")
            return []
        except Exception as e:
            print(f"  ⚠️ 微信爬取失败: {str(e)}")
            return []

    def _crawl_twitter(
        self,
        accounts: List[str],
        keywords: Optional[List[str]] = None,
        date_range: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        爬取 Twitter 账号推文内容

        Args:
            accounts: Twitter 用户名列表（不带 @）
            keywords: 关键词列表（可选）
            date_range: 时间范围 "YYYY-MM-DD到YYYY-MM-DD"（可选）

        Returns:
            推文数据（符合 findings 格式）
        """
        try:
            from utils.twitter_crawler import TwitterCrawler

            if not self.twitter_bearer_token and self.twitter_api_type == "official":
                print("  ⚠️ 未配置 Twitter Bearer Token，跳过 Twitter 爬取")
                return []

            # 解析时间范围
            start_date, end_date = None, None
            if date_range and "到" in date_range:
                parts = date_range.split("到")
                start_date = parts[0].strip()
                end_date = parts[1].strip()

            # 初始化爬虫
            crawler_kwargs = {"api_type": self.twitter_api_type}
            if self.twitter_api_type == "official":
                crawler_kwargs["bearer_token"] = self.twitter_bearer_token

            crawler = TwitterCrawler(**crawler_kwargs)

            # 批量爬取账号
            tweets = crawler.crawl_multiple_accounts(
                usernames=accounts,
                keywords=keywords,
                start_date=start_date,
                end_date=end_date,
                limit_per_account=30
            )

            # 转换为 findings 格式（只保留文字内容）
            findings = []
            for tweet in tweets:
                finding = {
                    "topic": f"@{tweet.get('username')} - {tweet.get('created_at', '')}",
                    "data": tweet.get('text', ''),
                    "source": tweet.get('url', ''),
                    "date": tweet.get('created_at', '').split(' ')[0] if tweet.get('created_at') else '',
                    "publication_date": tweet.get('created_at', ''),
                    "time_facts": [],
                    "metadata": {
                        "source_type": "twitter",
                        "username": tweet.get('username', ''),
                        "tweet_id": tweet.get('id', '')
                    }
                }
                findings.append(finding)

            return findings

        except ImportError:
            print("  ⚠️ twitter_crawler 模块未找到")
            print("     安装: pip install tweepy")
            return []
        except Exception as e:
            print(f"  ⚠️ Twitter 爬取失败: {str(e)}")
            return []

    def _extract_keywords(self, search_terms: List[str]) -> List[str]:
        """
        从检索词中提取关键词列表

        Args:
            search_terms: ["词1,词2,词3", "词4,词5", ...]

        Returns:
            所有关键词的扁平列表
        """
        keywords = []
        for term_group in search_terms:
            # 按逗号分割并添加到关键词列表
            keywords.extend(term_group.split(','))

        # 去重并过滤空值
        return list(set(k.strip() for k in keywords if k.strip()))

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
