"""
Twitter/X 信息爬取工具

支持两种爬取方式：
1. 官方 Twitter API v2（推荐，需要申请免费 API key）
2. RapidAPI Twitter API（付费，但更稳定，无需申请）

官方 API 申请：https://developer.twitter.com/
RapidAPI 服务：https://rapidapi.com/Glavier/api/twitter-api45
"""
import os
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time


class TwitterCrawler:
    """
    Twitter/X 爬取器

    支持两种数据源：
    - 官方 Twitter API v2（免费，需申请）
    - RapidAPI Twitter API（付费，更稳定）
    """

    def __init__(
        self,
        api_type: str = "official",  # "official" 或 "rapidapi"
        bearer_token: Optional[str] = None,
        rapidapi_key: Optional[str] = None,
        rapidapi_host: str = "twitter-api45.p.rapidapi.com"
    ):
        """
        初始化 Twitter 爬取器

        Args:
            api_type: API 类型 ("official" 或 "rapidapi")
            bearer_token: Twitter 官方 API Bearer Token
            rapidapi_key: RapidAPI 密钥
            rapidapi_host: RapidAPI 服务地址

        环境变量:
            TWITTER_BEARER_TOKEN: Twitter 官方 API token
            RAPIDAPI_KEY: RapidAPI 密钥
        """
        self.api_type = api_type
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        self.rapidapi_key = rapidapi_key or os.getenv("RAPIDAPI_KEY")
        self.rapidapi_host = rapidapi_host

        # 初始化对应的客户端
        if api_type == "official":
            self._init_official_api()
        elif api_type == "rapidapi":
            self._init_rapidapi()
        else:
            raise ValueError(f"不支持的 API 类型: {api_type}，请使用 'official' 或 'rapidapi'")

    def _init_official_api(self):
        """初始化官方 Twitter API v2"""
        if not self.bearer_token:
            raise ValueError(
                "需要提供 TWITTER_BEARER_TOKEN\n"
                "申请地址: https://developer.twitter.com/\n"
                "设置环境变量: export TWITTER_BEARER_TOKEN='your-token'"
            )

        try:
            import tweepy
            self.client = tweepy.Client(bearer_token=self.bearer_token)
            print("  ✓ Twitter 官方 API v2 已初始化")
        except ImportError:
            raise ImportError(
                "需要安装 tweepy: pip install tweepy\n"
                "文档: https://docs.tweepy.org/"
            )

    def _init_rapidapi(self):
        """初始化 RapidAPI"""
        if not self.rapidapi_key:
            raise ValueError(
                "需要提供 RAPIDAPI_KEY\n"
                "注册地址: https://rapidapi.com/\n"
                "设置环境变量: export RAPIDAPI_KEY='your-key'"
            )

        self.rapidapi_headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": self.rapidapi_host
        }
        print("  ✓ RapidAPI Twitter 已初始化")

    def search_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        搜索 Twitter 用户

        Args:
            username: 用户名（不带 @）

        Returns:
            用户信息字典
        """
        if self.api_type == "official":
            return self._search_user_official(username)
        elif self.api_type == "rapidapi":
            return self._search_user_rapidapi(username)

    def _search_user_official(self, username: str) -> Optional[Dict[str, Any]]:
        """使用官方 API 搜索用户"""
        try:
            user = self.client.get_user(username=username)
            if user.data:
                return {
                    "id": user.data.id,
                    "username": user.data.username,
                    "name": user.data.name,
                    "description": getattr(user.data, "description", ""),
                    "followers_count": getattr(user.data, "public_metrics", {}).get("followers_count", 0)
                }
        except Exception as e:
            print(f"  ⚠️  搜索用户失败 (@{username}): {str(e)}")
        return None

    def _search_user_rapidapi(self, username: str) -> Optional[Dict[str, Any]]:
        """使用 RapidAPI 搜索用户"""
        try:
            url = f"https://{self.rapidapi_host}/userbyusername.php"
            params = {"username": username}

            response = requests.get(url, headers=self.rapidapi_headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data and "rest_id" in data:
                return {
                    "id": data["rest_id"],
                    "username": data.get("legacy", {}).get("screen_name", username),
                    "name": data.get("legacy", {}).get("name", ""),
                    "description": data.get("legacy", {}).get("description", ""),
                    "followers_count": data.get("legacy", {}).get("followers_count", 0)
                }
        except Exception as e:
            print(f"  ⚠️  RapidAPI 搜索用户失败 (@{username}): {str(e)}")
        return None

    def fetch_tweets(
        self,
        username: str,
        keywords: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取用户推文

        Args:
            username: Twitter 用户名（不带 @，如 "elonmusk"）
            keywords: 关键词过滤（可选），只返回包含这些关键词的推文
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            limit: 返回数量限制（默认 50）

        Returns:
            推文列表，每条推文包含：
            - id: 推文 ID
            - text: 推文内容
            - created_at: 发布时间
            - url: 推文链接
            - metrics: 互动数据（转发、点赞、回复）
            - username: 用户名

        示例:
            tweets = crawler.fetch_tweets(
                username="elonmusk",
                keywords=["AI", "Tesla"],
                start_date="2026-01-01",
                end_date="2026-04-01",
                limit=100
            )
        """
        print(f"  🐦 获取 @{username} 的推文...")

        # 先搜索用户
        user = self.search_user(username)
        if not user:
            print(f"  ⚠️  未找到用户 @{username}")
            return []

        if self.api_type == "official":
            return self._fetch_tweets_official(user["id"], user["username"], keywords, start_date, end_date, limit)
        elif self.api_type == "rapidapi":
            return self._fetch_tweets_rapidapi(user["id"], user["username"], keywords, start_date, end_date, limit)

        return []

    def _fetch_tweets_official(
        self,
        user_id: str,
        username: str,
        keywords: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """使用官方 API 获取推文"""
        try:
            # 构建查询参数
            tweet_fields = ["created_at", "text", "public_metrics", "author_id", "conversation_id"]

            # 时间过滤
            kwargs = {
                "max_results": min(limit, 100),  # API 限制每次最多 100
                "tweet_fields": tweet_fields,
                "exclude": "retweets"  # 排除转推
            }

            if start_date:
                # 转换为 RFC 3339 格式
                start_time = datetime.strptime(start_date, "%Y-%m-%d")
                kwargs["start_time"] = start_time.isoformat() + "Z"

            if end_date:
                end_time = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                kwargs["end_time"] = end_time.isoformat() + "Z"

            # 获取用户时间线
            tweets = self.client.get_users_tweets(id=user_id, **kwargs)

            if not tweets.data:
                print(f"  ℹ️  未找到符合条件的推文")
                return []

            # 转换为标准格式
            results = []
            for tweet in tweets.data:
                # 关键词过滤
                if keywords:
                    if not any(kw.lower() in tweet.text.lower() for kw in keywords):
                        continue

                results.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": tweet.created_at.strftime("%Y-%m-%d %H:%M:%S") if tweet.created_at else "",
                    "url": f"https://twitter.com/{username}/status/{tweet.id}",
                    "metrics": {
                        "retweet_count": tweet.public_metrics.get("retweet_count", 0) if hasattr(tweet, "public_metrics") else 0,
                        "like_count": tweet.public_metrics.get("like_count", 0) if hasattr(tweet, "public_metrics") else 0,
                        "reply_count": tweet.public_metrics.get("reply_count", 0) if hasattr(tweet, "public_metrics") else 0
                    },
                    "username": username
                })

            print(f"  ✓ 获取 {len(results)} 条推文")
            return results

        except Exception as e:
            print(f"  ⚠️  获取推文失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _fetch_tweets_rapidapi(
        self,
        user_id: str,
        username: str,
        keywords: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """使用 RapidAPI 获取推文"""
        try:
            url = f"https://{self.rapidapi_host}/usertimeline.php"
            params = {
                "user_id": user_id,
                "count": str(min(limit, 200))  # RapidAPI 限制
            }

            response = requests.get(url, headers=self.rapidapi_headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # 解析响应
            results = []
            tweets = data.get("timeline", {}).get("instructions", [])

            for instruction in tweets:
                if instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    for entry in entries:
                        content = entry.get("content", {})
                        if content.get("entryType") == "TimelineTimelineItem":
                            item_content = content.get("itemContent", {})
                            if item_content.get("itemType") == "TimelineTweet":
                                tweet_results = item_content.get("tweet_results", {}).get("result", {})
                                legacy = tweet_results.get("legacy", {})

                                # 时间过滤
                                created_at = legacy.get("created_at", "")
                                if created_at:
                                    tweet_date = self._parse_twitter_time(created_at)
                                    if start_date and tweet_date < start_date:
                                        continue
                                    if end_date and tweet_date > end_date:
                                        continue
                                else:
                                    tweet_date = ""

                                text = legacy.get("full_text", "")

                                # 关键词过滤
                                if keywords:
                                    if not any(kw.lower() in text.lower() for kw in keywords):
                                        continue

                                tweet_id = legacy.get("id_str", "")
                                results.append({
                                    "id": tweet_id,
                                    "text": text,
                                    "created_at": tweet_date,
                                    "url": f"https://twitter.com/{username}/status/{tweet_id}",
                                    "metrics": {
                                        "retweet_count": legacy.get("retweet_count", 0),
                                        "like_count": legacy.get("favorite_count", 0),
                                        "reply_count": legacy.get("reply_count", 0)
                                    },
                                    "username": username
                                })

            print(f"  ✓ 获取 {len(results)} 条推文")
            return results[:limit]

        except Exception as e:
            print(f"  ⚠️  RapidAPI 获取推文失败: {str(e)}")
            return []

    @staticmethod
    def _parse_twitter_time(twitter_time: str) -> str:
        """
        解析 Twitter 时间格式

        Twitter 格式: "Wed Oct 10 20:19:24 +0000 2018"
        转换为: "2018-10-10 20:19:24"
        """
        try:
            dt = datetime.strptime(twitter_time, "%a %b %d %H:%M:%S %z %Y")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return twitter_time

    def crawl_multiple_accounts(
        self,
        usernames: List[str],
        keywords: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit_per_account: int = 50
    ) -> List[Dict[str, Any]]:
        """
        批量爬取多个账户

        Args:
            usernames: Twitter 用户名列表（不带 @）
            keywords: 关键词过滤
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            limit_per_account: 每个账户的推文数量限制

        Returns:
            所有推文列表

        示例:
            tweets = crawler.crawl_multiple_accounts(
                usernames=["elonmusk", "sama", "ylecun"],
                keywords=["AI"],
                start_date="2026-01-01",
                limit_per_account=20
            )
        """
        all_tweets = []

        for i, username in enumerate(usernames, 1):
            print(f"\n  [{i}/{len(usernames)}] 处理 @{username}")

            tweets = self.fetch_tweets(
                username=username,
                keywords=keywords,
                start_date=start_date,
                end_date=end_date,
                limit=limit_per_account
            )

            all_tweets.extend(tweets)

            # 避免频率限制
            if i < len(usernames):
                time.sleep(1)

        return all_tweets
