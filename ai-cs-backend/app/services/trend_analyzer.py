"""
Trend Analyzer Service - REAL DATA VERSION
Scrapes actual trending CS2 content from public sources:
1. Twitch - top CS2 streams via TwitchTracker scraping
2. YouTube - trending CS2 shorts/videos via RSS feeds + search pages
3. Platform trend analysis - what formats/styles/hooks are performing

All data flows INTO the montage engine via get_platform_design_hints().
Self-learning: tracks which design combos perform best and adjusts weights.
"""

import json
import os
import re
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ===================================================================
# SECTION 1: LIVE DATA CACHE
# ===================================================================

_CACHE_DIR = Path("/tmp/trend_cache")
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_LEARNING_WEIGHTS_FILE = Path("/tmp/trend_learning_weights.json")

_CACHE_TTL = {
    "twitch_streams": 300,
    "youtube_trending": 1800,
    "combined_insights": 600,
    "format_analysis": 3600,
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _cache_get(key: str) -> Optional[dict]:
    """Read cached data if it exists and is not expired."""
    path = _CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        ttl = 600
        for ttl_key, ttl_val in _CACHE_TTL.items():
            if key.startswith(ttl_key) or key == ttl_key:
                ttl = ttl_val
                break
        if time.time() - data.get("_cached_at", 0) > ttl:
            return None
        return data
    except Exception:
        return None


def _cache_set(key: str, data: dict):
    """Write data to disk cache."""
    try:
        data["_cached_at"] = time.time()
        path = _CACHE_DIR / f"{key}.json"
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Cache write failed for {key}: {e}")


# ===================================================================
# SECTION 2: KNOWN CS2 DATABASE (fallback when scraping fails)
# ===================================================================

_KNOWN_CS2_STREAMERS = [
    {"name": "s1mple", "viewers": 25000, "title": "CS2 FPL GRINDING", "language": "en"},
    {"name": "m0NESY", "viewers": 18000, "title": "CS2 FACEIT LVL10", "language": "en"},
    {"name": "ZywOo", "viewers": 15000, "title": "CS2 Ranked", "language": "en"},
    {"name": "donk", "viewers": 22000, "title": "CS2 Pro Matches", "language": "ru"},
    {"name": "NiKo", "viewers": 14000, "title": "CS2 FPL", "language": "en"},
    {"name": "ropz", "viewers": 9000, "title": "CS2 Practice", "language": "en"},
    {"name": "b1t", "viewers": 8500, "title": "CS2 FACEIT", "language": "ru"},
    {"name": "sh1ro", "viewers": 7500, "title": "CS2 AWP God", "language": "ru"},
    {"name": "frozen", "viewers": 6000, "title": "CS2 Stream", "language": "en"},
    {"name": "Twistzz", "viewers": 10000, "title": "CS2 Rank Up", "language": "en"},
    {"name": "EliGE", "viewers": 7000, "title": "CS2 NA FPL", "language": "en"},
    {"name": "broky", "viewers": 5500, "title": "CS2 Highlights", "language": "en"},
    {"name": "jL", "viewers": 6500, "title": "CS2 FPL", "language": "en"},
    {"name": "rain", "viewers": 5000, "title": "CS2 Legends Match", "language": "en"},
    {"name": "device", "viewers": 12000, "title": "CS2 Return", "language": "en"},
]

_KNOWN_YT_CHANNELS = [
    {"channel": "ohnePixel", "subscribers": 1200000, "focus": "cs2_highlights"},
    {"channel": "Sparkles", "subscribers": 2500000, "focus": "cs2_highlights"},
    {"channel": "JEEMZZ", "subscribers": 800000, "focus": "cs2_pro"},
    {"channel": "Virre", "subscribers": 700000, "focus": "cs2_edits"},
    {"channel": "Grim", "subscribers": 600000, "focus": "cs2_pro_plays"},
    {"channel": "NadeKing", "subscribers": 1100000, "focus": "cs2_tips"},
    {"channel": "voo CSGO", "subscribers": 900000, "focus": "cs2_analysis"},
    {"channel": "WarOwl", "subscribers": 2000000, "focus": "cs2_education"},
    {"channel": "fl0m", "subscribers": 500000, "focus": "cs2_content"},
]

_KNOWN_FORMATS = {
    "sigma_edit": {
        "hook_type": "text_hook",
        "avg_duration": 15,
        "music_style": "phonk",
        "text_style": "bold_caps",
        "color_grade": "high_contrast",
        "pacing": "fast",
        "transitions": ["zoom_cut", "whip_pan"],
        "popularity_score": 9.2,
    },
    "highlight_react": {
        "hook_type": "girl_reaction",
        "avg_duration": 30,
        "music_style": "electronic",
        "text_style": "glow_outline",
        "color_grade": "vibrant",
        "pacing": "medium",
        "transitions": ["cut", "zoom_in"],
        "popularity_score": 8.8,
    },
    "pro_clutch": {
        "hook_type": "question_hook",
        "avg_duration": 25,
        "music_style": "dramatic",
        "text_style": "impact",
        "color_grade": "cinematic",
        "pacing": "build_up",
        "transitions": ["slow_mo", "speed_ramp"],
        "popularity_score": 8.5,
    },
    "funny_moments": {
        "hook_type": "funny_text",
        "avg_duration": 20,
        "music_style": "meme",
        "text_style": "comic_sans_ironic",
        "color_grade": "saturated",
        "pacing": "fast",
        "transitions": ["zoom_cut", "shake"],
        "popularity_score": 8.0,
    },
    "ace_compilation": {
        "hook_type": "stat_hook",
        "avg_duration": 45,
        "music_style": "epic",
        "text_style": "minimal",
        "color_grade": "dark_moody",
        "pacing": "escalating",
        "transitions": ["crossfade", "zoom_cut"],
        "popularity_score": 7.5,
    },
    "tutorial_tip": {
        "hook_type": "value_hook",
        "avg_duration": 35,
        "music_style": "ambient",
        "text_style": "clean_modern",
        "color_grade": "neutral",
        "pacing": "medium",
        "transitions": ["cut", "slide"],
        "popularity_score": 7.8,
    },
}


# ===================================================================
# SECTION 3: TWITCH SCRAPER
# ===================================================================

async def _twitch_api_streams(client_id: str, secret: str) -> list[dict]:
    """Try Twitch Helix API for CS2 streams."""
    try:
        # Support direct access token (skip client_credentials flow)
        direct_token = os.environ.get("TWITCH_ACCESS_TOKEN", "")
        if direct_token:
            token = direct_token
            if not client_id:
                client_id = os.environ.get("TWITCH_CLIENT_ID", "")
        else:
            async with httpx.AsyncClient(timeout=15.0) as hclient:
                token_resp = await hclient.post(
                    "https://id.twitch.tv/oauth2/token",
                    data={
                        "client_id": client_id,
                        "client_secret": secret,
                        "grant_type": "client_credentials",
                    },
                )
                if token_resp.status_code != 200:
                    logger.warning(f"Twitch OAuth failed: {token_resp.status_code}")
                    return []
                token = token_resp.json().get("access_token", "")
                if not token:
                    return []
        async with httpx.AsyncClient(timeout=15.0) as api_client:
            resp = await api_client.get(
                "https://api.twitch.tv/helix/streams",
                params={"game_id": "32399", "first": "20", "type": "live"},
                headers={"Client-ID": client_id, "Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", [])
            streams = []
            for s in data:
                streams.append({
                    "name": s.get("user_name", "Unknown"),
                    "viewers": s.get("viewer_count", 0),
                    "title": s.get("title", ""),
                    "language": s.get("language", "en"),
                    "started_at": s.get("started_at", ""),
                    "source": "twitch_api",
                    "is_live": True,
                })
            logger.info(f"Twitch API: found {len(streams)} CS2 streams")
            return streams
    except Exception as e:
        logger.warning(f"Twitch API error: {e}")
        return []


async def _scrape_twitch_tracker_cs2() -> list[dict]:
    """Scrape TwitchTracker for top CS2 streamers (public page, no API)."""
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://twitchtracker.com/games/32399",
                headers=_HEADERS,
            )
            if resp.status_code != 200:
                logger.warning(f"TwitchTracker returned {resp.status_code}")
                return []
            soup = BeautifulSoup(resp.text, "lxml")
            streams = []
            rows = soup.select("table tbody tr")
            if not rows:
                rows = soup.select(".ranked-item, .streamer-row, tr[data-id]")
            for row in rows[:20]:
                try:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        name_el = cells[0].find("a") or cells[1].find("a")
                        name = name_el.get_text(strip=True) if name_el else ""
                        if not name:
                            name = cells[0].get_text(strip=True)
                        viewer_text = ""
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            cleaned = text.replace(",", "").replace(".", "")
                            if cleaned.isdigit() and int(cleaned) > 10:
                                viewer_text = cleaned
                                break
                        viewers = int(viewer_text) if viewer_text else 0
                        if name and len(name) > 1:
                            streams.append({
                                "name": name,
                                "viewers": viewers,
                                "title": "CS2 Stream",
                                "language": "en",
                                "source": "twitchtracker",
                                "is_live": True,
                            })
                except Exception:
                    continue
            if not streams:
                cards = soup.select("[class*=channel], [class*=streamer]")
                for card in cards[:20]:
                    name = card.get_text(strip=True)[:30]
                    if name and len(name) > 2:
                        streams.append({
                            "name": name,
                            "viewers": 0,  # Unknown — scraped without viewer count
                            "title": "CS2 Stream",
                            "language": "en",
                            "source": "twitchtracker",
                            "is_live": True,
                        })
            logger.info(f"TwitchTracker: scraped {len(streams)} CS2 streamers")
            return streams
    except Exception as e:
        logger.warning(f"TwitchTracker scrape error: {e}")
        return []


def _get_known_cs2_streamers() -> list[dict]:
    """Fallback: return known CS2 streamers database.
    
    WARNING: This is STATIC data — viewer counts are historical averages,
    not live. The source is marked as 'known_db' so freshness gates can
    detect and reject this data when strict mode is enabled.
    """
    logger.info("Using known CS2 streamers database (fallback — NOT live data)")
    streamers = []
    for s in _KNOWN_CS2_STREAMERS:
        streamers.append({
            "name": s["name"],
            "viewers": s["viewers"],  # Static historical average, NOT live
            "title": s["title"],
            "language": s["language"],
            "source": "known_db",
            "is_live": False,  # We don't know — mark as not live
        })
    return streamers


async def scrape_twitch_cs2_streams(
    twitch_client_id: str = "", twitch_secret: str = ""
) -> list[dict]:
    """Main entry: Twitch CS2 streams. Fallback: API -> TwitchTracker -> known DB"""
    cache = _cache_get("twitch_streams")
    if cache and cache.get("streams"):
        logger.info(f"Twitch: serving {len(cache['streams'])} streams from cache")
        streams = cache["streams"]
        # Preserve a visible freshness timestamp on each record.
        cached_at = cache.get("_cached_at")
        fetched_at = (
            datetime.utcfromtimestamp(cached_at).isoformat()
            if cached_at
            else datetime.utcnow().isoformat()
        )
        for s in streams:
            s.setdefault("fetched_at", fetched_at)
        return streams
    if not twitch_client_id:
        twitch_client_id = os.environ.get("TWITCH_CLIENT_ID", "")
    if not twitch_secret:
        twitch_secret = os.environ.get("TWITCH_CLIENT_SECRET", "")
    direct_token = os.environ.get("TWITCH_ACCESS_TOKEN", "")
    streams: list[dict] = []
    if direct_token or (twitch_client_id and twitch_secret):
        streams = await _twitch_api_streams(twitch_client_id, twitch_secret)
    if not streams:
        streams = await _scrape_twitch_tracker_cs2()
    if not streams:
        streams = _get_known_cs2_streamers()
    if streams:
        fetched_at = datetime.utcnow().isoformat()
        for s in streams:
            s["fetched_at"] = fetched_at
        _cache_set("twitch_streams", {"streams": streams})
    return streams


# ===================================================================
# SECTION 4: YOUTUBE SCRAPER
# ===================================================================

async def _youtube_api_search(api_key: str) -> list[dict]:
    """Use YouTube Data API v3 to find trending CS2 content."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "key": api_key,
                    "q": f"CS2 highlights {datetime.utcnow().year}",
                    "part": "snippet",
                    "type": "video",
                    "order": "viewCount",
                    "publishedAfter": (
                        datetime.utcnow() - timedelta(days=7)
                    ).isoformat() + "Z",
                    "maxResults": 20,
                    "videoDuration": "short",
                },
            )
            if resp.status_code != 200:
                return []
            items = resp.json().get("items", [])
            videos = []
            for item in items:
                snippet = item.get("snippet", {})
                videos.append({
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "video_id": item.get("id", {}).get("videoId", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "description": snippet.get("description", "")[:200],
                    "source": "youtube_api",
                })
            logger.info(f"YouTube API: found {len(videos)} CS2 videos")
            return videos
    except Exception as e:
        logger.warning(f"YouTube API error: {e}")
        return []


async def _scrape_youtube_rss_cs2() -> list[dict]:
    """Scrape YouTube RSS feeds for known CS2 channels (public, no API key)."""
    channel_ids = [
        "UCWifWMvi0MI42TxMOEsFgtg",  # ohnePixel
        "UC0JZ68IE-GS1sGTxLdZwqOQ",  # Sparkles
        "UCQsHWW7UMmPh1LUjMkFAgeA",  # NadeKing
        "UC5BKXQ-hOLMPAYkQ8URsVgg",  # WarOwl
        "UCJvRh1aPTQJPHKPkH1btiqg",  # fl0m
    ]
    videos: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for channel_id in channel_ids:
                try:
                    resp = await client.get(
                        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
                        headers=_HEADERS,
                    )
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "lxml-xml")
                    entries = soup.find_all("entry")
                    for entry in entries[:5]:
                        title_el = entry.find("title")
                        title_text = title_el.get_text(strip=True) if title_el else ""
                        cs2_keywords = [
                            "cs2", "counter-strike", "csgo", "cs 2", "ace",
                            "clutch", "highlight", "frag", "awp", "headshot",
                            "ninja",
                        ]
                        is_cs2 = any(kw in title_text.lower() for kw in cs2_keywords)
                        if not is_cs2 and title_text:
                            continue
                        published = entry.find("published")
                        pub_text = published.get_text(strip=True) if published else ""
                        video_id_el = entry.find("yt:videoId")
                        vid_id = video_id_el.get_text(strip=True) if video_id_el else ""
                        author = entry.find("author")
                        channel_name = ""
                        if author:
                            name_el = author.find("name")
                            channel_name = name_el.get_text(strip=True) if name_el else ""
                        media_group = entry.find("media:group")
                        description = ""
                        if media_group:
                            desc_el = media_group.find("media:description")
                            description = (
                                desc_el.get_text(strip=True)[:200] if desc_el else ""
                            )
                        views = 0
                        stats = (
                            entry.find("media:statistics")
                            or entry.find("media:community")
                        )
                        if stats:
                            views_attr = stats.get("views", "0")
                            try:
                                views = int(views_attr)
                            except (ValueError, TypeError):
                                views = 0
                        if title_text:
                            videos.append({
                                "title": title_text,
                                "channel": channel_name,
                                "video_id": vid_id,
                                "published_at": pub_text,
                                "description": description,
                                "views": views,
                                "source": "youtube_rss",
                            })
                except Exception as e:
                    logger.debug(f"RSS feed error for {channel_id}: {e}")
                    continue
        logger.info(f"YouTube RSS: found {len(videos)} CS2 videos")
    except Exception as e:
        logger.warning(f"YouTube RSS scrape error: {e}")
    return videos


async def _scrape_youtube_search_page() -> list[dict]:
    """Scrape YouTube search results page for CS2 trending content."""
    queries = [
        "CS2 highlights today",
        f"CS2 best clips {datetime.utcnow().year}",
        "CS2 funny moments",
        "CS2 pro plays",
    ]
    videos: list[dict] = []
    try:
        async with httpx.AsyncClient(
            timeout=20.0, follow_redirects=True
        ) as client:
            # Deterministic query selection (avoid randomness in pipeline)
            query = queries[0]
            search_url = (
                "https://www.youtube.com/results?search_query="
                + query.replace(" ", "+")
                + "&sp=EgQIAxAB"
            )
            resp = await client.get(search_url, headers=_HEADERS)
            if resp.status_code != 200:
                return []
            text = resp.text
            pattern = r'var ytInitialData\s*=\s*(\{.*?\});\s*</script>'
            match = re.search(pattern, text)
            if not match:
                pattern2 = r'ytInitialData\s*=\s*(\{.*?\});\s*'
                match = re.search(pattern2, text)
            if match:
                try:
                    yt_data = json.loads(match.group(1))
                    contents = (
                        yt_data.get("contents", {})
                        .get("twoColumnSearchResultsRenderer", {})
                        .get("primaryContents", {})
                        .get("sectionListRenderer", {})
                        .get("contents", [])
                    )
                    for section in contents:
                        items = (
                            section.get("itemSectionRenderer", {})
                            .get("contents", [])
                        )
                        for item in items:
                            video = item.get("videoRenderer", {})
                            if not video:
                                continue
                            title_runs = video.get("title", {}).get("runs", [])
                            title_text = (
                                title_runs[0].get("text", "") if title_runs else ""
                            )
                            channel_runs = (
                                video.get("ownerText", {}).get("runs", [])
                            )
                            channel_name = (
                                channel_runs[0].get("text", "")
                                if channel_runs
                                else ""
                            )
                            vid_id = video.get("videoId", "")
                            view_text = (
                                video.get("viewCountText", {})
                                .get("simpleText", "0")
                            )
                            views = 0
                            view_match = re.search(
                                r'[\d,]+', view_text.replace(",", "")
                            )
                            if view_match:
                                try:
                                    views = int(
                                        view_match.group().replace(",", "")
                                    )
                                except ValueError:
                                    views = 0
                            if title_text and vid_id:
                                videos.append({
                                    "title": title_text,
                                    "channel": channel_name,
                                    "video_id": vid_id,
                                    "views": views,
                                    "source": "youtube_search_page",
                                })
                except json.JSONDecodeError:
                    logger.warning("Failed to parse ytInitialData JSON")
            logger.info(f"YouTube search: found {len(videos)} CS2 videos")
    except Exception as e:
        logger.warning(f"YouTube search scrape error: {e}")
    return videos


def _get_known_youtube_patterns() -> list[dict]:
    """Fallback (DISABLED): previously returned FAKE YouTube data.

    This project must not generate or use simulated trend data.
    If no real YouTube data can be scraped, return an empty list and let
    freshness gates / callers decide whether to proceed.
    """
    logger.info("No real YouTube data available (fallback disabled)")
    return []


async def scrape_youtube_cs2_trending(youtube_api_key: str = "") -> list[dict]:
    """Main entry: YouTube CS2 trending. Fallback: API -> RSS -> Search -> known"""
    cache = _cache_get("youtube_trending")
    if cache and cache.get("videos"):
        logger.info(f"YouTube: serving {len(cache['videos'])} videos from cache")
        return cache["videos"]
    if not youtube_api_key:
        youtube_api_key = os.environ.get("YOUTUBE_API_KEY", "")
    videos: list[dict] = []
    if youtube_api_key:
        videos = await _youtube_api_search(youtube_api_key)
    if not videos:
        videos = await _scrape_youtube_rss_cs2()
    if len(videos) < 5:
        search_videos = await _scrape_youtube_search_page()
        existing_ids = {v.get("video_id") for v in videos}
        for sv in search_videos:
            if sv.get("video_id") not in existing_ids:
                videos.append(sv)
    # No fake fallback - if we can't scrape real YouTube data, return empty.
    if not videos:
        videos = []
    if videos:
        _cache_set("youtube_trending", {"videos": videos})
    return videos


# ===================================================================
# SECTION 5: FORMAT & TREND ANALYSIS
# ===================================================================

def _classify_video_format(title: str, description: str = "") -> dict:
    """Classify a video into a format category based on title/description."""
    text = f"{title} {description}".lower()
    scores: dict[str, int] = {}
    if any(w in text for w in ["sigma", "edit", "phonk", "gigachad", "chad"]):
        scores["sigma_edit"] = 9
    if any(w in text for w in ["react", "reaction", "girl", "watching", "reacts"]):
        scores["highlight_react"] = 8
    if any(w in text for w in ["clutch", "1v5", "1v4", "1v3", "insane", "impossible"]):
        scores["pro_clutch"] = 8
    if any(w in text for w in ["funny", "fail", "wtf", "lol", "moments", "meme"]):
        scores["funny_moments"] = 7
    if any(w in text for w in ["ace", "compilation", "top 10", "best of", "top"]):
        scores["ace_compilation"] = 7
    if any(w in text for w in ["tip", "guide", "how to", "tutorial", "settings", "rank up"]):
        scores["tutorial_tip"] = 6
    if any(w in text for w in ["highlight", "plays", "best", "insane", "crazy"]):
        scores["highlight_react"] = max(scores.get("highlight_react", 0), 7)
    if not scores:
        scores["highlight_react"] = 5
    top_format = max(scores, key=scores.get)
    return {
        "format": top_format,
        "confidence": min(scores[top_format] / 10.0, 1.0),
        "all_scores": scores,
    }


def _analyze_title_hooks(titles: list[str]) -> dict:
    """Analyze what hook types are trending in video titles."""
    hook_counts = {
        "question": 0,
        "caps_shock": 0,
        "stat_number": 0,
        "emoji_hook": 0,
        "challenge": 0,
        "pov_hook": 0,
        "superlative": 0,
    }
    for title in titles:
        if "?" in title:
            hook_counts["question"] += 1
        upper_ratio = sum(1 for c in title if c.isupper()) / max(len(title), 1)
        if title.upper() == title or upper_ratio > 0.4:
            hook_counts["caps_shock"] += 1
        if re.search(r'\d+', title):
            hook_counts["stat_number"] += 1
        if any(ord(c) > 127 for c in title):
            hook_counts["emoji_hook"] += 1
        if any(w in title.lower() for w in ["challenge", "try", "attempt", "can you"]):
            hook_counts["challenge"] += 1
        if "pov" in title.lower():
            hook_counts["pov_hook"] += 1
        if any(w in title.lower() for w in [
            "best", "worst", "insane", "crazy", "craziest", "most"
        ]):
            hook_counts["superlative"] += 1
    total = max(sum(hook_counts.values()), 1)
    hook_percentages = {k: round(v / total * 100, 1) for k, v in hook_counts.items()}
    top_hook = max(hook_counts, key=hook_counts.get)
    return {
        "top_hook_type": top_hook,
        "hook_distribution": hook_percentages,
        "total_analyzed": len(titles),
    }


def _analyze_format_trends(videos: list[dict]) -> dict:
    """Analyze trending formats from video data."""
    format_counts: dict[str, int] = {}
    format_details: dict[str, list] = {}
    for video in videos:
        classification = _classify_video_format(
            video.get("title", ""), video.get("description", ""),
        )
        fmt = classification["format"]
        format_counts[fmt] = format_counts.get(fmt, 0) + 1
        if fmt not in format_details:
            format_details[fmt] = []
        format_details[fmt].append({
            "title": video.get("title", "")[:80],
            "views": video.get("views", 0),
            "confidence": classification["confidence"],
        })
    sorted_formats = sorted(
        format_counts.items(), key=lambda x: x[1], reverse=True
    )
    titles = [v.get("title", "") for v in videos if v.get("title")]
    hook_analysis = _analyze_title_hooks(titles)
    format_scores: dict[str, float] = {}
    for fmt, details in format_details.items():
        avg_views = sum(d["views"] for d in details) / max(len(details), 1)
        count_weight = len(details) / max(len(videos), 1)
        view_score = min(avg_views / 200000, 10)
        format_scores[fmt] = round(count_weight * 5 + view_score * 0.5, 2)
    top_format = sorted_formats[0][0] if sorted_formats else "highlight_react"
    top_score = format_scores.get(top_format, 5.0)
    return {
        "top_format": top_format,
        "top_format_score": top_score,
        "format_distribution": dict(sorted_formats),
        "format_scores": format_scores,
        "hook_analysis": hook_analysis,
        "total_videos_analyzed": len(videos),
        "analyzed_at": datetime.utcnow().isoformat(),
    }


# ===================================================================
# SECTION 6: DESIGN RECOMMENDATIONS
# ===================================================================

_COLOR_MAP = {
    "sigma_edit": "high_contrast",
    "highlight_react": "vibrant",
    "pro_clutch": "cinematic",
    "funny_moments": "saturated",
    "ace_compilation": "dark_moody",
    "tutorial_tip": "neutral",
}
_MUSIC_MAP = {
    "sigma_edit": "phonk",
    "highlight_react": "electronic",
    "pro_clutch": "dramatic",
    "funny_moments": "meme",
    "ace_compilation": "epic",
    "tutorial_tip": "ambient",
}
_FONT_MAP = {
    "sigma_edit": "bold_caps",
    "highlight_react": "glow_outline",
    "pro_clutch": "impact",
    "funny_moments": "comic_sans_ironic",
    "ace_compilation": "minimal",
    "tutorial_tip": "clean_modern",
}
_DURATION_MAP = {
    "sigma_edit": 15,
    "highlight_react": 30,
    "pro_clutch": 25,
    "funny_moments": 20,
    "ace_compilation": 45,
    "tutorial_tip": 35,
}
_HOOK_TYPE_MAP = {
    "question": "question_hook",
    "caps_shock": "shock_text",
    "stat_number": "stat_hook",
    "emoji_hook": "emoji_burst",
    "challenge": "challenge_hook",
    "pov_hook": "pov_hook",
    "superlative": "superlative_hook",
}


def _build_design_recommendations(
    format_analysis: dict,
    twitch_data: list[dict],
    youtube_data: list[dict],
) -> dict:
    """Build concrete design recommendations from trend analysis."""
    top_format = format_analysis.get("top_format", "highlight_react")
    top_score = format_analysis.get("top_format_score", 5.0)
    hook_analysis = format_analysis.get("hook_analysis", {})
    fmt_template = _KNOWN_FORMATS.get(
        top_format, _KNOWN_FORMATS["highlight_react"]
    )
    top_hook = hook_analysis.get("top_hook_type", "text_hook")
    recommended_hook = _HOOK_TYPE_MAP.get(top_hook, "text_hook")

    total_twitch_viewers = sum(s.get("viewers", 0) for s in twitch_data[:10])
    avg_viewers = total_twitch_viewers / max(len(twitch_data[:10]), 1)
    if avg_viewers > 15000:
        recommended_pacing = "fast"
    elif avg_viewers > 5000:
        recommended_pacing = "medium"
    else:
        recommended_pacing = "build_up"

    data_sources = list(set(
        [s.get("source", "unknown") for s in twitch_data[:5]]
        + [v.get("source", "unknown") for v in youtube_data[:5]]
    ))

    return {
        "preferred_style": top_format,
        "top_format_score": top_score,
        "recommended_hook": recommended_hook,
        "recommended_pacing": recommended_pacing,
        "recommended_color_grade": _COLOR_MAP.get(top_format, "vibrant"),
        "recommended_music_style": _MUSIC_MAP.get(top_format, "electronic"),
        "recommended_font_style": _FONT_MAP.get(top_format, "glow_outline"),
        "recommended_duration_sec": _DURATION_MAP.get(top_format, 30),
        "recommended_transitions": fmt_template.get(
            "transitions", ["cut", "zoom_cut"]
        ),
        "twitch_insight": {
            "total_streams": len(twitch_data),
            "avg_viewers": round(avg_viewers),
            "top_streamer": (
                twitch_data[0]["name"] if twitch_data else "Unknown"
            ),
            "top_viewers": (
                twitch_data[0]["viewers"] if twitch_data else 0
            ),
        },
        "youtube_insight": {
            "total_videos": len(youtube_data),
            "top_video": (
                youtube_data[0]["title"][:60] if youtube_data else "None"
            ),
            "top_channel": (
                youtube_data[0]["channel"] if youtube_data else "Unknown"
            ),
        },
        "format_analysis": {
            "top_format": top_format,
            "score": top_score,
            "hook_type": recommended_hook,
            "all_formats": format_analysis.get("format_distribution", {}),
        },
        "data_sources_used": data_sources,
        "freshness": datetime.utcnow().isoformat(),
    }


# ===================================================================
# SECTION 7: MAIN ANALYSIS ORCHESTRATOR
# ===================================================================

async def analyze_current_trends(
    twitch_client_id: str = "",
    twitch_secret: str = "",
    youtube_api_key: str = "",
) -> dict:
    """Main orchestrator: scrape all sources, analyze, build recommendations."""
    cache = _cache_get("combined_insights")
    if cache and cache.get("recommendations"):
        logger.info("Serving combined insights from cache")
        return cache
    twitch_data = await scrape_twitch_cs2_streams(
        twitch_client_id, twitch_secret
    )
    youtube_data = await scrape_youtube_cs2_trending(youtube_api_key)
    format_analysis = _analyze_format_trends(youtube_data)
    recommendations = _build_design_recommendations(
        format_analysis, twitch_data, youtube_data,
    )
    result = {
        "twitch_streams": twitch_data[:10],
        "youtube_videos": youtube_data[:15],
        "format_analysis": format_analysis,
        "recommendations": recommendations,
        "meta": {
            "scraped_at": datetime.utcnow().isoformat(),
            "twitch_source": (
                twitch_data[0].get("source", "none") if twitch_data else "none"
            ),
            "youtube_source": (
                youtube_data[0].get("source", "none") if youtube_data else "none"
            ),
            "total_data_points": len(twitch_data) + len(youtube_data),
        },
    }
    _cache_set("combined_insights", result)
    return result


# ===================================================================
# SECTION 8: BRIDGE FUNCTION - get_platform_design_hints()
# Imported by smart_montage_engine.py / producer_analyze_material
# ===================================================================

def get_platform_design_hints(platform: str = "tiktok") -> dict:
    """
    Synchronous bridge: returns design hints for montage engine.
    Called by producer_analyze_material() in smart_montage_engine.py.
    Returns real trend data if available (from cache), otherwise known patterns.
    """
    cache = _cache_get("combined_insights")
    if cache and cache.get("recommendations"):
        recs = dict(cache["recommendations"])
        logger.info(
            f"get_platform_design_hints: serving REAL trend data for {platform}"
        )
        if platform == "tiktok":
            recs["recommended_duration_sec"] = min(
                recs.get("recommended_duration_sec", 30), 30
            )
            recs["recommended_pacing"] = "fast"
        elif platform == "youtube_shorts":
            recs["recommended_duration_sec"] = min(
                recs.get("recommended_duration_sec", 45), 58
            )
        elif platform == "instagram":
            recs["recommended_duration_sec"] = min(
                recs.get("recommended_duration_sec", 30), 30
            )
            recs["recommended_color_grade"] = "vibrant"
        recs["platform"] = platform
        recs["data_type"] = "real_scraped"
        return recs

    # Fallback: build hints from known patterns
    logger.info(
        f"get_platform_design_hints: using known patterns for {platform}"
    )
    formats_by_score = sorted(
        _KNOWN_FORMATS.items(),
        key=lambda x: x[1]["popularity_score"],
        reverse=True,
    )
    weights = _load_learning_weights()
    if weights and weights.get("format_weights"):
        for fmt_name, fmt_data in formats_by_score:
            weight = weights["format_weights"].get(fmt_name, 1.0)
            fmt_data["adjusted_score"] = fmt_data["popularity_score"] * weight
        formats_by_score = sorted(
            formats_by_score,
            key=lambda x: x[1].get(
                "adjusted_score", x[1]["popularity_score"]
            ),
            reverse=True,
        )
    top_fmt_name, top_fmt = formats_by_score[0]
    duration = top_fmt["avg_duration"]
    if platform == "tiktok":
        duration = min(duration, 30)
    elif platform == "youtube_shorts":
        duration = min(duration, 58)
    elif platform == "instagram":
        duration = min(duration, 30)
    avg_viewers = sum(
        s["viewers"] for s in _KNOWN_CS2_STREAMERS
    ) // len(_KNOWN_CS2_STREAMERS)
    return {
        "preferred_style": top_fmt_name,
        "top_format_score": top_fmt["popularity_score"],
        "recommended_hook": top_fmt["hook_type"],
        "recommended_pacing": top_fmt["pacing"],
        "recommended_color_grade": top_fmt["color_grade"],
        "recommended_music_style": top_fmt["music_style"],
        "recommended_font_style": top_fmt["text_style"],
        "recommended_duration_sec": duration,
        "recommended_transitions": top_fmt["transitions"],
        "platform": platform,
        "data_type": "known_patterns",
        "twitch_insight": {
            "total_streams": len(_KNOWN_CS2_STREAMERS),
            "avg_viewers": avg_viewers,
            "top_streamer": _KNOWN_CS2_STREAMERS[0]["name"],
            "top_viewers": _KNOWN_CS2_STREAMERS[0]["viewers"],
        },
        "youtube_insight": {
            "total_videos": len(_KNOWN_YT_CHANNELS),
            "top_channel": _KNOWN_YT_CHANNELS[0]["channel"],
        },
        "format_analysis": {
            "top_format": top_fmt_name,
            "score": top_fmt["popularity_score"],
            "hook_type": top_fmt["hook_type"],
            "all_formats": {
                k: v["popularity_score"] for k, v in _KNOWN_FORMATS.items()
            },
        },
        "data_sources_used": ["known_patterns"],
        "freshness": datetime.utcnow().isoformat(),
    }


# ===================================================================
# SECTION 9: SELF-LEARNING ENGINE
# ===================================================================

def _load_learning_weights() -> dict:
    """Load persisted learning weights from disk."""
    try:
        if _LEARNING_WEIGHTS_FILE.exists():
            with open(_LEARNING_WEIGHTS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load learning weights: {e}")
    return {}


def _save_learning_weights(weights: dict):
    """Persist learning weights to disk."""
    try:
        with open(_LEARNING_WEIGHTS_FILE, "w") as f:
            json.dump(weights, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save learning weights: {e}")


def learn_from_feedback(
    format_used: str,
    hook_used: str,
    music_used: str,
    performance_score: float,
    views: int = 0,
    likes: int = 0,
    shares: int = 0,
    watch_time_pct: float = 0.0,
) -> dict:
    """Learn from reel performance. Updates weights for future recommendations."""
    weights = _load_learning_weights()
    if "format_weights" not in weights:
        weights["format_weights"] = {}
    if "hook_weights" not in weights:
        weights["hook_weights"] = {}
    if "music_weights" not in weights:
        weights["music_weights"] = {}
    if "history" not in weights:
        weights["history"] = []
    if "total_reels" not in weights:
        weights["total_reels"] = 0
    weights["total_reels"] += 1

    alpha = 0.3  # Learning rate
    normalized_score = performance_score / 10.0

    # Update format weight (exponential moving average)
    current_fmt = weights["format_weights"].get(format_used, 1.0)
    new_fmt = current_fmt * (1 - alpha) + normalized_score * alpha * 2
    weights["format_weights"][format_used] = round(
        max(0.1, min(3.0, new_fmt)), 4
    )

    # Update hook weight
    current_hook = weights["hook_weights"].get(hook_used, 1.0)
    new_hook = current_hook * (1 - alpha) + normalized_score * alpha * 2
    weights["hook_weights"][hook_used] = round(
        max(0.1, min(3.0, new_hook)), 4
    )

    # Update music weight
    current_music = weights["music_weights"].get(music_used, 1.0)
    new_music = current_music * (1 - alpha) + normalized_score * alpha * 2
    weights["music_weights"][music_used] = round(
        max(0.1, min(3.0, new_music)), 4
    )

    # Add to history (keep last 100)
    weights["history"].append({
        "format": format_used,
        "hook": hook_used,
        "music": music_used,
        "score": performance_score,
        "views": views,
        "likes": likes,
        "shares": shares,
        "watch_time_pct": watch_time_pct,
        "timestamp": datetime.utcnow().isoformat(),
    })
    weights["history"] = weights["history"][-100:]
    weights["last_updated"] = datetime.utcnow().isoformat()
    _save_learning_weights(weights)

    return {
        "status": "learned",
        "total_reels_learned": weights["total_reels"],
        "format_weight_updated": {
            format_used: weights["format_weights"][format_used]
        },
        "hook_weight_updated": {
            hook_used: weights["hook_weights"][hook_used]
        },
        "music_weight_updated": {
            music_used: weights["music_weights"][music_used]
        },
    }


def get_learning_insights() -> dict:
    """Return what the system has learned so far."""
    weights = _load_learning_weights()
    if not weights:
        return {
            "status": "no_data",
            "message": (
                "No learning data yet. "
                "System learns from reel performance feedback."
            ),
            "total_reels": 0,
        }
    fmt_weights = weights.get("format_weights", {})
    hook_weights = weights.get("hook_weights", {})
    music_weights = weights.get("music_weights", {})
    best_format = max(fmt_weights, key=fmt_weights.get) if fmt_weights else "none"
    best_hook = max(hook_weights, key=hook_weights.get) if hook_weights else "none"
    best_music = max(music_weights, key=music_weights.get) if music_weights else "none"
    worst_format = min(fmt_weights, key=fmt_weights.get) if fmt_weights else "none"
    history = weights.get("history", [])
    avg_score = sum(h["score"] for h in history) / max(len(history), 1)
    avg_views = sum(h.get("views", 0) for h in history) / max(len(history), 1)
    return {
        "status": "active",
        "total_reels_learned": weights.get("total_reels", 0),
        "best_format": {
            "name": best_format,
            "weight": fmt_weights.get(best_format, 0),
        },
        "worst_format": {
            "name": worst_format,
            "weight": fmt_weights.get(worst_format, 0),
        },
        "best_hook": {
            "name": best_hook,
            "weight": hook_weights.get(best_hook, 0),
        },
        "best_music": {
            "name": best_music,
            "weight": music_weights.get(best_music, 0),
        },
        "all_format_weights": fmt_weights,
        "all_hook_weights": hook_weights,
        "all_music_weights": music_weights,
        "avg_performance_score": round(avg_score, 2),
        "avg_views": round(avg_views),
        "total_history_entries": len(history),
        "last_updated": weights.get("last_updated", "never"),
    }


# ===================================================================
# SECTION 10: DB INTEGRATION (backwards compatible)
# ===================================================================

async def analyze_trends(db_session=None, platforms: list[str] | None = None, categories: list[str] | None = None) -> list[dict]:
    """Backwards-compatible function for database-aware trend analysis.
    Returns list of trend dicts compatible with the trends router."""
    result = await analyze_current_trends()
    trends_list: list[dict] = []
    recs = result.get("recommendations", {})
    fmt_analysis = result.get("format_analysis", {})
    for fmt_name, count in fmt_analysis.get("format_distribution", {}).items():
        fmt_template = _KNOWN_FORMATS.get(fmt_name, {})
        trends_list.append({
            "platform": "youtube",
            "trend_type": "format",
            "title": f"Trending: {fmt_name.replace('_', ' ').title()}",
            "description": f"Format '{fmt_name}' detected in {count} videos. "
                           f"Score: {fmt_analysis.get('format_scores', {}).get(fmt_name, 0)}",
            "score": fmt_analysis.get("format_scores", {}).get(fmt_name, 5.0),
            "metadata": {
                "format": fmt_name,
                "count": count,
                "music": fmt_template.get("music_style", "electronic"),
                "pacing": fmt_template.get("pacing", "medium"),
                "color_grade": fmt_template.get("color_grade", "vibrant"),
            },
            "source_url": None,
        })
    hook_analysis = fmt_analysis.get("hook_analysis", {})
    for hook_type, pct in hook_analysis.get("hook_distribution", {}).items():
        if pct > 5:
            trends_list.append({
                "platform": "multi",
                "trend_type": "hook",
                "title": f"Hook trend: {hook_type.replace('_', ' ').title()}",
                "description": f"{pct}% of analyzed titles use {hook_type} hooks",
                "score": pct / 10.0,
                "metadata": {"hook_type": hook_type, "percentage": pct},
                "source_url": None,
            })
    return trends_list


async def get_trend_recommendations(
    platform: str = "tiktok", db_session=None
) -> dict:
    """Backwards-compatible: get recommendations."""
    try:
        full_analysis = await analyze_current_trends()
        if full_analysis and full_analysis.get("recommendations"):
            recs = full_analysis["recommendations"]
            recs["platform"] = platform
            recs["data_type"] = "real_scraped"
            return recs
    except Exception as e:
        logger.warning(f"Failed to get fresh trends: {e}")
    return get_platform_design_hints(platform)


def get_viral_patterns() -> dict:
    """Return current viral patterns (backwards compatible with trends router)."""
    hints = get_platform_design_hints("tiktok")
    return {
        "top_format": hints.get("preferred_style", "highlight_react"),
        "top_hook": hints.get("recommended_hook", "text_hook"),
        "top_music": hints.get("recommended_music_style", "electronic"),
        "top_pacing": hints.get("recommended_pacing", "fast"),
        "top_color": hints.get("recommended_color_grade", "vibrant"),
        "recommended_duration": hints.get("recommended_duration_sec", 30),
        "data_type": hints.get("data_type", "known_patterns"),
        "all_formats": {
            k: {
                "popularity": v["popularity_score"],
                "music": v["music_style"],
                "pacing": v["pacing"],
                "hook": v["hook_type"],
            }
            for k, v in _KNOWN_FORMATS.items()
        },
    }


# ===================================================================
# SECTION 11: UTILITY FUNCTIONS
# ===================================================================

def get_cache_status() -> dict:
    """Return status of all caches."""
    status = {}
    for key in ["twitch_streams", "youtube_trending", "combined_insights"]:
        path = _CACHE_DIR / f"{key}.json"
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                cached_at = data.get("_cached_at", 0)
                age = time.time() - cached_at
                ttl = _CACHE_TTL.get(key, 600)
                status[key] = {
                    "exists": True,
                    "age_seconds": round(age),
                    "ttl_seconds": ttl,
                    "is_fresh": age < ttl,
                    "cached_at": (
                        datetime.fromtimestamp(cached_at).isoformat()
                        if cached_at
                        else "never"
                    ),
                }
            except Exception:
                status[key] = {"exists": True, "error": "corrupt"}
        else:
            status[key] = {"exists": False}
    return status


def clear_cache():
    """Clear all cached trend data."""
    for path in _CACHE_DIR.glob("*.json"):
        try:
            path.unlink()
        except Exception:
            pass
    logger.info("Trend cache cleared")


def get_available_formats() -> dict:
    """Return all known format templates."""
    return _KNOWN_FORMATS


def get_system_status() -> dict:
    """Return full system status."""
    weights = _load_learning_weights()
    return {
        "cache_status": get_cache_status(),
        "learning_status": {
            "has_weights": bool(weights),
            "total_reels": weights.get("total_reels", 0),
            "last_updated": weights.get("last_updated", "never"),
        },
        "known_streamers_count": len(_KNOWN_CS2_STREAMERS),
        "known_yt_channels_count": len(_KNOWN_YT_CHANNELS),
        "known_formats_count": len(_KNOWN_FORMATS),
        "env_keys": {
            "TWITCH_CLIENT_ID": bool(os.environ.get("TWITCH_CLIENT_ID")),
            "TWITCH_CLIENT_SECRET": bool(
                os.environ.get("TWITCH_CLIENT_SECRET")
            ),
            "TWITCH_ACCESS_TOKEN": bool(os.environ.get("TWITCH_ACCESS_TOKEN")),
            "YOUTUBE_API_KEY": bool(os.environ.get("YOUTUBE_API_KEY")),
        },
    }
