import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Sparkles, Save } from "lucide-react";
import { api, AIGirlConfig } from "@/hooks/useApi";

export default function AIGirlPage() {
  const [config, setConfig] = useState<AIGirlConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAIGirlConfig().then(setConfig).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const updated = await api.updateAIGirlConfig({
        is_enabled: config.is_enabled,
        model_name: config.model_name,
        voice_style: config.voice_style,
        appearance_style: config.appearance_style,
        overlay_position: config.overlay_position,
        overlay_size: config.overlay_size,
        use_only_when_better: config.use_only_when_better,
        min_improvement_pct: config.min_improvement_pct,
      });
      setConfig(updated);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !config) return <div className="text-zinc-400 text-center py-8">Загрузка...</div>;

  const comparisonData = [
    { name: "С AI девушкой", retention: config.avg_retention_with, clips: config.total_clips_with },
    { name: "Без AI девушки", retention: config.avg_retention_without, clips: config.total_clips_without },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-pink-400" />
            Настройка AI девушки
          </h2>
          <p className="text-sm text-zinc-400">Настройка оверлея AI девушки для форматов клипов</p>
        </div>
        <Button onClick={handleSave} disabled={saving} className="bg-pink-600 hover:bg-pink-700">
          <Save className="h-4 w-4 mr-2" />
          {saving ? "Сохранение..." : "Сохранить"}
        </Button>
      </div>

      {/* Status & Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg text-white">Сравнение эффективности</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" tick={{ fill: "#999" }} />
                <YAxis tick={{ fill: "#999" }} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #333", borderRadius: 8 }} />
                <Legend />
                <Bar dataKey="retention" fill="#ec4899" name="Ср. удержание %" />
                <Bar dataKey="clips" fill="#6366f1" name="Всего клипов" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg text-white">Статистика</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-zinc-400">Клипы с AI девушкой</div>
                <div className="text-xl font-bold text-pink-400">{config.total_clips_with}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-400">Клипы без</div>
                <div className="text-xl font-bold text-zinc-300">{config.total_clips_without}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-400">Удержание с</div>
                <div className="text-xl font-bold text-green-400">{config.avg_retention_with}%</div>
              </div>
              <div>
                <div className="text-xs text-zinc-400">Удержание без</div>
                <div className="text-xl font-bold text-zinc-300">{config.avg_retention_without}%</div>
              </div>
            </div>
            {config.avg_retention_with > config.avg_retention_without ? (
              <Badge className="bg-green-500/20 text-green-400">AI девушка улучшает удержание</Badge>
            ) : config.total_clips_with < 5 ? (
              <Badge className="bg-yellow-500/20 text-yellow-400">Нужно больше данных</Badge>
            ) : (
              <Badge className="bg-red-500/20 text-red-400">AI девушка не даёт результат</Badge>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Configuration */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-lg text-white">Настройки</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Enable/Disable */}
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-white">Включить AI девушку</Label>
              <p className="text-xs text-zinc-400">Показывать оверлей AI девушки в подходящих форматах</p>
            </div>
            <Switch
              checked={config.is_enabled}
              onCheckedChange={(val) => setConfig({ ...config, is_enabled: val })}
            />
          </div>

          <Separator className="bg-zinc-800" />

          {/* Use Only When Better */}
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-white">Только когда лучше</Label>
              <p className="text-xs text-zinc-400">Использовать AI девушку только когда метрики улучшаются</p>
            </div>
            <Switch
              checked={config.use_only_when_better}
              onCheckedChange={(val) => setConfig({ ...config, use_only_when_better: val })}
            />
          </div>

          <Separator className="bg-zinc-800" />

          <div className="grid grid-cols-2 gap-6">
            {/* Model Name */}
            <div>
              <Label className="text-zinc-400">Имя модели</Label>
              <Input
                value={config.model_name}
                onChange={(e) => setConfig({ ...config, model_name: e.target.value })}
                className="bg-zinc-800 border-zinc-700 text-white"
              />
            </div>

            {/* Voice Style */}
            <div>
              <Label className="text-zinc-400">Стиль голоса</Label>
              <Select value={config.voice_style} onValueChange={(val) => setConfig({ ...config, voice_style: val })}>
                <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-zinc-800 border-zinc-700">
                  <SelectItem value="energetic">Энергичный</SelectItem>
                  <SelectItem value="calm">Спокойный</SelectItem>
                  <SelectItem value="excited">Возбуждённый</SelectItem>
                  <SelectItem value="sarcastic">Саркастичный</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Appearance */}
            <div>
              <Label className="text-zinc-400">Стиль внешности</Label>
              <Select value={config.appearance_style} onValueChange={(val) => setConfig({ ...config, appearance_style: val })}>
                <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-zinc-800 border-zinc-700">
                  <SelectItem value="anime">Аниме</SelectItem>
                  <SelectItem value="realistic">Реалистичный</SelectItem>
                  <SelectItem value="cartoon">Мультяшный</SelectItem>
                  <SelectItem value="vtuber">ВТьюбер</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Overlay Position */}
            <div>
              <Label className="text-zinc-400">Позиция оверлея</Label>
              <Select value={config.overlay_position} onValueChange={(val) => setConfig({ ...config, overlay_position: val })}>
                <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-zinc-800 border-zinc-700">
                  <SelectItem value="bottom-right">Внизу справа</SelectItem>
                  <SelectItem value="bottom-left">Внизу слева</SelectItem>
                  <SelectItem value="top-right">Вверху справа</SelectItem>
                  <SelectItem value="top-left">Вверху слева</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Separator className="bg-zinc-800" />

          {/* Overlay Size */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-zinc-400">Размер оверлея</Label>
              <span className="text-sm text-violet-400">{(config.overlay_size * 100).toFixed(0)}%</span>
            </div>
            <Slider
              value={[config.overlay_size]}
              min={0.1}
              max={0.5}
              step={0.05}
              onValueChange={(val) => setConfig({ ...config, overlay_size: val[0] })}
            />
          </div>

          {/* Min Improvement */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-zinc-400">Мин. улучшение % (для авто-включения)</Label>
              <span className="text-sm text-violet-400">{config.min_improvement_pct}%</span>
            </div>
            <Slider
              value={[config.min_improvement_pct]}
              min={1}
              max={30}
              step={1}
              onValueChange={(val) => setConfig({ ...config, min_improvement_pct: val[0] })}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
