import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  CheckCircle, XCircle, Loader2, Music, Volume2, Mic, Film,
  Wand2, Play, Clapperboard, Clock, Layers, Sparkles, Download,
  AlertCircle, Zap,
} from "lucide-react";
import {
  api,
  MontageStatus,
  MontageTemplate,
  MontageResult,
  MontageClipFile,
} from "@/hooks/useApi";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type Tab = "create" | "templates" | "library" | "clips";

const COLOR_GRADES = [
  { value: "cinematic", label: "Кинематографичный" },
  { value: "vibrant", label: "Яркий" },
  { value: "dark", label: "Тёмный" },
  { value: "none", label: "Без обработки" },
];

const MOMENT_TYPES = [
  { value: "ace", label: "Эйс" },
  { value: "clutch", label: "Клатч" },
  { value: "multi_kill", label: "Мульти-килл" },
  { value: "headshot_sequence", label: "Хедшот серия" },
  { value: "funny", label: "Смешной момент" },
  { value: "fail_moment", label: "Фейл" },
  { value: "toxic_play", label: "Токсик плей" },
  { value: "knife_kill", label: "Убийство ножом" },
  { value: "comeback", label: "Камбэк" },
  { value: "insane_play", label: "Невероятный плей" },
  { value: "default", label: "Стандартный" },
];

const GIRL_POSITIONS = [
  { value: "pip_bottom_right", label: "PiP снизу-справа", desc: "Классический PiP в углу" },
  { value: "pip_top_right", label: "PiP сверху-справа", desc: "Для субтитров снизу" },
  { value: "split_bottom", label: "Сплит 50/50", desc: "Instagram-нативный" },
  { value: "fullscreen", label: "Полный экран", desc: "Девушка на весь экран" },
  { value: "bottom_third", label: "Нижняя треть", desc: "Новостной стиль" },
  { value: "dynamic", label: "Динамический", desc: "Меняется по фазам" },
];

const TEMPLATE_CATEGORIES: Record<string, { label: string; color: string }> = {
  core: { label: "Базовые", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  ai_girl: { label: "AI Девушка", color: "bg-pink-500/20 text-pink-400 border-pink-500/30" },
  meme: { label: "Мемы/Вирал", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  dramatic: { label: "Кинематограф", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  engagement: { label: "Вовлечение", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  trending: { label: "Тренды", color: "bg-red-500/20 text-red-400 border-red-500/30" },
};

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000) return (bytes / 1_000_000).toFixed(1) + " МБ";
  if (bytes >= 1_000) return (bytes / 1_000).toFixed(0) + " КБ";
  return bytes + " Б";
}

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return m > 0 ? `${m}м ${s}с` : `${s}с`;
}

const PHASE_COLORS: Record<string, string> = {
  hook: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  build: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  peak: "bg-red-500/20 text-red-400 border-red-500/30",
  react: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  cta: "bg-green-500/20 text-green-400 border-green-500/30",
  action: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  replay: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  girl_intro: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  gameplay: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  peak_react: "bg-red-500/20 text-red-400 border-red-500/30",
  outro: "bg-green-500/20 text-green-400 border-green-500/30",
};

const STEP_LABELS: Record<string, string> = {
  download: "Скачивание",
  process_game: "Обработка видео",
  generate_assets: "Генерация ассетов",
  girl_pipeline: "AI Девушка",
  assembly: "Финальная сборка",
};

export default function MontagePage() {
  const [status, setStatus] = useState<MontageStatus | null>(null);
  const [templates, setTemplates] = useState<Record<string, MontageTemplate>>({});
  const [clips, setClips] = useState<MontageClipFile[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("create");
  const [loading, setLoading] = useState(true);

  // Create form
  const [clipUrl, setClipUrl] = useState("https://clips.twitch.tv/CheerfulSmallGuanacoBleedPurple-E57nOO_JmOfAVvIH");
  const [templateId, setTemplateId] = useState("highlight_react");
  const [momentType, setMomentType] = useState("insane_play");
  const [hookText, setHookText] = useState("WAIT FOR IT...");
  const [ctaText, setCtaText] = useState("Follow for daily CS2 highlights!");
  const [subtitleText, setSubtitleText] = useState("");
  const [colorGrade, setColorGrade] = useState("cinematic");
  const [maxDuration, setMaxDuration] = useState("15");
  const [enableGirl, setEnableGirl] = useState(false);
  const [girlVoice, setGirlVoice] = useState("jessica");
  const [girlPosition, setGirlPosition] = useState("pip_bottom_right");
  const [girlImageUrl, setGirlImageUrl] = useState("");
  const [falApiKey, setFalApiKey] = useState("");
  const [musicTrack, setMusicTrack] = useState<string>("");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<MontageResult | null>(null);
  const [error, setError] = useState("");
  const [demoVoice, setDemoVoice] = useState("jessica");

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, t, c] = await Promise.all([
        api.getMontageStatus().catch(() => null),
        api.getMontageTemplates().catch(() => ({})),
        api.getMontageClips().catch(() => ({ clips: [], total: 0 })),
      ]);
      if (s) setStatus(s);
      setTemplates(t as Record<string, MontageTemplate>);
      setClips(c.clips);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleCreateMontage = async () => {
    if (!clipUrl) return;
    setGenerating(true);
    setResult(null);
    setError("");
    try {
      const res = await api.createMontage({
        clip_url: clipUrl,
        template_id: templateId,
        moment_type: momentType,
        hook_text: hookText || undefined,
        cta_text: ctaText || undefined,
        subtitle_text: subtitleText || undefined,
        max_duration: parseFloat(maxDuration) || 15,
        enable_girl: enableGirl,
        girl_voice: girlVoice,
        girl_image_url: girlImageUrl || null,
        fal_api_key: falApiKey || null,
        color_grade: colorGrade,
        music_track: musicTrack || null,
      });
      setResult(res);
      await loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка генерации монтажа");
    } finally {
      setGenerating(false);
    }
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "create", label: "Создать монтаж", icon: <Clapperboard className="h-4 w-4" /> },
    { id: "templates", label: "Шаблоны драматургии", icon: <Layers className="h-4 w-4" /> },
    { id: "library", label: "SFX и музыка", icon: <Music className="h-4 w-4" /> },
    { id: "clips", label: "Готовые монтажи", icon: <Film className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg sm:text-xl font-bold text-white truncate">Интеллектуальный Монтаж</h2>
          <p className="text-xs sm:text-sm text-zinc-400 truncate">Клип + музыка + SFX + AI девушка + сборка</p>
        </div>
        <Badge className="bg-violet-500/20 text-violet-400 border border-violet-500/30 shrink-0">
          <Zap className="h-3 w-3 mr-1" />
          {status?.engine || "..."}
        </Badge>
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5 sm:gap-2 flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-violet-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 active:bg-zinc-700"
            }`}
          >
            {tab.icon}<span className="hidden sm:inline">{tab.label}</span><span className="sm:hidden">{tab.label.split(' ')[0]}</span>
          </button>
        ))}
      </div>

      {/* ── TAB: Create Montage ── */}
      {activeTab === "create" && (
        <div className="space-y-6">
          {/* Status */}
          {status && (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-white flex items-center gap-2">
                  <Wand2 className="h-5 w-5 text-violet-400" /> Статус движка
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 sm:gap-3">
                  {Object.entries(status.tools).map(([tool, ok]) => (
                    <div key={tool} className="bg-zinc-800/50 rounded-lg p-3 text-center">
                      <div className="text-xs text-zinc-500 mb-1">{tool.replace(/_/g, " ")}</div>
                      <div className="flex items-center justify-center gap-1">
                        {ok ? <CheckCircle className="h-4 w-4 text-green-400" /> : <XCircle className="h-4 w-4 text-red-400" />}
                        <span className={`text-sm font-medium ${ok ? "text-green-400" : "text-red-400"}`}>
                          {ok ? "Готов" : "Нет"}
                        </span>
                      </div>
                    </div>
                  ))}
                  <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                    <div className="text-xs text-zinc-500 mb-1">SFX кэш</div>
                    <div className="text-lg font-bold text-violet-400">{status.assets.sfx_cached}</div>
                  </div>
                  <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                    <div className="text-xs text-zinc-500 mb-1">Монтажей</div>
                    <div className="text-lg font-bold text-violet-400">{status.assets.clips_generated}</div>
                  </div>
                </div>

                {/* Capabilities */}
                <div className="mt-4">
                  <h4 className="text-xs font-semibold text-zinc-400 mb-2">Возможности</h4>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(status.capabilities).map(([cap, val]) => {
                      const isActive = val === true;
                      const isString = typeof val === "string";
                      return (
                        <Badge
                          key={cap}
                          className={
                            isActive
                              ? "bg-green-500/10 text-green-400 border border-green-500/20"
                              : isString
                              ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                              : "bg-zinc-800 text-zinc-500 border border-zinc-700"
                          }
                        >
                          {isActive ? <CheckCircle className="h-3 w-3 mr-1" /> : isString ? <AlertCircle className="h-3 w-3 mr-1" /> : <XCircle className="h-3 w-3 mr-1" />}
                          {cap.replace(/_/g, " ")}
                        </Badge>
                      );
                    })}
                  </div>
                </div>

                {/* APIs needed */}
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-xs font-semibold text-green-400 mb-2">Бесплатные инструменты</h4>
                    {status.apis_needed.free.map((a) => (
                      <div key={a.name} className="flex items-center gap-2 text-xs text-zinc-300 mb-1">
                        <CheckCircle className="h-3 w-3 text-green-400 shrink-0" />
                        <span className="font-medium">{a.name}</span>
                        <span className="text-zinc-500">— {a.purpose}</span>
                        <Badge className="bg-green-500/10 text-green-400 text-[10px]">{a.status}</Badge>
                      </div>
                    ))}
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-yellow-400 mb-2">Платные API (опционально)</h4>
                    {status.apis_needed.paid.map((a) => (
                      <div key={a.name} className="flex items-center gap-2 text-xs text-zinc-300 mb-1">
                        <AlertCircle className="h-3 w-3 text-yellow-400 shrink-0" />
                        <span className="font-medium">{a.name}</span>
                        <span className="text-zinc-500">— {a.purpose}</span>
                        <Badge className="bg-yellow-500/10 text-yellow-400 text-[10px]">{a.cost}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Demo Reels — ElevenLabs v3 */}
          <Card className="bg-zinc-900 border-zinc-800 border-violet-500/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Play className="h-5 w-5 text-violet-400" /> Демо-рилсы — ElevenLabs v3 (4 голоса)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Voice selector */}
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: "jessica", label: "Jessica", desc: "Playful & bright", color: "bg-pink-500/20 text-pink-400 border-pink-500/30" },
                    { id: "laura", label: "Laura", desc: "Quirky enthusiast", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
                    { id: "ivanna", label: "Ivanna", desc: "Young & casual", color: "bg-green-500/20 text-green-400 border-green-500/30" },
                    { id: "lily", label: "Lily", desc: "Dramatic actress", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
                  ].map((v) => (
                    <button
                      key={v.id}
                      onClick={() => setDemoVoice(v.id)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                        demoVoice === v.id ? v.color + " ring-1 ring-offset-1 ring-offset-zinc-900" : "bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-zinc-700"
                      }`}
                    >
                      <Mic className="h-3 w-3 inline mr-1" />{v.label}
                      <span className="text-[10px] ml-1 opacity-70">({v.desc})</span>
                    </button>
                  ))}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  <div className="flex justify-center">
                    <video
                      key={demoVoice}
                      controls
                      autoPlay={false}
                      className="rounded-lg border border-zinc-700 max-h-[360px] sm:max-h-[480px] w-full"
                    >
                      <source src={`${API_URL}/api/montage/files/output/demo_${demoVoice}.mp4`} type="video/mp4" />
                      Ваш браузер не поддерживает видео.
                    </video>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-semibold text-violet-400 mb-2">Что в каждом демо:</h4>
                      <div className="space-y-2 text-sm text-zinc-300">
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-400 shrink-0" />
                          <span>Клип m0NESY с Twitch (вертикальный 9:16)</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-400 shrink-0" />
                          <span>ElevenLabs v3 — живая озвучка с эмоциями</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-400 shrink-0" />
                          <span>Аудио-теги: [excited], [whispers], [laughs], [gasps]</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-400 shrink-0" />
                          <span>4 SFX + фоновая музыка (Phonk Beat)</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-400 shrink-0" />
                          <span>Цветокоррекция "Cinematic"</span>
                        </div>
                      </div>
                    </div>
                    <div className="bg-zinc-800/50 rounded-lg p-3">
                      <h4 className="text-xs font-semibold text-green-400 mb-1">ElevenLabs v3 подключён</h4>
                      <p className="text-xs text-zinc-400">
                        Используется модель eleven_v3 с аудио-тегами для живой озвучки.
                        8 женских голосов: Jessica, Sarah, Laura, Alice, Matilda, Bella, Lily, Ivanna.
                        Каждый голос имеет свой стиль — от playful до dramatic.
                      </p>
                    </div>
                    <a
                      href={`${API_URL}/api/montage/files/output/demo_${demoVoice}.mp4`}
                      download={`demo_${demoVoice}.mp4`}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      <Download className="h-4 w-4" /> Скачать демо ({demoVoice})
                    </a>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Create Form */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Clapperboard className="h-5 w-5 text-violet-400" /> Создать монтаж
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Source */}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                  <Play className="h-4 w-4 text-blue-400" /> Источник
                </h4>
                <div>
                  <Label className="text-zinc-400 text-xs">URL клипа (Twitch, YouTube, прямая ссылка)</Label>
                  <Input
                    value={clipUrl}
                    onChange={(e) => setClipUrl(e.target.value)}
                    className="bg-zinc-800 border-zinc-700 text-white"
                    placeholder="https://clips.twitch.tv/..."
                  />
                </div>
              </div>

              {/* Template & Style */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                <div>
                  <Label className="text-zinc-400 text-xs">Шаблон драматургии</Label>
                  <Select value={templateId} onValueChange={setTemplateId}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(status?.templates || {}).map(([id, t]) => (
                        <SelectItem key={id} value={id}>
                          {t.name} ({t.duration}с, {t.phases} фаз)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-zinc-400 text-xs">Тип момента</Label>
                  <Select value={momentType} onValueChange={setMomentType}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MOMENT_TYPES.map((m) => (
                        <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-zinc-400 text-xs">Цветокоррекция</Label>
                  <Select value={colorGrade} onValueChange={setColorGrade}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {COLOR_GRADES.map((c) => (
                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Text overlays */}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-yellow-400" /> Текстовые оверлеи
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                  <div>
                    <Label className="text-zinc-400 text-xs">Хук-текст (начало)</Label>
                    <Input value={hookText} onChange={(e) => setHookText(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="WAIT FOR IT..." />
                  </div>
                  <div>
                    <Label className="text-zinc-400 text-xs">CTA-текст (конец)</Label>
                    <Input value={ctaText} onChange={(e) => setCtaText(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="Follow for more!" />
                  </div>
                  <div>
                    <Label className="text-zinc-400 text-xs">Субтитры</Label>
                    <Input value={subtitleText} onChange={(e) => setSubtitleText(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="Insane play..." />
                  </div>
                </div>
              </div>

              {/* Music & Duration */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <Label className="text-zinc-400 text-xs">Музыка</Label>
                  <Select value={musicTrack} onValueChange={setMusicTrack}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue placeholder="Автоматически по шаблону" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Автоматически</SelectItem>
                      {Object.entries(status?.music_library || {}).map(([id, m]) => (
                        <SelectItem key={id} value={id}>{m.name} ({m.mood})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-zinc-400 text-xs">Макс. длительность (сек)</Label>
                  <Input value={maxDuration} onChange={(e) => setMaxDuration(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" type="number" min={5} max={60} />
                </div>
              </div>

              {/* AI Girl */}
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <h4 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
                    <Mic className="h-4 w-4 text-pink-400" /> AI Девушка
                  </h4>
                  <button
                    onClick={() => setEnableGirl(!enableGirl)}
                    className={`relative w-10 h-5 rounded-full transition-colors ${enableGirl ? "bg-pink-500" : "bg-zinc-700"}`}
                  >
                    <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${enableGirl ? "left-5" : "left-0.5"}`} />
                  </button>
                  <span className="text-xs text-zinc-500">{enableGirl ? "Включена" : "Выключена"}</span>
                </div>

                {enableGirl && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 bg-zinc-800/50 rounded-lg p-3 sm:p-4">
                    <div>
                      <Label className="text-zinc-400 text-xs">Голос</Label>
                      <Select value={girlVoice} onValueChange={setGirlVoice}>
                        <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(status?.girl_voices || {}).map(([id, v]) => (
                            <SelectItem key={id} value={id}>{v.desc} ({v.style})</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-zinc-400 text-xs">Позиция девушки</Label>
                      <Select value={girlPosition} onValueChange={setGirlPosition}>
                        <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {GIRL_POSITIONS.map((p) => (
                            <SelectItem key={p.value} value={p.value}>{p.label} — {p.desc}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-zinc-400 text-xs">URL фото девушки (для lip-sync)</Label>
                      <Input value={girlImageUrl} onChange={(e) => setGirlImageUrl(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="https://..." />
                    </div>
                    <div>
                      <Label className="text-zinc-400 text-xs">fal.ai API Key (для lip-sync)</Label>
                      <Input value={falApiKey} onChange={(e) => setFalApiKey(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="Опционально" type="password" />
                    </div>
                    <div className="md:col-span-3">
                      <p className="text-xs text-zinc-500">
                        Голос: ElevenLabs v3 (если ключ подключён) или edge-tts (бесплатно). Lip-sync видео требует fal.ai API key (~$0.02/клип). Позиции: PiP в углу, сплит 50/50 (инста), нижняя треть, полный экран.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Generate Button */}
              <Button
                onClick={handleCreateMontage}
                disabled={generating || !clipUrl}
                className="w-full bg-gradient-to-r from-violet-600 to-pink-600 hover:from-violet-700 hover:to-pink-700 text-white font-medium py-3"
              >
                {generating ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Генерация монтажа...</>
                ) : (
                  <><Wand2 className="h-4 w-4 mr-2" /> Создать монтаж</>
                )}
              </Button>

              {/* Error */}
              {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-red-400 text-sm">
                    <XCircle className="h-4 w-4" /><span>{error}</span>
                  </div>
                </div>
              )}

              {/* Result */}
              {result && (
                <div className={`border rounded-lg p-4 space-y-3 ${result.success ? "bg-green-500/10 border-green-500/30" : "bg-red-500/10 border-red-500/30"}`}>
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {result.success ? (
                      <><CheckCircle className="h-4 w-4 text-green-400" /><span className="text-green-400">Монтаж готов!</span></>
                    ) : (
                      <><XCircle className="h-4 w-4 text-red-400" /><span className="text-red-400">Ошибка: {result.error}</span></>
                    )}
                  </div>

                  {result.success && (
                    <>
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 sm:gap-3 text-xs">
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-zinc-500">Длительность</div>
                          <div className="text-white font-medium">{formatDuration(result.duration || 0)}</div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-zinc-500">Разрешение</div>
                          <div className="text-white font-medium">{result.resolution}</div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-zinc-500">Размер</div>
                          <div className="text-white font-medium">{formatBytes(result.file_size || 0)}</div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-zinc-500">Стоимость</div>
                          <div className="text-white font-medium">${(result.total_cost || 0).toFixed(3)}</div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-zinc-500">Шаблон</div>
                          <div className="text-white font-medium">{result.template}</div>
                        </div>
                      </div>

                      {/* Tracks */}
                      {result.tracks && (
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(result.tracks).map(([key, val]) => (
                            <Badge key={key} className={val ? "bg-green-500/10 text-green-400" : "bg-zinc-800 text-zinc-500"}>
                              {key === "game_audio" ? "Игровой звук" :
                               key === "music" ? "Музыка" :
                               key === "girl_voice" ? "Голос девушки" :
                               key === "girl_video" ? "Видео девушки" :
                               key === "sfx_count" ? `SFX: ${val}` : key}
                              {typeof val === "boolean" && (val ? " ON" : " OFF")}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {/* Steps */}
                      {result.steps && result.steps.length > 0 && (
                        <div className="space-y-1">
                          <h5 className="text-xs font-semibold text-zinc-400">Этапы выполнения:</h5>
                          {result.steps.map((s, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs">
                              {s.status === "success" ? <CheckCircle className="h-3 w-3 text-green-400" /> :
                               s.status === "failed" ? <XCircle className="h-3 w-3 text-red-400" /> :
                               <Loader2 className="h-3 w-3 text-yellow-400 animate-spin" />}
                              <span className="text-zinc-300">{STEP_LABELS[s.step] || s.step}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Download link */}
                      {result.output_path && (
                        <a
                          href={`${API_URL}/api/montage/files/output/${result.output_path.split("/").pop()}`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm transition-colors"
                        >
                          <Download className="h-4 w-4" /> Скачать монтаж
                        </a>
                      )}
                    </>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── TAB: Templates ── */}
      {activeTab === "templates" && (
        <div className="space-y-6">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Layers className="h-5 w-5 text-violet-400" /> Шаблоны драматургии v2.0
              </CardTitle>
              <p className="text-sm text-zinc-400">
                {Object.keys(templates).length} шаблонов: базовые, AI девушка, мемы/вирал, кинематограф, вовлечение, тренды. Каждый определяет фазы, тайминги, эффекты, позиционирование.
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                {Object.entries(TEMPLATE_CATEGORIES).map(([, cat]) => (
                  <Badge key={cat.label} className={`${cat.color} border text-xs`}>{cat.label}</Badge>
                ))}
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {Object.entries(templates).map(([id, t]) => (
                <div key={id} className="border border-zinc-800 rounded-lg p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-white font-semibold flex items-center gap-2">
                        {t.name}
                        <Badge className="bg-violet-500/20 text-violet-400">{id}</Badge>
                      </h4>
                      <p className="text-xs text-zinc-400 mt-1">{t.description}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-zinc-500">Длительность</div>
                      <div className="text-white font-bold">{t.total_duration}с</div>
                    </div>
                  </div>

                  {/* Timeline visualization */}
                  <div className="space-y-2">
                    <h5 className="text-xs font-semibold text-zinc-400">Таймлайн фаз:</h5>
                    <div className="relative h-10 bg-zinc-800 rounded-lg overflow-hidden flex">
                      {t.phases.map((phase, pi) => {
                        const width = ((phase.end - phase.start) / t.total_duration) * 100;
                        const colorClass = PHASE_COLORS[phase.name] || "bg-zinc-600/50 text-zinc-300";
                        return (
                          <div
                            key={pi}
                            className={`h-full flex items-center justify-center text-[10px] font-medium border-r border-zinc-900 ${colorClass}`}
                            style={{ width: `${width}%` }}
                            title={`${phase.name}: ${phase.start}s - ${phase.end}s — ${phase.purpose}`}
                          >
                            {width > 10 && phase.name}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Phase details */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {t.phases.map((phase, pi) => (
                      <div key={pi} className={`rounded-lg p-3 border ${PHASE_COLORS[phase.name] || "border-zinc-700 bg-zinc-800/30"}`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-bold uppercase">{phase.name}</span>
                          <span className="text-[10px] font-mono">{phase.start}s — {phase.end}s</span>
                        </div>
                        <p className="text-[11px] opacity-80 mb-2">{phase.purpose}</p>
                        <div className="flex flex-wrap gap-1">
                          {phase.sfx && <Badge className="bg-zinc-900/50 text-[10px]"><Volume2 className="h-2.5 w-2.5 mr-0.5" />{phase.sfx}</Badge>}
                          {phase.girl_visible && <Badge className="bg-pink-500/20 text-pink-300 text-[10px]"><Sparkles className="h-2.5 w-2.5 mr-0.5" />Girl</Badge>}
                          {phase.girl_speaks && <Badge className="bg-pink-500/20 text-pink-300 text-[10px]"><Mic className="h-2.5 w-2.5 mr-0.5" />Speaks</Badge>}
                          {phase.has_zoom && <Badge className="bg-orange-500/20 text-orange-300 text-[10px]">Zoom</Badge>}
                          {phase.has_slow_mo && <Badge className="bg-purple-500/20 text-purple-300 text-[10px]">Slow-Mo</Badge>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── TAB: SFX & Music Library ── */}
      {activeTab === "library" && status && (
        <div className="space-y-6">
          {/* SFX */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Volume2 className="h-5 w-5 text-yellow-400" /> Звуковые эффекты (SFX)
              </CardTitle>
              <p className="text-sm text-zinc-400">Генерируются автоматически через FFmpeg — бесплатно</p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {Object.entries(status.sfx_library).map(([id, sfx]) => (
                  <div key={id} className="bg-zinc-800/50 rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-white">{sfx.name}</span>
                      <Badge className="bg-zinc-700 text-zinc-400 text-[10px]">{sfx.category}</Badge>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                      <Clock className="h-3 w-3" /> {sfx.duration}с
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full text-xs border-zinc-700 text-zinc-300 hover:bg-zinc-700"
                      onClick={async () => {
                        try {
                          await api.generateMontageSfx(id);
                          await loadData();
                        } catch (e) { console.error(e); }
                      }}
                    >
                      <Play className="h-3 w-3 mr-1" /> Сгенерировать
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Music */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Music className="h-5 w-5 text-green-400" /> Фоновая музыка
              </CardTitle>
              <p className="text-sm text-zinc-400">Процедурно генерируется через FFmpeg — бесплатно</p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(status.music_library).map(([id, track]) => (
                  <div key={id} className="bg-zinc-800/50 rounded-lg p-4 flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-white">{track.name}</div>
                      <div className="flex items-center gap-2 text-xs text-zinc-500 mt-1">
                        <Badge className="bg-zinc-700 text-zinc-400 text-[10px]">{track.category}</Badge>
                        <span>Настроение: {track.mood}</span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-zinc-700 text-zinc-300 hover:bg-zinc-700"
                      onClick={async () => {
                        try {
                          await api.generateMontageMusic(id, 30);
                          await loadData();
                        } catch (e) { console.error(e); }
                      }}
                    >
                      <Play className="h-3 w-3 mr-1" /> Генерировать 30с
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Girl Voices */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Mic className="h-5 w-5 text-pink-400" /> Голоса AI девушки
              </CardTitle>
              <p className="text-sm text-zinc-400">Бесплатно через edge-tts (Microsoft Neural TTS)</p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {Object.entries(status.girl_voices).map(([id, voice]) => (
                  <div key={id} className="bg-zinc-800/50 rounded-lg p-3 text-center">
                    <div className="text-sm font-medium text-white">{voice.desc}</div>
                    <div className="text-xs text-zinc-500 mt-1">{voice.style}</div>
                    <Badge className="mt-2 bg-violet-500/20 text-violet-400 text-[10px]">{id}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── TAB: Generated Clips ── */}
      {activeTab === "clips" && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Film className="h-5 w-5 text-violet-400" /> Готовые монтажи
            </CardTitle>
          </CardHeader>
          <CardContent>
            {clips.length === 0 ? (
              <div className="text-center text-zinc-500 py-8">
                <Clapperboard className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>Пока нет монтажей. Создайте первый во вкладке "Создать монтаж"</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {clips.map((clip) => (
                  <div key={clip.filename} className="bg-zinc-800/50 rounded-lg overflow-hidden">
                    {clip.thumbnail && (
                      <img
                        src={`${API_URL}/api/montage/files/output/${clip.thumbnail.split("/").pop()}`}
                        alt={clip.filename}
                        className="w-full h-40 object-cover"
                      />
                    )}
                    <div className="p-3 space-y-2">
                      <div className="text-sm font-medium text-white truncate">{clip.filename}</div>
                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        <span>{formatBytes(clip.file_size)}</span>
                        <span>{new Date(clip.created_at).toLocaleDateString("ru-RU")}</span>
                      </div>
                      <a
                        href={`${API_URL}/api/montage/files/output/${clip.filename}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 px-3 py-1.5 bg-violet-600 hover:bg-violet-700 text-white rounded text-xs transition-colors"
                      >
                        <Download className="h-3 w-3" /> Скачать
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-violet-400" />
        </div>
      )}
    </div>
  );
}
