import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Radio, Clock, ExternalLink, Users, Eye, Star, Scissors, Settings, Zap, TrendingUp } from "lucide-react";
import { api, Stream, TwitchStreamer, ClippingPipeline } from "@/hooks/useApi";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-zinc-500/20 text-zinc-400",
  analyzing: "bg-yellow-500/20 text-yellow-400",
  analyzed: "bg-green-500/20 text-green-400",
};
const STATUS_LABELS: Record<string, string> = { pending: "В очереди", analyzing: "Анализируется", analyzed: "Проанализировано" };
const PLATFORM_LABELS: Record<string, string> = { twitch: "Twitch", youtube: "YouTube", kick: "Kick" };
const REGION_LABELS: Record<string, string> = { CIS: "СНГ", "Brazil/LATAM": "Бразилия/LATAM", "North America": "Сев. Америка", "Western Europe": "Зап. Европа", Global: "Глобально" };
const getLabel = (labels: Record<string, string>, key: string) => labels[key] || key;
function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(n >= 10_000 ? 0 : 1) + "K";
  return String(n);
}
type Tab = "streams" | "streamers" | "pipeline";

export default function StreamsPage() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [twitchStreamers, setTwitchStreamers] = useState<TwitchStreamer[]>([]);
  const [pipeline, setPipeline] = useState<ClippingPipeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("streams");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ title: "", platform: "twitch", url: "", streamer_name: "" });

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [s, tw, pl] = await Promise.all([
        api.getStreams(),
        api.getTwitchStreamers().catch(() => ({ streamers: [], total: 0, regions_available: [], recommendation: "" })),
        api.getClippingPipeline().catch(() => null),
      ]);
      setStreams(s);
      setTwitchStreamers(tw.streamers);
      setPipeline(pl);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    if (!form.title || !form.streamer_name) return;
    const url = form.url || `https://www.twitch.tv/${form.streamer_name}`;
    await api.createStream({ ...form, url });
    setForm({ title: "", platform: "twitch", url: "", streamer_name: "" });
    setDialogOpen(false);
    loadAll();
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "streams", label: "Стримы", icon: <Radio className="h-4 w-4" /> },
    { id: "streamers", label: "Топ стримеры CS2", icon: <Users className="h-4 w-4" /> },
    { id: "pipeline", label: "Пайплайн нарезки", icon: <Scissors className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg sm:text-xl font-bold text-white truncate">Стримы и Twitch</h2>
          <p className="text-xs sm:text-sm text-zinc-400">Управление стримами, анализ стримеров, система нарезки</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-violet-600 hover:bg-violet-700 active:bg-violet-800 shrink-0 text-xs sm:text-sm"><Plus className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Добавить стрим</span></Button>
          </DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800">
            <DialogHeader><DialogTitle className="text-white">Новый стрим</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div><Label className="text-zinc-400">Название</Label><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="bg-zinc-800 border-zinc-700 text-white" placeholder="CS2 рейтинг сессия" /></div>
              <div><Label className="text-zinc-400">Ник стримера (Twitch)</Label><Input value={form.streamer_name} onChange={(e) => setForm({ ...form, streamer_name: e.target.value })} className="bg-zinc-800 border-zinc-700 text-white" placeholder="например, s1mple" /></div>
              <div>
                <Label className="text-zinc-400">Платформа</Label>
                <select value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })} className="w-full rounded-md bg-zinc-800 border border-zinc-700 text-white px-3 py-2 text-sm">
                  <option value="twitch">Twitch</option><option value="youtube">YouTube</option><option value="kick">Kick</option>
                </select>
              </div>
              <div><Label className="text-zinc-400">URL (автозаполнится из ника)</Label><Input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} className="bg-zinc-800 border-zinc-700 text-white" placeholder="https://www.twitch.tv/..." /></div>
              <Button onClick={handleCreate} className="w-full bg-violet-600 hover:bg-violet-700">Создать стрим</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5 sm:gap-2 flex-wrap">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors ${activeTab === tab.id ? "bg-violet-600 text-white" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 active:bg-zinc-700"}`}>
            {tab.icon}<span className="hidden sm:inline">{tab.label}</span><span className="sm:hidden">{tab.label.split(' ')[0]}</span>
          </button>
        ))}
      </div>

      {loading ? (<div className="text-zinc-400 text-center py-8">Загрузка...</div>) : (<>
        {/* TAB 1: Streams */}
        {activeTab === "streams" && (<div className="space-y-4">
          <h3 className="text-sm font-semibold text-zinc-300">Отслеживаемые стримы</h3>
          {streams.length === 0 ? (<div className="text-zinc-400 text-center py-8">Стримов пока нет. Нажми «Добавить стрим».</div>) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              {streams.map((stream) => (
                <Card key={stream.id} className="bg-zinc-900 border-zinc-800 hover:border-violet-800/50 transition-colors">
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-center justify-between mb-2">
                      <Badge className={STATUS_COLORS[stream.status] || "bg-zinc-500/20 text-zinc-400"}>{getLabel(STATUS_LABELS, stream.status)}</Badge>
                      <span className="text-xs text-zinc-500">#{stream.id}</span>
                    </div>
                    <h3 className="text-white font-medium mb-1">{stream.title}</h3>
                    <div className="flex items-center gap-2 text-xs text-zinc-500 mb-2">
                      <Radio className="h-3 w-3 text-violet-400" />
                      <span>{getLabel(PLATFORM_LABELS, stream.platform)}</span>
                      <span>&#8226;</span>
                      <a href={stream.url || `https://www.twitch.tv/${stream.streamer_name}`} target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 hover:underline flex items-center gap-1">
                        {stream.streamer_name}<ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                    {stream.started_at && (<div className="flex items-center gap-1 text-xs text-zinc-500"><Clock className="h-3 w-3" /><span>{new Date(stream.started_at).toLocaleString("ru-RU")}</span></div>)}
                    <div className="mt-2">
                      <a href={stream.url || `https://www.twitch.tv/${stream.streamer_name}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 px-2 py-1 rounded bg-violet-600/20 text-violet-400 hover:bg-violet-600/30 text-xs font-medium transition-colors">
                        <ExternalLink className="h-3 w-3" />Открыть Twitch
                      </a>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>)}

        {/* TAB 2: Top CS2 Streamers */}
        {activeTab === "streamers" && (<div className="space-y-4">
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2"><TrendingUp className="h-4 w-4 text-violet-400" /><h3 className="text-sm font-semibold text-white">Рекомендация</h3></div>
            <p className="text-xs text-zinc-400">Приоритет: <span className="text-violet-400">ESLCS/BLASTPremier</span> (турниры = максимум хайлайтов), <span className="text-green-400">gaules/yuurih</span> (LATAM — низкая конкуренция), <span className="text-yellow-400">s1mple/donk</span> (CIS — глобальный аппил)</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {twitchStreamers.map((streamer) => (
              <Card key={streamer.username} className="bg-zinc-900 border-zinc-800 hover:border-violet-800/50 transition-colors">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-center justify-between mb-2">
                    <a href={streamer.twitch_url} target="_blank" rel="noreferrer" className="text-white font-semibold hover:text-violet-400 flex items-center gap-1 transition-colors">
                      {streamer.display_name}<ExternalLink className="h-3.5 w-3.5 text-violet-400" />
                    </a>
                    <Badge className="bg-violet-500/20 text-violet-400"><Star className="h-3 w-3 mr-1" />{streamer.clip_potential}</Badge>
                  </div>
                  <p className="text-xs text-zinc-400 mb-3">{streamer.description}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                    <div className="bg-zinc-800/50 rounded px-2 py-1.5"><div className="text-zinc-500">Ср. зрители</div><div className="text-white font-medium flex items-center gap-1"><Eye className="h-3 w-3 text-green-400" />{formatNumber(streamer.avg_viewers)}</div></div>
                    <div className="bg-zinc-800/50 rounded px-2 py-1.5"><div className="text-zinc-500">Подписчики</div><div className="text-white font-medium flex items-center gap-1"><Users className="h-3 w-3 text-blue-400" />{formatNumber(streamer.followers)}</div></div>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2"><span className="text-zinc-500">Регион:</span><span className="text-zinc-300">{getLabel(REGION_LABELS, streamer.region)}</span></div>
                    <span className="text-zinc-500">{streamer.language.toUpperCase()}</span>
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">Контент: <span className="text-zinc-400">{streamer.content_style}</span></div>
                  <a href={streamer.twitch_url} target="_blank" rel="noreferrer" className="mt-3 w-full inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded bg-violet-600/20 text-violet-400 hover:bg-violet-600/30 text-xs font-medium transition-colors">
                    <ExternalLink className="h-3 w-3" />Открыть Twitch канал
                  </a>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>)}

        {/* TAB 3: Clipping Pipeline */}
        {activeTab === "pipeline" && pipeline && (<div className="space-y-6">
          {/* Auto-Detection */}
          <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-2 mb-3"><Zap className="h-5 w-5 text-yellow-400" /><h3 className="text-white font-semibold">Автодетекция моментов</h3>
              <Badge className={pipeline.auto_detection.enabled ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}>{pipeline.auto_detection.enabled ? "Активно" : "Выкл"}</Badge>
            </div>
            <p className="text-xs text-zinc-400 mb-4">{pipeline.auto_detection.description}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
              {Object.entries(pipeline.auto_detection.triggers).map(([key, trigger]) => (
                <div key={key} className="bg-zinc-800/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1"><span className="text-xs font-medium text-white">{key.replace(/_/g, " ").toUpperCase()}</span><span className="text-xs text-yellow-400 font-mono">w: {trigger.weight}</span></div>
                  <p className="text-xs text-zinc-400">{trigger.description}</p>
                </div>
              ))}
            </div>
          </CardContent></Card>

          {/* Clip Settings */}
          <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-2 mb-3"><Settings className="h-5 w-5 text-zinc-400" /><h3 className="text-white font-semibold">Настройки клипов</h3></div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 mb-4">
              <div className="bg-zinc-800/50 rounded p-2 text-center"><div className="text-xs text-zinc-500">Длительность</div><div className="text-lg text-white font-bold">{pipeline.clip_settings.default_duration_sec}с</div></div>
              <div className="bg-zinc-800/50 rounded p-2 text-center"><div className="text-xs text-zinc-500">Буфер до</div><div className="text-lg text-white font-bold">{pipeline.clip_settings.pre_moment_buffer_sec}с</div></div>
              <div className="bg-zinc-800/50 rounded p-2 text-center"><div className="text-xs text-zinc-500">Буфер после</div><div className="text-lg text-white font-bold">{pipeline.clip_settings.post_moment_buffer_sec}с</div></div>
              <div className="bg-zinc-800/50 rounded p-2 text-center"><div className="text-xs text-zinc-500">Макс. длина</div><div className="text-lg text-white font-bold">{pipeline.clip_settings.max_clip_duration_sec}с</div></div>
            </div>
            <h4 className="text-xs font-semibold text-zinc-300 mb-2">Форматы вывода</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3">
              {Object.entries(pipeline.clip_settings.output_formats).map(([name, fmt]) => (
                <div key={name} className="bg-zinc-800/50 rounded-lg p-3"><div className="text-xs font-medium text-white mb-1">{name.replace(/_/g, " ").toUpperCase()}</div><div className="text-xs text-zinc-400">{fmt.resolution} &#8226; {fmt.aspect_ratio} &#8226; макс. {fmt.max_duration}с</div></div>
              ))}
            </div>
          </CardContent></Card>

          {/* Post-Processing */}
          <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-2 mb-3"><Scissors className="h-5 w-5 text-violet-400" /><h3 className="text-white font-semibold">Пост-обработка</h3></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(pipeline.post_processing).map(([key, config]) => (
                <div key={key} className="bg-zinc-800/50 rounded-lg p-3 flex items-start gap-2">
                  <div className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${config.enabled ? "bg-green-400" : "bg-zinc-600"}`} />
                  <div><div className="text-xs font-medium text-white">{key.replace(/^add_/, "").replace(/_/g, " ").toUpperCase()}</div>
                    <div className="text-xs text-zinc-500">{config.enabled ? "Активно" : "Выкл"}{config.model ? ` \u2022 ${String(config.model)}` : ""}{config.style ? ` \u2022 ${String(config.style)}` : ""}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent></Card>

          {/* Publishing */}
          <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-2 mb-3"><TrendingUp className="h-5 w-5 text-green-400" /><h3 className="text-white font-semibold">Публикация</h3></div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(pipeline.publishing).map(([key, value]) => (
                <div key={key} className="bg-zinc-800/50 rounded p-2"><div className="text-xs text-zinc-500">{key.replace(/_/g, " ")}</div>
                  <div className="text-sm text-white font-medium">{typeof value === "boolean" ? (value ? "Да" : "Нет") : Array.isArray(value) ? (value as string[]).join(", ") : String(value)}</div>
                </div>
              ))}
            </div>
          </CardContent></Card>
        </div>)}
      </>)}
    </div>
  );
}
