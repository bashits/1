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
  GalleryPhoto,
  VoiceIdentity,
  ProfileLearningResponse,
  GeneratedPersona,
  LoraStatus,
  TrainLoraResult,
} from "@/hooks/useApi";
import {
  Plus, Sparkles, Trash2, Mic, Video, Image, Brain, Share2,
  DollarSign, Play, Eye, RefreshCw, Send, Zap,
  Volume2, FileText, ChevronRight, Hash, Clock, BarChart3,
  Camera, Download, Star, Dice5, Loader2, User, Lock, Unlock, Shield,
} from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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
  // Video generation is RunPod-only now (no fal.ai, no LoRA needed)

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

  // LoRA training state
  const [loraStatus, setLoraStatus] = useState<LoraStatus | null>(null);
  const [loraTraining, setLoraTraining] = useState(false);
  const [loraResult, setLoraResult] = useState<TrainLoraResult | null>(null);
  const [loraPolling, setLoraPolling] = useState(false);

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

  // Smart persona generation state
  const [personaPreview, setPersonaPreview] = useState<GeneratedPersona | null>(null);
  const [personaLoading, setPersonaLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createMode, setCreateMode] = useState<"smart" | "manual">("smart");

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
    try {
      setLoraStatus(await api.getLoraStatus(p.id));
    } catch {
      setLoraStatus(null);
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

  const handleGeneratePersona = async () => {
    setPersonaLoading(true);
    try {
      const persona = await api.generatePersona(form.name || undefined);
      setPersonaPreview(persona);
    } catch (e) {
      alert("Ошибка генерации персоны: " + e);
    } finally {
      setPersonaLoading(false);
    }
  };

  const handleCreate = async () => {
    setCreateLoading(true);
    try {
      if (createMode === "smart") {
        // Smart auto-generation
        const p = await api.createProfile({
          name: form.name || undefined,
          auto_generate: true,
          auto_generate_photo: true,
          style: "realistic",
          description: form.description || undefined,
          instagram_handle: form.instagram_handle || undefined,
          tiktok_handle: form.tiktok_handle || undefined,
          telegram_channel: form.telegram_channel || undefined,
        });
        setProfiles([p, ...profiles]);
        selectProfile(p);
      } else {
        // Manual preset-based
        const p = await api.createProfile({
          name: form.name,
          auto_generate: false,
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
        selectProfile(p);
      }
      setShowCreate(false);
      setPersonaPreview(null);
      setForm({
        name: "", style: "realistic", description: "",
        appearance_preset: "realistic_european", personality_preset: "energetic_gamer",
        voice_preset: "energetic_female", voice_persona: "jessica_fire",
        instagram_handle: "", tiktok_handle: "", telegram_channel: "",
      });
    } catch (e) {
      alert("Ошибка создания: " + e);
    } finally {
      setCreateLoading(false);
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
        use_lora: true,
        lora_scale: 1.0,
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

  const handleTrainLora = async () => {
    if (!selected) return;
    setLoraTraining(true);
    setLoraResult(null);
    try {
      const res = await api.trainLora(selected.id, { num_photos: 15, steps: 1000 });
      setLoraResult(res);
      if (res.success) {
        // Start polling for completion
        setLoraPolling(true);
        pollLoraStatus(selected.id);
      }
    } catch (e) {
      setLoraResult({ success: false, error: String(e) });
    } finally {
      setLoraTraining(false);
    }
  };

  const pollLoraStatus = async (profileId: number) => {
    const poll = async () => {
      try {
        const status = await api.getLoraStatus(profileId);
        setLoraStatus(status);
        if (status.lora_status === "training" || status.lora_status === "generating_dataset" || status.lora_status === "queued") {
          setTimeout(poll, 10000); // Poll every 10 seconds
        } else {
          setLoraPolling(false);
          // Refresh profile
          const updated = await api.getProfiles();
          setProfiles(updated);
          const refreshed = updated.find((p) => p.id === profileId);
          if (refreshed) setSelected(refreshed);
        }
      } catch {
        setLoraPolling(false);
      }
    };
    poll();
  };

  const personaGrad = (p: AIProfile) => {
    const pid = (p.voice_config?.persona_id as string) || "jessica_fire";
    return PERSONA_COLORS[pid] || "from-pink-500 to-violet-500";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-lg sm:text-2xl font-bold">AI Девушки</h1>
          <p className="text-zinc-400 text-xs sm:text-sm mt-1">
            Управление персонажами: голос, фото, видео, соцсети, память
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 bg-pink-600 hover:bg-pink-700 active:bg-pink-800 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors shrink-0"
        >
          <Plus className="h-4 w-4" /><span className="hidden sm:inline">Новая девушка</span><span className="sm:hidden">Новая</span>
        </button>
      </div>

      {showCreate && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 sm:p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-pink-400">Создать AI девушку</h3>
            <div className="flex gap-2">
              <button
                onClick={() => setCreateMode("smart")}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  createMode === "smart" ? "bg-pink-600 text-white" : "bg-zinc-800 text-zinc-400 hover:text-white"
                }`}
              >
                <Dice5 className="h-3 w-3 inline mr-1" /> Умная генерация
              </button>
              <button
                onClick={() => setCreateMode("manual")}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  createMode === "manual" ? "bg-pink-600 text-white" : "bg-zinc-800 text-zinc-400 hover:text-white"
                }`}
              >
                <User className="h-3 w-3 inline mr-1" /> Вручную
              </button>
            </div>
          </div>

          {createMode === "smart" ? (
            <div className="space-y-4">
              <div className="bg-gradient-to-r from-pink-500/10 to-violet-500/10 border border-pink-500/20 rounded-lg p-4">
                <p className="text-sm text-zinc-300">
                  Система автоматически сгенерирует <span className="text-pink-400 font-semibold">уникальную</span> девушку
                  с неповторимой внешностью, характером и голосом. Каждая девушка — полностью уникальна.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <label className="block text-xs text-zinc-400 mb-1">Имя (опционально)</label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    placeholder="Оставь пустым — сгенерируется автоматически"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={handleGeneratePersona}
                    disabled={personaLoading}
                    className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors w-full justify-center"
                  >
                    {personaLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Dice5 className="h-4 w-4" />}
                    Превью персоны
                  </button>
                </div>
              </div>

              {personaPreview && (
                <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-pink-500 to-violet-500 flex items-center justify-center text-lg font-bold">
                      {personaPreview.name[0]}
                    </div>
                    <div>
                      <div className="font-semibold text-pink-400">{personaPreview.name}</div>
                      <div className="text-xs text-zinc-500">Архетип: {personaPreview.archetype_name} | Голос: {personaPreview.elevenlabs_voice_name}</div>
                    </div>
                  </div>
                  <p className="text-xs text-zinc-400 leading-relaxed">{personaPreview.bio}</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[10px]">
                    <div className="bg-zinc-900 rounded p-2">
                      <div className="text-zinc-500 mb-1">Внешность</div>
                      <div className="text-zinc-300">{personaPreview.appearance.ethnicity}, {personaPreview.appearance.hair_color} {personaPreview.appearance.hair_style}</div>
                      <div className="text-zinc-300">{personaPreview.appearance.eye_color} глаза, {personaPreview.appearance.skin_tone}</div>
                      <div className="text-zinc-400 mt-1">{personaPreview.appearance.unique_feature}</div>
                    </div>
                    <div className="bg-zinc-900 rounded p-2">
                      <div className="text-zinc-500 mb-1">Характер</div>
                      <div className="text-zinc-300">{personaPreview.personality.tone}</div>
                      <div className="text-zinc-400 mt-1">{personaPreview.personality.catchphrases?.slice(0, 2).join(", ")}</div>
                    </div>
                    <div className="bg-zinc-900 rounded p-2">
                      <div className="text-zinc-500 mb-1">Стиль</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {personaPreview.appearance.style_tags?.map((tag) => (
                          <span key={tag} className="bg-pink-500/20 text-pink-400 px-1.5 py-0.5 rounded text-[9px]">{tag}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                <div>
                  <label className="block text-xs text-zinc-400 mb-1">Instagram</label>
                  <input
                    value={form.instagram_handle}
                    onChange={(e) => setForm({ ...form, instagram_handle: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    placeholder="@handle"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 mb-1">TikTok</label>
                  <input
                    value={form.tiktok_handle}
                    onChange={(e) => setForm({ ...form, tiktok_handle: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    placeholder="@handle"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 mb-1">Telegram</label>
                  <input
                    value={form.telegram_channel}
                    onChange={(e) => setForm({ ...form, telegram_channel: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    placeholder="@channel"
                  />
                </div>
              </div>

              <button
                onClick={handleCreate}
                disabled={createLoading}
                className="flex items-center gap-2 bg-pink-600 hover:bg-pink-700 active:bg-pink-800 disabled:opacity-50 px-4 sm:px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors"
              >
                {createLoading ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Генерация уникальной девушки + фото...</>
                ) : (
                  <><Sparkles className="h-4 w-4" /> Создать уникальную девушку</>
                )}
              </button>
              {createLoading && (
                <p className="text-xs text-zinc-500">Генерируем персону + первое фото... ~15-30 сек</p>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
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
                disabled={!form.name || createLoading}
                className="bg-pink-600 hover:bg-pink-700 disabled:opacity-50 px-6 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {createLoading ? "Создание..." : "Создать профиль"}
              </button>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 md:gap-6">
        <div className="md:col-span-1 space-y-3">
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

        <div className="md:col-span-3 space-y-4">
          {selected ? (
            <>
              <div className="flex gap-1 bg-zinc-900 border border-zinc-800 rounded-xl p-1 overflow-x-auto">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => handleTabChange(t.id)}
                    className={`flex-1 flex items-center justify-center gap-1 sm:gap-2 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors min-w-0 ${
                      tab === t.id
                        ? "bg-pink-600 text-white"
                        : "text-zinc-400 hover:text-white hover:bg-zinc-800 active:bg-zinc-800"
                    }`}
                  >
                    <t.icon className="h-4 w-4 shrink-0" /> <span className="truncate">{t.label}</span>
                  </button>
                ))}
              </div>

              {tab === "overview" && (
                <OverviewTab
                  selected={selected} pipeline={pipeline} personaGrad={personaGrad}
                  loraStatus={loraStatus} loraTraining={loraTraining} loraPolling={loraPolling}
                  loraResult={loraResult} onTrainLora={handleTrainLora}
                />
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
                  selected={selected}
                />
              )}
              {tab === "brain" && (
                <BrainTab
                  memory={memory} voiceSamples={voiceSamples}
                  memoryNotes={memoryNotes} setMemoryNotes={setMemoryNotes}
                  onUpdateMemory={handleUpdateMemory}
                  selected={selected}
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

/* ========== IDENTITY LOCK PANEL ========== */

function IdentityLockPanel({ selected }: { selected: AIProfile }) {
  const [locking, setLocking] = useState(false);
  const [unlocking, setUnlocking] = useState(false);
  const [baseVideos, setBaseVideos] = useState<import("@/hooks/useApi").BaseVideo[]>([]);
  const [lockResult, setLockResult] = useState<import("@/hooks/useApi").IdentityLockResult | null>(null);
  const isLocked = selected.identity_locked;

  useEffect(() => {
    if (isLocked) {
      api.getBaseVideos(selected.id).then((r) => setBaseVideos(r.videos || [])).catch(() => {});
    }
  }, [selected.id, isLocked]);

  const handleLock = async () => {
    setLocking(true);
    setLockResult(null);
    try {
      const res = await api.lockIdentity(selected.id);
      setLockResult(res);
      if (res.success) {
        setBaseVideos(res.videos || []);
      }
    } catch { /* ok */ }
    setLocking(false);
  };

  const handleUnlock = async () => {
    setUnlocking(true);
    try {
      await api.unlockIdentity(selected.id);
      setBaseVideos([]);
      setLockResult(null);
    } catch { /* ok */ }
    setUnlocking(false);
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 sm:p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base sm:text-lg font-semibold flex items-center gap-2">
          <Shield className="h-5 w-5 text-cyan-400" /> Smart Identity Lock
        </h3>
        {isLocked ? (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs bg-green-500/20 text-green-400 px-2.5 py-1 rounded-full">
              <Lock className="h-3 w-3" /> Заблокировано
            </span>
            <button
              onClick={handleUnlock}
              disabled={unlocking}
              className="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded"
            >
              {unlocking ? "..." : "Разблокировать"}
            </button>
          </div>
        ) : (
          <span className="flex items-center gap-1.5 text-xs bg-zinc-700 text-zinc-400 px-2.5 py-1 rounded-full">
            <Unlock className="h-3 w-3" /> Не заблокировано
          </span>
        )}
      </div>

      {!isLocked && !lockResult && (
        <div className="space-y-3">
          <p className="text-sm text-zinc-400">
            Identity Lock находит одну и ту же девушку на Pexels (группировка по фотографу) и фиксирует её видео для генерации.
            Результат: визуальная консистентность — одна и та же модель во всех видео.
          </p>
          <button
            onClick={handleLock}
            disabled={locking}
            className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {locking ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Поиск модели на Pexels...</>
            ) : (
              <><Lock className="h-4 w-4" /> Заблокировать внешность (бесплатно)</>
            )}
          </button>
        </div>
      )}

      {lockResult && lockResult.success && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 mb-3">
          <div className="text-sm text-green-400 font-medium">
            Заблокировано {lockResult.videos_locked} видео от фотографа &ldquo;{lockResult.photographer}&rdquo;
          </div>
        </div>
      )}

      {baseVideos.length > 0 && (
        <div className="space-y-2 mt-3">
          <div className="text-xs text-zinc-400 mb-2">Закреплённые видео ({baseVideos.length}):</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
            {baseVideos.map((v) => (
              <div key={v.id} className="bg-zinc-800 rounded-lg p-2 text-center">
                <div className="text-xs text-zinc-300 truncate">{v.pexels_video_id}</div>
                <div className="text-[10px] text-zinc-500 mt-0.5">
                  {v.width}x{v.height} &middot; {v.duration}s
                </div>
                <div className="text-[10px] text-cyan-400 truncate">{v.photographer}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ========== OVERVIEW TAB ========== */

function OverviewTab({
  selected, pipeline, personaGrad,
  loraStatus, loraTraining, loraPolling, loraResult, onTrainLora,
}: {
  selected: AIProfile;
  pipeline: ProfilePipeline | null;
  personaGrad: (p: AIProfile) => string;
  loraStatus: LoraStatus | null;
  loraTraining: boolean;
  loraPolling: boolean;
  loraResult: TrainLoraResult | null;
  onTrainLora: () => void;
}) {
  const lStatus = loraStatus?.lora_status || selected.lora_training_status || "not_trained";
  const statusColors: Record<string, string> = {
    not_trained: "bg-zinc-700 text-zinc-300",
    sourcing_photos: "bg-amber-500/20 text-amber-400",
    generating_dataset: "bg-yellow-500/20 text-yellow-400",
    training: "bg-blue-500/20 text-blue-400",
    trained: "bg-green-500/20 text-green-400",
    failed: "bg-red-500/20 text-red-400",
  };
  const statusLabels: Record<string, string> = {
    not_trained: "Не обучена",
    sourcing_photos: "Поиск реальных фото модели...",
    generating_dataset: "Генерация датасета...",
    training: "Обучение LoRA...",
    trained: "LoRA обучена",
    failed: "Ошибка обучения",
    queued: "В очереди...",
  };

  return (
    <div className="space-y-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4 mb-4">
          <div className={`w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-gradient-to-br ${personaGrad(selected)} flex items-center justify-center text-xl sm:text-2xl font-bold shrink-0`}>
            {selected.name[0]}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg sm:text-xl font-bold truncate">{selected.name}</h2>
            <p className="text-zinc-400 text-xs sm:text-sm">{selected.description}</p>
            <div className="flex flex-wrap gap-2 sm:gap-3 mt-1 text-xs text-zinc-500">
              {selected.instagram_handle && <span>IG: {selected.instagram_handle}</span>}
              {selected.tiktok_handle && <span>TT: {selected.tiktok_handle}</span>}
              {selected.telegram_channel && <span>TG: {selected.telegram_channel}</span>}
            </div>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-xl sm:text-2xl font-bold text-green-400">${(selected.total_cost || 0).toFixed(2)}</div>
            <div className="text-xs text-zinc-500">потрачено</div>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
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

      {/* LoRA Face Identity Section */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-semibold mb-3 flex items-center gap-2">
          <User className="h-5 w-5 text-pink-400" /> LoRA — Фиксация лица
        </h3>
        <div className="flex items-center gap-4 mb-4">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[lStatus] || statusColors.not_trained}`}>
            {statusLabels[lStatus] || lStatus}
          </span>
          {lStatus === "trained" && selected.lora_trigger_word && (
            <span className="text-xs text-zinc-400">
              Trigger: <code className="text-pink-400 bg-zinc-800 px-1.5 py-0.5 rounded">{selected.lora_trigger_word}</code>
            </span>
          )}
          {lStatus === "trained" && selected.lora_trained_at && (
            <span className="text-xs text-zinc-500">Обучена: {new Date(selected.lora_trained_at).toLocaleDateString()}</span>
          )}
        </div>

        {lStatus === "not_trained" || lStatus === "failed" ? (
          <div className="space-y-3">
            <p className="text-sm text-zinc-400">
              LoRA находит 10-20 реальных фото модели из открытого доступа (Pexels) и обучает модель.
              Результат: живая девушка с фиксированным лицом. ~$2 за обучение, ~$0.05 за фото.
            </p>
            <p className="text-xs text-amber-400">
              Важно: генерация фото доступна только после обучения LoRA.
            </p>
            <button
              onClick={onTrainLora}
              disabled={loraTraining}
              className="flex items-center gap-2 bg-pink-600 hover:bg-pink-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              {loraTraining ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Поиск фото модели...</>
              ) : (
                <><Sparkles className="h-4 w-4" /> Обучить LoRA на реальных фото (~$2, 5-15 мин)</>
              )}
            </button>
            {lStatus === "failed" && loraResult?.error && (
              <p className="text-xs text-red-400">Ошибка: {loraResult.error}</p>
            )}
          </div>
        ) : lStatus === "training" || lStatus === "generating_dataset" || lStatus === "sourcing_photos" || lStatus === "queued" ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
              <span className="text-sm text-blue-400">
                {lStatus === "sourcing_photos" ? "Поиск реальных фото модели (Pexels)..." :
                 lStatus === "generating_dataset" ? "Подготовка датасета из реальных фото..." :
                 lStatus === "queued" ? "В очереди на обучение..." :
                 "Обучение LoRA на реальных фото... (5-15 мин)"}
              </span>
            </div>
            {loraResult?.training_photos && (
              <p className="text-xs text-zinc-500">{loraResult.training_photos} фото загружено, {loraResult.steps} шагов обучения</p>
            )}
            {loraPolling && <p className="text-xs text-zinc-600">Автоматическая проверка каждые 10 сек...</p>}
          </div>
        ) : lStatus === "trained" ? (
          <div className="space-y-2">
            <p className="text-sm text-green-400 font-medium">
              LoRA обучена на реальных фото! Генерация фото доступна — лицо зафиксировано.
            </p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-zinc-800 rounded-lg p-3">
                <div className="text-zinc-400">Стоимость обучения</div>
                <div className="text-lg font-bold text-green-400">$2.00</div>
              </div>
              <div className="bg-zinc-800 rounded-lg p-3">
                <div className="text-zinc-400">Стоимость за фото</div>
                <div className="text-lg font-bold text-green-400">$0.05</div>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Smart Identity Lock (Pexels Video Consistency) */}
      <IdentityLockPanel selected={selected} />

      {pipeline?.voice_persona && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Volume2 className="h-5 w-5 text-violet-400" /> Голосовая персона
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
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
  { id: "portrait", label: "Портрет" },
  { id: "pool_luxury", label: "Бассейн / Люкс" },
  { id: "beach_sunset", label: "Пляж / Закат" },
  { id: "instagram_lifestyle", label: "Лайфстайл" },
  { id: "instagram_glam", label: "Глэм / Вечер" },
  { id: "wine_evening", label: "Вино / Терраса" },
  { id: "morning_coffee", label: "Кофе / Утро" },
  { id: "travel_exotic", label: "Путешествие" },
  { id: "fitness_gym", label: "Фитнес" },
  { id: "selfie", label: "Селфи" },
  { id: "intimate_cozy", label: "Будуар" },
  { id: "full_body", label: "В полный рост" },
  { id: "outdoor", label: "На улице" },
  { id: "gaming_reaction", label: "Гейм реакция" },
  { id: "gaming_chill", label: "Гейм чилл" },
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

          {/* Custom prompt with smart interpreter hint */}
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">
              Промт {photoContentType !== "custom" && "(необязательно, по умолчанию автогенерация)"}
            </label>
            <textarea
              value={photoPrompt}
              onChange={(e) => setPhotoPrompt(e.target.value)}
              placeholder={photoContentType === "custom"
                ? "Пиши на русском! Например: красное платье на пляже, селфи в кафе с кофе, в спортзале в топике..."
                : "Оставь пустым — промт будет сгенерирован автоматически по типу контента"
              }
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              rows={2}
            />
            <p className="text-xs text-violet-400/70 mt-1">
              Smart Prompt: пиши на русском — система сама переведёт в профессиональный EN промт с реализмом
            </p>
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

          {/* Generate button — blocked without LoRA */}
          {selected?.lora_training_status !== "trained" ? (
            <div className="w-full bg-zinc-800 border border-amber-500/30 px-4 py-3 rounded-lg text-center">
              <p className="text-sm text-amber-400 font-medium mb-1">
                Генерация заблокирована — сначала обучите LoRA
              </p>
              <p className="text-xs text-zinc-400">
                {selected?.lora_training_status === "training" || selected?.lora_training_status === "sourcing_photos"
                  ? "Обучение уже идёт... Подождите 5-15 минут."
                  : "Перейдите в таб 'Обзор' и нажмите 'Обучить LoRA на реальных фото'"}
              </p>
            </div>
          ) : (
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
                  <Camera className="h-4 w-4" /> Сгенерировать фото (LoRA)
                </>
              )}
            </button>
          )}
          <p className="text-xs text-zinc-500">
            {selected?.lora_training_status === "trained" ? (
              <span className="text-green-400">LoRA обучена на реальных фото — лицо зафиксировано (~$0.05/фото)</span>
            ) : (
              <span className="text-amber-400">LoRA не обучена — генерация недоступна</span>
            )}
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
                      {photoResult.used_lora && (
                        <span className="text-green-400">LoRA ✓</span>
                      )}
                      {photoResult.used_reference_images && !photoResult.used_lora && (
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
                      src={`${API_URL}/api/montage/files/${voiceResult.file_path?.split("/").slice(-2).join("/")}`}
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

      {/* ===== VIDEO GENERATION (RunPod LatentSync 1.6) ===== */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Video className="h-5 w-5 text-violet-400" /> Генерация видео (RunPod LatentSync 1.6)
        </h3>
        <div className="space-y-3">
          <textarea
            value={videoText}
            onChange={(e) => setVideoText(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            rows={2}
            placeholder="Текст для озвучки — длительность видео = длительность речи"
          />

          {/* Pipeline info */}
          <div className="bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20 rounded-lg p-3">
            <p className="text-xs text-emerald-400 font-semibold mb-1">RunPod Serverless — LatentSync 1.6</p>
            <p className="text-[10px] text-zinc-400">
              edge-tts голос (FREE) + Pexels базовое видео (FREE) + LatentSync 1.6 lip-sync (~$0.009/3с GPU).
              Длительность видео = длительность озвучки текста.
            </p>
          </div>

          {/* Generate button — always available, no LoRA needed */}
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
                <Zap className="h-4 w-4" /> Сгенерировать видео (~$0.009/3с)
              </>
            )}
          </button>
          <p className="text-xs text-emerald-400">
            Pexels видео + edge-tts голос (FREE) + LatentSync 1.6 lip-sync (RunPod)
          </p>

          {videoResult && (
            <div className={`rounded-lg p-4 ${
              videoResult.success
                ? "bg-green-500/10 border border-green-500/30"
                : "bg-red-500/10 border border-red-500/30"
            }`}>
              {videoResult.success ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="text-green-400 text-sm font-medium">
                      Видео создано! ~${(videoResult.total_cost || 0).toFixed(4)}
                    </div>
                  </div>
                  {/* Video player */}
                  {(() => {
                    const lipsyncStep = videoResult.steps?.find((s) => s.step === "lipsync");
                    const res = lipsyncStep?.result as Record<string, unknown> | undefined;
                    const videoObj = res?.video as Record<string, unknown> | undefined;
                    const videoUrl = (videoObj?.url as string) || (res?.video_url as string);
                    if (videoUrl) {
                      return (
                        <div className="space-y-2">
                          <video
                            controls
                            className="w-full rounded-lg border border-zinc-700"
                            src={videoUrl}
                            preload="metadata"
                          />
                          <a
                            href={videoUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            download
                            className="inline-flex items-center gap-2 bg-violet-600 hover:bg-violet-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                          >
                            <Download className="h-4 w-4" /> Скачать видео
                          </a>
                        </div>
                      );
                    }
                    return null;
                  })()}
                  {/* Step results */}
                  <div className="flex flex-wrap gap-3 text-xs">
                    {videoResult.steps?.map((s, i) => (
                      <span key={i} className={s.result?.success ? "text-green-400" : "text-red-400"}>
                        {s.step}: {s.result?.success ? "OK" : String(s.result?.error || "?")}
                      </span>
                    ))}
                  </div>
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
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  const photos = contentItems.filter((i) => i.content_type === "photo");
  const videos = contentItems.filter((i) => i.content_type === "video");
  const voices = contentItems.filter((i) => i.content_type === "voice");

  const FILTERS = [
    { id: "", label: "Все", icon: Eye, count: contentItems.length },
    { id: "photo", label: "Фото", icon: Camera, count: photos.length },
    { id: "video", label: "Видео", icon: Video, count: videos.length },
    { id: "voice", label: "Голос", icon: Mic, count: voices.length },
  ];

  return (
    <div className="space-y-4">
      {/* Cost summary bar */}
      {costs && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-green-400" /> Статистика
            </h3>
            <div className="flex gap-4">
              <div className="text-center">
                <div className="text-sm font-bold text-green-400">${costs.total_cost.toFixed(2)}</div>
                <div className="text-[10px] text-zinc-500">Потрачено</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-bold">{costs.total_photos}</div>
                <div className="text-[10px] text-zinc-500">Фото</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-bold">{costs.total_videos}</div>
                <div className="text-[10px] text-zinc-500">Видео</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-bold">{voices.length}</div>
                <div className="text-[10px] text-zinc-500">Голосов</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters and view mode */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => {
                setContentFilter(f.id);
                api.getProfileContent(selected.id, f.id || undefined).then(setContentItems).catch(() => {});
              }}
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-all ${
                contentFilter === f.id
                  ? "bg-pink-600 text-white"
                  : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
              }`}
            >
              <f.icon className="h-3 w-3" /> {f.label} ({f.count})
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setViewMode("grid")}
            className={`p-1.5 rounded ${viewMode === "grid" ? "bg-zinc-700 text-white" : "text-zinc-500"}`}
          >
            <Image className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`p-1.5 rounded ${viewMode === "list" ? "bg-zinc-700 text-white" : "text-zinc-500"}`}
          >
            <FileText className="h-4 w-4" />
          </button>
        </div>
      </div>

      {contentItems.length === 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
          <Camera className="h-10 w-10 text-zinc-600 mx-auto mb-3" />
          <div className="text-zinc-500 text-sm">Нет контента</div>
          <div className="text-zinc-600 text-xs mt-1">Сгенерируй фото или видео во вкладке "Генерация"</div>
        </div>
      ) : viewMode === "grid" ? (
        /* ===== GRID VIEW — photos as thumbnails, voice as cards, video as players ===== */
        <div className="grid grid-cols-3 gap-3">
          {contentItems.map((item) => (
            <div key={item.id} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden group relative">
              {/* Photo — show actual image */}
              {item.content_type === "photo" && item.file_url && (
                <div className="relative cursor-pointer" onClick={() => setLightboxUrl(item.file_url)}>
                  <img
                    src={item.file_url}
                    alt={item.title || "Photo"}
                    className="w-full aspect-square object-cover"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center">
                    <Eye className="h-6 w-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  {/* Type badge */}
                  <div className="absolute top-2 left-2">
                    <span className="bg-blue-500/80 text-white text-[9px] px-1.5 py-0.5 rounded font-medium backdrop-blur-sm">
                      <Camera className="h-2.5 w-2.5 inline mr-0.5" /> ФОТО
                    </span>
                  </div>
                </div>
              )}
              {/* Photo without URL — fallback card */}
              {item.content_type === "photo" && !item.file_url && (
                <div className="w-full aspect-square bg-zinc-800 flex items-center justify-center">
                  <Camera className="h-8 w-8 text-zinc-600" />
                </div>
              )}
              {/* Video — show player */}
              {item.content_type === "video" && (
                <div className="relative">
                  {item.file_url ? (
                    <video
                      src={item.file_url}
                      className="w-full aspect-video object-cover"
                      controls
                      preload="metadata"
                    />
                  ) : item.file_path ? (
                    <video
                      src={`${API_URL}/api/montage/files/${item.file_path.split("/").slice(-2).join("/")}`}
                      className="w-full aspect-video object-cover"
                      controls
                      preload="metadata"
                    />
                  ) : (
                    <div className="w-full aspect-video bg-zinc-800 flex items-center justify-center">
                      <Video className="h-8 w-8 text-zinc-600" />
                    </div>
                  )}
                  <div className="absolute top-2 left-2">
                    <span className="bg-violet-500/80 text-white text-[9px] px-1.5 py-0.5 rounded font-medium backdrop-blur-sm">
                      <Video className="h-2.5 w-2.5 inline mr-0.5" /> ВИДЕО
                    </span>
                  </div>
                </div>
              )}
              {/* Voice — audio card with waveform style */}
              {item.content_type === "voice" && (
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-10 h-10 rounded-full bg-pink-500/20 flex items-center justify-center flex-shrink-0">
                      <Mic className="h-5 w-5 text-pink-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium truncate">{item.title || "Голос"}</div>
                      <div className="text-[10px] text-zinc-500">{item.duration ? `${item.duration}с` : ""}</div>
                    </div>
                    <span className="bg-pink-500/80 text-white text-[9px] px-1.5 py-0.5 rounded font-medium">
                      ГОЛОС
                    </span>
                  </div>
                  {item.file_path && (
                    <audio
                      controls
                      className="w-full h-8"
                      src={`${API_URL}/api/montage/files/${item.file_path.split("/").slice(-2).join("/")}`}
                    />
                  )}
                </div>
              )}
              {/* Info bar at bottom */}
              <div className="px-3 py-2 flex items-center justify-between border-t border-zinc-800">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-green-400 font-medium">${item.cost.toFixed(3)}</span>
                  <span className="text-[10px] text-zinc-600">&middot;</span>
                  <span className="text-[10px] text-zinc-500">{item.created_at?.slice(0, 10)}</span>
                </div>
                <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                  item.status === "completed"
                    ? "bg-green-500/20 text-green-400"
                    : "bg-yellow-500/20 text-yellow-400"
                }`}>
                  {item.status === "completed" ? "OK" : item.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* ===== LIST VIEW ===== */
        <div className="space-y-2">
          {contentItems.map((item) => (
            <div key={item.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 flex items-center gap-3">
              {/* Thumbnail */}
              <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 bg-zinc-800">
                {item.content_type === "photo" && item.file_url ? (
                  <img src={item.file_url} alt="" className="w-full h-full object-cover cursor-pointer" onClick={() => setLightboxUrl(item.file_url)} loading="lazy" />
                ) : item.content_type === "video" ? (
                  <div className="w-full h-full flex items-center justify-center"><Video className="h-6 w-6 text-violet-400" /></div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center"><Mic className="h-6 w-6 text-pink-400" /></div>
                )}
              </div>
              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                    item.content_type === "photo" ? "bg-blue-500/20 text-blue-400" :
                    item.content_type === "video" ? "bg-violet-500/20 text-violet-400" :
                    "bg-pink-500/20 text-pink-400"
                  }`}>
                    {item.content_type === "photo" ? "ФОТО" : item.content_type === "video" ? "ВИДЕО" : "ГОЛОС"}
                  </span>
                  <span className="text-xs font-medium truncate">{item.title || item.content_type}</span>
                </div>
                <div className="text-[10px] text-zinc-500 truncate mt-0.5">{item.prompt}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] text-green-400">${item.cost.toFixed(3)}</span>
                  <span className="text-[10px] text-zinc-600">{item.created_at?.slice(0, 16)}</span>
                </div>
              </div>
              {/* Audio player for voice items */}
              {item.content_type === "voice" && item.file_path && (
                <audio controls className="h-8 w-40 flex-shrink-0" src={`${API_URL}/api/montage/files/${item.file_path.split("/").slice(-2).join("/")}`} />
              )}
              {/* Open link for photos/videos */}
              {item.file_url && item.content_type !== "voice" && (
                <a href={item.file_url} target="_blank" rel="noopener noreferrer" className="text-zinc-400 hover:text-white p-1">
                  <Download className="h-4 w-4" />
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Lightbox */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center cursor-pointer"
          onClick={() => setLightboxUrl(null)}
        >
          <img src={lightboxUrl} alt="Full size" className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg" />
          <div className="absolute top-4 right-4 flex gap-2">
            <a
              href={lightboxUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="bg-zinc-800 hover:bg-zinc-700 text-white px-3 py-2 rounded-lg text-sm flex items-center gap-1"
            >
              <Download className="h-4 w-4" /> Скачать
            </a>
            <button
              onClick={() => setLightboxUrl(null)}
              className="bg-zinc-800 hover:bg-zinc-700 text-white px-3 py-2 rounded-lg text-sm"
            >
              Закрыть
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ========== SOCIAL TAB (Instagram Autopilot) ========== */

function SocialTab({
  postPlatform, setPostPlatform, postHashtags, setPostHashtags,
  postCaption, setPostCaption, socialPosts, onSchedule, selected,
}: {
  postPlatform: string; setPostPlatform: (v: string) => void;
  postHashtags: string; setPostHashtags: (v: string) => void;
  postCaption: string; setPostCaption: (v: string) => void;
  socialPosts: SocialPost[];
  onSchedule: () => void;
  selected: AIProfile;
}) {
  const [autopilotConfig, setAutopilotConfig] = useState<import("@/hooks/useApi").AutopilotConfig | null>(null);
  const [calendar, setCalendar] = useState<import("@/hooks/useApi").CalendarEntry[]>([]);
  const [analytics, setAnalytics] = useState<import("@/hooks/useApi").AutopilotAnalytics | null>(null);
  const [captionResult, setCaptionResult] = useState<import("@/hooks/useApi").CaptionResult | null>(null);
  const [captionLoading, setCaptionLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [autopilotSection, setAutopilotSection] = useState<"schedule" | "calendar" | "captions" | "analytics">("schedule");

  useEffect(() => {
    api.getAutopilot(selected.id).then(setAutopilotConfig).catch(() => {});
    api.getCalendar(selected.id).then((r) => setCalendar(r.entries || [])).catch(() => {});
    api.getAutopilotAnalytics(selected.id).then(setAnalytics).catch(() => {});
  }, [selected.id]);

  const handleToggleAutopilot = async () => {
    if (!autopilotConfig) return;
    const updated = await api.updateAutopilot(selected.id, { is_active: !autopilotConfig.is_active });
    setAutopilotConfig(updated);
  };

  const handleGenerateCalendar = async () => {
    setCalendarLoading(true);
    try {
      const res = await api.generateCalendar(selected.id, 7, 2);
      setCalendar(res.entries || []);
    } catch { /* ok */ }
    setCalendarLoading(false);
  };

  const handleGenerateCaption = async (momentType: string) => {
    setCaptionLoading(true);
    try {
      const res = await api.generateCaption(selected.id, momentType);
      setCaptionResult(res);
    } catch { /* ok */ }
    setCaptionLoading(false);
  };

  const AP_SECTIONS = [
    { id: "schedule" as const, label: "Пост", icon: Send },
    { id: "calendar" as const, label: "Календарь", icon: Clock },
    { id: "captions" as const, label: "Подписи", icon: FileText },
    { id: "analytics" as const, label: "Аналитика", icon: BarChart3 },
  ];

  return (
    <div className="space-y-4">
      {/* Autopilot Status Bar */}
      <div className="bg-gradient-to-r from-purple-900/30 to-pink-900/30 border border-purple-500/20 rounded-xl p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${autopilotConfig?.is_active ? "bg-green-500 animate-pulse" : "bg-zinc-600"}`} />
            <div>
              <div className="text-sm font-semibold">Instagram Автопилот</div>
              <div className="text-xs text-zinc-400">
                {autopilotConfig?.is_active ? "Активен" : "Выключен"}
                {autopilotConfig?.instagram_username && ` \u2014 @${autopilotConfig.instagram_username}`}
              </div>
            </div>
          </div>
          <button
            onClick={handleToggleAutopilot}
            className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              autopilotConfig?.is_active
                ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                : "bg-green-500/20 text-green-400 hover:bg-green-500/30"
            }`}
          >
            {autopilotConfig?.is_active ? "Выключить" : "Включить"}
          </button>
        </div>
        {analytics && (
          <div className="grid grid-cols-4 gap-2 mt-3">
            {[
              { label: "Контент", value: analytics.content.total_content || 0 },
              { label: "Запланировано", value: analytics.calendar.total_planned || 0 },
              { label: "Опубликовано", value: analytics.calendar.total_posted || 0 },
              { label: "Память", value: analytics.memory_entries || 0 },
            ].map((s) => (
              <div key={s.label} className="bg-zinc-800/50 rounded-lg p-2 text-center">
                <div className="text-lg font-bold">{s.value}</div>
                <div className="text-xs text-zinc-500">{s.label}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section Tabs */}
      <div className="flex gap-1 bg-zinc-900 rounded-lg p-1">
        {AP_SECTIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => setAutopilotSection(s.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-medium transition-colors ${
              autopilotSection === s.id ? "bg-zinc-700 text-white" : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            <s.icon className="h-3.5 w-3.5" /> {s.label}
          </button>
        ))}
      </div>

      {/* Schedule Post Section */}
      {autopilotSection === "schedule" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 sm:p-6 space-y-4">
          <h3 className="text-base font-semibold flex items-center gap-2">
            <Send className="h-5 w-5 text-blue-400" /> Запланировать пост
          </h3>
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
            rows={3}
            placeholder="Текст поста..."
          />
          <button
            onClick={onSchedule}
            disabled={!postCaption}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm flex items-center gap-2"
          >
            <Clock className="h-4 w-4" /> Запланировать
          </button>

          {/* Post History */}
          <div className="border-t border-zinc-800 pt-4 mt-4">
            <h4 className="text-sm font-medium text-zinc-400 mb-3">История постов</h4>
            {socialPosts.length === 0 ? (
              <div className="text-center text-zinc-600 text-xs py-4">Постов пока нет</div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {socialPosts.map((post) => (
                  <div key={post.id} className="bg-zinc-800 rounded-lg p-3 flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <Hash className="h-4 w-4 text-zinc-500 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-sm truncate">{post.caption?.slice(0, 50) || "\u2014"}</div>
                        <div className="text-xs text-zinc-500">{post.platform} &middot; {post.status}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Content Calendar */}
      {autopilotSection === "calendar" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 sm:p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-400" /> Контент-календарь
            </h3>
            <button
              onClick={handleGenerateCalendar}
              disabled={calendarLoading}
              className="flex items-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            >
              {calendarLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Сгенерировать на 7 дней
            </button>
          </div>
          {calendar.length === 0 ? (
            <div className="text-center py-8">
              <Clock className="h-8 w-8 mx-auto text-zinc-600 mb-2" />
              <div className="text-sm text-zinc-500">Контент-календарь пуст</div>
              <div className="text-xs text-zinc-600 mt-1">Нажмите кнопку выше для генерации плана на неделю</div>
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {calendar.map((entry, i) => (
                <div key={i} className="bg-zinc-800 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        entry.content_type === "reel" ? "bg-pink-500/20 text-pink-400" :
                        entry.content_type === "story" ? "bg-blue-500/20 text-blue-400" :
                        "bg-violet-500/20 text-violet-400"
                      }`}>
                        {entry.content_type}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        entry.status === "planned" ? "bg-amber-500/10 text-amber-400" :
                        entry.status === "posted" ? "bg-green-500/10 text-green-400" :
                        "bg-zinc-700 text-zinc-400"
                      }`}>
                        {entry.status === "planned" ? "запланирован" : entry.status}
                      </span>
                    </div>
                    <span className="text-xs text-zinc-500">
                      {new Date(entry.planned_date).toLocaleDateString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <div className="text-sm text-zinc-300">{entry.topic}</div>
                  <div className="text-xs text-zinc-500 mt-1 line-clamp-2">{entry.caption_draft}</div>
                  {entry.hashtags?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {entry.hashtags.slice(0, 5).map((h, j) => (
                        <span key={j} className="text-xs bg-zinc-700 text-zinc-400 px-1.5 py-0.5 rounded">{h}</span>
                      ))}
                      {entry.hashtags.length > 5 && (
                        <span className="text-xs text-zinc-600">+{entry.hashtags.length - 5}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Smart Captions Generator */}
      {autopilotSection === "captions" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 sm:p-6 space-y-4">
          <h3 className="text-base font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5 text-violet-400" /> Генератор подписей
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {["clutch", "ace", "highlight", "generic", "meme"].map((type) => (
              <button
                key={type}
                onClick={() => handleGenerateCaption(type)}
                disabled={captionLoading}
                className="bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 px-3 py-2 rounded-lg text-xs font-medium transition-colors capitalize"
              >
                {type}
              </button>
            ))}
          </div>
          {captionResult && (
            <div className="bg-zinc-800 rounded-lg p-4 space-y-3">
              <div className="text-sm whitespace-pre-line">{captionResult.caption}</div>
              <div className="border-t border-zinc-700 pt-2">
                <div className="text-xs text-zinc-400 mb-1">Хештеги ({captionResult.hashtags.length}):</div>
                <div className="flex flex-wrap gap-1">
                  {captionResult.hashtags.map((h, i) => (
                    <span key={i} className="text-xs bg-violet-500/20 text-violet-300 px-1.5 py-0.5 rounded">{h}</span>
                  ))}
                </div>
              </div>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`${captionResult.caption}\n\n${captionResult.hashtags_text}`);
                }}
                className="text-xs text-violet-400 hover:text-violet-300"
              >
                Копировать всё
              </button>
            </div>
          )}
        </div>
      )}

      {/* Analytics */}
      {autopilotSection === "analytics" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 sm:p-6 space-y-4">
          <h3 className="text-base font-semibold flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-green-400" /> Аналитика автопилота
          </h3>
          {analytics ? (
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-zinc-800 rounded-lg p-4">
                <div className="text-xs text-zinc-400 mb-1">Контент</div>
                <div className="text-2xl font-bold">{analytics.content.total_content || 0}</div>
                <div className="flex gap-3 mt-1 text-xs text-zinc-500">
                  <span>Видео: {analytics.content.total_videos || 0}</span>
                  <span>Фото: {analytics.content.total_photos || 0}</span>
                </div>
              </div>
              <div className="bg-zinc-800 rounded-lg p-4">
                <div className="text-xs text-zinc-400 mb-1">Затраты</div>
                <div className="text-2xl font-bold text-green-400">${(analytics.content.total_cost || 0).toFixed(2)}</div>
                <div className="text-xs text-zinc-500 mt-1">за весь контент</div>
              </div>
              <div className="bg-zinc-800 rounded-lg p-4">
                <div className="text-xs text-zinc-400 mb-1">Публикации</div>
                <div className="text-2xl font-bold">{analytics.social.total_posts || 0}</div>
                <div className="flex gap-3 mt-1 text-xs text-zinc-500">
                  <span>IG: {analytics.social.instagram_posts || 0}</span>
                  <span>TT: {analytics.social.tiktok_posts || 0}</span>
                </div>
              </div>
              <div className="bg-zinc-800 rounded-lg p-4">
                <div className="text-xs text-zinc-400 mb-1">Календарь</div>
                <div className="text-2xl font-bold">{analytics.calendar.total_planned || 0}</div>
                <div className="text-xs text-zinc-500 mt-1">
                  Опубликовано: {analytics.calendar.total_posted || 0}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-zinc-500 text-sm py-8">Загрузка аналитики...</div>
          )}
        </div>
      )}
    </div>
  );
}

/* ========== BRAIN TAB ========== */

function BrainTab({
  memory, voiceSamples, memoryNotes, setMemoryNotes, onUpdateMemory, selected,
}: {
  memory: MemoryData | null;
  voiceSamples: VoiceSample[];
  memoryNotes: string;
  setMemoryNotes: (v: string) => void;
  onUpdateMemory: () => void;
  selected: AIProfile | null;
}) {
  const [gallery, setGallery] = useState<GalleryPhoto[]>([]);
  const [voiceId, setVoiceId] = useState<VoiceIdentity | null>(null);
  const [learning, setLearning] = useState<ProfileLearningResponse | null>(null);
  const [brainSection, setBrainSection] = useState<"memory" | "gallery" | "voice" | "learning">("memory");

  useEffect(() => {
    if (!selected) return;
    api.getProfileGallery(selected.id).then((r) => setGallery(r.gallery)).catch(() => {});
    api.getVoiceIdentity(selected.id).then(setVoiceId).catch(() => {});
    api.getProfileLearning(selected.id).then(setLearning).catch(() => {});
  }, [selected]);

  const handleApprove = async (photoId: number, asRef: boolean) => {
    if (!selected) return;
    await api.approveGalleryPhoto(selected.id, photoId, { set_as_reference: asRef, quality_rating: 5 });
    const r = await api.getProfileGallery(selected.id);
    setGallery(r.gallery);
  };

  const handleDeletePhoto = async (photoId: number) => {
    if (!selected) return;
    await api.deleteGalleryPhoto(selected.id, photoId);
    setGallery(gallery.filter((g) => g.id !== photoId));
  };

  const memStats = (memory?.memory?.stats || {}) as Record<string, number>;
  const memNotes = memory?.memory?.personality_notes;
  const memTags = memory?.memory?.favorite_tags as string[] | undefined;
  const genHistory = (memory?.memory?.generation_history || []) as { type: string; content_type: string; cost: number; timestamp: string }[];

  const BRAIN_SECTIONS = [
    { id: "memory" as const, label: "Память", icon: Brain },
    { id: "gallery" as const, label: `Галерея (${gallery.length})`, icon: Image },
    { id: "voice" as const, label: "Голос", icon: Volume2 },
    { id: "learning" as const, label: `Обучение (${learning?.total_learned_prompts || 0})`, icon: BarChart3 },
  ];

  return (
    <div className="space-y-4">
      {/* Section tabs */}
      <div className="flex gap-2">
        {BRAIN_SECTIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => setBrainSection(s.id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              brainSection === s.id
                ? "bg-purple-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
            }`}
          >
            <s.icon className="h-3.5 w-3.5" /> {s.label}
          </button>
        ))}
      </div>

      {/* ===== MEMORY SECTION ===== */}
      {brainSection === "memory" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-400" /> Память профиля
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
              {/* Generation history */}
              {genHistory.length > 0 && (
                <div className="bg-zinc-800 rounded-lg p-4">
                  <div className="text-xs text-zinc-400 mb-2">История генераций (последние 10)</div>
                  <div className="space-y-1">
                    {genHistory.slice(0, 10).map((h, i) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="text-zinc-300">
                          {h.type === "photo" ? "Фото" : h.type} &middot; {h.content_type}
                        </span>
                        <span className="text-zinc-500">
                          ${(h.cost || 0).toFixed(3)} &middot; {h.timestamp?.slice(0, 10)}
                        </span>
                      </div>
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
                  placeholder="Добавь информацию о персонаже..."
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
      )}

      {/* ===== GALLERY SECTION (Cloud URLs) ===== */}
      {brainSection === "gallery" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Image className="h-5 w-5 text-emerald-400" /> Галерея фото (облако, {gallery.length} шт)
          </h3>
          {gallery.length === 0 ? (
            <div className="text-center text-zinc-500 text-sm py-8">
              Нет фото. Сгенерируй во вкладке "Генерация"
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              {gallery.map((photo) => (
                <div key={photo.id} className="relative group">
                  <img
                    src={photo.image_url}
                    alt={photo.content_type}
                    className={`w-full aspect-square object-cover rounded-lg border ${
                      photo.is_reference ? "border-amber-500 ring-2 ring-amber-500/30" : "border-zinc-700"
                    }`}
                    loading="lazy"
                  />
                  {/* Badges */}
                  <div className="absolute top-1 left-1 flex gap-1">
                    {photo.is_reference === 1 && (
                      <span className="bg-amber-500 text-black text-[9px] px-1.5 py-0.5 rounded font-bold">REF</span>
                    )}
                    {photo.is_favorite === 1 && (
                      <span className="bg-pink-500 text-white text-[9px] px-1.5 py-0.5 rounded">FAV</span>
                    )}
                  </div>
                  {/* Hover actions */}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex flex-col items-center justify-center gap-2">
                    <div className="text-xs text-zinc-300">{photo.content_type}</div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleApprove(photo.id, true)}
                        className="bg-amber-600 hover:bg-amber-700 text-white text-xs px-2 py-1 rounded"
                      >
                        <Star className="h-3 w-3 inline" /> Референс
                      </button>
                      <a
                        href={photo.image_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-zinc-600 hover:bg-zinc-500 text-white text-xs px-2 py-1 rounded"
                      >
                        <Download className="h-3 w-3 inline" /> Скачать
                      </a>
                      <button
                        onClick={() => handleDeletePhoto(photo.id)}
                        className="bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-1 rounded"
                      >
                        <Trash2 className="h-3 w-3 inline" />
                      </button>
                    </div>
                    <div className="text-[10px] text-zinc-400">
                      ${photo.cost.toFixed(3)} &middot; {photo.created_at?.slice(0, 10)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ===== VOICE IDENTITY SECTION ===== */}
      {brainSection === "voice" && (
        <div className="space-y-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Mic className="h-5 w-5 text-pink-400" /> Голосовая идентичность
            </h3>
            {voiceId && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-zinc-800 rounded-lg p-3">
                    <div className="text-xs text-zinc-500">Провайдер</div>
                    <div className="text-sm font-medium">{voiceId.provider}</div>
                  </div>
                  <div className="bg-zinc-800 rounded-lg p-3">
                    <div className="text-xs text-zinc-500">Voice ID</div>
                    <div className="text-sm font-mono truncate">{voiceId.voice_id || "Не назначен"}</div>
                  </div>
                  <div className="bg-zinc-800 rounded-lg p-3">
                    <div className="text-xs text-zinc-500">Стиль речи</div>
                    <div className="text-sm">{voiceId.speaking_style || "natural"}</div>
                  </div>
                  <div className="bg-zinc-800 rounded-lg p-3">
                    <div className="text-xs text-zinc-500">Язык</div>
                    <div className="text-sm">{voiceId.language || "en"}</div>
                  </div>
                </div>
                {voiceId.audio_tags && voiceId.audio_tags.length > 0 && (
                  <div className="bg-zinc-800 rounded-lg p-4">
                    <div className="text-xs text-zinc-400 mb-2">Аудио-теги</div>
                    <div className="flex flex-wrap gap-1">
                      {voiceId.audio_tags.map((tag) => (
                        <span key={tag} className="text-xs bg-pink-500/20 text-pink-300 px-2 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {voiceId.personality_traits && voiceId.personality_traits.length > 0 && (
                  <div className="bg-zinc-800 rounded-lg p-4">
                    <div className="text-xs text-zinc-400 mb-2">Черты личности</div>
                    <div className="flex flex-wrap gap-1">
                      {voiceId.personality_traits.map((trait) => (
                        <span key={trait} className="text-xs bg-violet-500/20 text-violet-300 px-2 py-0.5 rounded">
                          {trait}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div className={`text-xs px-3 py-2 rounded ${voiceId.has_identity ? "bg-green-500/10 text-green-400" : "bg-yellow-500/10 text-yellow-400"}`}>
                  {voiceId.has_identity ? "Голосовая идентичность установлена" : "Голос будет создан при первой генерации"}
                </div>
              </div>
            )}
          </div>

          {/* Voice samples */}
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
                          src={`${API_URL}/api/montage/files/${s.file_path.split("/").slice(-2).join("/")}`}
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== LEARNING SECTION ===== */}
      {brainSection === "learning" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-blue-400" /> Обучение и самоулучшение
          </h3>
          {learning && (
            <div className="space-y-4">
              <div className="text-sm text-zinc-400">
                Изучено промтов: <span className="text-white font-bold">{learning.total_learned_prompts}</span>
              </div>

              {/* Content type performance */}
              {Object.keys(learning.content_type_performance).length > 0 && (
                <div>
                  <div className="text-xs text-zinc-400 mb-2">Эффективность по типам контента</div>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(learning.content_type_performance).map(([ct, data]) => (
                      <div key={ct} className="bg-zinc-800 rounded-lg p-3">
                        <div className="text-xs font-medium text-zinc-200">{ct}</div>
                        <div className="flex justify-between mt-1">
                          <span className="text-xs text-zinc-500">Генераций: {data.count}</span>
                          <span className="text-xs text-emerald-400">Score: {data.total_score.toFixed(1)}</span>
                        </div>
                        {data.best_prompt && (
                          <div className="text-[10px] text-zinc-500 mt-1 truncate" title={data.best_prompt}>
                            Лучший: {data.best_prompt.slice(0, 60)}...
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Learning entries */}
              {learning.learning_data.length > 0 && (
                <div>
                  <div className="text-xs text-zinc-400 mb-2">Последние записи обучения</div>
                  <div className="space-y-2">
                    {learning.learning_data.slice(0, 10).map((entry) => (
                      <div key={entry.id} className="bg-zinc-800 rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-zinc-300">{entry.content_type || entry.prompt_type}</span>
                          <div className="flex gap-2 text-xs">
                            <span className="text-emerald-400">Score: {entry.success_score.toFixed(1)}</span>
                            {entry.user_rating && (
                              <span className="text-amber-400">{entry.user_rating}/5</span>
                            )}
                          </div>
                        </div>
                        <div className="text-[10px] text-zinc-500 mt-1 truncate">{entry.original_prompt}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {learning.total_learned_prompts === 0 && (
                <div className="text-center text-zinc-500 text-sm py-4">
                  Система начнёт учиться после первых генераций. Каждое фото, голос и видео записываются в память.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
