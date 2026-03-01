import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Eye, Heart, MessageCircle, Share2, Trash2, Download, Scissors, Play,
  CheckCircle, XCircle, Loader2, Video, Settings, Key, Zap, Film,
} from "lucide-react";
import { api, Clip, ClipExecutorStatus, ProcessedClipFile } from "@/hooks/useApi";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const FORMAT_COLORS: Record<string, string> = {
  clean_highlight: "bg-blue-500/20 text-blue-400",
  highlight_reaction: "bg-green-500/20 text-green-400",
  highlight_subtitles: "bg-cyan-500/20 text-cyan-400",
  highlight_ai_girl: "bg-pink-500/20 text-pink-400",
  meme_format: "bg-yellow-500/20 text-yellow-400",
  dramatic_clutch: "bg-red-500/20 text-red-400",
  provocative: "bg-orange-500/20 text-orange-400",
  hard_fragmovie: "bg-purple-500/20 text-purple-400",
  fail_format: "bg-zinc-500/20 text-zinc-400",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-zinc-500/20 text-zinc-400",
  generated: "bg-blue-500/20 text-blue-400",
  pipeline_ready: "bg-cyan-500/20 text-cyan-400",
  rendered: "bg-green-500/20 text-green-400",
  published: "bg-green-500/20 text-green-400",
};

const FORMAT_LABELS: Record<string, string> = {
  clean_highlight: "Чистый хайлайт",
  highlight_reaction: "Хайлайт + реакция",
  highlight_subtitles: "Хайлайт + субтитры",
  highlight_ai_girl: "Хайлайт + AI девушка",
  meme_format: "Мем-формат",
  dramatic_clutch: "Драматичный клатч",
  provocative: "Провокация",
  hard_fragmovie: "Жёсткий фрагмуви",
  fail_format: "Фейл",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  generated: "Сгенерировано",
  pipeline_ready: "Готово к публикации",
  rendered: "Нарезано",
  published: "Опубликовано",
};

const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Инстаграм",
  youtube: "Ютуб",
  youtube_shorts: "Ютуб Шортс",
  tiktok: "ТикТок",
};

const COLOR_GRADES = [
  { value: "none", label: "Без обработки" },
  { value: "cinematic", label: "Кинематографичный" },
  { value: "vibrant", label: "Яркий" },
  { value: "dark", label: "Тёмный" },
];

const getLabel = (labels: Record<string, string>, key: string) => labels[key] || key;
function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000) return (bytes / 1_000_000).toFixed(1) + " МБ";
  if (bytes >= 1_000) return (bytes / 1_000).toFixed(0) + " КБ";
  return bytes + " Б";
}

type Tab = "executor" | "processed" | "clips";

function ErrorDisplay({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
      <div className="flex items-center gap-2 text-red-400 text-sm">
        <XCircle className="h-4 w-4" /><span>{message}</span>
      </div>
    </div>
  );
}

interface StepInfo { step: string; result: Record<string, unknown> }

function SuccessDisplay({ result }: { result: Record<string, unknown> | null }) {
  if (!result || !result.success) return null;
  const steps = Array.isArray(result.steps) ? (result.steps as StepInfo[]) : [];
  return (
    <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2 text-green-400 text-sm font-medium"><CheckCircle className="h-4 w-4" /> Клип успешно создан!</div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div className="bg-zinc-800/50 rounded p-2"><div className="text-zinc-500">Длительность</div><div className="text-white font-medium">{String(result.duration)}с</div></div>
        <div className="bg-zinc-800/50 rounded p-2"><div className="text-zinc-500">Разрешение</div><div className="text-white font-medium">{String(result.resolution)}</div></div>
        <div className="bg-zinc-800/50 rounded p-2"><div className="text-zinc-500">Размер</div><div className="text-white font-medium">{formatBytes(result.file_size as number)}</div></div>
        <div className="bg-zinc-800/50 rounded p-2"><div className="text-zinc-500">Файл</div><div className="text-white font-medium truncate">{String(result.output_file || "").split("/").pop()}</div></div>
      </div>
      {steps.length > 0 && (
        <div className="text-xs text-zinc-400">
          <span className="font-medium text-zinc-300">Этапы: </span>
          {steps.map((s, i) => (
            <Badge key={i} className={`mr-1 ${s.result.success ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
              {s.step === "download" ? "Скачивание" : s.step === "process" ? "Обработка" : String(s.step)}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ClipsPage() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [formatFilter, setFormatFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("created_at");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("executor");

  // Executor state
  const [executorStatus, setExecutorStatus] = useState<ClipExecutorStatus | null>(null);
  const [processedClips, setProcessedClips] = useState<ProcessedClipFile[]>([]);
  const [twitchClientId, setTwitchClientId] = useState("");
  const [twitchClientSecret, setTwitchClientSecret] = useState("");
  const [savingCreds, setSavingCreds] = useState(false);

  // Test clip form
  const [testUrl, setTestUrl] = useState("https://clips.twitch.tv/CheerfulSmallGuanacoBleedPurple-E57nOO_JmOfAVvIH");
  const [testHook, setTestHook] = useState("WAIT FOR IT...");
  const [testCta, setTestCta] = useState("Follow for daily CS2 highlights!");
  const [testSubtitle, setTestSubtitle] = useState("Insane play by the GOAT");
  const [testColorGrade, setTestColorGrade] = useState("cinematic");
  const [testMaxDuration, setTestMaxDuration] = useState("30");
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<Record<string, unknown> | null>(null);
  const [genError, setGenError] = useState("");

  const loadClips = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (formatFilter !== "all") params.set("format_type", formatFilter);
    params.set("sort_by", sortBy);
    params.set("limit", "100");
    api.getClips(params.toString()).then(setClips).catch(console.error).finally(() => setLoading(false));
  };

  const loadExecutorData = async () => {
    try {
      const [status, processed] = await Promise.all([
        api.getExecutorStatus().catch(() => null),
        api.getProcessedClips().catch(() => ({ clips: [], total: 0 })),
      ]);
      if (status) setExecutorStatus(status);
      setProcessedClips(processed.clips);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadClips();
    loadExecutorData();
  }, [formatFilter, sortBy]);

  const handleDelete = async (id: number) => {
    await api.deleteClip(id);
    loadClips();
  };

  const handleSaveTwitchCreds = async () => {
    if (!twitchClientId || !twitchClientSecret) return;
    setSavingCreds(true);
    try {
      await api.setTwitchCredentials(twitchClientId, twitchClientSecret);
      await loadExecutorData();
      setTwitchClientId("");
      setTwitchClientSecret("");
    } catch (e) {
      console.error(e);
    } finally {
      setSavingCreds(false);
    }
  };

  const handleGenerateTestClip = async () => {
    if (!testUrl) return;
    setGenerating(true);
    setGenResult(null);
    setGenError("");
    try {
      const result = await api.generateTestClip({
        twitch_url: testUrl,
        hook_text: testHook || undefined,
        cta_text: testCta || undefined,
        subtitle_text: testSubtitle || undefined,
        color_grade: testColorGrade,
        max_duration: parseFloat(testMaxDuration) || 30,
      });
      setGenResult(result as unknown as Record<string, unknown>);
      await loadExecutorData();
    } catch (e: unknown) {
      setGenError(e instanceof Error ? e.message : "Ошибка генерации");
    } finally {
      setGenerating(false);
    }
  };

  const totalViews = clips.reduce((s, c) => s + c.views, 0);
  const avgRetention = clips.length ? (clips.reduce((s, c) => s + c.retention_rate, 0) / clips.length).toFixed(1) : "0";

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "executor", label: "Нарезчик", icon: <Scissors className="h-4 w-4" /> },
    { id: "processed", label: "Готовые клипы", icon: <Film className="h-4 w-4" /> },
    { id: "clips", label: "Все клипы", icon: <Video className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Клипы и Нарезка</h2>
          <p className="text-sm text-zinc-400">Нарезка видео, обработка, готовые клипы</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.id ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"}`}>
            {tab.icon}{tab.label}
          </button>
        ))}
      </div>

      {/* TAB: Executor */}
      {activeTab === "executor" && (
        <div className="space-y-6">
          {/* Status */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-white flex items-center gap-2"><Settings className="h-5 w-5 text-violet-400" /> Статус системы нарезки</CardTitle>
            </CardHeader>
            <CardContent>
              {executorStatus ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                      <div className="text-xs text-zinc-500 mb-1">FFmpeg</div>
                      <div className="flex items-center justify-center gap-1">
                        {executorStatus.ffmpeg_available ? <CheckCircle className="h-4 w-4 text-green-400" /> : <XCircle className="h-4 w-4 text-red-400" />}
                        <span className={`text-sm font-medium ${executorStatus.ffmpeg_available ? "text-green-400" : "text-red-400"}`}>
                          {executorStatus.ffmpeg_available ? "Готов" : "Нет"}
                        </span>
                      </div>
                    </div>
                    <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                      <div className="text-xs text-zinc-500 mb-1">yt-dlp</div>
                      <div className="flex items-center justify-center gap-1">
                        {executorStatus.ytdlp_available ? <CheckCircle className="h-4 w-4 text-green-400" /> : <XCircle className="h-4 w-4 text-red-400" />}
                        <span className={`text-sm font-medium ${executorStatus.ytdlp_available ? "text-green-400" : "text-red-400"}`}>
                          {executorStatus.ytdlp_available ? "Готов" : "Нет"}
                        </span>
                      </div>
                    </div>
                    <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                      <div className="text-xs text-zinc-500 mb-1">Twitch API</div>
                      <div className="flex items-center justify-center gap-1">
                        {executorStatus.twitch_api_configured ? <CheckCircle className="h-4 w-4 text-green-400" /> : <XCircle className="h-4 w-4 text-yellow-400" />}
                        <span className={`text-sm font-medium ${executorStatus.twitch_api_configured ? "text-green-400" : "text-yellow-400"}`}>
                          {executorStatus.twitch_api_configured ? "Подключён" : "Не настроен"}
                        </span>
                      </div>
                    </div>
                    <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
                      <div className="text-xs text-zinc-500 mb-1">Готовых клипов</div>
                      <div className="text-lg font-bold text-violet-400">{executorStatus.processed_clips}</div>
                    </div>
                  </div>

                  {/* Capabilities */}
                  <div>
                    <h4 className="text-xs font-semibold text-zinc-400 mb-2">Возможности</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(executorStatus.capabilities).map(([cap, available]) => (
                        <Badge key={cap} className={available ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-zinc-800 text-zinc-500 border border-zinc-700"}>
                          {available ? <CheckCircle className="h-3 w-3 mr-1" /> : <XCircle className="h-3 w-3 mr-1" />}
                          {cap.replace(/_/g, " ")}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-zinc-400 text-center py-4">Загрузка статуса...</div>
              )}
            </CardContent>
          </Card>

          {/* Twitch API Credentials */}
          {executorStatus && !executorStatus.twitch_api_configured && (
            <Card className="bg-zinc-900 border-yellow-500/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-yellow-400 flex items-center gap-2"><Key className="h-5 w-5" /> Twitch API (опционально)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-zinc-400">
                  Для автоматического поиска клипов стримеров нужен Twitch API. Без него можно нарезать клипы по прямой ссылке.
                  <br />
                  <a href="https://dev.twitch.tv/console/apps" target="_blank" rel="noreferrer" className="text-violet-400 hover:underline">
                    Получить ключи: dev.twitch.tv/console/apps
                  </a>
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <Label className="text-zinc-400 text-xs">Client ID</Label>
                    <Input value={twitchClientId} onChange={(e) => setTwitchClientId(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="Twitch Client ID" />
                  </div>
                  <div>
                    <Label className="text-zinc-400 text-xs">Client Secret</Label>
                    <Input type="password" value={twitchClientSecret} onChange={(e) => setTwitchClientSecret(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="Twitch Client Secret" />
                  </div>
                </div>
                <Button onClick={handleSaveTwitchCreds} disabled={savingCreds || !twitchClientId || !twitchClientSecret} className="bg-yellow-600 hover:bg-yellow-700">
                  {savingCreds ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Key className="h-4 w-4 mr-2" />}
                  Сохранить
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Test Clip Generator */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-white flex items-center gap-2"><Zap className="h-5 w-5 text-yellow-400" /> Генератор тестового клипа</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-zinc-400">
                Вставь ссылку на Twitch клип — система скачает, обрежет в вертикальный формат (1080x1920), добавит хук-текст, субтитры, CTA и цветокоррекцию.
              </p>

              <div className="space-y-3">
                <div>
                  <Label className="text-zinc-400 text-xs">Ссылка на Twitch клип</Label>
                  <Input value={testUrl} onChange={(e) => setTestUrl(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="https://clips.twitch.tv/..." />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <Label className="text-zinc-400 text-xs">Хук-текст (сверху, первые 3 сек)</Label>
                    <Input value={testHook} onChange={(e) => setTestHook(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="WAIT FOR IT..." />
                  </div>
                  <div>
                    <Label className="text-zinc-400 text-xs">CTA-текст (снизу, последние 4 сек)</Label>
                    <Input value={testCta} onChange={(e) => setTestCta(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="Follow for daily CS2 highlights!" />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <Label className="text-zinc-400 text-xs">Субтитры (центр)</Label>
                    <Input value={testSubtitle} onChange={(e) => setTestSubtitle(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="Insane play" />
                  </div>
                  <div>
                    <Label className="text-zinc-400 text-xs">Цветокоррекция</Label>
                    <Select value={testColorGrade} onValueChange={setTestColorGrade}>
                      <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-zinc-800 border-zinc-700">
                        {COLOR_GRADES.map((cg) => (
                          <SelectItem key={cg.value} value={cg.value}>{cg.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-zinc-400 text-xs">Макс. длительность (сек)</Label>
                    <Input type="number" value={testMaxDuration} onChange={(e) => setTestMaxDuration(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" placeholder="30" />
                  </div>
                </div>
              </div>

              <Button onClick={handleGenerateTestClip} disabled={generating || !testUrl} className="bg-violet-600 hover:bg-violet-700 w-full md:w-auto">
                {generating ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Генерация (скачивание + обработка)...</>
                ) : (
                  <><Scissors className="h-4 w-4 mr-2" /> Нарезать клип</>
                )}
              </Button>

              {/* Error */}
              <ErrorDisplay message={genError} />

              {/* Success Result */}
              <SuccessDisplay result={genResult} />
            </CardContent>
          </Card>

          {/* Pipeline Info */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-white flex items-center gap-2"><Film className="h-5 w-5 text-cyan-400" /> Пайплайн обработки</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  { step: "1. Скачивание", desc: "yt-dlp скачивает клип с Twitch", icon: <Download className="h-4 w-4 text-blue-400" /> },
                  { step: "2. Кроп 9:16", desc: "FFmpeg обрезает в вертикальный формат 1080x1920", icon: <Scissors className="h-4 w-4 text-violet-400" /> },
                  { step: "3. Оверлеи", desc: "Хук-текст (верх), субтитры (центр), CTA (низ)", icon: <Video className="h-4 w-4 text-yellow-400" /> },
                  { step: "4. Пост-обработка", desc: "Цветокоррекция, нормализация звука, генерация превью", icon: <Play className="h-4 w-4 text-green-400" /> },
                ].map((item) => (
                  <div key={item.step} className="bg-zinc-800/50 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">{item.icon}<span className="text-xs font-semibold text-white">{item.step}</span></div>
                    <p className="text-xs text-zinc-400">{item.desc}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB: Processed Clips */}
      {activeTab === "processed" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-300">Готовые клипы ({processedClips.length})</h3>
            <Button variant="ghost" size="sm" onClick={loadExecutorData} className="text-zinc-400 hover:text-white">Обновить</Button>
          </div>

          {processedClips.length === 0 ? (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="py-8 text-center text-zinc-400">
                Готовых клипов пока нет. Перейди на вкладку «Нарезчик» и создай первый клип.
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {processedClips.map((clip) => (
                <Card key={clip.filename} className="bg-zinc-900 border-zinc-800 hover:border-violet-800/50 transition-colors">
                  <CardContent className="pt-4 pb-4 space-y-3">
                    {clip.thumbnail_url && (
                      <div className="aspect-[9/16] max-h-48 rounded-lg overflow-hidden bg-zinc-800 flex items-center justify-center">
                        <img src={`${API_URL}${clip.thumbnail_url}`} alt={clip.filename} className="object-cover w-full h-full" />
                      </div>
                    )}
                    <div>
                      <h4 className="text-sm font-medium text-white truncate">{clip.filename}</h4>
                      <div className="flex items-center gap-3 text-xs text-zinc-400 mt-1">
                        <span>{formatBytes(clip.size_bytes)}</span>
                        <span>{new Date(clip.created_at * 1000).toLocaleString("ru-RU")}</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <a href={`${API_URL}${clip.video_url}`} target="_blank" rel="noreferrer" className="flex-1">
                        <Button variant="outline" size="sm" className="w-full border-violet-600 text-violet-400 hover:bg-violet-600/20">
                          <Play className="h-3 w-3 mr-1" /> Смотреть
                        </Button>
                      </a>
                      <a href={`${API_URL}${clip.video_url}`} download className="flex-1">
                        <Button variant="outline" size="sm" className="w-full border-zinc-700 text-zinc-400 hover:bg-zinc-800">
                          <Download className="h-3 w-3 mr-1" /> Скачать
                        </Button>
                      </a>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB: All Clips (existing table) */}
      {activeTab === "clips" && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-3 gap-4">
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-zinc-400">Всего клипов</div>
                <div className="text-2xl font-bold text-white">{clips.length}</div>
              </CardContent>
            </Card>
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-zinc-400">Просмотры</div>
                <div className="text-2xl font-bold text-violet-400">{totalViews.toLocaleString()}</div>
              </CardContent>
            </Card>
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-zinc-400">Ср. удержание</div>
                <div className="text-2xl font-bold text-green-400">{avgRetention}%</div>
              </CardContent>
            </Card>
          </div>

          {/* Filters */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent className="pt-4 pb-4 flex gap-4 items-center">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Формат</label>
                <Select value={formatFilter} onValueChange={setFormatFilter}>
                  <SelectTrigger className="w-48 bg-zinc-800 border-zinc-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-800 border-zinc-700">
                    <SelectItem value="all">Все форматы</SelectItem>
                    {Object.keys(FORMAT_COLORS).map((f) => (
                      <SelectItem key={f} value={f}>{getLabel(FORMAT_LABELS, f)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Сортировка</label>
                <Select value={sortBy} onValueChange={setSortBy}>
                  <SelectTrigger className="w-48 bg-zinc-800 border-zinc-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-800 border-zinc-700">
                    <SelectItem value="created_at">Дата создания</SelectItem>
                    <SelectItem value="views">Просмотры</SelectItem>
                    <SelectItem value="retention_rate">Удержание</SelectItem>
                    <SelectItem value="ctr">Кликабельность</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Clips Table */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white">Клипы ({clips.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-zinc-400 text-center py-8">Загрузка...</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="border-zinc-800">
                      <TableHead className="text-zinc-400">Название</TableHead>
                      <TableHead className="text-zinc-400">Формат</TableHead>
                      <TableHead className="text-zinc-400">Статус</TableHead>
                      <TableHead className="text-zinc-400">Платформа</TableHead>
                      <TableHead className="text-zinc-400 text-right">Просмотры</TableHead>
                      <TableHead className="text-zinc-400 text-right">Удержание</TableHead>
                      <TableHead className="text-zinc-400 text-right">Кликабельность</TableHead>
                      <TableHead className="text-zinc-400 text-right">Активность</TableHead>
                      <TableHead className="text-zinc-400"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {clips.map((clip) => (
                      <TableRow key={clip.id} className="border-zinc-800 hover:bg-zinc-800/50">
                        <TableCell className="text-white text-sm max-w-64 truncate">{clip.title}</TableCell>
                        <TableCell>
                          <Badge className={FORMAT_COLORS[clip.format_type] || "bg-zinc-500/20 text-zinc-400"}>
                            {getLabel(FORMAT_LABELS, clip.format_type)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={STATUS_COLORS[clip.status] || "bg-zinc-500/20 text-zinc-400"}>
                            {getLabel(STATUS_LABELS, clip.status)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-zinc-300 text-sm">{clip.platform ? getLabel(PLATFORM_LABELS, clip.platform) : "-"}</TableCell>
                        <TableCell className="text-right">
                          <span className="text-white flex items-center justify-end gap-1">
                            <Eye className="h-3 w-3 text-zinc-500" />{clip.views.toLocaleString()}
                          </span>
                        </TableCell>
                        <TableCell className="text-right text-green-400">{clip.retention_rate}%</TableCell>
                        <TableCell className="text-right text-cyan-400">{clip.ctr}%</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-3 text-xs text-zinc-400">
                            <span className="flex items-center gap-1"><Heart className="h-3 w-3" />{clip.likes}</span>
                            <span className="flex items-center gap-1"><MessageCircle className="h-3 w-3" />{clip.comments}</span>
                            <span className="flex items-center gap-1"><Share2 className="h-3 w-3" />{clip.shares}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(clip.id)} className="text-red-400 hover:text-red-300">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
