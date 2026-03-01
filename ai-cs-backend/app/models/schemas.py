from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ============ STREAMS ============

class StreamCreate(BaseModel):
    title: str
    platform: str = "twitch"
    url: Optional[str] = None
    streamer_name: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


class StreamResponse(BaseModel):
    id: int
    title: str
    platform: str
    url: Optional[str]
    streamer_name: str
    started_at: Optional[str]
    ended_at: Optional[str]
    status: str
    created_at: str


# ============ MOMENTS ============

class MomentCreate(BaseModel):
    stream_id: Optional[int] = None
    moment_type: str
    timestamp_start: float = 0
    timestamp_end: float = 0
    score: float = 0.0
    description: Optional[str] = None
    metadata: Optional[dict] = None


class MomentDetectRequest(BaseModel):
    stream_id: int
    sensitivity: float = Field(default=0.7, ge=0.0, le=1.0)
    moment_types: Optional[list[str]] = None


class MomentResponse(BaseModel):
    id: int
    stream_id: Optional[int]
    moment_type: str
    timestamp_start: float
    timestamp_end: float
    score: float
    description: Optional[str]
    metadata: dict
    status: str
    created_at: str


# ============ TEMPLATES ============

class TemplateCreate(BaseModel):
    name: str
    format_type: str
    description: Optional[str] = None
    config: Optional[dict] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    format_type: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None
    weight: Optional[float] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    format_type: str
    description: Optional[str]
    config: dict
    is_active: bool
    weight: float
    total_clips: int
    avg_retention: float
    avg_ctr: float
    created_at: str
    updated_at: str


# ============ CLIPS ============

class ClipCreate(BaseModel):
    moment_id: Optional[int] = None
    template_id: Optional[int] = None
    ab_test_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    format_type: str
    duration: float = 0.0
    hook_text: Optional[str] = None
    cta_text: Optional[str] = None
    has_ai_girl: bool = False
    has_subtitles: bool = False
    has_face_cam: bool = False
    platform: Optional[str] = None


class ClipUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    hook_text: Optional[str] = None
    cta_text: Optional[str] = None
    platform: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    ctr: Optional[float] = None
    retention_rate: Optional[float] = None
    watch_through_rate: Optional[float] = None
    published_at: Optional[str] = None


class ClipResponse(BaseModel):
    id: int
    moment_id: Optional[int]
    template_id: Optional[int]
    ab_test_id: Optional[int]
    title: str
    description: Optional[str]
    format_type: str
    duration: float
    status: str
    hook_text: Optional[str]
    cta_text: Optional[str]
    has_ai_girl: bool
    has_subtitles: bool
    has_face_cam: bool
    file_path: Optional[str]
    thumbnail_path: Optional[str]
    platform: Optional[str]
    published_at: Optional[str]
    views: int
    likes: int
    comments: int
    shares: int
    ctr: float
    retention_rate: float
    watch_through_rate: float
    created_at: str
    updated_at: str


# ============ A/B TESTS ============

class ABTestCreate(BaseModel):
    name: str
    moment_id: Optional[int] = None
    clip_ids: Optional[list[int]] = None


class ABTestResultSubmit(BaseModel):
    clip_id: int
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    ctr: float = 0.0
    retention_rate: float = 0.0
    watch_through_rate: float = 0.0


class ABTestResponse(BaseModel):
    id: int
    name: str
    moment_id: Optional[int]
    status: str
    winner_clip_id: Optional[int]
    started_at: str
    ended_at: Optional[str]
    created_at: str
    clips: list[ClipResponse] = []


# ============ TRENDS ============

class TrendCreate(BaseModel):
    platform: str
    trend_type: str
    title: str
    description: Optional[str] = None
    score: float = 0.0
    metadata: Optional[dict] = None
    source_url: Optional[str] = None


class TrendAnalyzeRequest(BaseModel):
    platforms: list[str] = ["youtube", "tiktok", "instagram"]
    categories: list[str] = ["cs2", "counter-strike"]


class TrendResponse(BaseModel):
    id: int
    platform: str
    trend_type: str
    title: str
    description: Optional[str]
    score: float
    metadata: dict
    source_url: Optional[str]
    detected_at: str
    expires_at: Optional[str]
    is_active: bool
    created_at: str


# ============ ANALYTICS ============

class AnalyticsOverview(BaseModel):
    total_clips: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    avg_retention: float = 0.0
    avg_ctr: float = 0.0
    avg_watch_through: float = 0.0
    active_ab_tests: int = 0
    active_trends: int = 0
    top_format: Optional[str] = None
    current_phase: int = 1
    clips_this_week: int = 0
    views_this_week: int = 0


class FormatPerformance(BaseModel):
    format_type: str
    total_clips: int = 0
    total_views: int = 0
    avg_ctr: float = 0.0
    avg_retention: float = 0.0
    avg_watch_through: float = 0.0
    avg_comments: float = 0.0
    score: float = 0.0
    trend: str = "stable"


# ============ AI GIRL ============

class AIGirlConfigResponse(BaseModel):
    id: int
    is_enabled: bool
    model_name: str
    voice_style: str
    appearance_style: str
    overlay_position: str
    overlay_size: float
    use_only_when_better: bool
    min_improvement_pct: float
    total_clips_with: int
    total_clips_without: int
    avg_retention_with: float
    avg_retention_without: float
    updated_at: str


class AIGirlConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    model_name: Optional[str] = None
    voice_style: Optional[str] = None
    appearance_style: Optional[str] = None
    overlay_position: Optional[str] = None
    overlay_size: Optional[float] = None
    use_only_when_better: Optional[bool] = None
    min_improvement_pct: Optional[float] = None


# ============ STRATEGY ============

class StrategyResponse(BaseModel):
    id: int
    current_phase: int
    phase_name: str
    started_at: str
    config: dict
    updated_at: str
    recommendations: list[str] = []


class StrategyPhaseUpdate(BaseModel):
    phase: int = Field(ge=1, le=5)


# ============ AI PROFILES ============

class AIProfileCreate(BaseModel):
    name: str
    style: str = "realistic"
    description: Optional[str] = None
    appearance_preset: str = "realistic_european"
    personality_preset: str = "energetic_gamer"
    voice_preset: str = "energetic_female"
    custom_appearance: Optional[dict] = None
    custom_personality: Optional[dict] = None
    custom_voice: Optional[dict] = None
    instagram_handle: Optional[str] = None


class AIProfileUpdate(BaseModel):
    name: Optional[str] = None
    style: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[dict] = None
    voice_config: Optional[dict] = None
    personality: Optional[dict] = None
    instagram_handle: Optional[str] = None
    is_active: Optional[bool] = None


class AIProfileResponse(BaseModel):
    id: int
    name: str
    style: str
    description: Optional[str]
    appearance: dict
    voice_config: dict
    personality: dict
    reference_images: list
    instagram_handle: Optional[str]
    total_posts: int
    total_videos: int
    is_active: bool
    created_at: str
    updated_at: str


# ============ GENERATION TASKS ============

class GenerationTaskCreate(BaseModel):
    profile_id: int
    task_type: str  # image, lip_sync_video, voice, full_video, instagram_post, private_content
    prompt: Optional[str] = None
    config: Optional[dict] = None


class GenerationTaskResponse(BaseModel):
    id: int
    profile_id: Optional[int]
    task_type: str
    prompt: Optional[str]
    config: dict
    status: str
    result: dict
    error: Optional[str]
    created_at: str
    completed_at: Optional[str]


# ============ TOOL REGISTRY ============

class ToolRegistryResponse(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str]
    github_url: Optional[str]
    github_stars: int
    license: Optional[str]
    min_vram_gb: float
    is_free: bool
    api_cost_per_use: float
    quality_score: float
    speed_score: float
    config: dict
    is_selected: bool
    created_at: str


class ToolSelectUpdate(BaseModel):
    is_selected: bool


# ============ ACCOUNTS ============

class AccountCreate(BaseModel):
    platform: str
    handle: str
    account_type: str = "streamer"  # streamer, ai_girl, highlights
    region: str = "global"
    language: str = "en"
    target_audience: Optional[dict] = None
    streamer_names: Optional[list[str]] = None


class AccountUpdate(BaseModel):
    handle: Optional[str] = None
    region: Optional[str] = None
    language: Optional[str] = None
    target_audience: Optional[dict] = None
    streamer_names: Optional[list[str]] = None
    status: Optional[str] = None
    total_posts: Optional[int] = None
    total_followers: Optional[int] = None


class AccountResponse(BaseModel):
    id: int
    platform: str
    handle: str
    account_type: str
    region: str
    language: str
    target_audience: dict
    streamer_names: list
    status: str
    total_posts: int
    total_followers: int
    created_at: str
    updated_at: str


# ============ REGION ANALYSIS ============

class RegionAnalysisResponse(BaseModel):
    id: int
    region: str
    platform: str
    audience_size: int
    competition_level: str
    avg_views_per_reel: int
    top_languages: list
    top_content_types: list
    growth_potential: float
    recommendation: Optional[str]
    analyzed_at: str


# ============ PIPELINE CONFIG ============

class PipelineConfigResponse(BaseModel):
    budget: str
    total_monthly_cost: str
    setup: str
    image: dict
    lip_sync: dict
    voice: dict
    video: dict
    orchestration: str
