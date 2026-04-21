"""
微信公众号文章爬取封装 - 基于 wechat-article-exporter Web API
项目地址: https://github.com/wechat-article/wechat-article-exporter
在线服务: https://down.mptext.top
文档: https://docs.mptext.top
查看: https://down.mptext.top/dashboard/api
"""
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime


class WeChatCrawler:
    """
    微信公众号爬取器

    使用 wechat-article-exporter 的 Web API 进行爬取
    API 文档: https://docs.mptext.top/advanced/api.html
    """

    def __init__(
        self,
        api_key: str,
        api_base_url: str = "https://down.mptext.top"
    ):
        """
        初始化爬取器

        Args:
            api_key: API 密钥（在网站登录后自动生成）
            api_base_url: API 基础 URL（可使用在线服务或自部署实例）
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Industry-Analyst/1.0",
            "X-Auth-Key": api_key  # API 认证
        })

    def search_account(self, account_name: str) -> Optional[Dict[str, Any]]:
        """
        搜索公众号

        Args:
            account_name: 公众号名称

        Returns:
            公众号信息 {"fakeid": "xxx", "nickname": "xxx", ...}
        """
        try:
            response = self.session.get(
                f"{self.api_base_url}/api/public/v1/account",
                params={"keyword": account_name},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # 实际 API 返回格式: {"base_resp": {"ret": 0}, "list": [...], "total": N}
            if data.get("base_resp", {}).get("ret") == 0:
                results = data.get("list", [])
                if results and len(results) > 0:
                    print(f"  ✓ 找到 {len(results)} 个匹配公众号，选择第一个")
                    return results[0]

            print(f"  ⚠️ API 返回错误: {data.get('base_resp', {}).get('err_msg', '未知错误')}")
            return None

        except Exception as e:
            print(f"搜索公众号失败 {account_name}: {str(e)}")
            return None

    def fetch_articles(
        self,
        account_id: str,
        keywords: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取公众号文章列表

        Args:
            account_id: 公众号 ID (fakeid)
            keywords: 关键词过滤（可选）
            start_date: 开始日期 YYYY-MM-DD（可选，API 不支持，本地过滤）
            end_date: 结束日期 YYYY-MM-DD（可选，API 不支持，本地过滤）
            limit: 返回数量限制（最大 30）

        Returns:
            文章列表
        """
        try:
            all_articles = []
            page_size = min(limit, 20)  # API 限制最大 20
            begin = 0

            # 分页获取（如果需要超过 20 篇）
            while len(all_articles) < limit:
                params = {
                    "fakeid": account_id,
                    "begin": begin,
                    "size": page_size
                }

                # API 支持标题关键词搜索
                if keywords and len(keywords) > 0:
                    params["keyword"] = keywords[0]  # 使用第一个关键词

                response = self.session.get(
                    f"{self.api_base_url}/api/public/v1/article",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                # 检查响应格式（实际返回 "articles" 字段）
                if data.get("base_resp", {}).get("ret") == 0:
                    articles = data.get("articles", [])  # 实际字段是 "articles"
                elif data.get("code") == 0:
                    articles = data.get("data", {}).get("list", [])
                else:
                    print(f"  API 返回错误: {data}")
                    break

                if not articles:
                    break

                all_articles.extend(articles)
                print(f"    ✓ 本页获取 {len(articles)} 篇")

                # 如果返回数量少于请求数量，说明已经到最后一页
                if len(articles) < page_size:
                    break

                begin += page_size

            # 应用本地过滤
            if keywords and len(keywords) > 1:
                # 如果有多个关键词，进行额外过滤
                all_articles = self._filter_by_keywords(all_articles, keywords)

            if start_date or end_date:
                all_articles = self._filter_by_date(all_articles, start_date, end_date)

            return all_articles[:limit]

        except Exception as e:
            print(f"获取文章列表失败: {str(e)}")
            return []

    def crawl_accounts(
        self,
        accounts: List[str],
        keywords: Optional[List[str]] = None,
        date_range: Optional[str] = None,
        limit_per_account: int = 20
    ) -> List[Dict[str, Any]]:
        """
        批量爬取多个公众号

        Args:
            accounts: 公众号名称列表
            keywords: 关键词过滤
            date_range: 日期范围 "YYYY-MM-DD到YYYY-MM-DD"
            limit_per_account: 每个账号返回的文章数量限制

        Returns:
            所有文章列表
        """
        all_articles = []

        # 解析日期范围
        start_date, end_date = None, None
        if date_range:
            try:
                start_str, end_str = date_range.split("到")
                start_date = start_str.strip()
                end_date = end_str.strip()
            except ValueError:
                print(f"日期范围格式错误: {date_range}")

        for account_name in accounts:
            print(f"🔍 爬取公众号: {account_name}")

            # 1. 搜索公众号
            account_info = self.search_account(account_name)
            if not account_info:
                print(f"  ⚠️ 未找到公众号: {account_name}")
                continue

            account_id = account_info.get("fakeid")
            print(f"  ✓ 找到公众号 ID: {account_id}")

            # 2. 获取文章
            articles = self.fetch_articles(
                account_id=account_id,
                keywords=keywords,
                start_date=start_date,
                end_date=end_date,
                limit=limit_per_account
            )

            # 3. 标记来源
            for article in articles:
                article["_source_account"] = account_name

            all_articles.extend(articles)
            print(f"  ✓ 获取 {len(articles)} 篇文章")

        return all_articles

    def format_for_research(
        self,
        articles: List[Dict[str, Any]],
        use_full_content: bool = True
    ) -> List[Dict[str, Any]]:
        """
        格式化为研究所需格式（符合 RESEARCHER_PROMPT 输出格式）

        Args:
            articles: 文章列表
            use_full_content: 是否使用全文（如果可用）

        Returns:
            findings 列表
        """
        findings = []

        for article in articles:
            # 选择内容来源
            if use_full_content:
                # 优先级：content > digest
                content = article.get("content") or article.get("digest", "")
            else:
                # 仅使用摘要
                content = article.get("digest", "")

            finding = {
                "topic": article.get("title", "未知标题"),
                "data": content,
                "source": f"微信公众号: {article.get('_source_account', '未知')}",
                "date": self._format_date(article.get("create_time")),
                "metadata": {
                    "title": article.get("title", ""),
                    "source_type": "wechat",
                    "url": article.get("link", ""),
                    "author": article.get("author", ""),
                    "has_full_content": bool(article.get("content"))
                }
            }
            findings.append(finding)

        return findings

    def _filter_by_keywords(
        self,
        articles: List[Dict[str, Any]],
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """按关键词过滤文章"""
        filtered = []
        for article in articles:
            title = article.get("title", "")
            digest = article.get("digest", "")  # 使用摘要
            content = article.get("content", "")
            # 任一关键词匹配即保留
            if any(kw in title or kw in digest or kw in content for kw in keywords):
                filtered.append(article)

        return filtered

    def _filter_by_date(
        self,
        articles: List[Dict[str, Any]],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        按日期范围过滤

        Args:
            start_date: "YYYY-MM-DD" 或 None
            end_date: "YYYY-MM-DD" 或 None
        """
        if not start_date and not end_date:
            return articles

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        except ValueError:
            print(f"日期格式错误: {start_date} 到 {end_date}")
            return articles

        filtered = []
        for article in articles:
            # API 返回的是时间戳（秒）
            timestamp = article.get("create_time") or article.get("update_time")
            if not timestamp:
                continue

            try:
                article_date = datetime.fromtimestamp(timestamp)

                # 检查是否在范围内
                if start_dt and article_date < start_dt:
                    continue
                if end_dt and article_date > end_dt:
                    continue

                filtered.append(article)
            except (ValueError, OSError):
                continue

        return filtered

    def _format_date(self, timestamp: Optional[int]) -> str:
        """
        格式化时间戳为日期字符串

        Args:
            timestamp: Unix 时间戳（秒）

        Returns:
            "YYYY-MM-DD" 格式日期
        """
        if not timestamp:
            return ""

        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return ""


# 测试代码
if __name__ == "__main__":
    # 使用提供的 API 密钥
    API_KEY = "a4f69a7e2ac74e12acc93dbe433ccd0e"

    crawler = WeChatCrawler(api_key=API_KEY)

    print("=" * 60)
    print("测试微信公众号爬取功能")
    print("=" * 60)

    # 测试爬取
    print("\n🔍 开始爬取公众号...")
    articles = crawler.crawl_accounts(
        accounts=["36氪", "虎嗅APP"],
        keywords=["AI", "人工智能"],
        date_range="2024-01-01到2026-04-14",
        limit_per_account=5
    )

    print(f"\n✅ 总共爬取 {len(articles)} 篇文章")

    if articles:
        # 格式化为研究格式
        findings = crawler.format_for_research(articles)

        print("\n📊 格式化后的研究发现（前2条）:")
        import json
        print(json.dumps(findings[:2], ensure_ascii=False, indent=2))
    else:
        print("\n⚠️ 未获取到文章，可能原因：")
        print("  1. API 密钥已过期（有效期 4 天）")
        print("  2. 公众号名称不匹配")
        print("  3. 网络连接问题")
