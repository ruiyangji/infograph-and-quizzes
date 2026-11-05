from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import urllib.parse

from src.models.schemas import RawIngestedItem, SourceConnectorConfig, SourceType


class XTwitterConnector:
    '''
    X API v2 Connector supporting user post timelines (/2/users/:id/tweets)
    and Filtered Stream rules with stateful since_id checkpointing.
    Ref: https://generaltranslation.mintlify.app/x-api/posts/timelines/migrate/standard-to-twitter-api-v2
    '''
    BASE_URL = "https://api.x.com/2"

    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token
        self.since_id_checkpoints: Dict[str, str] = {}

    def build_user_timeline_Query(self, user_id: str, max_results: int = 20) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "max_results": max(5, min(max_results, 100)),
            "tweet.fields": "created_at,public_metrics,entities,referenced_tweets,note_tweet",
            "expansions": "author_id,referenced_tweets.id",
            "exclude": "retweets,replies",
        }
        if user_id in self.since_id_checkpoints:
            params["since_id"] = self.since_id_checkpoints[user_id]
        return {
            "endpoint": f"{self.BASE_URL}/users/{user_id}/tweets",
            "params": params,
        }

    def normalize_tweet_payload(
        self,
        tweet: Dict[str, Any],
        handle: str,
        niche_id: str,
    ) -> RawIngestedItem:
        tweet_id = str(tweet["id"])
        text = tweet.get("note_tweet", {}).get("text") or tweet.get("text", "")
        created_str = tweet.get("created_at", "2026-11-05T08:00:00Z")
        published_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        clean_handle = handle.lstrip("@")
        self.since_id_checkpoints[clean_handle] = max(
            tweet_id, self.since_id_checkpoints.get(clean_handle, "0")
        )
        return RawIngestedItem(
            external_id=f"x_{tweet_id}",
            source_type=SourceType.X_TWITTER,
            source_identifier=f"@{clean_handle}",
            source_display_name=f"@{clean_handle} on X",
            title=text[:90] + ("..." if len(text) > 90 else ""),
            content=text,
            url=f"https://x.com/{clean_handle}/status/{tweet_id}",
            published_at=published_at,
            niche_id=niche_id,
            metadata={"tweet_id": tweet_id, "handle": f"@{clean_handle}"},
        )


class NYTimesConnector:
    '''
    The New York Times Developer API Connector supporting Top Stories v2
    (/svc/topstories/v2/{section}.json) and Article Search v2 (/svc/search/v2/articlesearch.json).
    Ref: https://dlthub.com/context/source/nytimes-data
    '''
    BASE_URL = "https://api.nytimes.com/svc"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "demo_nyt_key"

    def build_top_stories_request(self, section: str) -> Dict[str, Any]:
        clean_section = section.lower().strip()
        return {
            "url": f"{self.BASE_URL}/topstories/v2/{clean_section}.json",
            "params": {"api-key": self.api_key},
            "data_selector": "results",
        }

    def build_article_search_request(
        self,
        query: str,
        news_desk: Optional[str] = None,
        begin_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "q": query,
            "sort": "newest",
            "api-key": self.api_key,
        }
        if news_desk:
            params["fq"] = f'news_desk:("{news_desk}")'
        if begin_date:
            params["begin_date"] = begin_date
        return {
            "url": f"{self.BASE_URL}/search/v2/articlesearch.json",
            "params": params,
            "data_selector": "response.docs",
        }

    def normalize_top_story(self, item: Dict[str, Any], section: str, niche_id: str) -> RawIngestedItem:
        url = item.get("url") or "https://www.nytimes.com"
        uid_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        pub_str = item.get("published_date", "2026-11-05T07:30:00Z")
        published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        title = item.get("title", "Untitled NYT Article")
        abstract = item.get("abstract", "")
        return RawIngestedItem(
            external_id=f"nyt_{uid_hash}",
            source_type=SourceType.NYT,
            source_identifier=f"nyt:{section.lower()}",
            source_display_name=f"NYT {section.title()}",
            title=title,
            content=f"{title}. {abstract}".strip(),
            url=url,
            published_at=published_at,
            niche_id=niche_id,
            metadata={"section": section, "byline": item.get("byline", "")},
        )


class RSSFeedConnector:
    '''Connector for custom RSS/Atom feeds, Substack publications, and preprints.'''

    def normalize_entry(
        self,
        entry: Dict[str, str],
        feed_config: SourceConnectorConfig,
        niche_id: str,
    ) -> RawIngestedItem:
        link = entry.get("link", "https://substack.com")
        uid_hash = hashlib.sha256(link.encode("utf-8")).hexdigest()[:12]
        pub_str = entry.get("published_at", "2026-11-05T06:00:00Z")
        published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        return RawIngestedItem(
            external_id=f"rss_{uid_hash}",
            source_type=feed_config.source_type,
            source_identifier=feed_config.identifier,
            source_display_name=feed_config.display_name,
            title=entry.get("title", "Untitled Feed Entry"),
            content=entry.get("summary", ""),
            url=link,
            published_at=published_at,
            niche_id=niche_id,
        )

import xml.etree.ElementTree as ET
import urllib.request


class ArxivPaperConnector:
    """
    Fetches research preprints from the official arXiv API:
    http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate
    Ref: https://info.arxiv.org/help/api/basics.html
    """
    BASE_URL = "http://export.arxiv.org/api/query"

    def fetch_recent_papers(self, category_or_query: str, niche_id: str, max_results: int = 5) -> List[RawIngestedItem]:
        q = category_or_query.removeprefix("arxiv:")
        search_query = f"cat:{q}" if "." in q and " " not in q else f"all:{urllib.parse.quote(q)}"
        url = f"{self.BASE_URL}?search_query={search_query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
        req = urllib.request.Request(url, headers={"User-Agent": "NexusPulse/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items: List[RawIngestedItem] = []
        for entry in root.findall("atom:entry", ns):
            paper_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
            title = " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split())
            summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split())
            pub_str = entry.findtext("atom:published", default="2026-11-05T00:00:00Z", namespaces=ns)
            published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            uid_hash = hashlib.sha256(paper_id.encode("utf-8")).hexdigest()[:10]
            items.append(
                RawIngestedItem(
                    external_id=f"arxiv_{uid_hash}",
                    source_type=SourceType.RSS_SUBSTACK,
                    source_identifier=f"arxiv:{q}",
                    source_display_name=f"arXiv ({q})",
                    title=title,
                    content=summary,
                    url=paper_id,
                    published_at=published_at,
                    niche_id=niche_id,
                    metadata={"source_kind": "research_paper", "query": q},
                )
            )
        return items


class SemanticScholarConnector:
    """
    Queries the Semantic Scholar Academic Graph API (/graph/v1/paper/search)
    for high-velocity peer-reviewed papers and citation velocity.
    Ref: https://www.semanticscholar.org/product/api
    """
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def fetch_papers(self, query: str, niche_id: str, limit: int = 5) -> List[RawIngestedItem]:
        clean_q = query.removeprefix("s2:").strip()
        params = urllib.parse.urlencode({
            "query": clean_q,
            "limit": limit,
            "fields": "title,abstract,url,year,citationCount,publicationDate",
        })
        req = urllib.request.Request(
            f"{self.BASE_URL}?{params}",
            headers={"User-Agent": "NexusPulse/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        items: List[RawIngestedItem] = []
        for paper in payload.get("data", []):
            pid = paper.get("paperId", "")
            title = paper.get("title", "Untitled Paper")
            abstract = paper.get("abstract") or title
            url = paper.get("url") or f"https://www.semanticscholar.org/paper/{pid}"
            items.append(
                RawIngestedItem(
                    external_id=f"s2_{pid[:12]}",
                    source_type=SourceType.RSS_SUBSTACK,
                    source_identifier=f"s2:{clean_q}",
                    source_display_name=f"Semantic Scholar ({clean_q})",
                    title=title,
                    content=abstract,
                    url=url,
                    published_at=datetime.now(timezone.utc),
                    niche_id=niche_id,
                    metadata={"citations": str(paper.get("citationCount", 0))},
                )
            )
        return items


class RedditSubredditConnector:
    """
    Ingests subreddit discussions via Reddit OAuth (https://oauth.reddit.com/r/{sub}/hot)
    or public Atom RSS fallback (https://www.reddit.com/r/{sub}/.rss).
    Ref: https://hermes-agent.nousresearch.com/docs/zh-Hans/user-guide/skills/optional/social-media/social-media-reddit-reading
    """

    def fetch_subreddit(self, subreddit: str, niche_id: str, limit: int = 5) -> List[RawIngestedItem]:
        clean_sub = subreddit.removeprefix("r/").removeprefix("/r/").strip("/")
        url = f"https://www.reddit.com/r/{clean_sub}/hot/.rss?limit={limit}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) NexusPulse/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items: List[RawIngestedItem] = []
        for entry in root.findall("atom:entry", ns)[:limit]:
            title = entry.findtext("atom:title", default="", namespaces=ns) or ""
            content_html = entry.findtext("atom:content", default="", namespaces=ns) or ""
            link_el = entry.find("atom:link", ns)
            link = link_el.attrib.get("href", f"https://www.reddit.com/r/{clean_sub}") if link_el is not None else ""
            uid_hash = hashlib.sha256(link.encode("utf-8")).hexdigest()[:10]
            items.append(
                RawIngestedItem(
                    external_id=f"reddit_{uid_hash}",
                    source_type=SourceType.RSS_SUBSTACK,
                    source_identifier=f"r/{clean_sub}",
                    source_display_name=f"r/{clean_sub}",
                    title=title,
                    content=content_html[:600],
                    url=link,
                    published_at=datetime.now(timezone.utc),
                    niche_id=niche_id,
                    metadata={"subreddit": clean_sub},
                )
            )
        return items


class HackerNewsAlgoliaConnector:
    """
    Fetches high-signal technical discussions via the official Hacker News Algolia API:
    https://hn.algolia.com/api/v1/search?query=...&tags=story
    Ref: https://www.agent37.com/blog/hacker-news-api
    """
    BASE_URL = "https://hn.algolia.com/api/v1/search"

    def fetch_stories(self, query: str, niche_id: str, hits_per_page: int = 5) -> List[RawIngestedItem]:
        clean_q = query.removeprefix("hn:").strip()
        params = urllib.parse.urlencode({
            "query": clean_q,
            "tags": "story",
            "hitsPerPage": hits_per_page,
        })
        req = urllib.request.Request(f"{self.BASE_URL}?{params}", headers={"User-Agent": "NexusPulse/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        items: List[RawIngestedItem] = []
        for hit in payload.get("hits", []):
            oid = str(hit.get("objectID", ""))
            title = hit.get("title") or "HN Discussion"
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={oid}"
            points = hit.get("points", 0)
            items.append(
                RawIngestedItem(
                    external_id=f"hn_{oid}",
                    source_type=SourceType.RSS_SUBSTACK,
                    source_identifier=f"hn:{clean_q}",
                    source_display_name=f"Hacker News ({clean_q})",
                    title=title,
                    content=f"{title} ({points} points on HN)",
                    url=url,
                    published_at=datetime.now(timezone.utc),
                    niche_id=niche_id,
                    metadata={"points": str(points), "hn_id": oid},
                )
            )
        return items
