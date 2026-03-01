import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { api, Template } from "@/hooks/useApi";

const FORMAT_ICONS: Record<string, string> = {
  clean_highlight: "Чистый хайлайт",
  highlight_reaction: "Хайлайт + реакция",
  highlight_subtitles: "Хайлайт + субтитры",
  highlight_ai_girl: "Хайлайт + AI девушка",
  meme_format: "Мем формат",
  dramatic_clutch: "Драматичный клатч",
  provocative: "Провокационный",
  hard_fragmovie: "Жёсткий фрагмуви",
  fail_format: "Фейлы",
};

const DESC_LABELS: Record<string, string> = {
  "Clean highlight without overlays": "Чистый хайлайт без оверлеев",
  "Highlight with streamer reaction cam": "Хайлайт с фейс-камерой стримера",
  "Highlight with large dynamic subtitles": "Хайлайт с крупными динамическими субтитрами",
  "Highlight with AI girl commentator": "Хайлайт с комментарием AI девушки",
  "Meme-style edit with sound effects": "Мем-формат с звуковыми эффектами",
  "Dramatic clutch breakdown with slow-mo": "Драматичный разбор клатча со слоу-мо",
  "Provocative title/hook format": "Провокационный формат с цепляющим заголовком",
  "Hard fragmovie style edit": "Жёсткий монтаж в стиле фрагмуви",
  "Fail/blooper compilation style": "Компиляция фейлов и забавных моментов",
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = () => {
    setLoading(true);
    api.getTemplates().then(setTemplates).catch(console.error).finally(() => setLoading(false));
  };

  const handleToggle = async (id: number, active: boolean) => {
    await api.updateTemplate(id, { is_active: active });
    loadTemplates();
  };

  const handleWeightChange = async (id: number, weight: number) => {
    await api.updateTemplate(id, { weight });
    setTemplates((prev) =>
      prev.map((t) => (t.id === id ? { ...t, weight } : t))
    );
  };

  const chartData = templates.map((t) => ({
    name: (FORMAT_ICONS[t.format_type] || t.name).substring(0, 15),
    weight: t.weight,
    retention: t.avg_retention,
    ctr: t.avg_ctr,
  }));

  if (loading) return <div className="text-zinc-400 text-center py-8">Загрузка...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">Шаблоны форматов</h2>
        <p className="text-sm text-zinc-400">Управляй шаблонами форматов и их весами</p>
      </div>

      {/* Weight Distribution Chart */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-lg text-white">Распределение весов шаблонов</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#999" }} angle={-25} textAnchor="end" height={60} />
              <YAxis tick={{ fill: "#999" }} />
              <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #333", borderRadius: 8 }} />
              <Bar dataKey="weight" fill="#8b5cf6" name="Вес" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Template Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map((tmpl) => {
          const config = tmpl.config as Record<string, unknown>;
          return (
            <Card key={tmpl.id} className={`border transition-colors ${tmpl.is_active ? "bg-zinc-900 border-zinc-800 hover:border-zinc-700" : "bg-zinc-950 border-zinc-900 opacity-60"}`}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-white font-medium text-sm">
                    {FORMAT_ICONS[tmpl.format_type] || tmpl.name}
                  </h3>
                  <Switch
                    checked={tmpl.is_active}
                    onCheckedChange={(val) => handleToggle(tmpl.id, val)}
                  />
                </div>
                <p className="text-xs text-zinc-400 mb-3">{(tmpl.description && DESC_LABELS[tmpl.description]) || tmpl.description || ""}</p>

                {/* Feature badges */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {config.subtitles ? <Badge variant="outline" className="text-xs text-cyan-400 border-cyan-400/30">Субтитры</Badge> : null}
                  {config.ai_girl ? <Badge variant="outline" className="text-xs text-pink-400 border-pink-400/30">AI девушка</Badge> : null}
                  {config.face_cam ? <Badge variant="outline" className="text-xs text-green-400 border-green-400/30">Фейс-кам</Badge> : null}
                  {config.slow_motion ? <Badge variant="outline" className="text-xs text-blue-400 border-blue-400/30">Слоу-мо</Badge> : null}
                  {config.meme_sounds ? <Badge variant="outline" className="text-xs text-yellow-400 border-yellow-400/30">Мем SFX</Badge> : null}
                  {config.sync_music ? <Badge variant="outline" className="text-xs text-purple-400 border-purple-400/30">Синк муз.</Badge> : null}
                  {config.zoom_effects ? <Badge variant="outline" className="text-xs text-orange-400 border-orange-400/30">Зум FX</Badge> : null}
                </div>

                {/* Weight slider */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-zinc-400">Вес</span>
                    <span className="text-violet-400 font-medium">{tmpl.weight.toFixed(2)}</span>
                  </div>
                  <Slider
                    value={[tmpl.weight]}
                    min={0}
                    max={3}
                    step={0.1}
                    onValueCommit={(val) => handleWeightChange(tmpl.id, val[0])}
                    className="w-full"
                  />
                </div>

                {/* Stats */}
                <div className="flex gap-4 mt-3 text-xs text-zinc-500">
                  <span>Клипы: {tmpl.total_clips}</span>
                  <span>Удерж.: {tmpl.avg_retention}%</span>
                  <span>CTR: {tmpl.avg_ctr}%</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
