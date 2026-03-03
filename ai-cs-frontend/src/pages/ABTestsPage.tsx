import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Trophy, FlaskConical, Zap } from "lucide-react";
import { api, ABTest } from "@/hooks/useApi";

const AB_STATUS_LABELS: Record<string, string> = {
  running: "Идёт",
  completed: "Завершён",
  draft: "Черновик",
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

function fmtLabel(key: string): string {
  return FORMAT_LABELS[key] || key.replace(/_/g, " ");
}

export default function ABTestsPage() {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [adapting, setAdapting] = useState(false);

  useEffect(() => {
    api.getABTests().then(setTests).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleAdapt = async () => {
    setAdapting(true);
    try {
      const result = await api.adaptWeights();
      alert(result.adapted ? `Веса обновлены: ${result.changes?.length} форматов.` : result.reason || "Без изменений");
    } catch (e) {
      console.error(e);
    } finally {
      setAdapting(false);
    }
  };

  const running = tests.filter((t) => t.status === "running");
  const completed = tests.filter((t) => t.status === "completed");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">A/B тестирование</h2>
          <p className="text-sm text-zinc-400">Сравнение форматов и авто-оптимизация</p>
        </div>
        <Button onClick={handleAdapt} disabled={adapting} className="bg-yellow-600 hover:bg-yellow-700">
          <Zap className={`h-4 w-4 mr-2 ${adapting ? "animate-spin" : ""}`} />
          {adapting ? "Адаптация..." : "Авто-адаптация весов"}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-zinc-400 flex items-center gap-1"><FlaskConical className="h-3 w-3" /> Активные тесты</div>
            <div className="text-2xl font-bold text-yellow-400">{running.length}</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-zinc-400 flex items-center gap-1"><Trophy className="h-3 w-3" /> Завершено</div>
            <div className="text-2xl font-bold text-green-400">{completed.length}</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-zinc-400">Всего тестов</div>
            <div className="text-2xl font-bold text-white">{tests.length}</div>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <div className="text-zinc-400 text-center py-8">Загрузка...</div>
      ) : (
        <div className="space-y-6">
          {tests.map((test) => (
            <ABTestCard key={test.id} test={test} />
          ))}
          {tests.length === 0 && (
            <div className="text-zinc-400 text-center py-8">A/B тестов пока нет. Найди моменты и сгенерируй варианты.</div>
          )}
        </div>
      )}
    </div>
  );
}

function ABTestCard({ test }: { test: ABTest }) {
  const chartData = test.clips.map((c) => ({
    name: fmtLabel(c.format_type),
    views: c.views,
    retention: c.retention_rate,
    ctr: c.ctr,
    watch_through: c.watch_through_rate,
  }));

  const winner = test.clips.find((c) => c.id === test.winner_clip_id);

  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            {test.name}
            <Badge className={test.status === "running" ? "bg-yellow-500/20 text-yellow-400" : "bg-green-500/20 text-green-400"}>
              {AB_STATUS_LABELS[test.status] || test.status}
            </Badge>
          </CardTitle>
          {winner && (
            <div className="flex items-center gap-2 text-sm">
              <Trophy className="h-4 w-4 text-yellow-400" />
              <span className="text-yellow-400">Победитель: {fmtLabel(winner.format_type)}</span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {test.clips.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Chart */}
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#999" }} angle={-20} textAnchor="end" height={60} />
                <YAxis tick={{ fill: "#999" }} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #333", borderRadius: 8 }} />
                <Legend />
                <Bar dataKey="retention" fill="#10b981" name="Удержание %" />
                <Bar dataKey="ctr" fill="#06b6d4" name="CTR %" />
                <Bar dataKey="watch_through" fill="#f59e0b" name="Досмотр %" />
              </BarChart>
            </ResponsiveContainer>

            {/* Clip List */}
            <div className="space-y-2">
              {test.clips.map((clip) => (
                <div
                  key={clip.id}
                  className={`p-3 rounded-lg border ${clip.id === test.winner_clip_id ? "border-yellow-500/50 bg-yellow-500/5" : "border-zinc-800 bg-zinc-800/50"}`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm text-white">{fmtLabel(clip.format_type)}</span>
                      {clip.id === test.winner_clip_id && <Trophy className="h-3 w-3 text-yellow-400 inline ml-2" />}
                    </div>
                    <div className="flex gap-4 text-xs text-zinc-400">
                      <span>Просм.: <span className="text-white">{clip.views.toLocaleString()}</span></span>
                      <span>Удерж.: <span className="text-green-400">{clip.retention_rate}%</span></span>
                      <span>Кликабельность: <span className="text-cyan-400">{clip.ctr}%</span></span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-zinc-500 text-sm">В этом тесте пока нет клипов</div>
        )}
      </CardContent>
    </Card>
  );
}
