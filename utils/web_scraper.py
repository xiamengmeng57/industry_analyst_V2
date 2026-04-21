"""
网页抓取模块 - 提取URL内容
"""

import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


class WebScraper:
    """网页内容抓取器"""

    def __init__(self):
        """初始化网页抓取器"""
        self.timeout = 30
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        self.current_ua_index = 0

        self.min_content_length = 100
        self.max_content_length = 50000
        self.remove_elements = ['script', 'style', 'nav', 'footer', 'header', 'aside']

    def _get_user_agent(self) -> str:
        """获取下一个User-Agent"""
        ua = self.user_agents[self.current_ua_index]
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        return ua

    def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        抓取URL内容

        Args:
            url: 要抓取的URL

        Returns:
            包含 title, content, metadata 的字典
        """
        try:
            print(f"  📄 抓取: {url}")

            headers = {
                "User-Agent": self._get_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # 提取标题
            title = self._extract_title(soup)

            # 提取正文内容
            content = self._extract_content(soup)

            # 提取元数据
            metadata = self._extract_metadata(soup, url)

            result = {
                'url': url,
                'title': title,
                'content': content,
                'metadata': metadata,
                'status': 'success'
            }

            # 延迟以避免被封
            time.sleep(0.5)

            return result

        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  抓取失败 {url}: {e}")
            return {
                'url': url,
                'title': '',
                'content': '',
                'metadata': {},
                'status': 'error',
                'error': str(e)
            }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取页面标题"""
        # 尝试 <title> 标签
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        # 尝试 <h1> 标签
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        # 尝试 og:title meta 标签
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        return "Untitled"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """从页面提取正文内容"""
        # 移除不需要的元素
        for element in self.remove_elements:
            for tag in soup.find_all(element):
                tag.decompose()

        # 尝试找到主要内容区域
        main_content = None

        # 尝试 <article> 标签
        article = soup.find('article')
        if article:
            main_content = article

        # 尝试 <main> 标签
        if not main_content:
            main = soup.find('main')
            if main:
                main_content = main

        # 尝试常见的内容class名称
        if not main_content:
            for class_name in ['content', 'main-content', 'article-content', 'post-content', 'entry-content']:
                content_div = soup.find('div', class_=class_name)
                if content_div:
                    main_content = content_div
                    break

        # 回退到body
        if not main_content:
            main_content = soup.body

        if not main_content:
            return ""

        # 提取文本
        text = main_content.get_text(separator='\n', strip=True)

        # 清理文本
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # 移除空行
        text = '\n'.join(lines)

        # 强制长度限制
        if len(text) < self.min_content_length:
            print(f"  ⚠️  内容过短: {len(text)} 字符")

        if len(text) > self.max_content_length:
            print(f"  ⚠️  内容过长，截断: {len(text)} 字符")
            text = text[:self.max_content_length] + "..."

        return text

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """提取元数据"""
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc
        }

        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            metadata['description'] = meta_desc['content'].strip()

        # Open Graph metadata
        og_tags = {
            'og:description': 'og_description',
            'og:image': 'og_image',
            'og:type': 'og_type',
            'og:site_name': 'site_name'
        }

        for og_tag, key in og_tags.items():
            tag = soup.find('meta', property=og_tag)
            if tag and tag.get('content'):
                metadata[key] = tag['content'].strip()

        # Author
        author = soup.find('meta', attrs={'name': 'author'})
        if author and author.get('content'):
            metadata['author'] = author['content'].strip()

        # Published date
        for date_tag in ['article:published_time', 'datePublished']:
            tag = soup.find('meta', property=date_tag) or soup.find('meta', attrs={'name': date_tag})
            if tag and tag.get('content'):
                metadata['published_date'] = tag['content'].strip()
                break

        return metadata

    def scrape_multiple(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        抓取多个URL

        Args:
            urls: URL列表

        Returns:
            抓取内容列表
        """
        results = []

        for i, url in enumerate(urls):
            print(f"  正在抓取 {i+1}/{len(urls)}")
            result = self.scrape_url(url)
            if result and result.get('status') == 'success':
                results.append(result)

            # 请求间延迟
            if i < len(urls) - 1:
                time.sleep(1)

        return results
