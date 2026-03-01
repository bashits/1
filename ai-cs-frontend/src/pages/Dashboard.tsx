import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend
} from "recharts";
import { Eye, Heart, MessageCircle, TrendingUp, Zap, Target, Film, Activity } from "lucide-react";
import { api, AnalyticsOverview, FormatPerformance, GrowthPhase } from "@/hooks/useApi";

const COLORS = ["#8b5cf6", "#06b6d4", "#f59e0b", "#ef4444", "#10b981", "#ec4899", "#3b82f6", "#f97316", "#6366f1"];

const PHASE_LABELS: Record<number, string> = {
  1: "Макс. тесты",
  2: "Топ форматы",
  3: "Масштаб",
  4: "Брендинг",
  5: "Реклама",
};

const FORMAT_LABELS: Record<string, string> = {
  clean_highlight: "Чистый хайлайт",
  highlight_reaction: "Хайлайт + реакция",
  highlight_subtitles: "Хайлайт + субтитры",
  highlight_ai_girl: "Хайлайт + AI девушка",
  meme_format: "Мем-формат",
  dramatic_clutch: "Драматичный клатч",
  provocative: "Провокация",
  hard_fragmovie: "Фрагмуви",
  fail_format: "Фейл-формат",
};

const PHASE_DESC: Record<string, string> = {
  "Test all formats with maximum volume": "Тестируем все форматы на максимальных объёмах",
  "Double down on winning formats": "Удваиваем ставку на лучшие форматы",
  "Scale winning formats across platforms": "Масштабируем лучшие форматы на все платформы",
  "Build recognizable brand and style": "Строим узнаваемый бренд и стиль",
  "Integrate advertising and sponsorships": "Интегрируем рекламу и спонсорство",
};

function formatLabel(key: string): string {
  return FORMAT_LABELS[key] || key.replace(/_/g, " ");
}

export default function Dashboard() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [formats, setFormats] = useState<FormatPerformance[]>([]);
  const [phase, setPhase] = useState<GrowthPhase | null>(null);
  const [recommendations, setRecommendations] = useState<string[]>([]);

  useEffect(() => {
    api.getOverview().then(setOverview).catch(console.error);
    api.getFormatPerformance().then(setFormats).catch(console.error);
    api.getGrowthPhase().then(setPhase).catch(console.error);
    api.getRecommendations().then((r) => setRecommendations(r.recommendations)).catch(console.error);
  }, []);

  if (!overview) return <div className="flex items-center justify-center h-64 text-zinc-400">Загрузка...</div>;

  const formatChartData = formats.map((f) => ({
    name: formatLabel(f.format_type),
    views: f.total_views,
    retention: f.avg_retention,
    ctr: f.avg_ctr,
    score: f.score,
  }));

  const pieData = formats.map((f) => ({
    name: formatLabel(f.format_type),
    value: f.total_clips,
  }));

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Film className="h-4 w-4" />} label="Всего клипов" value={overview.total_clips} />
        <StatCard icon={<Eye className="h-4 w-4" />} label="Просмотры" value={formatNumber(overview.total_views)} />
        <StatCard icon={<Heart className="h-4 w-4" />} label="Лайки" value={formatNumber(overview.total_likes)} />
        <StatCard icon={<MessageCircle className="h-4 w-4" />} label="Комментарии" value={formatNumber(overview.total_comments)} />
        <StatCard icon={<TrendingUp className="h-4 w-4" />} label="Ср. удержание" value={`${overview.avg_retention}%`} color="text-green-400" />
        <StatCard icon={<Target className="h-4 w-4" />} label="Ср. CTR" value={`${overview.avg_ctr}%`} color="text-cyan-400" />
        <StatCard icon={<Zap className="h-4 w-4" />} label="A/B тесты" value={overview.active_ab_tests} color="text-yellow-400" />
        <StatCard icon={<Activity className="h-4 w-4" />} label="Акт. тренды" value={overview.active_trends} color="text-purple-400" />
      </div>

      {/* Growth Phase */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-lg text-white flex items-center gap-2">
            Фаза роста
            <Badge variant="outline" className="text-violet-400 border-violet-400">
              Фаза {phase?.current_phase || overview.current_phase}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            {[1, 2, 3, 4, 5].map((p) => (
              <div key={p} className="flex-1">
                <div className={`text-xs mb-1 text-center ${p <= (phase?.current_phase || 1) ? "text-violet-400" : "text-zinc-600"}`}>
                  {PHASE_LABELS[p]}
                </div>
                <Progress
                  value={p < (phase?.current_phase || 1) ? 100 : p === (phase?.current_phase || 1) ? 50 : 0}
                  className="h-2"
                />
              </div>
            ))}
          </div>
          <p className="text-sm text-zinc-400">{PHASE_DESC[phase?.phase_info?.description || ""] || phase?.phase_info?.description || "Загрузка..."}</p>
        </CardContent>
      </Card>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Format Performance Bar Chart */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg text-white">Эффективность форматов (просмотры)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={formatChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#999" }} angle={-35} textAnchor="end" height={80} />
                <YAxis tick={{ fill: "#999" }} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #333", borderRadius: 8 }} />
                <Bar dataKey="views" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Clip Distribution Pie */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg text-white">Распределение клипов по форматам</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #333", borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Retention & CTR Comparison */}
        <Card className="bg-zinc-900 border-zinc-800 lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg text-white">Удержание vs CTR по форматам</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={formatChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#999" }} angle={-35} textAnchor="end" height={80} />
                <YAxis tick={{ fill: "#999" }} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #333", borderRadius: 8 }} />
                <Legend />
                <Line type="monotone" dataKey="retention" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} name="Удержание %" />
                <Line type="monotone" dataKey="ctr" stroke="#06b6d4" strokeWidth={2} dot={{ r: 4 }} name="CTR %" />
                <Line type="monotone" dataKey="score" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} name="Скор" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-lg text-white">Рекомендации по стратегии</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {recommendations.map((rec, i) => (
              <li key={i} className="text-sm text-zinc-300 flex items-start gap-2">
                <span className="text-violet-400 mt-0.5">&#8226;</span>
                {rec}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
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
        <div className={`text-2xl font-bold ${color || "text-white"}`}>{value}</div>
      </CardContent>
    </Card>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toString();
}
