const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`Ошибка API: ${res.status}`);
  return res.json();
}

export const api = {
  // Analytics
  getOverview: () => apiFetch<AnalyticsOverview>("/api/analytics/overview"),
  getFormatPerformance: () => apiFetch<FormatPerformance[]>("/api/analytics/formats"),
  getGrowthPhase: () => apiFetch<GrowthPhase>("/api/analytics/growth-phase"),
  getRecommendations: () => apiFetch<{ recommendations: string[] }>("/api/analytics/recommendations"),
  adaptWeights: () => apiFetch<AdaptResult>("/api/analytics/adapt-weights", { method: "POST" }),
  updateGrowthPhase: (phase: number) =>
    apiFetch("/api/analytics/growth-phase", { method: "PUT", body: JSON.stringify({ phase }) }),

  // Clips
  getClips: (params?: string) => apiFetch<Clip[]>(`/api/clips${params ? `?${params}` : ""}`),
  createClip: (data: Partial<Clip>) =>
    apiFetch<Clip>("/api/clips", { method: "POST", body: JSON.stringify(data) }),
  deleteClip: (id: number) => apiFetch(`/api/clips/${id}`, { method: "DELETE" }),

  // Streams
  getStreams: () => apiFetch<Stream[]>("/api/streams"),
  createStream: (data: Partial<Stream>) =>
    apiFetch<Stream>("/api/streams", { method: "POST", body: JSON.stringify(data) }),

  // Twitch Streamers & Clipping
  getTwitchStreamers: () => apiFetch<TwitchStreamersResponse>("/api/streams/twitch/top-streamers"),
  getClippingPipeline: () => apiFetch<ClippingPipeline>("/api/streams/twitch/clipping-pipeline"),
  getStreamerStats: () => apiFetch<StreamerStatsResponse>("/api/streams/twitch/streamer-stats"),

  // Moments
  getMoments: (params?: string) => apiFetch<Moment[]>(`/api/moments${params ? `?${params}` : ""}`),
  detectMoments: (streamId: number) =>
    apiFetch<DetectResult>("/api/moments/detect", {
      method: "POST",
      body: JSON.stringify({ stream_id: streamId, sensitivity: 0.7 }),
    }),

  // Templates
  getTemplates: () => apiFetch<Template[]>("/api/templates"),
  updateTemplate: (id: number, data: Partial<Template>) =>
    apiFetch<Template>(`/api/templates/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  // A/B Tests
  getABTests: () => apiFetch<ABTest[]>("/api/ab-tests"),
  createABTest: (data: { name: string; moment_id: number }) =>
    apiFetch("/api/ab-tests", { method: "POST", body: JSON.stringify(data) }),
  submitABResult: (testId: number, data: ABResultSubmit) =>
    apiFetch(`/api/ab-tests/${testId}/results`, { method: "POST", body: JSON.stringify(data) }),

  // Trends
  getTrends: (platform?: string) =>
    apiFetch<Trend[]>(`/api/trends${platform ? `?platform=${platform}` : ""}`),
  analyzeTrends: () =>
    apiFetch("/api/trends/analyze", {
      method: "POST",
      body: JSON.stringify({ platforms: ["youtube", "tiktok", "instagram"], categories: ["cs2"] }),
    }),

  // AI Girl
  getAIGirlConfig: () => apiFetch<AIGirlConfig>("/api/ai-girl/config"),
  updateAIGirlConfig: (data: Partial<AIGirlConfig>) =>
    apiFetch<AIGirlConfig>("/api/ai-girl/config", { method: "PUT", body: JSON.stringify(data) }),

  // AI Profiles
  getProfiles: () => apiFetch<AIProfile[]>("/api/ai-profiles/"),
  getProfilePresets: () => apiFetch<ProfilePresets>("/api/ai-profiles/presets"),
  createProfile: (data: CreateProfileData) =>
    apiFetch<AIProfile>("/api/ai-profiles/", { method: "POST", body: JSON.stringify(data) }),
  updateProfile: (id: number, data: Partial<AIProfile>) =>
    apiFetch<AIProfile>(`/api/ai-profiles/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  getProfilePipeline: (id: number) => apiFetch<ProfilePipeline>(`/api/ai-profiles/${id}/pipeline`),
  generatePrompt: (id: number, contentType: string) =>
    apiFetch<{ prompt: string }>(`/api/ai-profiles/${id}/generate-prompt?content_type=${contentType}`, { method: "POST" }),
  generateScript: (id: number, momentType: string) =>
    apiFetch<{ script: string }>(`/api/ai-profiles/${id}/generate-script?moment_type=${momentType}`, { method: "POST" }),
  deleteProfile: (id: number) => apiFetch(`/api/ai-profiles/${id}`, { method: "DELETE" }),

  // AI Profile Generation
  generateProfileVoice: (id: number, data: GenerateVoiceReq) =>
    apiFetch<VoiceGenResult>(`/api/ai-profiles/${id}/generate-voice`, { method: "POST", body: JSON.stringify(data) }),
  previewScript: (id: number, data: GenerateVoiceReq) =>
    apiFetch<ScriptPreview>(`/api/ai-profiles/${id}/preview-script`, { method: "POST", body: JSON.stringify(data) }),
  getVoiceSamples: (id: number) => apiFetch<VoiceSample[]>(`/api/ai-profiles/${id}/voice-samples`),
  generateProfilePhoto: (id: number, data: GenPhotoReq) =>
    apiFetch<PhotoResult>(`/api/ai-profiles/${id}/generate-photo`, { method: "POST", body: JSON.stringify(data) }),
  generateProfileVideo: (id: number, data: GenVideoReq) =>
    apiFetch<VideoGenResult>(`/api/ai-profiles/${id}/generate-video`, { method: "POST", body: JSON.stringify(data) }),
  getProfileContent: (id: number, type?: string) =>
    apiFetch<ContentItem[]>(`/api/ai-profiles/${id}/content${type ? `?content_type=${type}` : ""}`),
  getProfileCosts: (id: number) => apiFetch<CostBreakdown>(`/api/ai-profiles/${id}/costs`),
  schedulePost: (id: number, data: SchedulePostReq) =>
    apiFetch<{ success: boolean }>(`/api/ai-profiles/${id}/schedule-post`, { method: "POST", body: JSON.stringify(data) }),
  getSocialPosts: (id: number, platform?: string) =>
    apiFetch<SocialPost[]>(`/api/ai-profiles/${id}/social-posts${platform ? `?platform=${platform}` : ""}`),
  getProfileMemory: (id: number) => apiFetch<MemoryData>(`/api/ai-profiles/${id}/memory`),
  updateProfileMemory: (id: number, data: UpdateMemoryReq) =>
    apiFetch<{ success: boolean; memory: Record<string, unknown> }>(`/api/ai-profiles/${id}/memory`, { method: "PUT", body: JSON.stringify(data) }),
  getElevenLabsVoices: () => apiFetch<{ success: boolean; voices: ElevenLabsVoice[]; total: number }>("/api/ai-profiles/elevenlabs-voices"),
  setElevenLabsKey: (api_key: string) =>
    apiFetch<{ success: boolean }>("/api/ai-profiles/set-elevenlabs-key", { method: "POST", body: JSON.stringify({ api_key }) }),

  // Profile Gallery (cloud URLs, no local storage)
  getProfileGallery: (id: number, contentType?: string) =>
    apiFetch<ProfileGalleryResponse>(`/api/ai-profiles/${id}/gallery${contentType ? `?content_type=${contentType}` : ""}`),
  approveGalleryPhoto: (profileId: number, photoId: number, opts: { set_as_reference?: boolean; is_favorite?: boolean; quality_rating?: number }) =>
    apiFetch<{ success: boolean }>(`/api/ai-profiles/${profileId}/gallery/${photoId}/approve?set_as_reference=${opts.set_as_reference || false}&is_favorite=${opts.is_favorite || false}${opts.quality_rating ? `&quality_rating=${opts.quality_rating}` : ""}`, { method: "POST" }),
  deleteGalleryPhoto: (profileId: number, photoId: number) =>
    apiFetch<{ success: boolean }>(`/api/ai-profiles/${profileId}/gallery/${photoId}`, { method: "DELETE" }),

  // Voice Identity (unique voice per girl)
  getVoiceIdentity: (id: number) => apiFetch<VoiceIdentity>(`/api/ai-profiles/${id}/voice-identity`),
  updateVoiceIdentity: (id: number, data: Partial<VoiceIdentityUpdate>) =>
    apiFetch<{ success: boolean }>(`/api/ai-profiles/${id}/voice-identity?${new URLSearchParams(Object.entries(data).filter(([,v]) => v !== undefined).map(([k,v]) => [k, Array.isArray(v) ? JSON.stringify(v) : String(v)])).toString()}`, { method: "PUT" }),

  // Prompt Learning / Auto-improvement
  getProfileLearning: (id: number) => apiFetch<ProfileLearningResponse>(`/api/ai-profiles/${id}/learning`),

  // Tool Registry
  getTools: (category?: string) =>
    apiFetch<Tool[]>(`/api/tools/${category ? `?category=${category}` : ""}`),
  getToolCategories: () => apiFetch<ToolCategory[]>("/api/tools/categories"),
  toggleToolSelection: (id: number, selected: boolean) =>
    apiFetch<Tool>(`/api/tools/${id}/select`, { method: "PUT", body: JSON.stringify({ is_selected: selected }) }),
  getPipelineConfig: (budget: string) => apiFetch<PipelineConfig>(`/api/tools/pipeline/${budget}`),
  compareBudgets: () => apiFetch<Record<string, PipelineConfig>>("/api/tools/comparison"),

  // Accounts & Regions
  getAccounts: () => apiFetch<Account[]>("/api/accounts/"),
  createAccount: (data: CreateAccountData) =>
    apiFetch<Account>("/api/accounts/", { method: "POST", body: JSON.stringify(data) }),
  deleteAccount: (id: number) => apiFetch(`/api/accounts/${id}`, { method: "DELETE" }),
  getRegions: (platform?: string) =>
    apiFetch<RegionAnalysis[]>(`/api/accounts/regions${platform ? `?platform=${platform}` : ""}`),
  getRegionRecommendations: () => apiFetch<RegionRecommendations>("/api/accounts/regions/recommendations"),
  getStrategy: () => apiFetch<AccountStrategy>("/api/accounts/strategy"),

  // Generation
  getGenerationStatus: () => apiFetch<GenerationStatus>("/api/generate/status"),
  getVoices: () => apiFetch<VoiceList>("/api/generate/voices"),
  getPhotoPresets: () => apiFetch<PhotoPresets>("/api/generate/photo-presets"),
  generateTTS: (data: TTSRequest) =>
    apiFetch<TTSResult>("/api/generate/tts", { method: "POST", body: JSON.stringify(data) }),
  generatePhoto: (data: PhotoGenRequest) =>
    apiFetch<LegacyPhotoResult>("/api/generate/photo", { method: "POST", body: JSON.stringify(data) }),
  generatePhotoFace: (data: FacePhotoRequest) =>
    apiFetch<LegacyPhotoResult>("/api/generate/photo-face", { method: "POST", body: JSON.stringify(data) }),
  generateLipsync: (data: LipsyncRequest) =>
    apiFetch<LipsyncResult>("/api/generate/lipsync", { method: "POST", body: JSON.stringify(data) }),
  runFullPipeline: (data: FullPipelineRequest) =>
    apiFetch<PipelineResult>("/api/generate/full-pipeline", { method: "POST", body: JSON.stringify(data) }),
  getGallery: () => apiFetch<Gallery>("/api/generate/gallery"),
  setFalKey: (fal_key: string) =>
    apiFetch("/api/generate/set-api-key", { method: "POST", body: JSON.stringify({ fal_key }) }),

  // Seed
  seedData: () => apiFetch("/api/seed-demo-data", { method: "POST" }),

  // Montage Engine
  getMontageStatus: () => apiFetch<MontageStatus>("/api/montage/status"),
  getMontageTemplates: () => apiFetch<Record<string, MontageTemplate>>("/api/montage/templates"),
  getMontageSfxLibrary: () => apiFetch<Record<string, MontageSfxItem>>("/api/montage/sfx-library"),
  getMontageMusicLibrary: () => apiFetch<Record<string, MontageMusicItem>>("/api/montage/music-library"),
  getMontageGirlConfig: () => apiFetch<MontageGirlConfig>("/api/montage/girl-config"),
  createMontage: (data: CreateMontageRequest) =>
    apiFetch<MontageResult>("/api/montage/create", { method: "POST", body: JSON.stringify(data) }),
  generateMontageSfx: (sfx_id: string) =>
    apiFetch<{ success: boolean; sfx_id: string; file_path: string }>("/api/montage/generate-sfx", { method: "POST", body: JSON.stringify({ sfx_id }) }),
  generateMontageMusic: (track_id: string, duration: number) =>
    apiFetch<{ success: boolean; track_id: string; file_path: string }>("/api/montage/generate-music", { method: "POST", body: JSON.stringify({ track_id, duration }) }),
  generateMontageGirlAudio: (text: string, voice: string) =>
    apiFetch<MontageGirlAudioResult>("/api/montage/generate-girl-audio", { method: "POST", body: JSON.stringify({ text, voice }) }),
  previewMontageAssets: (template_id: string, duration: number) =>
    apiFetch<{ success: boolean; assets: Record<string, unknown> }>("/api/montage/preview-assets", { method: "POST", body: JSON.stringify({ template_id, duration }) }),
  getMontageClips: () => apiFetch<{ clips: MontageClipFile[]; total: number }>("/api/montage/clips"),

  // Clip Executor
  getExecutorStatus: () => apiFetch<ClipExecutorStatus>("/api/clip-executor/status"),
  setTwitchCredentials: (client_id: string, client_secret: string) =>
    apiFetch("/api/clip-executor/set-twitch-credentials", { method: "POST", body: JSON.stringify({ client_id, client_secret }) }),
  discoverClips: (broadcaster_name: string, period?: string, limit?: number) =>
    apiFetch<DiscoverClipsResult>("/api/clip-executor/discover-clips", { method: "POST", body: JSON.stringify({ broadcaster_name, period: period || "24h", limit: limit || 20 }) }),
  downloadClip: (url: string) =>
    apiFetch<DownloadResult>("/api/clip-executor/download", { method: "POST", body: JSON.stringify({ url }) }),
  processClip: (data: ProcessClipRequest) =>
    apiFetch<ProcessClipResult>("/api/clip-executor/process", { method: "POST", body: JSON.stringify(data) }),
  generateTestClip: (data: TestClipRequest) =>
    apiFetch<TestClipResult>("/api/clip-executor/test-clip", { method: "POST", body: JSON.stringify(data) }),
  executeFromMoment: (data: MomentClipRequest) =>
    apiFetch("/api/clip-executor/execute-moment", { method: "POST", body: JSON.stringify(data) }),
  getProcessedClips: () => apiFetch<ProcessedClipsList>("/api/clip-executor/processed-clips"),
};

// Types
export interface AnalyticsOverview {
  total_clips: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  avg_retention: number;
  avg_ctr: number;
  avg_watch_through: number;
  active_ab_tests: number;
  active_trends: number;
  top_format: string | null;
  current_phase: number;
  clips_this_week: number;
  views_this_week: number;
}

export interface FormatPerformance {
  format_type: string;
  total_clips: number;
  total_views: number;
  avg_ctr: number;
  avg_retention: number;
  avg_watch_through: number;
  avg_comments: number;
  score: number;
  trend: string;
}

export interface GrowthPhase {
  current_phase: number;
  phase_name: string;
  phase_info: { name: string; label: string; min_clips: number; description: string };
  all_phases: Record<string, { name: string; label: string; min_clips: number; description: string }>;
  started_at: string;
  config: Record<string, unknown>;
}

export interface Clip {
  id: number;
  moment_id: number | null;
  template_id: number | null;
  ab_test_id: number | null;
  title: string;
  description: string | null;
  format_type: string;
  duration: number;
  status: string;
  hook_text: string | null;
  cta_text: string | null;
  has_ai_girl: boolean;
  has_subtitles: boolean;
  has_face_cam: boolean;
  platform: string | null;
  published_at: string | null;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  ctr: number;
  retention_rate: number;
  watch_through_rate: number;
  created_at: string;
  updated_at: string;
  file_path?: string | null;
  thumbnail_path?: string | null;
}

export interface Stream {
  id: number;
  title: string;
  platform: string;
  url: string | null;
  streamer_name: string;
  started_at: string | null;
  ended_at: string | null;
  status: string;
  created_at: string;
}

export interface Moment {
  id: number;
  stream_id: number | null;
  moment_type: string;
  timestamp_start: number;
  timestamp_end: number;
  score: number;
  description: string | null;
  metadata: Record<string, unknown>;
  status: string;
  created_at: string;
}

export interface Template {
  id: number;
  name: string;
  format_type: string;
  description: string | null;
  config: Record<string, unknown>;
  is_active: boolean;
  weight: number;
  total_clips: number;
  avg_retention: number;
  avg_ctr: number;
  created_at: string;
  updated_at: string;
}

export interface ABTest {
  id: number;
  name: string;
  moment_id: number | null;
  status: string;
  winner_clip_id: number | null;
  started_at: string;
  ended_at: string | null;
  created_at: string;
  clips: Clip[];
}

export interface Trend {
  id: number;
  platform: string;
  trend_type: string;
  title: string;
  description: string | null;
  score: number;
  metadata: Record<string, unknown>;
  source_url: string | null;
  detected_at: string;
  is_active: boolean;
  created_at: string;
}

export interface AIGirlConfig {
  id: number;
  is_enabled: boolean;
  model_name: string;
  voice_style: string;
  appearance_style: string;
  overlay_position: string;
  overlay_size: number;
  use_only_when_better: boolean;
  min_improvement_pct: number;
  total_clips_with: number;
  total_clips_without: number;
  avg_retention_with: number;
  avg_retention_without: number;
  updated_at: string;
}

export interface DetectResult {
  stream_id: number;
  moments_detected: number;
  moments: Moment[];
}

export interface ABResultSubmit {
  clip_id: number;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  ctr: number;
  retention_rate: number;
  watch_through_rate: number;
}

export interface AdaptResult {
  adapted: boolean;
  changes?: { format_type: string; new_weight: number; score: number }[];
  reason?: string;
}

// AI Profiles
export interface AIProfile {
  id: number;
  name: string;
  style: string;
  description: string | null;
  appearance: Record<string, unknown>;
  voice_config: Record<string, unknown>;
  personality: Record<string, unknown>;
  reference_images: string[];
  instagram_handle: string | null;
  tiktok_handle: string | null;
  telegram_channel: string | null;
  elevenlabs_voice_id: string | null;
  elevenlabs_voice_settings: Record<string, unknown>;
  voice_audio_tags: string[];
  memory: Record<string, unknown>;
  content_style: Record<string, unknown>;
  social_config: Record<string, unknown>;
  total_posts: number;
  total_videos: number;
  total_photos: number;
  total_cost: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfilePresets {
  appearance: Record<string, Record<string, unknown>>;
  personality: Record<string, Record<string, unknown>>;
  voice: Record<string, Record<string, unknown>>;
  voice_personas: Record<string, { name: string; description: string; elevenlabs_voice: string; signature_tags: string[]; style_guide: string; default_settings: Record<string, number>; moment_types: string[] }>;
  audio_tags: Record<string, string[]>;
  enhancement_tips: Record<string, unknown>;
}

export interface CreateProfileData {
  name: string;
  style?: string;
  description?: string;
  appearance_preset?: string;
  personality_preset?: string;
  voice_preset?: string;
  voice_persona?: string;
  instagram_handle?: string;
  tiktok_handle?: string;
  telegram_channel?: string;
}

export interface ProfilePipeline {
  profile_id: number;
  name: string;
  voice_persona: { id: string; name: string; description: string; voice: string; signature_tags: string[]; style_guide: string };
  pipeline: Record<string, { tool: string; description: string; cost: string; [key: string]: unknown }>;
  content_types: Record<string, string>;
  cost_summary: Record<string, string>;
}

// Voice Generation
export interface GenerateVoiceReq {
  text: string;
  moment_type?: string;
  use_audio_tags?: boolean;
  voice_name_override?: string;
}

export interface VoiceGenResult {
  success: boolean;
  file_path?: string;
  filename?: string;
  voice?: string;
  text?: string;
  char_count?: number;
  cost?: number;
  engine?: string;
  persona?: string;
  moment_type?: string;
  original_text?: string;
  expressive_text?: string;
  error?: string;
}

export interface ScriptPreview {
  original_text: string;
  expressive_text: string;
  persona: string;
  persona_name: string;
  moment_type: string;
  tags_used: string[];
}

export interface VoiceSample {
  id: number;
  profile_id: number;
  text: string;
  audio_tags: string[];
  file_path: string | null;
  duration: number | null;
  cost: number;
  voice_settings: Record<string, unknown>;
  rating: number | null;
  created_at: string;
}

export interface ElevenLabsVoice {
  voice_id: string;
  name: string;
  category: string;
  labels: Record<string, string>;
  preview_url: string | null;
}

// Photo/Video Generation for Profiles
export interface GenPhotoReq {
  prompt?: string;
  content_type?: string;
  num_images?: number;
  width?: number;
  height?: number;
  model_key?: string;
  use_reference_images?: boolean;
  set_as_reference?: boolean;
}

export interface PhotoResult {
  success: boolean;
  images?: { url: string; width: number; height: number }[];
  model?: string;
  model_name?: string;
  prompt?: string;
  cost_estimate?: number;
  total_cost?: number;
  used_reference_images?: boolean;
  gallery_ids?: number[];
  error?: string;
}

// Gallery types
export interface GalleryPhoto {
  id: number;
  profile_id: number;
  image_url: string;
  thumbnail_url: string | null;
  content_type: string;
  prompt: string | null;
  model_key: string | null;
  is_reference: number;
  is_approved: number;
  is_favorite: number;
  quality_rating: number | null;
  metadata: Record<string, unknown>;
  cost: number;
  created_at: string;
}

export interface ProfileGalleryResponse {
  gallery: GalleryPhoto[];
  total: number;
}

// Voice Identity types
export interface VoiceIdentity {
  profile_id: number;
  has_identity: boolean;
  provider: string;
  voice_id: string | null;
  voice_name: string | null;
  voice_settings: Record<string, unknown>;
  audio_tags: string[];
  sample_urls?: string[];
  personality_traits?: string[];
  speaking_style?: string;
  language?: string;
  total_generations?: number;
}

export interface VoiceIdentityUpdate {
  voice_id: string;
  voice_name: string;
  speaking_style: string;
  language: string;
  personality_traits: string[];
  audio_tags: string[];
}

// Learning types
export interface LearningEntry {
  id: number;
  profile_id: number;
  prompt_type: string;
  original_prompt: string;
  refined_prompt: string | null;
  model_key: string | null;
  content_type: string | null;
  success_score: number;
  user_rating: number | null;
  auto_features: Record<string, unknown>;
  generation_count: number;
  created_at: string;
}

export interface ProfileLearningResponse {
  profile_id: number;
  learning_data: LearningEntry[];
  content_type_performance: Record<string, { count: number; total_score: number; best_prompt: string }>;
  total_learned_prompts: number;
}

export interface GenVideoReq {
  text: string;
  moment_type?: string;
  photo_prompt?: string;
  photo_model_key?: string;
  lipsync_model_key?: string;
  generate_i2v?: boolean;
  i2v_model_key?: string;
  i2v_prompt?: string;
}

export interface VideoGenResult {
  success: boolean;
  total_cost?: number;
  steps?: { step: string; result: Record<string, unknown> }[];
  error?: string;
}

// Content & Social
export interface ContentItem {
  id: number;
  profile_id: number;
  content_type: string;
  title: string | null;
  prompt: string | null;
  file_path: string | null;
  file_url: string | null;
  thumbnail_path: string | null;
  duration: number | null;
  cost: number;
  metadata: Record<string, unknown>;
  status: string;
  created_at: string;
}

export interface CostBreakdown {
  profile_id: number;
  name: string;
  total_cost: number;
  total_photos: number;
  total_videos: number;
  total_posts: number;
  breakdown: { type: string; count: number; cost: number }[];
  cost_estimates: Record<string, string>;
}

export interface SchedulePostReq {
  content_item_id?: number;
  platform?: string;
  caption?: string;
  hashtags?: string[];
  scheduled_at?: string;
}

export interface SocialPost {
  id: number;
  profile_id: number;
  content_item_id: number | null;
  platform: string;
  caption: string | null;
  hashtags: string[];
  scheduled_at: string | null;
  posted_at: string | null;
  post_url: string | null;
  status: string;
  engagement: Record<string, unknown>;
  created_at: string;
}

export interface UpdateMemoryReq {
  personality_notes?: string;
  style_preferences?: Record<string, unknown>;
  audience_insights?: Record<string, unknown>;
  voice_preferences?: Record<string, unknown>;
  custom_data?: Record<string, unknown>;
}

export interface MemoryData {
  profile_id: number;
  name: string;
  memory: Record<string, unknown>;
  personality: Record<string, unknown>;
  content_style: Record<string, unknown>;
  voice_config: Record<string, unknown>;
  social_config: Record<string, unknown>;
}

// Tool Registry
export interface Tool {
  id: number;
  name: string;
  category: string;
  description: string | null;
  github_url: string | null;
  github_stars: number;
  license: string | null;
  min_vram_gb: number;
  is_free: boolean;
  api_cost_per_use: number;
  quality_score: number;
  speed_score: number;
  config: Record<string, unknown>;
  is_selected: boolean;
  created_at: string;
}

export interface ToolCategory {
  category: string;
  count: number;
}

export interface PipelineConfig {
  total_monthly_cost: string;
  setup: string;
  image: Record<string, string>;
  lip_sync: Record<string, string>;
  voice: Record<string, string>;
  video: Record<string, string>;
  orchestration: string;
}

// Accounts & Regions
export interface Account {
  id: number;
  platform: string;
  handle: string;
  account_type: string;
  region: string;
  language: string;
  target_audience: Record<string, unknown>;
  streamer_names: string[];
  status: string;
  total_posts: number;
  total_followers: number;
  created_at: string;
  updated_at: string;
}

export interface CreateAccountData {
  platform: string;
  handle: string;
  account_type?: string;
  region?: string;
  language?: string;
  streamer_names?: string[];
}

export interface RegionAnalysis {
  id: number;
  region: string;
  platform: string;
  audience_size: number;
  competition_level: string;
  avg_views_per_reel: number;
  top_languages: string[];
  top_content_types: string[];
  growth_potential: number;
  recommendation: string | null;
  analyzed_at: string;
}

export interface RegionRecommendations {
  top_regions: RegionAnalysis[];
  strategy: {
    recommended_accounts: {
      platform: string;
      type: string;
      region: string;
      language: string;
      reason: string;
      streamers_per_account?: number;
    }[];
    sim_card_strategy: Record<string, string>;
    account_warming: Record<string, string>;
  };
}

// Generation types
export interface GenerationStatus {
  fal_api_configured: boolean;
  tts_available: boolean;
  photo_generation_available: boolean;
  lipsync_available: boolean;
  available_voices: string[];
  available_photo_models: { id: string; name: string; cost: string; quality: string }[];
  available_lipsync_models: { id: string; name: string; cost: string; cost_3s: string }[];
  budget_estimate: Record<string, Record<string, string>>;
  generated_files: { photos: number; audio: number; video: number };
}

export interface VoiceList {
  voices: Record<string, { voice_id: string; language: string; gender: string; name: string }>;
  default_voice: string;
}

export interface PhotoPresets {
  presets: Record<string, { prompt: string }>;
  reaction_scripts: Record<string, string[]>;
}

export interface TTSRequest { text: string; voice_id?: string; }
export interface TTSResult { success: boolean; file_path: string; filename: string; voice: string; text: string; file_size_bytes: number; cost: number; engine: string; error?: string; }

export interface PhotoGenRequest { prompt: string; negative_prompt?: string; width?: number; height?: number; num_images?: number; model?: string; }
export interface LegacyPhotoResult { success: boolean; images?: { file_path: string; url: string }[]; cost_estimate: number; model: string; error?: string; }

export interface FacePhotoRequest { prompt: string; face_image_url: string; negative_prompt?: string; width?: number; height?: number; }

export interface LipsyncRequest { image_url: string; audio_url: string; model?: string; }
export interface LipsyncResult { success: boolean; video_path?: string; video_url?: string; cost_estimate: number; model: string; error?: string; }

export interface FullPipelineRequest { text: string; photo_prompt: string; voice_id?: string; face_image_url?: string; lipsync_model?: string; }
export interface PipelineResult { steps: { step: string; result: Record<string, unknown> }[]; total_cost: number; success: boolean; error?: string; }

export interface Gallery {
  photos: GalleryItem[];
  audio: GalleryItem[];
  video: GalleryItem[];
}
export interface GalleryItem { filename: string; size_bytes: number; created_at: number; url: string; }

export interface AccountStrategy {
  overview: Record<string, unknown>;
  account_structure: Record<string, unknown[]>;
  content_calendar: Record<string, Record<string, unknown>>;
  growth_targets: Record<string, Record<string, string>>;
}

// Twitch Streamers
export interface TwitchStreamer {
  username: string;
  display_name: string;
  twitch_url: string;
  region: string;
  language: string;
  avg_viewers: number;
  followers: number;
  content_style: string;
  clip_potential: number;
  description: string;
}

export interface TwitchStreamersResponse {
  total: number;
  streamers: TwitchStreamer[];
  regions_available: string[];
  recommendation: string;
}

export interface ClippingPipeline {
  auto_detection: {
    enabled: boolean;
    description: string;
    triggers: Record<string, { description: string; weight: number; [key: string]: unknown }>;
  };
  clip_settings: {
    default_duration_sec: number;
    pre_moment_buffer_sec: number;
    post_moment_buffer_sec: number;
    max_clip_duration_sec: number;
    min_clip_duration_sec: number;
    output_formats: Record<string, { aspect_ratio: string; max_duration: number; resolution: string }>;
  };
  post_processing: Record<string, { enabled: boolean; [key: string]: unknown }>;
  publishing: Record<string, unknown>;
}

// Clip Executor types
export interface ClipExecutorStatus {
  ffmpeg_available: boolean;
  ytdlp_available: boolean;
  twitch_api_configured: boolean;
  font_path: string;
  clips_dir: string;
  source_clips: number;
  processed_clips: number;
  capabilities: Record<string, boolean>;
  required_apis: Record<string, { configured: boolean; required_for: string; how_to_get: string; env_vars: string[] }>;
}

export interface DiscoverClipsResult {
  clips: TwitchClipInfo[];
  total: number;
  broadcaster: string;
}

export interface TwitchClipInfo {
  clip_id: string;
  url: string;
  title: string;
  broadcaster_name: string;
  view_count: number;
  duration: number;
  created_at: string;
  thumbnail_url: string;
  download_url: string;
}

export interface DownloadResult {
  success: boolean;
  file_path?: string;
  filename?: string;
  duration?: number;
  width?: number;
  height?: number;
  file_size?: number;
  error?: string;
}

export interface ProcessClipRequest {
  source_path: string;
  hook_text?: string;
  hook_duration?: number;
  cta_text?: string;
  cta_start_offset?: number;
  subtitle_text?: string;
  color_grade?: string;
  max_duration?: number;
  target_width?: number;
  target_height?: number;
  fps?: number;
  volume_boost?: number;
}

export interface ProcessClipResult {
  success: boolean;
  file_path?: string;
  filename?: string;
  thumbnail_path?: string;
  duration?: number;
  width?: number;
  height?: number;
  file_size?: number;
  resolution?: string;
  hook_text?: string;
  cta_text?: string;
  error?: string;
}

export interface TestClipRequest {
  twitch_url: string;
  hook_text?: string;
  cta_text?: string;
  subtitle_text?: string;
  color_grade?: string;
  max_duration?: number;
}

export interface TestClipResult {
  success: boolean;
  output_file?: string;
  thumbnail?: string;
  duration?: number;
  file_size?: number;
  resolution?: string;
  steps?: { step: string; result: Record<string, unknown> }[];
  error?: string;
}

export interface MomentClipRequest {
  moment_id: number;
  template_format?: string;
  hook_text?: string;
  cta_text?: string;
}

export interface ProcessedClipFile {
  filename: string;
  file_path: string;
  size_bytes: number;
  created_at: number;
  video_url: string;
  thumbnail_url: string | null;
}

export interface ProcessedClipsList {
  clips: ProcessedClipFile[];
  total: number;
}

// Montage Engine types
export interface MontageStatus {
  engine: string;
  tools: Record<string, boolean>;
  capabilities: Record<string, boolean | string>;
  templates: Record<string, { name: string; description: string; duration: number; phases: number; has_girl: boolean }>;
  sfx_library: Record<string, { name: string; category: string; duration: number }>;
  music_library: Record<string, { name: string; category: string; mood: string }>;
  girl_voices: Record<string, { desc: string; style: string }>;
  girl_scripts: string[];
  assets: { sfx_cached: number; music_cached: number; clips_generated: number };
  directories: Record<string, string>;
  apis_needed: {
    free: { name: string; purpose: string; status: string }[];
    paid: { name: string; purpose: string; cost: string; required: boolean }[];
  };
}

export interface MontageTemplate {
  name: string;
  description: string;
  total_duration: number;
  phases: {
    name: string;
    start: number;
    end: number;
    purpose: string;
    girl_visible: boolean;
    girl_speaks: boolean;
    sfx: string | null;
    has_zoom: boolean;
    has_slow_mo: boolean;
  }[];
}

export interface MontageSfxItem {
  name: string;
  category: string;
  duration: number;
}

export interface MontageMusicItem {
  name: string;
  category: string;
  bpm: number;
  mood: string;
}

export interface MontageGirlConfig {
  voices: Record<string, { desc: string; style: string }>;
  scripts: Record<string, Record<string, string>>;
}

export interface CreateMontageRequest {
  clip_url: string;
  template_id?: string;
  moment_type?: string;
  hook_text?: string;
  cta_text?: string;
  subtitle_text?: string;
  start_time?: number;
  max_duration?: number;
  action_timestamp?: number | null;
  enable_girl?: boolean;
  girl_voice?: string;
  girl_image_url?: string | null;
  fal_api_key?: string | null;
  color_grade?: string;
  music_track?: string | null;
}

export interface MontageResult {
  success: boolean;
  output_path?: string;
  thumbnail_path?: string | null;
  duration?: number;
  resolution?: string;
  file_size?: number;
  template?: string;
  moment_type?: string;
  tracks?: Record<string, boolean | number>;
  steps?: { step: string; status: string; result?: Record<string, unknown> }[];
  total_cost?: number;
  session_id?: string;
  created_at?: string;
  error?: string;
}

export interface MontageGirlAudioResult {
  success: boolean;
  audio_path?: string;
  srt_path?: string;
  duration?: number;
  text?: string;
  voice?: string;
  cost?: number;
  error?: string;
}

export interface MontageClipFile {
  filename: string;
  file_path: string;
  file_size: number;
  thumbnail: string | null;
  created_at: string;
}

export interface StreamerStatsResponse {
  streamers: {
    streamer_name: string;
    twitch_url: string;
    total_streams: number;
    total_moments: number;
    avg_moment_score: number;
    best_moment_score: number | null;
    last_status: string;
    region?: string;
    language?: string;
    clip_potential?: number;
    followers?: number;
  }[];
}
