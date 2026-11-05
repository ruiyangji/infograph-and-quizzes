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
