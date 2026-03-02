import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle, XCircle, Film, TrendingUp, Clapperboard,
  UserCircle, Radio, Scissors, RefreshCw, Zap, Music, Volume2,
} from "lucide-react";
import {
  api,
  MontageStatus,
  ClipExecutorStatus,
  Trend,
  MontageClipFile,
  AIProfile,
} from "@/hooks/useApi";

export default function Dashboard() {
  const [montageStatus, setMontageStatus] = useState<MontageStatus | null>(null);
  const [executorStatus, setExecutorStatus] = useState<ClipExecutorStatus | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [montageClips, setMontageClips] = useState<MontageClipFile[]>([]);
  const [profiles, setProfiles] = useState<AIProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const [ms, es, tr, mc, pr] = await Promise.all([
        api.getMontageStatus().catch(() => null),
        api.getExecutorStatus().catch(() => null),
        api.getTrends().catch(() => []),
        api.getMontageClips().catch(() => ({ clips: [], total: 0 })),
        api.getProfiles().catch(() => []),
      ]);
      if (ms) setMontageStatus(ms);
      if (es) setExecutorStatus(es);
      setTrends(tr);
      setMontageClips(mc.clips);
      setProfiles(pr);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-zinc-400">Загрузка...</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg sm:text-xl font-bold text-white truncate">Панель управления</h2>
          <p className="text-xs sm:text-sm text-zinc-400">Статус системы и обзор контента</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-violet-600 hover:bg-violet-700 active:bg-violet-800 text-white text-sm font-medium transition-colors disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">Обновить</span>
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 sm:gap-4">
        <StatCard
          icon={<Clapperboard className="h-4 w-4 text-violet-400" />}
          label="Монтажей"
          value={montageStatus?.assets.clips_generated ?? 0}
          color="text-violet-400"
        />
        <StatCard
          icon={<Scissors className="h-4 w-4 text-blue-400" />}
          label="Нарезанных клипов"
          value={executorStatus?.processed_clips ?? 0}
          color="text-blue-400"
        />
        <StatCard
          icon={<TrendingUp className="h-4 w-4 text-green-400" />}
          label="Активных трендов"
          value={trends.length}
          color="text-green-400"
        />
        <StatCard
          icon={<UserCircle className="h-4 w-4 text-pink-400" />}
          label="AI девушек"
          value={profiles.length}
          color="text-pink-400"
        />
        <StatCard
          icon={<Music className="h-4 w-4 text-yellow-400" />}
          label="SFX в кэше"
          value={montageStatus?.assets.sfx_cached ?? 0}
          color="text-yellow-400"
        />
      </div>

      {/* System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Montage Engine Status */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Clapperboard className="h-5 w-5 text-violet-400" />
              Движок монтажа
              <Badge className="bg-green-500/20 text-green-400 ml-auto">
                {montageStatus?.engine || "N/A"}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {montageStatus ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-3 gap-2 sm:gap-3">
                  {Object.entries(montageStatus.tools).map(([tool, ok]) => (
                    <div key={tool} className="bg-zinc-800/50 rounded-lg p-3 flex items-center gap-2">
                      {ok ? <CheckCircle className="h-4 w-4 text-green-400 shrink-0" /> : <XCircle className="h-4 w-4 text-red-400 shrink-0" />}
                      <span className={`text-sm ${ok ? "text-green-400" : "text-red-400"}`}>
                        {tool.replace(/_/g, " ")}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Capabilities */}
                <div>
                  <h4 className="text-xs font-semibold text-zinc-400 mb-2">Возможности</h4>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(montageStatus.capabilities).map(([cap, val]) => {
                      const isActive = val === true;
                      return (
                        <Badge
                          key={cap}
                          className={
                            isActive
                              ? "bg-green-500/10 text-green-400 border border-green-500/20"
                              : "bg-zinc-800 text-zinc-500 border border-zinc-700"
                          }
                        >
                          {isActive ? <CheckCircle className="h-3 w-3 mr-1" /> : <XCircle className="h-3 w-3 mr-1" />}
                          {cap.replace(/_/g, " ")}
                        </Badge>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-zinc-500 text-sm text-center py-4">Статус недоступен</div>
            )}
          </CardContent>
        </Card>

        {/* Clip Executor Status */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Scissors className="h-5 w-5 text-blue-400" />
              Система нарезки
            </CardTitle>
          </CardHeader>
          <CardContent>
            {executorStatus ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <ToolStatus label="FFmpeg" ok={executorStatus.ffmpeg_available} />
                  <ToolStatus label="yt-dlp" ok={executorStatus.ytdlp_available} />
                  <ToolStatus label="Twitch API" ok={executorStatus.twitch_api_configured} />
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
                      <Badge
                        key={cap}
                        className={
                          available
                            ? "bg-green-500/10 text-green-400 border border-green-500/20"
                            : "bg-zinc-800 text-zinc-500 border border-zinc-700"
                        }
                      >
                        {available ? <CheckCircle className="h-3 w-3 mr-1" /> : <XCircle className="h-3 w-3 mr-1" />}
                        {cap.replace(/_/g, " ")}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-zinc-500 text-sm text-center py-4">Статус недоступен</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* APIs Status */}
      {montageStatus && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Zap className="h-5 w-5 text-yellow-400" />
              Подключённые API
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-semibold text-green-400 mb-2">Бесплатные</h4>
                {montageStatus.apis_needed.free.map((a) => (
                  <div key={a.name} className="flex items-center gap-2 text-xs text-zinc-300 mb-1.5 flex-wrap">
                    <CheckCircle className="h-3.5 w-3.5 text-green-400 shrink-0" />
                    <span className="font-medium">{a.name}</span>
                    <span className="text-zinc-500 hidden sm:inline">— {a.purpose}</span>
                    <Badge className="bg-green-500/10 text-green-400 text-[10px] ml-auto">{a.status}</Badge>
                  </div>
                ))}
              </div>
              <div>
                <h4 className="text-xs font-semibold text-yellow-400 mb-2">Платные (опционально)</h4>
                {montageStatus.apis_needed.paid.map((a) => (
                  <div key={a.name} className="flex items-center gap-2 text-xs text-zinc-300 mb-1.5 flex-wrap">
                    <Volume2 className="h-3.5 w-3.5 text-yellow-400 shrink-0" />
                    <span className="font-medium">{a.name}</span>
                    <span className="text-zinc-500 hidden sm:inline">— {a.purpose}</span>
                    <Badge className="bg-yellow-500/10 text-yellow-400 text-[10px] ml-auto">{a.cost}</Badge>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Montages */}
      {montageClips.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Film className="h-5 w-5 text-violet-400" />
              Последние монтажи ({montageClips.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {montageClips.slice(0, 6).map((clip) => (
                <div key={clip.filename} className="bg-zinc-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Film className="h-4 w-4 text-violet-400 shrink-0" />
                    <span className="text-sm text-white truncate font-medium">{clip.filename}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-zinc-500">
                    <span>{formatBytes(clip.file_size)}</span>
                    <span>{new Date(clip.created_at).toLocaleDateString("ru-RU")}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Trends */}
      {trends.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-400" />
              Активные тренды ({trends.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {trends.sort((a, b) => b.score - a.score).slice(0, 6).map((trend) => (
                <div key={trend.id} className="bg-zinc-800/50 rounded-lg p-3 flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className="bg-violet-500/20 text-violet-400 text-[10px]">{trend.platform}</Badge>
                      <span className="text-sm text-white truncate">{trend.title}</span>
                    </div>
                    <p className="text-xs text-zinc-500 truncate">{trend.description}</p>
                  </div>
                  <div className="text-right ml-2 shrink-0">
                    <div className="text-lg font-bold text-green-400">{trend.score}</div>
                    <div className="text-[10px] text-zinc-500">скор</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* AI Profiles */}
      {profiles.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <UserCircle className="h-5 w-5 text-pink-400" />
              AI Девушки ({profiles.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {profiles.slice(0, 6).map((profile) => (
                <div key={profile.id} className="bg-zinc-800/50 rounded-lg p-3 flex items-center gap-3">
                  {profile.reference_images && profile.reference_images.length > 0 ? (
                    <img
                      src={profile.reference_images[0]}
                      alt={profile.name}
                      className="w-10 h-10 rounded-full object-cover shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-pink-500 to-violet-500 flex items-center justify-center shrink-0">
                      <UserCircle className="h-5 w-5 text-white" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-white truncate">{profile.name}</div>
                    <div className="text-xs text-zinc-500 truncate">{profile.style} &middot; {String(profile.voice_config?.persona_id ?? "default")}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Templates Available */}
      {montageStatus && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Radio className="h-5 w-5 text-cyan-400" />
              Шаблоны монтажа ({Object.keys(montageStatus.templates).length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(montageStatus.templates).map(([id, tmpl]) => (
                <div key={id} className="bg-zinc-800/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-white">{tmpl.name}</span>
                    {tmpl.has_girl && (
                      <Badge className="bg-pink-500/10 text-pink-400 text-[10px]">AI girl</Badge>
                    )}
                  </div>
                  <p className="text-xs text-zinc-500 mb-1">{tmpl.description}</p>
                  <div className="flex gap-3 text-xs text-zinc-500">
                    <span>{tmpl.duration}с</span>
                    <span>{tmpl.phases} фаз</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string | number; color?: string }) {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center gap-2 text-zinc-400 mb-1">
          {icon}
          <span className="text-xs">{label}</span>
        </div>
        <div className={`text-xl sm:text-2xl font-bold ${color || "text-white"}`}>{value}</div>
      </CardContent>
    </Card>
  );
}

function ToolStatus({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className="flex items-center justify-center gap-1">
        {ok ? <CheckCircle className="h-4 w-4 text-green-400" /> : <XCircle className="h-4 w-4 text-red-400" />}
        <span className={`text-sm font-medium ${ok ? "text-green-400" : "text-red-400"}`}>
          {ok ? "Готов" : "Нет"}
        </span>
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_000_000) return (bytes / 1_000_000).toFixed(1) + " МБ";
  if (bytes >= 1_000) return (bytes / 1_000).toFixed(0) + " КБ";
  return bytes + " Б";
}
