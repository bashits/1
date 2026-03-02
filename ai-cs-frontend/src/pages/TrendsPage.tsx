import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { RefreshCw, TrendingUp, Youtube, Instagram } from "lucide-react";
import { api, Trend } from "@/hooks/useApi";

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  youtube: <Youtube className="h-4 w-4 text-red-500" />,
  tiktok: <span className="text-sm">ТТ</span>,
  instagram: <Instagram className="h-4 w-4 text-pink-500" />,
};

const TYPE_COLORS: Record<string, string> = {
  format: "bg-violet-500/20 text-violet-400",
  moment: "bg-cyan-500/20 text-cyan-400",
  style: "bg-green-500/20 text-green-400",
  hook: "bg-orange-500/20 text-orange-400",
};

const PLATFORM_LABELS: Record<string, string> = {
  youtube: "Ютуб",
  tiktok: "ТикТок",
  instagram: "Инстаграм",
};

const TYPE_LABELS: Record<string, string> = {
  format: "Формат",
  moment: "Момент",
  style: "Стиль",
  hook: "Хук",
};

const getLabel = (labels: Record<string, string>, key: string) => labels[key] || key;

export default function TrendsPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  const loadTrends = () => {
    setLoading(true);
    api.getTrends().then(setTrends).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTrends();
  }, []);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await api.analyzeTrends();
      loadTrends();
    } catch (e) {
      console.error(e);
    } finally {
      setAnalyzing(false);
    }
  };

  const platformTrends = (platform: string) => trends.filter((t) => t.platform === platform);

  const chartData = trends
    .sort((a, b) => b.score - a.score)
    .slice(0, 12)
    .map((t) => ({
      name: t.title.length > 20 ? t.title.slice(0, 20) + "..." : t.title,
      score: t.score,
      platform: t.platform,
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg sm:text-xl font-bold text-white">Анализ трендов</h2>
          <p className="text-xs sm:text-sm text-zinc-400">Отслеживай тренды CS2 на платформах</p>
        </div>
        <Button onClick={handleAnalyze} disabled={analyzing} className="bg-violet-600 hover:bg-violet-700 active:bg-violet-800 shrink-0 text-xs sm:text-sm">
          <RefreshCw className={`h-4 w-4 mr-1 sm:mr-2 ${analyzing ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">{analyzing ? "Анализ..." : "Анализировать"}</span>
          <span className="sm:hidden">{analyzing ? "..." : "Анализ"}</span>
        </Button>
      </div>

      {/* Top Trends Chart */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-lg text-white">Топ тренды по скору</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis type="number" domain={[0, 10]} tick={{ fill: "#999", fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 10, fill: "#999" }} />
              <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #333", borderRadius: 8 }} />
              <Bar dataKey="score" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Platform Tabs */}
      <Tabs defaultValue="youtube" className="w-full">
        <TabsList className="bg-zinc-800 border-zinc-700">
          <TabsTrigger value="youtube" className="data-[state=active]:bg-red-500/20 data-[state=active]:text-red-400">
            {getLabel(PLATFORM_LABELS, "youtube")} ({platformTrends("youtube").length})
          </TabsTrigger>
          <TabsTrigger value="tiktok" className="data-[state=active]:bg-zinc-100 data-[state=active]:text-black">
            {getLabel(PLATFORM_LABELS, "tiktok")} ({platformTrends("tiktok").length})
          </TabsTrigger>
          <TabsTrigger value="instagram" className="data-[state=active]:bg-pink-500/20 data-[state=active]:text-pink-400">
            {getLabel(PLATFORM_LABELS, "instagram")} ({platformTrends("instagram").length})
          </TabsTrigger>
        </TabsList>

        {["youtube", "tiktok", "instagram"].map((platform) => (
          <TabsContent key={platform} value={platform}>
            <div className="grid gap-4">
              {loading ? (
                <div className="text-zinc-400 text-center py-8">Загрузка...</div>
              ) : platformTrends(platform).length === 0 ? (
                <div className="text-zinc-400 text-center py-8">Тренды не найдены. Нажми «Анализировать».</div>
              ) : (
                platformTrends(platform).map((trend) => (
                  <Card key={trend.id} className="bg-zinc-900 border-zinc-800 hover:border-zinc-700 transition-colors">
                    <CardContent className="pt-4 pb-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            {PLATFORM_ICONS[platform]}
                            <span className="text-white font-medium">{trend.title}</span>
                            <Badge className={TYPE_COLORS[trend.trend_type] || "bg-zinc-500/20 text-zinc-400"}>
                              {getLabel(TYPE_LABELS, trend.trend_type)}
                            </Badge>
                          </div>
                          <p className="text-sm text-zinc-400">{trend.description}</p>
                          {trend.metadata ? (
                            <div className="flex gap-4 mt-2 text-xs text-zinc-500">
                              {(() => { const m = trend.metadata as Record<string, unknown>; return m.avg_video_length ? <span>Ср. длительность: {String(m.avg_video_length)}с</span> : null; })()}
                              {(() => { const m = trend.metadata as Record<string, unknown>; return m.has_face !== undefined ? <span>Фейс-кам: {m.has_face ? "Да" : "Нет"}</span> : null; })()}
                              {(() => { const m = trend.metadata as Record<string, unknown>; return m.has_subtitles !== undefined ? <span>Субтитры: {m.has_subtitles ? "Да" : "Нет"}</span> : null; })()}
                            </div>
                          ) : null}
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-1 text-violet-400">
                            <TrendingUp className="h-4 w-4" />
                            <span className="text-xl font-bold">{trend.score}</span>
                          </div>
                          <span className="text-xs text-zinc-500">скор</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
