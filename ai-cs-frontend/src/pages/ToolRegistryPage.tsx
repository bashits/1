import { useEffect, useState } from "react";
import { api, Tool, PipelineConfig } from "@/hooks/useApi";
import { Github, Star, Cpu, Check, DollarSign, Zap, Award } from "lucide-react";

const CATEGORY_LABELS: Record<string, string> = {
  image_generation: "Генерация изображений",
  image_consistency: "Консистентность лица/персонажа",
  lip_sync: "Липсинк / говорящая голова",
  face_animation: "Анимация лица",
  voice_tts: "Голос / TTS",
  video_generation: "Генерация видео",
  orchestration: "Оркестрация пайплайна",
  face_swap: "Свап лица",
};

const CATEGORY_COLORS: Record<string, string> = {
  image_generation: "text-blue-400 bg-blue-500/15",
  image_consistency: "text-cyan-400 bg-cyan-500/15",
  lip_sync: "text-pink-400 bg-pink-500/15",
  face_animation: "text-orange-400 bg-orange-500/15",
  voice_tts: "text-green-400 bg-green-500/15",
  video_generation: "text-violet-400 bg-violet-500/15",
  orchestration: "text-yellow-400 bg-yellow-500/15",
  face_swap: "text-red-400 bg-red-500/15",
};

const BUDGET_LABELS: Record<string, string> = {
  minimal: "минимум",
  moderate: "сбалансировано",
  full: "максимум качества",
};

export default function ToolRegistryPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [budgets, setBudgets] = useState<Record<string, PipelineConfig> | null>(null);
  const [selectedBudget, setSelectedBudget] = useState("minimal");
  const [filterCategory, setFilterCategory] = useState("");

  useEffect(() => {
    api.getTools().then(setTools).catch(() => {});
    api.compareBudgets().then(setBudgets).catch(() => {});
  }, []);

  const handleToggle = async (tool: Tool) => {
    const updated = await api.toggleToolSelection(tool.id, !tool.is_selected);
    setTools(tools.map(t => t.id === tool.id ? updated : t));
  };

  const categories = [...new Set(tools.map(t => t.category))];
  const filtered = filterCategory ? tools.filter(t => t.category === filterCategory) : tools;
  const grouped = categories.reduce<Record<string, Tool[]>>((acc, cat) => {
    acc[cat] = filtered.filter(t => t.category === cat);
    return acc;
  }, {});

  const selectedTools = tools.filter(t => t.is_selected);
  const totalStars = tools.reduce((s, t) => s + t.github_stars, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Реестр open-source инструментов</h1>
        <p className="text-zinc-400 text-sm mt-1">
          {tools.length} инструментов проанализировано &middot; {totalStars.toLocaleString()} звёзд GitHub &middot; {selectedTools.length} выбрано в пайплайн
        </p>
      </div>

      {/* Budget Comparison */}
      {budgets && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Сравнение стоимости</h3>
          <div className="grid grid-cols-3 gap-4">
            {(["minimal", "moderate", "full"] as const).map(budget => {
              const config = budgets[budget];
              if (!config) return null;
              return (
                <div key={budget} onClick={() => setSelectedBudget(budget)} className={`bg-zinc-900 border rounded-xl p-5 cursor-pointer transition-colors ${selectedBudget === budget ? "border-violet-500" : "border-zinc-800 hover:border-zinc-700"}`}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-semibold">{BUDGET_LABELS[budget] || budget}</span>
                    <span className="text-lg font-bold text-green-400">{config.total_monthly_cost}</span>
                  </div>
                  <p className="text-xs text-zinc-500 mb-3">{config.setup}</p>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between"><span className="text-zinc-400">Фото:</span> <span>{config.image?.tool}</span></div>
                    <div className="flex justify-between"><span className="text-zinc-400">Липсинк:</span> <span>{config.lip_sync?.tool}</span></div>
                    <div className="flex justify-between"><span className="text-zinc-400">Голос:</span> <span>{config.voice?.tool}</span></div>
                    <div className="flex justify-between"><span className="text-zinc-400">Видео:</span> <span>{config.video?.tool}</span></div>
                    <div className="flex justify-between"><span className="text-zinc-400">Оркестрация:</span> <span>{config.orchestration}</span></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Selected Pipeline */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-violet-400 mb-3">Выбранный пайплайн ({selectedTools.length} инструментов)</h3>
        <div className="flex gap-2 flex-wrap">
          {selectedTools.map(t => (
            <span key={t.id} className="flex items-center gap-1.5 text-xs bg-violet-500/15 text-violet-400 px-3 py-1.5 rounded-full">
              <Check className="h-3 w-3" /> {t.name}
            </span>
          ))}
          {selectedTools.length === 0 && <span className="text-xs text-zinc-500">Инструменты ещё не выбраны</span>}
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setFilterCategory("")} className={`text-xs px-3 py-1.5 rounded-full transition-colors ${!filterCategory ? "bg-violet-500/20 text-violet-400" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"}`}>
          Все ({tools.length})
        </button>
        {categories.map(cat => (
          <button key={cat} onClick={() => setFilterCategory(cat)} className={`text-xs px-3 py-1.5 rounded-full transition-colors ${filterCategory === cat ? (CATEGORY_COLORS[cat] || "bg-violet-500/20 text-violet-400") : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"}`}>
            {CATEGORY_LABELS[cat] || cat} ({tools.filter(t => t.category === cat).length})
          </button>
        ))}
      </div>

      {/* Tool Cards by Category */}
      {Object.entries(grouped).filter(([, items]) => items.length > 0).map(([category, items]) => (
        <div key={category} className="space-y-3">
          <h3 className={`text-sm font-semibold uppercase tracking-wider ${CATEGORY_COLORS[category]?.split(" ")[0] || "text-zinc-400"}`}>
            {CATEGORY_LABELS[category] || category}
          </h3>
          <div className="grid grid-cols-1 gap-3">
            {items.map(tool => (
              <div key={tool.id} className={`bg-zinc-900 border rounded-xl p-4 transition-colors ${tool.is_selected ? "border-violet-500/50" : "border-zinc-800"}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="font-medium">{tool.name}</span>
                      <div className="flex items-center gap-1 text-yellow-400 text-xs">
                        <Star className="h-3 w-3 fill-current" /> {tool.github_stars.toLocaleString()}
                      </div>
                      {tool.license && <span className="text-xs bg-zinc-800 px-2 py-0.5 rounded">{tool.license}</span>}
                      {tool.is_free && <span className="text-xs bg-green-500/15 text-green-400 px-2 py-0.5 rounded">Бесплатно</span>}
                    </div>
                    <p className="text-sm text-zinc-400 mb-2">{tool.description}</p>
                    <div className="flex gap-3 text-xs text-zinc-500">
                      <span className="flex items-center gap-1"><Cpu className="h-3 w-3" /> {tool.min_vram_gb} ГБ VRAM</span>
                      <span className="flex items-center gap-1"><Award className="h-3 w-3" /> Качество: {tool.quality_score}/10</span>
                      <span className="flex items-center gap-1"><Zap className="h-3 w-3" /> Скорость: {tool.speed_score}/10</span>
                      {tool.api_cost_per_use > 0 && <span className="flex items-center gap-1"><DollarSign className="h-3 w-3" /> ${tool.api_cost_per_use}/запрос</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 ml-4">
                    {tool.github_url && (
                      <a href={tool.github_url} target="_blank" rel="noopener noreferrer" className="text-zinc-500 hover:text-white transition-colors">
                        <Github className="h-5 w-5" />
                      </a>
                    )}
                    <button onClick={() => handleToggle(tool)} className={`w-10 h-6 rounded-full transition-colors relative ${tool.is_selected ? "bg-violet-500" : "bg-zinc-700"}`}>
                      <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-all ${tool.is_selected ? "left-4" : "left-0.5"}`} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
