import { useEffect, useState } from "react";
import {
  api,
  AIProfile,
  ProfilePresets,
  ProfilePipeline,
  VoiceGenResult,
  ScriptPreview,
  VoiceSample,
  ContentItem,
  CostBreakdown,
  SocialPost,
  MemoryData,
  VideoGenResult,
  PhotoResult,
} from "@/hooks/useApi";
import {
  Plus, Sparkles, Trash2, Mic, Video, Image, Brain, Share2,
  DollarSign, Play, Eye, RefreshCw, Send, Settings2, Zap,
  Volume2, FileText, ChevronRight, Hash, Clock, BarChart3,
  Camera, Download, Star,
} from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

type Tab = "overview" | "generate" | "content" | "social" | "brain";

const TABS: { id: Tab; label: string; icon: typeof Sparkles }[] = [
  { id: "overview", label: "Обзор", icon: Eye },
  { id: "generate", label: "Генерация", icon: Zap },
  { id: "content", label: "Контент", icon: Image },
  { id: "social", label: "Соцсети", icon: Share2 },
  { id: "brain", label: "Мозг", icon: Brain },
];

const PERSONA_COLORS: Record<string, string> = {
  jessica_fire: "from-red-500 to-orange-500",
  sofia_smooth: "from-violet-500 to-indigo-500",
  mia_cute: "from-pink-400 to-rose-400",
  alex_edgy: "from-gray-600 to-gray-800",
};

const MOMENT_TYPES = [
  "clutch", "ace", "multi_kill", "headshot_sequence",
  "emotional_reaction", "toxic_moment", "meme_fail", "generic",
];

export default function AIProfilesPage() {
  const [profiles, setProfiles] = useState<AIProfile[]>([]);
  const [presets, setPresets] = useState<ProfilePresets | null>(null);
  const [selected, setSelected] = useState<AIProfile | null>(null);
  const [pipeline, setPipeline] = useState<ProfilePipeline | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [showCreate, setShowCreate] = useState(false);

  const [voiceText, setVoiceText] = useState(
    "OH MY GOD did you SEE that ace?! Five kills, no deaths, absolutely INSANE!"
  );
  const [momentType, setMomentType] = useState("clutch");
  const [voiceResult, setVoiceResult] = useState<VoiceGenResult | null>(null);
  const [scriptPreview, setScriptPreview] = useState<ScriptPreview | null>(null);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [videoText, setVideoText] = useState(
    "That clutch was absolutely incredible, five kills with just a deagle!"
  );
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoResult, setVideoResult] = useState<VideoGenResult | null>(null);

  // Photo generation state
  const [photoPrompt, setPhotoPrompt] = useState("");
  const [photoContentType, setPhotoContentType] = useState("gaming_reaction");
  const [photoModel, setPhotoModel] = useState("flux2_realism");
  const [photoUseRef, setPhotoUseRef] = useState(true);
  const [photoSetRef, setPhotoSetRef] = useState(false);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [photoResult, setPhotoResult] = useState<PhotoResult | null>(null);

  const [contentItems, setContentItems] = useState<ContentItem[]>([]);
  const [contentFilter, setContentFilter] = useState("");
  const [costs, setCosts] = useState<CostBreakdown | null>(null);

  const [socialPosts, setSocialPosts] = useState<SocialPost[]>([]);
  const [postCaption, setPostCaption] = useState("");
  const [postPlatform, setPostPlatform] = useState("instagram");
  const [postHashtags, setPostHashtags] = useState("");

  const [memory, setMemory] = useState<MemoryData | null>(null);
  const [voiceSamples, setVoiceSamples] = useState<VoiceSample[]>([]);
  const [memoryNotes, setMemoryNotes] = useState("");

  const [form, setForm] = useState({
    name: "",
    style: "realistic",
    description: "",
    appearance_preset: "realistic_european",
    personality_preset: "energetic_gamer",
    voice_preset: "energetic_female",
    voice_persona: "jessica_fire",
    instagram_handle: "",
    tiktok_handle: "",
    telegram_channel: "",
  });

  useEffect(() => {
    api.getProfiles().then(setProfiles).catch(() => {});
    api.getProfilePresets().then(setPresets).catch(() => {});
  }, []);

  const selectProfile = async (p: AIProfile) => {
    setSelected(p);
    setTab("overview");
    try {
      setPipeline(await api.getProfilePipeline(p.id));
    } catch {
      setPipeline(null);
    }
  };

  const loadTabData = async (t: Tab, profileId: number) => {
    try {
      if (t === "content") {
        setContentItems(await api.getProfileContent(profileId, contentFilter || undefined));
        setCosts(await api.getProfileCosts(profileId));
      } else if (t === "social") {
        setSocialPosts(await api.getSocialPosts(profileId));
      } else if (t === "brain") {
        setMemory(await api.getProfileMemory(profileId));
        setVoiceSamples(await api.getVoiceSamples(profileId));
      }
    } catch {
      /* ok */
    }
  };

  const handleTabChange = (t: Tab) => {
    setTab(t);
    if (selected) loadTabData(t, selected.id);
  };

  const handleCreate = async () => {
    try {
      const p = await api.createProfile({
        name: form.name,
        style: form.style,
        description: form.description || undefined,
        appearance_preset: form.appearance_preset,
        personality_preset: form.personality_preset,
        voice_preset: form.voice_preset,
        voice_persona: form.voice_persona,
        instagram_handle: form.instagram_handle || undefined,
        tiktok_handle: form.tiktok_handle || undefined,
        telegram_channel: form.telegram_channel || undefined,
      });
      setProfiles([p, ...profiles]);
      setShowCreate(false);
      setForm({
        name: "", style: "realistic", description: "",
        appearance_preset: "realistic_european", personality_preset: "energetic_gamer",
        voice_preset: "energetic_female", voice_persona: "jessica_fire",
        instagram_handle: "", tiktok_handle: "", telegram_channel: "",
      });
    } catch (e) {
      alert("Error: " + e);
    }
  };

  const handleDelete = async (id: number) => {
    await api.deleteProfile(id);
    setProfiles(profiles.filter((p) => p.id !== id));
    if (selected?.id === id) {
      setSelected(null);
      setPipeline(null);
    }
  };

  const handlePreviewScript = async () => {
    if (!selected) return;
    try {
      const res = await api.previewScript(selected.id, {
        text: voiceText,
        moment_type: momentType,
      });
      setScriptPreview(res);
    } catch {
      /* ok */
    }
  };

  const handleGenerateVoice = async () => {
    if (!selected) return;
    setVoiceLoading(true);
    setVoiceResult(null);
    try {
      const res = await api.generateProfileVoice(selected.id, {
        text: voiceText,
        moment_type: momentType,
      });
      setVoiceResult(res);
    } catch (e) {
      setVoiceResult({ success: false, error: String(e) });
    }
    setVoiceLoading(false);
  };

  const handleGenerateVideo = async () => {
    if (!selected) return;
    setVideoLoading(true);
    setVideoResult(null);
    try {
      const res = await api.generateProfileVideo(selected.id, {
        text: videoText,
        moment_type: momentType,
        lipsync_model_key: "omnihuman",
      });
      setVideoResult(res);
    } catch (e) {
      setVideoResult({ success: false, error: String(e) });
    }
    setVideoLoading(false);
  };

  const handleGeneratePhoto = async () => {
    if (!selected) return;
    setPhotoLoading(true);
    setPhotoResult(null);
    try {
      const res = await api.generateProfilePhoto(selected.id, {
        prompt: photoPrompt || undefined,
        content_type: photoContentType,
        model_key: photoModel,
        use_reference_images: photoUseRef,
        set_as_reference: photoSetRef,
        num_images: 1,
        width: 1024,
        height: 1024,
      });
      setPhotoResult(res);
      // Reload profile to get updated reference_images
      if (res.success && photoSetRef) {
        const updated = await api.getProfiles();
        setProfiles(updated);
        const refreshed = updated.find((p) => p.id === selected.id);
        if (refreshed) setSelected(refreshed);
      }
    } catch (e) {
      setPhotoResult({ success: false, error: String(e) });
    }
    setPhotoLoading(false);
  };

  const handleSchedulePost = async () => {
    if (!selected) return;
    try {
      await api.schedulePost(selected.id, {
        platform: postPlatform,
        caption: postCaption,
        hashtags: postHashtags.split(",").map((h) => h.trim()).filter(Boolean),
      });
      setSocialPosts(await api.getSocialPosts(selected.id));
      setPostCaption("");
      setPostHashtags("");
    } catch {
      /* ok */
    }
  };

  const handleUpdateMemory = async () => {
    if (!selected) return;
    try {
      await api.updateProfileMemory(selected.id, { personality_notes: memoryNotes });
      setMemory(await api.getProfileMemory(selected.id));
    } catch {
      /* ok */
    }
  };

  const personaGrad = (p: AIProfile) => {
    const pid = (p.voice_config?.persona_id as string) || "jessica_fire";
    return PERSONA_COLORS[pid] || "from-pink-500 to-violet-500";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Девушки</h1>
          <p className="text-zinc-400 text-sm mt-1">
            Управление персонажами: голос, фото, видео, соцсети, память
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 bg-pink-600 hover:bg-pink-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="h-4 w-4" /> Новая девушка
        </button>
      </div>

      {showCreate && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
          <h3 className="text-lg font-semibold text-pink-400">Создать AI девушку</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Имя</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                placeholder="Jessica Fire"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Голосовая персона</label>
              <select
                value={form.voice_persona}
                onChange={(e) => setForm({ ...form, voice_persona: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="jessica_fire">Jessica Fire</option>
                <option value="sofia_smooth">Sofia Smooth</option>
                <option value="mia_cute">Mia Cute</option>
                <option value="alex_edgy">Alex Edgy</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Стиль</label>
              <select
                value={form.style}
                onChange={(e) => setForm({ ...form, style: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="realistic">Реалистичный</option>
                <option value="anime">Аниме</option>
                <option value="semi-realistic">Полуреалистичный</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Instagram</label>
              <input
                value={form.instagram_handle}
                onChange={(e) => setForm({ ...form, instagram_handle: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                placeholder="@jessica_gaming"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">TikTok</label>
              <input
                value={form.tiktok_handle}
                onChange={(e) => setForm({ ...form, tiktok_handle: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                placeholder="@jessica_ttk"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Telegram</label>
              <input
                value={form.telegram_channel}
                onChange={(e) => setForm({ ...form, telegram_channel: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                placeholder="@jessica_private"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Описание</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              rows={2}
              placeholder="Описание персонажа..."
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={!form.name}
            className="bg-pink-600 hover:bg-pink-700 disabled:opacity-50 px-6 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Создать профиль
          </button>
        </div>
      )}

      <div className="grid grid-cols-4 gap-6">
        <div className="col-span-1 space-y-3">
          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Профили</h3>
          {profiles.length === 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 text-center text-zinc-500 text-sm">
              Профилей пока нет
            </div>
          )}
          {profiles.map((p) => (
            <div
              key={p.id}
              onClick={() => selectProfile(p)}
              className={`bg-zinc-900 border rounded-xl p-4 cursor-pointer transition-colors ${
                selected?.id === p.id ? "border-pink-500" : "border-zinc-800 hover:border-zinc-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${personaGrad(p)} flex items-center justify-center text-sm font-bold`}>
                    {p.name[0]}
                  </div>
                  <div>
                    <div className="font-medium text-sm">{p.name}</div>
                    <div className="text-xs text-zinc-500">
                      {(p.voice_config?.persona_id as string) || "jessica_fire"}
                    </div>
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                  className="text-zinc-600 hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-2 flex gap-1.5 flex-wrap">
                <span className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded">
                  ${(p.total_cost || 0).toFixed(2)}
                </span>
                <span className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded">
                  {p.total_videos || 0} vid
                </span>
                <span className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded">
                  {p.total_photos || 0} img
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  p.is_active ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                }`}>
                  {p.is_active ? "ON" : "OFF"}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="col-span-3 space-y-4">
          {selected ? (
            <>
              <div className="flex gap-1 bg-zinc-900 border border-zinc-800 rounded-xl p-1">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => handleTabChange(t.id)}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-colors ${
                      tab === t.id
                        ? "bg-pink-600 text-white"
                        : "text-zinc-400 hover:text-white hover:bg-zinc-800"
                    }`}
                  >
                    <t.icon className="h-4 w-4" /> {t.label}
                  </button>
                ))}
              </div>

              {tab === "overview" && (
                <OverviewTab selected={selected} pipeline={pipeline} personaGrad={personaGrad} />
              )}
              {tab === "generate" && (
                <GenerateTab
                  selected={selected}
                  voiceText={voiceText} setVoiceText={setVoiceText}
                  momentType={momentType} setMomentType={setMomentType}
                  voiceLoading={voiceLoading} voiceResult={voiceResult}
                  scriptPreview={scriptPreview}
                  videoText={videoText} setVideoText={setVideoText}
                  videoLoading={videoLoading} videoResult={videoResult}
                  photoPrompt={photoPrompt} setPhotoPrompt={setPhotoPrompt}
                  photoContentType={photoContentType} setPhotoContentType={setPhotoContentType}
                  photoModel={photoModel} setPhotoModel={setPhotoModel}
                  photoUseRef={photoUseRef} setPhotoUseRef={setPhotoUseRef}
                  photoSetRef={photoSetRef} setPhotoSetRef={setPhotoSetRef}
                  photoLoading={photoLoading} photoResult={photoResult}
                  presets={presets}
                  onPreview={handlePreviewScript}
                  onVoice={handleGenerateVoice}
                  onVideo={handleGenerateVideo}
                  onPhoto={handleGeneratePhoto}
                />
              )}
              {tab === "content" && (
                <ContentTab
                  costs={costs} contentItems={contentItems}
                  contentFilter={contentFilter} setContentFilter={setContentFilter}
                  selected={selected} setContentItems={setContentItems}
                />
              )}
              {tab === "social" && (
                <SocialTab
                  postPlatform={postPlatform} setPostPlatform={setPostPlatform}
                  postHashtags={postHashtags} setPostHashtags={setPostHashtags}
                  postCaption={postCaption} setPostCaption={setPostCaption}
                  socialPosts={socialPosts} onSchedule={handleSchedulePost}
                />
              )}
              {tab === "brain" && (
                <BrainTab
                  memory={memory} voiceSamples={voiceSamples}
                  memoryNotes={memoryNotes} setMemoryNotes={setMemoryNotes}
                  onUpdateMemory={handleUpdateMemory}
                />
              )}
            </>
          ) : (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
              <Sparkles className="h-12 w-12 text-pink-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Выбери профиль</h3>
              <p className="text-zinc-400 text-sm">Создай новую AI девушку или выбери слева</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ========== OVERVIEW TAB ========== */

function OverviewTab({
  selected, pipeline, personaGrad,
}: {
  selected: AIProfile;
  pipeline: ProfilePipeline | null;
  personaGrad: (p: AIProfile) => string;
}) {
  return (
    <div className="space-y-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className={`w-16 h-16 rounded-full bg-gradient-to-br ${personaGrad(selected)} flex items-center justify-center text-2xl font-bold`}>
            {selected.name[0]}
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold">{selected.name}</h2>
            <p className="text-zinc-400 text-sm">{selected.description}</p>
            <div className="flex gap-3 mt-1 text-xs text-zinc-500">
              {selected.instagram_handle && <span>IG: {selected.instagram_handle}</span>}
              {selected.tiktok_handle && <span>TT: {selected.tiktok_handle}</span>}
              {selected.telegram_channel && <span>TG: {selected.telegram_channel}</span>}
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-green-400">${(selected.total_cost || 0).toFixed(2)}</div>
            <div className="text-xs text-zinc-500">потрачено</div>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Видео", value: selected.total_videos || 0, icon: Video },
            { label: "Фото", value: selected.total_photos || 0, icon: Image },
            { label: "Посты", value: selected.total_posts || 0, icon: Share2 },
            { label: "Стоимость", value: "$" + (selected.total_cost || 0).toFixed(2), icon: DollarSign },
          ].map((s) => (
            <div key={s.label} className="bg-zinc-800 rounded-lg p-3 text-center">
              <s.icon className="h-5 w-5 mx-auto text-pink-400 mb-1" />
              <div className="text-lg font-bold">{s.value}</div>
              <div className="text-xs text-zinc-500">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {pipeline?.voice_persona && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Volume2 className="h-5 w-5 text-violet-400" /> Голосовая персона
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-pink-400">{pipeline.voice_persona.name}</div>
              <div className="text-xs text-zinc-400 mt-1">{pipeline.voice_persona.description}</div>
              <div className="text-xs text-zinc-500 mt-2">
                ElevenLabs: <span className="text-white">{pipeline.voice_persona.voice}</span>
              </div>
              <div className="text-xs text-zinc-500 mt-1">Стиль: {pipeline.voice_persona.style_guide}</div>
            </div>
            <div>
              <div className="text-xs text-zinc-400 mb-2">Фирменные теги:</div>
              <div className="flex flex-wrap gap-1">
                {pipeline.voice_persona.signature_tags.map((tag) => (
                  <span key={tag} className="text-xs bg-violet-500/20 text-violet-300 px-2 py-0.5 rounded">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {pipeline && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-violet-400" /> Пайплайн
          </h3>
          <div className="space-y-2">
            {Object.entries(pipeline.pipeline).map(([key, step]) => (
              <div key={key} className="bg-zinc-800 rounded-lg p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ChevronRight className="h-4 w-4 text-pink-400" />
                  <div>
                    <div className="text-sm font-medium">{step.description}</div>
                    <div className="text-xs text-zinc-500">{step.tool}</div>
                  </div>
                </div>
                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">{step.cost}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ========== GENERATE TAB ========== */

const PHOTO_CONTENT_TYPES = [
  { id: "gaming_reaction", label: "Игровая реакция" },
  { id: "stream_preview", label: "Превью стрима" },
  { id: "social_selfie", label: "Селфи для соцсетей" },
  { id: "intimate_lingerie", label: "Нижнее бельё" },
  { id: "professional_portrait", label: "Портрет (проф.)" },
  { id: "custom", label: "Свой промт" },
];

const PHOTO_MODELS = [
  { id: "flux2_realism", label: "FLUX 2 Realism (быстро, $0.025)", cost: 0.025 },
  { id: "flux2_pro", label: "FLUX 2 Pro (качество, $0.05)", cost: 0.05 },
];

function GenerateTab({
  selected,
  voiceText, setVoiceText, momentType, setMomentType,
  voiceLoading, voiceResult, scriptPreview,
  videoText, setVideoText, videoLoading, videoResult,
  photoPrompt, setPhotoPrompt, photoContentType, setPhotoContentType,
  photoModel, setPhotoModel, photoUseRef, setPhotoUseRef,
  photoSetRef, setPhotoSetRef, photoLoading, photoResult,
  onPreview, onVoice, onVideo, onPhoto,
}: {
  selected: AIProfile | null;
  voiceText: string; setVoiceText: (v: string) => void;
  momentType: string; setMomentType: (v: string) => void;
  voiceLoading: boolean; voiceResult: VoiceGenResult | null;
  scriptPreview: ScriptPreview | null;
  videoText: string; setVideoText: (v: string) => void;
  videoLoading: boolean; videoResult: VideoGenResult | null;
  photoPrompt: string; setPhotoPrompt: (v: string) => void;
  photoContentType: string; setPhotoContentType: (v: string) => void;
  photoModel: string; setPhotoModel: (v: string) => void;
  photoUseRef: boolean; setPhotoUseRef: (v: boolean) => void;
  photoSetRef: boolean; setPhotoSetRef: (v: boolean) => void;
  photoLoading: boolean; photoResult: PhotoResult | null;
  presets: ProfilePresets | null;
  onPreview: () => void; onVoice: () => void; onVideo: () => void; onPhoto: () => void;
}) {
  const refCount = selected?.reference_images?.length || 0;

  return (
    <div className="space-y-4">
      {/* ===== PHOTO GENERATION ===== */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Camera className="h-5 w-5 text-emerald-400" /> Генерация фото (fal.ai FLUX)
        </h3>
        <div className="space-y-3">
          {/* Content type selector */}
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Тип контента</label>
            <div className="grid grid-cols-3 gap-2">
              {PHOTO_CONTENT_TYPES.map((ct) => (
                <button
                  key={ct.id}
                  onClick={() => setPhotoContentType(ct.id)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    photoContentType === ct.id
                      ? "bg-emerald-600 text-white ring-1 ring-emerald-400"
                      : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                  }`}
                >
                  {ct.label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom prompt (shown when content_type is custom or always as optional) */}
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">
              Промт {photoContentType !== "custom" && "(необязательно, по умолчанию автогенерация)"}
            </label>
            <textarea
              value={photoPrompt}
              onChange={(e) => setPhotoPrompt(e.target.value)}
              placeholder={photoContentType === "custom"
                ? "Опиши что хочешь сгенерировать..."
                : "Оставь пустым — промт будет сгенерирован автоматически по типу контента"
              }
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              rows={2}
            />
          </div>

          {/* Model + options row */}
          <div className="flex flex-wrap gap-3 items-center">
            <div className="flex-1 min-w-48">
              <label className="text-xs text-zinc-400 mb-1 block">Модель</label>
              <select
                value={photoModel}
                onChange={(e) => setPhotoModel(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              >
                {PHOTO_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-4 pt-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={photoUseRef}
                  onChange={(e) => setPhotoUseRef(e.target.checked)}
                  className="accent-emerald-500"
                />
                <span className="text-xs text-zinc-300">
                  Использовать референсы ({refCount} фото)
                </span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={photoSetRef}
                  onChange={(e) => setPhotoSetRef(e.target.checked)}
                  className="accent-amber-500"
                />
                <span className="text-xs text-zinc-300">
                  <Star className="h-3 w-3 inline text-amber-400" /> Сохранить как референс
                </span>
              </label>
            </div>
          </div>

          {/* Generate button */}
          <button
            onClick={onPhoto}
            disabled={photoLoading}
            className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all"
          >
            {photoLoading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" /> Генерация фото (~10сек)...
              </>
            ) : (
              <>
                <Camera className="h-4 w-4" /> Сгенерировать фото
              </>
            )}
          </button>
          <p className="text-xs text-zinc-500">
            ~${PHOTO_MODELS.find((m) => m.id === photoModel)?.cost || "0.025"} за фото
            {photoUseRef && refCount > 0 && " | Идентичность сохранена через референсы"}
          </p>

          {/* Photo result */}
          {photoResult && (
            <div className={`rounded-lg p-4 ${
              photoResult.success
                ? "bg-green-500/10 border border-green-500/30"
                : "bg-red-500/10 border border-red-500/30"
            }`}>
              {photoResult.success ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-green-400 text-sm font-medium">
                      <Camera className="h-4 w-4" /> Фото сгенерировано!
                    </div>
                    <div className="flex gap-2 text-xs text-zinc-400">
                      <span>{photoResult.model_name}</span>
                      <span>~${(photoResult.cost_estimate || photoResult.total_cost || 0).toFixed(3)}</span>
                      {photoResult.used_reference_images && (
                        <span className="text-amber-400">с референсами</span>
                      )}
                    </div>
                  </div>
                  {/* Image grid */}
                  <div className="grid grid-cols-2 gap-3">
                    {photoResult.images?.map((img, i) => (
                      <div key={i} className="relative group">
                        <img
                          src={img.url}
                          alt={`Generated ${i + 1}`}
                          className="w-full rounded-lg border border-zinc-700"
                          loading="lazy"
                        />
                        <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                          <a
                            href={img.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-black/70 hover:bg-black text-white px-2 py-1 rounded text-xs flex items-center gap-1"
                          >
                            <Download className="h-3 w-3" /> Скачать
                          </a>
                        </div>
                        <div className="text-xs text-zinc-500 mt-1">
                          {img.width}x{img.height}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-red-400 text-sm">{photoResult.error}</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ===== VOICE GENERATION ===== */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Mic className="h-5 w-5 text-pink-400" /> Генерация голоса (ElevenLabs v3)
        </h3>
        <div className="space-y-3">
          <textarea
            value={voiceText}
            onChange={(e) => setVoiceText(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            rows={3}
          />
          <div className="flex gap-3">
            <select
              value={momentType}
              onChange={(e) => setMomentType(e.target.value)}
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              {MOMENT_TYPES.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <button
              onClick={onPreview}
              className="bg-zinc-700 hover:bg-zinc-600 px-4 py-2 rounded-lg text-sm flex items-center gap-2"
            >
              <FileText className="h-4 w-4" /> Превью
            </button>
            <button
              onClick={onVoice}
              disabled={voiceLoading}
              className="bg-pink-600 hover:bg-pink-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm flex items-center gap-2"
            >
              {voiceLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {voiceLoading ? "Генерация..." : "Голос"}
            </button>
          </div>

          {scriptPreview && (
            <div className="bg-zinc-800 rounded-lg p-4 space-y-2">
              <div className="text-xs text-zinc-400">
                Персона: <span className="text-pink-400">{scriptPreview.persona_name}</span>
                {" | "}Момент: <span className="text-violet-400">{scriptPreview.moment_type}</span>
              </div>
              <div className="text-sm font-mono bg-zinc-900 p-3 rounded">{scriptPreview.expressive_text}</div>
              <div className="flex gap-1 flex-wrap">
                {scriptPreview.tags_used.map((tag) => (
                  <span key={tag} className="text-[10px] bg-violet-500/20 text-violet-300 px-1.5 py-0.5 rounded">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {voiceResult && (
            <div className={`rounded-lg p-4 ${
              voiceResult.success
                ? "bg-green-500/10 border border-green-500/30"
                : "bg-red-500/10 border border-red-500/30"
            }`}>
              {voiceResult.success ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-green-400 text-sm font-medium">
                    <Volume2 className="h-4 w-4" /> Голос сгенерирован!
                  </div>
                  {voiceResult.file_path && (
                    <audio
                      controls
                      className="w-full"
                      src={`${API_URL}/api/montage/files/${voiceResult.file_path?.replace("/data/", "")}`}
                    />
                  )}
                  <div className="flex gap-3 text-xs text-zinc-400">
                    <span>Символов: {voiceResult.char_count}</span>
                    <span>Стоимость: ${(voiceResult.cost || 0).toFixed(4)}</span>
                    <span>{voiceResult.engine}</span>
                    <span>{voiceResult.persona}</span>
                  </div>
                  {voiceResult.expressive_text && (
                    <div className="text-xs font-mono bg-zinc-800 p-2 rounded text-zinc-400">
                      {voiceResult.expressive_text}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-red-400 text-sm">{voiceResult.error}</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ===== VIDEO GENERATION ===== */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Video className="h-5 w-5 text-violet-400" /> Генерация видео (Голос + Фото + Lip-sync)
        </h3>
        <div className="space-y-3">
          <textarea
            value={videoText}
            onChange={(e) => setVideoText(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            rows={2}
          />
          <button
            onClick={onVideo}
            disabled={videoLoading}
            className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-50 px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all"
          >
            {videoLoading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" /> Генерация (~30сек)...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4" /> Сгенерировать видео
              </>
            )}
          </button>
          <p className="text-xs text-zinc-500">
            Пайплайн: ElevenLabs v3 голос &rarr; fal.ai фото &rarr; OmniHuman lip-sync
          </p>

          {videoResult && (
            <div className={`rounded-lg p-4 ${
              videoResult.success
                ? "bg-green-500/10 border border-green-500/30"
                : "bg-red-500/10 border border-red-500/30"
            }`}>
              {videoResult.success ? (
                <div className="space-y-2">
                  <div className="text-green-400 text-sm font-medium">
                    Видео создано! ~${(videoResult.total_cost || 0).toFixed(4)}
                  </div>
                  {videoResult.steps?.map((s, i) => (
                    <div key={i} className="text-xs text-zinc-400">
                      {s.step}: {s.result?.success ? "OK" : String(s.result?.error || "?")}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-red-400 text-sm">{videoResult.error}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ========== CONTENT TAB ========== */

function ContentTab({
  costs, contentItems, contentFilter, setContentFilter, selected, setContentItems,
}: {
  costs: CostBreakdown | null;
  contentItems: ContentItem[];
  contentFilter: string;
  setContentFilter: (v: string) => void;
  selected: AIProfile;
  setContentItems: (v: ContentItem[]) => void;
}) {
  return (
    <div className="space-y-4">
      {costs && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-green-400" /> Стоимость
          </h3>
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-zinc-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-green-400">${costs.total_cost.toFixed(2)}</div>
              <div className="text-xs text-zinc-500">Всего</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold">{costs.total_photos}</div>
              <div className="text-xs text-zinc-500">Фото</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold">{costs.total_videos}</div>
              <div className="text-xs text-zinc-500">Видео</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold">{costs.total_posts}</div>
              <div className="text-xs text-zinc-500">Постов</div>
            </div>
          </div>
          {costs.breakdown.length > 0 && costs.breakdown.map((b) => (
            <div key={b.type} className="flex items-center justify-between bg-zinc-800 rounded px-3 py-2 text-sm mb-1">
              <span>{b.type}</span>
              <span className="text-zinc-400">{b.count}x &middot; ${b.cost.toFixed(4)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Image className="h-5 w-5 text-pink-400" /> Галерея
          </h3>
          <div className="flex gap-2">
            {["", "voice", "photo", "video"].map((f) => (
              <button
                key={f}
                onClick={() => {
                  setContentFilter(f);
                  api.getProfileContent(selected.id, f || undefined).then(setContentItems).catch(() => {});
                }}
                className={`text-xs px-3 py-1 rounded ${
                  contentFilter === f ? "bg-pink-600 text-white" : "bg-zinc-800 text-zinc-400"
                }`}
              >
                {f || "Все"}
              </button>
            ))}
          </div>
        </div>
        {contentItems.length === 0 ? (
          <div className="text-center text-zinc-500 text-sm py-8">Нет контента</div>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            {contentItems.map((item) => (
              <div key={item.id} className="bg-zinc-800 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  {item.content_type === "voice" && <Mic className="h-4 w-4 text-pink-400" />}
                  {item.content_type === "photo" && <Image className="h-4 w-4 text-blue-400" />}
                  {item.content_type === "video" && <Video className="h-4 w-4 text-violet-400" />}
                  <span className="text-xs font-medium">{item.title || item.content_type}</span>
                </div>
                <div className="text-xs text-zinc-500 truncate">{item.prompt}</div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-[10px] text-green-400">${item.cost.toFixed(4)}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    item.status === "completed"
                      ? "bg-green-500/20 text-green-400"
                      : "bg-yellow-500/20 text-yellow-400"
                  }`}>
                    {item.status}
                  </span>
                </div>
                {item.file_path && item.content_type === "voice" && (
                  <audio
                    controls
                    className="w-full mt-2 h-8"
                    src={`${API_URL}/api/montage/files/${item.file_path.replace("/data/", "")}`}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ========== SOCIAL TAB ========== */

function SocialTab({
  postPlatform, setPostPlatform, postHashtags, setPostHashtags,
  postCaption, setPostCaption, socialPosts, onSchedule,
}: {
  postPlatform: string; setPostPlatform: (v: string) => void;
  postHashtags: string; setPostHashtags: (v: string) => void;
  postCaption: string; setPostCaption: (v: string) => void;
  socialPosts: SocialPost[];
  onSchedule: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Send className="h-5 w-5 text-blue-400" /> Запланировать пост
        </h3>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <select
              value={postPlatform}
              onChange={(e) => setPostPlatform(e.target.value)}
              className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            >
              <option value="instagram">Instagram</option>
              <option value="tiktok">TikTok</option>
              <option value="telegram">Telegram</option>
            </select>
            <input
              value={postHashtags}
              onChange={(e) => setPostHashtags(e.target.value)}
              className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              placeholder="#cs2, #gaming"
            />
          </div>
          <textarea
            value={postCaption}
            onChange={(e) => setPostCaption(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            rows={2}
            placeholder="Текст поста..."
          />
          <button
            onClick={onSchedule}
            disabled={!postCaption}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm flex items-center gap-2"
          >
            <Clock className="h-4 w-4" /> Запланировать
          </button>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-green-400" /> История постов
        </h3>
        {socialPosts.length === 0 ? (
          <div className="text-center text-zinc-500 text-sm py-8">Постов пока нет</div>
        ) : (
          <div className="space-y-2">
            {socialPosts.map((post) => (
              <div key={post.id} className="bg-zinc-800 rounded-lg p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Hash className="h-4 w-4 text-zinc-500" />
                  <div>
                    <div className="text-sm">{post.caption?.slice(0, 60) || "\u2014"}</div>
                    <div className="text-xs text-zinc-500">{post.platform} &middot; {post.status}</div>
                  </div>
                </div>
                <div className="flex gap-1">
                  {post.hashtags?.slice(0, 3).map((h) => (
                    <span key={h} className="text-[10px] bg-zinc-700 px-1.5 py-0.5 rounded">{h}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ========== BRAIN TAB ========== */

function BrainTab({
  memory, voiceSamples, memoryNotes, setMemoryNotes, onUpdateMemory,
}: {
  memory: MemoryData | null;
  voiceSamples: VoiceSample[];
  memoryNotes: string;
  setMemoryNotes: (v: string) => void;
  onUpdateMemory: () => void;
}) {
  const memStats = (memory?.memory?.stats || {}) as Record<string, number>;
  const memNotes = memory?.memory?.personality_notes;
  const memTags = memory?.memory?.favorite_tags as string[] | undefined;

  return (
    <div className="space-y-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Brain className="h-5 w-5 text-purple-400" /> Память и обучение
        </h3>
        {memory && (
          <div className="space-y-3">
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: "Контент", value: memStats.total_content || 0 },
                { label: "Голоса", value: memStats.total_voice_samples || 0 },
                { label: "Посты", value: memStats.total_social_posts || 0 },
                { label: "Потрачено", value: "$" + (memStats.total_cost || 0).toFixed(2) },
              ].map((s) => (
                <div key={s.label} className="bg-zinc-800 rounded-lg p-3 text-center">
                  <div className="text-lg font-bold">{s.value}</div>
                  <div className="text-xs text-zinc-500">{s.label}</div>
                </div>
              ))}
            </div>
            <div className="bg-zinc-800 rounded-lg p-4">
              <div className="text-xs text-zinc-400 mb-1">Заметки</div>
              <div className="text-sm">{String(memNotes || "Нет заметок")}</div>
            </div>
            {memTags && memTags.length > 0 && (
              <div className="bg-zinc-800 rounded-lg p-4">
                <div className="text-xs text-zinc-400 mb-2">Любимые аудио-теги</div>
                <div className="flex flex-wrap gap-1">
                  {memTags.map((tag) => (
                    <span key={tag} className="text-xs bg-violet-500/20 text-violet-300 px-2 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div>
              <textarea
                value={memoryNotes}
                onChange={(e) => setMemoryNotes(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                rows={2}
                placeholder="Добавь информацию..."
              />
              <button
                onClick={onUpdateMemory}
                disabled={!memoryNotes}
                className="mt-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm"
              >
                Обновить память
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Volume2 className="h-5 w-5 text-pink-400" /> Голосовые семплы ({voiceSamples.length})
        </h3>
        {voiceSamples.length === 0 ? (
          <div className="text-center text-zinc-500 text-sm py-4">Нет семплов</div>
        ) : (
          <div className="space-y-2">
            {voiceSamples.map((s) => (
              <div key={s.id} className="bg-zinc-800 rounded-lg p-3">
                <div className="text-sm truncate">{s.text}</div>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-zinc-500">
                    ${s.cost.toFixed(4)} &middot; {s.created_at?.slice(0, 10)}
                  </span>
                  {s.file_path && (
                    <audio
                      controls
                      className="h-8"
                      src={`${API_URL}/api/montage/files/${s.file_path.replace("/data/", "")}`}
                    />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {memory?.voice_config && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-yellow-400" /> Голосовые настройки
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(memory.voice_config).map(([k, v]) => (
              <div key={k} className="bg-zinc-800 rounded p-2">
                <div className="text-xs text-zinc-500">{k}</div>
                <div className="text-sm">{typeof v === "object" ? JSON.stringify(v) : String(v)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
