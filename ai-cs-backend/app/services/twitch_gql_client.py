"""
Twitch GQL Client — Robust, circuit-breaker protected access to Twitch data.

Uses Twitch's public GraphQL API (no auth token needed) to:
1. Get top CS2 clips (by game, by period)
2. Get clips from specific streamers
3. Get live CS2 streams
4. Get VODs from streamers

PROTECTION LAYERS:
- Circuit breaker: after N consecutive failures, stops calling API and raises HARD error
- Health check endpoint: /api/pipeline/twitch-health reports exact status
- Auto-retry with exponential backoff
- Request timeout protection
- Response validation (schema checks)
- Freshness tracking: every response tagged with fetch timestamp
- BLOCKING flag: if GQL is down, pipeline REFUSES to continue (no silent fallback)

If this module fails, the entire pipeline STOPS and shows a clear error.
No silent fallbacks. No stale data passed as fresh.
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("twitch_gql")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GQL_ENDPOINT = "https://gql.twitch.tv/gql"
# This is the public Twitch web Client-ID used by the Twitch website itself
TWITCH_PUBLIC_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
CS2_GAME_ID = "32399"  # Counter-Strike on Twitch (covers CS2/CSGO)
CS2_GAME_SLUG = "counter-strike"

# Circuit breaker settings
MAX_CONSECUTIVE_FAILURES = 5
CIRCUIT_RESET_SECONDS = 300  # 5 min cooldown after circuit opens
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds

# Cache settings
CACHE_DIR = Path("/tmp/twitch_gql_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_TTL = {
    "game_clips": 300,      # 5 min — clips change often
    "user_clips": 300,      # 5 min
    "live_streams": 120,    # 2 min — streams change fast
    "user_vods": 600,       # 10 min — VODs don't change often
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CIRCUIT BREAKER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failed too many times, blocking all requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker pattern for Twitch GQL API protection."""
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    last_error: str = ""
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    opened_at: float = 0.0

    def record_success(self):
        self.consecutive_failures = 0
        self.last_success_time = time.time()
        self.total_successes += 1
        self.total_requests += 1
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker CLOSED (service recovered)")
            self.state = CircuitState.CLOSED

    def record_failure(self, error: str):
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        self.last_error = error
        self.total_failures += 1
        self.total_requests += 1

        if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            if self.state != CircuitState.OPEN:
                logger.error(
                    "CIRCUIT BREAKER OPEN — Twitch GQL failed %d times in a row. "
                    "Last error: %s. Pipeline will BLOCK until resolved.",
                    self.consecutive_failures, error
                )
                self.state = CircuitState.OPEN
                self.opened_at = time.time()

    def can_request(self) -> tuple[bool, str]:
        """Check if we can make a request. Returns (allowed, reason)."""
        if self.state == CircuitState.CLOSED:
            return True, "ok"

        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.opened_at
            if elapsed > CIRCUIT_RESET_SECONDS:
                logger.info("Circuit breaker HALF_OPEN — testing if Twitch GQL recovered...")
                self.state = CircuitState.HALF_OPEN
                return True, "half_open_test"
            remaining = int(CIRCUIT_RESET_SECONDS - elapsed)
            return False, (
                f"TWITCH GQL ЗАБЛОКИРОВАН — {self.consecutive_failures} ошибок подряд. "
                f"Последняя: {self.last_error}. "
                f"Повтор через {remaining}с. "
                f"Пайплайн остановлен до восстановления."
            )

        # HALF_OPEN — allow one test request
        return True, "half_open_test"

    def get_status(self) -> dict:
        """Get full circuit breaker status for health check."""
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_time": (
                datetime.fromtimestamp(self.last_failure_time, tz=timezone.utc).isoformat()
                if self.last_failure_time > 0 else None
            ),
            "last_success_time": (
                datetime.fromtimestamp(self.last_success_time, tz=timezone.utc).isoformat()
                if self.last_success_time > 0 else None
            ),
            "last_error": self.last_error or None,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "is_blocking": self.state == CircuitState.OPEN,
            "blocking_reason": (
                f"Twitch GQL упал {self.consecutive_failures} раз подряд. "
                f"Ошибка: {self.last_error}"
                if self.state == CircuitState.OPEN else None
            ),
        }


# Global circuit breaker instance
_circuit = CircuitBreaker()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CACHE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cache_get(key: str) -> Optional[dict]:
    """Read from disk cache if fresh."""
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        cached_at = data.get("_cached_at", 0)
        ttl = 300
        for prefix, ttl_val in CACHE_TTL.items():
            if key.startswith(prefix):
                ttl = ttl_val
                break
        if time.time() - cached_at > ttl:
            return None
        return data
    except Exception:
        return None


def _cache_set(key: str, data: dict):
    """Write to disk cache."""
    try:
        data["_cached_at"] = time.time()
        data["_fetched_at_human"] = datetime.now(timezone.utc).isoformat()
        path = CACHE_DIR / f"{key}.json"
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Cache write failed for %s: %s", key, e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOW-LEVEL GQL REQUEST (with circuit breaker + retry)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TwitchGQLError(Exception):
    """Raised when Twitch GQL is unavailable and pipeline must stop."""
    pass


class TwitchGQLStaleDataError(Exception):
    """Raised when only stale data is available."""
    pass


async def _gql_request(query: str, operation_name: str = "custom") -> dict:
    """Execute a GQL query with circuit breaker protection.

    Raises TwitchGQLError if circuit is open (pipeline must stop).
    Returns parsed JSON response data.
    """
    # Check circuit breaker
    allowed, reason = _circuit.can_request()
    if not allowed:
        raise TwitchGQLError(reason)

    headers = {
        "Client-ID": TWITCH_PUBLIC_CLIENT_ID,
        "Content-Type": "application/json",
    }

    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    GQL_ENDPOINT,
                    headers=headers,
                    json={"query": query},
                )

                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(
                        "Twitch GQL attempt %d/%d failed: %s",
                        attempt, MAX_RETRIES, last_error
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
                    continue

                data = resp.json()

                # Check for GQL errors
                if "errors" in data and not data.get("data"):
                    last_error = f"GQL errors: {data['errors']}"
                    logger.warning(
                        "Twitch GQL attempt %d/%d returned errors: %s",
                        attempt, MAX_RETRIES, last_error
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
                    continue

                # Success!
                _circuit.record_success()
                return data.get("data", {})

        except httpx.TimeoutException:
            last_error = f"Timeout ({REQUEST_TIMEOUT_SECONDS}s)"
            logger.warning("Twitch GQL attempt %d/%d timed out", attempt, MAX_RETRIES)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
        except httpx.ConnectError as e:
            last_error = f"Connection error: {e}"
            logger.warning("Twitch GQL attempt %d/%d connection error: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
        except Exception as e:
            last_error = f"Unexpected: {e}"
            logger.warning("Twitch GQL attempt %d/%d unexpected error: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)

    # All retries exhausted
    _circuit.record_failure(last_error)
    raise TwitchGQLError(
        f"Twitch GQL недоступен после {MAX_RETRIES} попыток. "
        f"Ошибка: {last_error}. "
        f"Пайплайн остановлен."
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HIGH-LEVEL API: Get CS2 Top Clips
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_cs2_top_clips(
    period: str = "LAST_WEEK",
    limit: int = 20,
    use_cache: bool = True,
) -> dict:
    """Get top CS2 clips from Twitch.

    Args:
        period: LAST_DAY, LAST_WEEK, LAST_MONTH, ALL_TIME
        limit: max clips to return (1-25)

    Returns:
        {
            "clips": [...],
            "fetched_at": "ISO timestamp",
            "source": "twitch_gql",
            "is_fresh": True/False,
            "cache_age_seconds": int
        }

    Raises TwitchGQLError if service is down and no cache available.
    """
    cache_key = f"game_clips_{period}_{limit}"

    if use_cache:
        cached = _cache_get(cache_key)
        if cached and cached.get("clips"):
            cached["is_fresh"] = True
            cached["cache_age_seconds"] = int(time.time() - cached.get("_cached_at", 0))
            return cached

    query = f"""{{
        game(id: "{CS2_GAME_ID}") {{
            name
            clips(criteria: {{ period: {period} }}, first: {min(limit, 25)}) {{
                edges {{
                    node {{
                        id
                        slug
                        title
                        viewCount
                        createdAt
                        durationSeconds
                        url
                        thumbnailURL
                        broadcaster {{
                            login
                            displayName
                        }}
                    }}
                }}
            }}
        }}
    }}"""

    try:
        data = await _gql_request(query, "CS2TopClips")
    except TwitchGQLError:
        # Try stale cache as last resort but mark it
        stale = _cache_get_stale(cache_key)
        if stale and stale.get("clips"):
            stale["is_fresh"] = False
            stale["warning"] = "STALE DATA — Twitch GQL недоступен, используются устаревшие данные"
            stale["cache_age_seconds"] = int(time.time() - stale.get("_cached_at", 0))
            logger.warning("Using stale cache for %s (age: %ds)", cache_key, stale["cache_age_seconds"])
            return stale
        raise

    game = data.get("game")
    if not game:
        raise TwitchGQLError(
            "Twitch GQL вернул пустой ответ для CS2 (game=null). "
            "Возможно изменилась схема API. Пайплайн остановлен."
        )

    clips = []
    edges = game.get("clips", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        broadcaster = node.get("broadcaster", {})
        clips.append({
            "clip_id": node.get("id", ""),
            "slug": node.get("slug", ""),
            "title": node.get("title", ""),
            "view_count": node.get("viewCount", 0),
            "created_at": node.get("createdAt", ""),
            "duration_seconds": node.get("durationSeconds", 0),
            "url": f"https://clips.twitch.tv/{node.get('slug', '')}",
            "thumbnail_url": node.get("thumbnailURL", ""),
            "broadcaster_login": broadcaster.get("login", ""),
            "broadcaster_name": broadcaster.get("displayName", ""),
            "source": "twitch_gql",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })

    if not clips:
        logger.warning("Twitch GQL returned 0 CS2 clips for period=%s", period)

    result = {
        "clips": clips,
        "total": len(clips),
        "period": period,
        "source": "twitch_gql",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "is_fresh": True,
        "cache_age_seconds": 0,
    }

    _cache_set(cache_key, result)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HIGH-LEVEL API: Get Streamer Clips
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_streamer_clips(
    login: str,
    period: str = "LAST_WEEK",
    limit: int = 10,
    use_cache: bool = True,
) -> dict:
    """Get clips from a specific Twitch streamer.

    Returns same format as get_cs2_top_clips().
    Raises TwitchGQLError if service down.
    """
    # Sanitize login to prevent GQL injection (Twitch usernames: alphanumeric + underscores)
    login = re.sub(r'[^a-zA-Z0-9_]', '', login)
    if not login:
        return {"clips": [], "total": 0, "streamer": login, "error": "Invalid login"}

    cache_key = f"user_clips_{login}_{period}_{limit}"

    if use_cache:
        cached = _cache_get(cache_key)
        if cached and cached.get("clips"):
            cached["is_fresh"] = True
            cached["cache_age_seconds"] = int(time.time() - cached.get("_cached_at", 0))
            return cached

    query = f"""{{
        user(login: "{login}") {{
            login
            displayName
            clips(criteria: {{ period: {period} }}, first: {min(limit, 25)}) {{
                edges {{
                    node {{
                        id
                        slug
                        title
                        viewCount
                        createdAt
                        durationSeconds
                        url
                        thumbnailURL
                    }}
                }}
            }}
        }}
    }}"""

    try:
        data = await _gql_request(query, "StreamerClips")
    except TwitchGQLError:
        stale = _cache_get_stale(cache_key)
        if stale and stale.get("clips"):
            stale["is_fresh"] = False
            stale["warning"] = "STALE DATA"
            stale["cache_age_seconds"] = int(time.time() - stale.get("_cached_at", 0))
            return stale
        raise

    user = data.get("user")
    if not user:
        return {
            "clips": [],
            "total": 0,
            "streamer": login,
            "source": "twitch_gql",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "is_fresh": True,
            "warning": f"Стример '{login}' не найден на Twitch",
        }

    clips = []
    edges = user.get("clips", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        clips.append({
            "clip_id": node.get("id", ""),
            "slug": node.get("slug", ""),
            "title": node.get("title", ""),
            "view_count": node.get("viewCount", 0),
            "created_at": node.get("createdAt", ""),
            "duration_seconds": node.get("durationSeconds", 0),
            "url": f"https://clips.twitch.tv/{node.get('slug', '')}",
            "thumbnail_url": node.get("thumbnailURL", ""),
            "broadcaster_login": login,
            "broadcaster_name": user.get("displayName", login),
            "source": "twitch_gql",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })

    result = {
        "clips": clips,
        "total": len(clips),
        "streamer": login,
        "period": period,
        "source": "twitch_gql",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "is_fresh": True,
        "cache_age_seconds": 0,
    }

    _cache_set(cache_key, result)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HIGH-LEVEL API: Get Live CS2 Streams
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_cs2_live_streams(limit: int = 20, use_cache: bool = True) -> dict:
    """Get currently live CS2 streams from Twitch.

    Returns:
        {
            "streams": [...],
            "fetched_at": "ISO",
            "source": "twitch_gql",
            "is_fresh": True/False
        }
    """
    cache_key = f"live_streams_{limit}"

    if use_cache:
        cached = _cache_get(cache_key)
        if cached and cached.get("streams"):
            cached["is_fresh"] = True
            cached["cache_age_seconds"] = int(time.time() - cached.get("_cached_at", 0))
            return cached

    query = f"""{{
        game(id: "{CS2_GAME_ID}") {{
            name
            streams(first: {min(limit, 30)}) {{
                edges {{
                    node {{
                        broadcaster {{
                            login
                            displayName
                        }}
                        viewersCount
                        title
                    }}
                }}
            }}
        }}
    }}"""

    try:
        data = await _gql_request(query, "CS2LiveStreams")
    except TwitchGQLError:
        stale = _cache_get_stale(cache_key)
        if stale and stale.get("streams"):
            stale["is_fresh"] = False
            stale["warning"] = "STALE DATA"
            stale["cache_age_seconds"] = int(time.time() - stale.get("_cached_at", 0))
            return stale
        raise

    game = data.get("game")
    if not game:
        raise TwitchGQLError(
            "Twitch GQL вернул game=null для CS2 стримов. "
            "Возможно изменилась схема. Пайплайн остановлен."
        )

    streams = []
    edges = game.get("streams", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        broadcaster = node.get("broadcaster", {})
        streams.append({
            "login": broadcaster.get("login", ""),
            "display_name": broadcaster.get("displayName", ""),
            "viewers": node.get("viewersCount", 0),
            "title": node.get("title", ""),
            "source": "twitch_gql",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })

    result = {
        "streams": streams,
        "total": len(streams),
        "source": "twitch_gql",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "is_fresh": True,
        "cache_age_seconds": 0,
    }

    _cache_set(cache_key, result)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STALE CACHE READER (for emergency fallback, always marked as STALE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cache_get_stale(key: str) -> Optional[dict]:
    """Read cache even if expired (for emergency fallback only).
    Always marks data as stale. Max staleness: 1 hour.
    """
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        cached_at = data.get("_cached_at", 0)
        age = time.time() - cached_at
        if age > 3600:  # Too stale even for emergency (>1 hour)
            return None
        data["_stale"] = True
        data["_stale_age_seconds"] = int(age)
        return data
    except Exception:
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEALTH CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def health_check() -> dict:
    """Full health check of Twitch GQL service.

    Tests actual API connectivity + returns circuit breaker status.
    This is what /api/pipeline/twitch-health calls.
    """
    circuit_status = _circuit.get_status()

    # Test actual connectivity
    test_result = {
        "reachable": False,
        "response_time_ms": 0,
        "error": None,
        "cs2_game_found": False,
        "sample_clips_count": 0,
        "sample_streams_count": 0,
    }

    start = time.time()
    try:
        # Quick test query
        data = await _gql_request(
            f'{{ game(id: "{CS2_GAME_ID}") {{ name clips(criteria: {{ period: LAST_WEEK }}, first: 3) {{ edges {{ node {{ title viewCount }} }} }} }} }}',
            "HealthCheck"
        )
        elapsed_ms = int((time.time() - start) * 1000)
        test_result["reachable"] = True
        test_result["response_time_ms"] = elapsed_ms

        game = data.get("game")
        if game:
            test_result["cs2_game_found"] = True
            clips = game.get("clips", {}).get("edges", [])
            test_result["sample_clips_count"] = len(clips)
            if clips:
                test_result["newest_clip"] = {
                    "title": clips[0]["node"]["title"],
                    "views": clips[0]["node"]["viewCount"],
                }

    except TwitchGQLError as e:
        test_result["error"] = str(e)
        test_result["response_time_ms"] = int((time.time() - start) * 1000)

    # Check cache freshness
    cache_status = {}
    for key_prefix in ["game_clips", "user_clips", "live_streams"]:
        cache_files = list(CACHE_DIR.glob(f"{key_prefix}*.json"))
        if cache_files:
            newest = max(cache_files, key=lambda p: p.stat().st_mtime)
            try:
                with open(newest) as f:
                    d = json.load(f)
                age = int(time.time() - d.get("_cached_at", 0))
                cache_status[key_prefix] = {
                    "exists": True,
                    "age_seconds": age,
                    "is_fresh": age < CACHE_TTL.get(key_prefix, 300),
                    "fetched_at": d.get("_fetched_at_human"),
                }
            except Exception:
                cache_status[key_prefix] = {"exists": True, "error": "read_failed"}
        else:
            cache_status[key_prefix] = {"exists": False}

    # Overall verdict
    is_operational = test_result["reachable"] and test_result["cs2_game_found"]
    is_blocking = circuit_status["is_blocking"]

    return {
        "status": "operational" if is_operational else ("blocked" if is_blocking else "degraded"),
        "operational": is_operational,
        "blocking_pipeline": is_blocking,
        "message": (
            "Twitch GQL работает нормально"
            if is_operational
            else (
                circuit_status["blocking_reason"]
                if is_blocking
                else f"Twitch GQL деградирован: {test_result.get('error', 'unknown')}"
            )
        ),
        "circuit_breaker": circuit_status,
        "connectivity_test": test_result,
        "cache": cache_status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PIPELINE GATE: Verify data freshness before proceeding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def verify_data_freshness() -> dict:
    """Verify that we have fresh Twitch data before allowing pipeline to proceed.

    Returns:
        {
            "can_proceed": True/False,
            "reason": "...",
            "clips_available": int,
            "data_age_seconds": int
        }

    If can_proceed is False, the pipeline MUST stop and show the reason.
    """
    try:
        result = await get_cs2_top_clips(period="LAST_WEEK", limit=5, use_cache=True)
    except TwitchGQLError as e:
        return {
            "can_proceed": False,
            "reason": str(e),
            "clips_available": 0,
            "data_age_seconds": None,
            "error_type": "gql_unavailable",
        }

    clips = result.get("clips", [])
    is_fresh = result.get("is_fresh", False)
    age = result.get("cache_age_seconds", 0)

    if not clips:
        return {
            "can_proceed": False,
            "reason": "Twitch GQL вернул 0 клипов CS2. Нет данных для работы.",
            "clips_available": 0,
            "data_age_seconds": age,
            "error_type": "no_clips",
        }

    if not is_fresh and age > 1800:  # >30 min stale
        return {
            "can_proceed": False,
            "reason": f"Данные устарели на {age}с (>{1800}с максимум). Нужно обновление.",
            "clips_available": len(clips),
            "data_age_seconds": age,
            "error_type": "stale_data",
        }

    return {
        "can_proceed": True,
        "reason": "OK — свежие данные доступны",
        "clips_available": len(clips),
        "data_age_seconds": age,
        "is_fresh": is_fresh,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UTILITY: Reset circuit breaker (manual override)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def reset_circuit_breaker():
    """Manually reset the circuit breaker (for admin use)."""
    global _circuit
    logger.info("Circuit breaker manually reset")
    _circuit = CircuitBreaker()


def get_circuit_state() -> str:
    """Get current circuit breaker state."""
    return _circuit.state.value
