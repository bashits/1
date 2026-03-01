import { useEffect, useState } from "react";
import { api, RegionAnalysis, RegionRecommendations, Account } from "@/hooks/useApi";
import { Globe, TrendingUp, Users, Plus, Trash2, MapPin, Instagram, Youtube, BarChart3 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const PLATFORM_ICONS: Record<string, typeof Instagram> = {
  instagram: Instagram,
  youtube_shorts: Youtube,
};

const COMPETITION_COLORS: Record<string, string> = {
  low: "text-green-400 bg-green-500/15",
  "medium-low": "text-green-400 bg-green-500/15",
  medium: "text-yellow-400 bg-yellow-500/15",
  "medium-high": "text-orange-400 bg-orange-500/15",
  high: "text-red-400 bg-red-500/15",
  very_high: "text-red-400 bg-red-500/15",
};

const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Инстаграм",
  youtube_shorts: "Ютуб Шортс",
};

const REGION_LABELS: Record<string, string> = {
  CIS: "СНГ",
  "СНГ": "СНГ",
  "Brazil/LATAM": "Бразилия/LATAM",
  "Бразилия/LATAM": "Бразилия/LATAM",
  "Western Europe": "Западная Европа",
  "Западная Европа": "Западная Европа",
  "North America": "Северная Америка",
  "Turkey/Middle East": "Турция/Бл. Восток",
  "Турция/Ближний Восток": "Турция/Бл. Восток",
  "Southeast Asia": "Юго-Вост. Азия",
  "Юго-Восточная Азия": "Юго-Вост. Азия",
  "Глобально (EN)": "Глобально (EN)",
  "Глобально": "Глобально",
  "Западная Европа / Северная Америка": "Европа/Сев. Америка",
};

const LANGUAGE_LABELS: Record<string, string> = {
  ru: "Русский",
  en: "Английский",
  pt: "Португальский",
  es: "Испанский",
  tr: "Турецкий",
  ar: "Арабский",
  de: "Немецкий",
  fr: "Французский",
  id: "Индонезийский",
  th: "Тайский",
  ua: "Украинский",
};

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  streamer: "CS2 хайлайты",
  ai_girl: "AI девушка",
  highlights: "Смешанные хайлайты",
  cs2_highlights: "CS2 хайлайты",
};

const COMPETITION_LABELS: Record<string, string> = {
  low: "низкая",
  "medium-low": "средне-низкая",
  medium: "средняя",
  "medium-high": "средне-высокая",
  high: "высокая",
  very_high: "очень высокая",
};

const SIM_STRATEGY_LABELS: Record<string, string> = {
  recommended_provider: "Рекомендуемый провайдер",
  vpn_usage: "Использование VPN",
  warming_period: "Период прогрева",
  initial_region: "Начальный регион",
  secondary_region: "Вторичный регион",
  primary_region: "Основной регион",
  sim_type: "Тип SIM",
  services: "Сервисы",
  cost: "Стоимость",
  note: "Примечание",
};

const WARMING_LABELS: Record<string, string> = {
  day_1_3: "Дни 1–3",
  day_4_7: "Дни 4–7",
  day_8_14: "Дни 8–14",
  day_15_plus: "Дни 15+",
  week_2: "Неделя 2",
  week_3_4: "Недели 3–4",
  month_2_plus: "Месяц 2+",
};

const CONTENT_TYPE_LABELS: Record<string, string> = {
  highlights: "хайлайты",
  meme_clips: "мем-клипы",
  meme_format: "мем-формат",
  reactions: "реакции",
  fragmovies: "фрагмуви",
  tutorials: "туториалы",
  provocative: "провокация",
  dramatic_clutch: "драм. клатч",
  fail_format: "фейлы",
  clean_highlight: "чистый хайлайт",
  highlight_subtitles: "хайлайт + субтитры",
  highlight_ai_girl: "хайлайт + AI девушка",
  highlight_reaction: "хайлайт + реакция",
  hard_fragmovie: "жёсткий фрагмуви",
};

const getLabel = (labels: Record<string, string>, key: string) => labels[key] || key;

export default function AccountStrategyPage() {
  const [regions, setRegions] = useState<RegionAnalysis[]>([]);
  const [recommendations, setRecommendations] = useState<RegionRecommendations | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    platform: "instagram",
    handle: "",
    account_type: "streamer",
    region: "CIS",
    language: "ru",
  });

  useEffect(() => {
    api.getRegions().then(setRegions).catch(() => {});
    api.getRegionRecommendations().then(setRecommendations).catch(() => {});
    api.getAccounts().then(setAccounts).catch(() => {});
  }, []);

  const handleCreate = async () => {
    const account = await api.createAccount({
      platform: form.platform,
      handle: form.handle,
      account_type: form.account_type,
      region: form.region,
      language: form.language,
    });
    setAccounts([account, ...accounts]);
    setShowCreate(false);
    setForm({ platform: "instagram", handle: "", account_type: "streamer", region: "CIS", language: "ru" });
  };

  const handleDelete = async (id: number) => {
    await api.deleteAccount(id);
    setAccounts(accounts.filter(a => a.id !== id));
  };

  const chartData = regions.map(r => ({
    name: `${r.region.split("(")[0].trim()} (${r.platform === "instagram" ? "ИН" : "ЮТ"})`,
    growth: r.growth_potential,
    views: r.avg_views_per_reel / 1000,
    audience: r.audience_size / 1000000,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Аккаунты и регионы</h1>
          <p className="text-zinc-400 text-sm mt-1">Региональный анализ для выбора региона аккаунта и покупки SIM</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          <Plus className="h-4 w-4" /> Добавить аккаунт
        </button>
      </div>

      {/* Create Account Form */}
      {showCreate && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
          <h3 className="text-lg font-semibold text-violet-400">Добавить аккаунт платформы</h3>
          <div className="grid grid-cols-5 gap-4">
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Платформа</label>
              <select value={form.platform} onChange={e => setForm({...form, platform: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
                <option value="instagram">Инстаграм</option>
                <option value="youtube_shorts">Ютуб Шортс</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Ник</label>
              <input value={form.handle} onChange={e => setForm({...form, handle: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm" placeholder="@ник" />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Тип</label>
              <select value={form.account_type} onChange={e => setForm({...form, account_type: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
                <option value="streamer">CS2 хайлайты</option>
                <option value="ai_girl">AI девушка</option>
                <option value="highlights">Смешанные хайлайты</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Регион</label>
              <select value={form.region} onChange={e => setForm({...form, region: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
                <option value="CIS">СНГ (Россия/Украина)</option>
                <option value="Brazil/LATAM">Бразилия / Латинская Америка</option>
                <option value="Western Europe">Западная Европа</option>
                <option value="North America">Северная Америка</option>
                <option value="Turkey/Middle East">Турция/Ближний Восток</option>
                <option value="Southeast Asia">Юго-Восточная Азия</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Язык</label>
              <select value={form.language} onChange={e => setForm({...form, language: e.target.value})} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
                <option value="ru">Русский</option>
                <option value="en">Английский</option>
                <option value="pt">Португальский</option>
                <option value="es">Испанский</option>
                <option value="tr">Турецкий</option>
              </select>
            </div>
          </div>
          <button onClick={handleCreate} disabled={!form.handle} className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50 px-6 py-2 rounded-lg text-sm font-medium transition-colors">
            Добавить аккаунт
          </button>
        </div>
      )}

      {/* Accounts List */}
      {accounts.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Твои аккаунты ({accounts.length})</h3>
          <div className="grid grid-cols-3 gap-3">
            {accounts.map(a => {
              const Icon = PLATFORM_ICONS[a.platform] || Globe;
              return (
                <div key={a.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Icon className="h-5 w-5 text-violet-400" />
                      <span className="font-medium">{a.handle}</span>
                    </div>
                    <button onClick={() => handleDelete(a.id)} className="text-zinc-600 hover:text-red-400"><Trash2 className="h-4 w-4" /></button>
                  </div>
                  <div className="flex gap-2 text-xs">
                    <span className="bg-zinc-800 px-2 py-0.5 rounded">{getLabel(PLATFORM_LABELS, a.platform)}</span>
                    <span className="bg-zinc-800 px-2 py-0.5 rounded">{getLabel(REGION_LABELS, a.region)}</span>
                    <span className="bg-zinc-800 px-2 py-0.5 rounded">{getLabel(LANGUAGE_LABELS, a.language)}</span>
                    <span className="bg-violet-500/15 text-violet-400 px-2 py-0.5 rounded">{getLabel(ACCOUNT_TYPE_LABELS, a.account_type)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Region Growth Chart */}
      {chartData.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Потенциал роста по регионам</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <XAxis dataKey="name" tick={{ fill: "#a1a1aa", fontSize: 10 }} angle={-20} textAnchor="end" height={60} />
              <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: "8px" }} labelStyle={{ color: "#fff" }} />
              <Bar dataKey="growth" name="Потенциал роста" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.growth >= 8.5 ? "#22c55e" : entry.growth >= 7 ? "#eab308" : "#ef4444"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Region Cards */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Анализ регионов</h3>
        <div className="grid grid-cols-2 gap-4">
          {regions.map(r => (
            <div key={r.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-violet-400" />
                    <span className="font-medium">{r.region}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    {r.platform === "instagram" ? <Instagram className="h-3 w-3 text-pink-400" /> : <Youtube className="h-3 w-3 text-red-400" />}
                    <span className="text-xs text-zinc-400">{r.platform === "instagram" ? "Рилсы (Инстаграм)" : "Шортсы (Ютуб)"}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-green-400">{r.growth_potential}</div>
                  <div className="text-xs text-zinc-500">скор роста</div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-3 text-xs">
                <div className="bg-zinc-800 rounded p-2 text-center">
                  <Users className="h-3 w-3 mx-auto mb-1 text-zinc-500" />
                  <div className="font-medium">{(r.audience_size / 1000000).toFixed(1)}M</div>
                  <div className="text-zinc-500">Аудитория</div>
                </div>
                <div className="bg-zinc-800 rounded p-2 text-center">
                  <BarChart3 className="h-3 w-3 mx-auto mb-1 text-zinc-500" />
                  <div className="font-medium">{(r.avg_views_per_reel / 1000).toFixed(0)}K</div>
                  <div className="text-zinc-500">Ср. просмотры</div>
                </div>
                <div className="bg-zinc-800 rounded p-2 text-center">
                  <TrendingUp className="h-3 w-3 mx-auto mb-1 text-zinc-500" />
                  <div className={`font-medium ${COMPETITION_COLORS[r.competition_level]?.split(" ")[0] || ""}`}>{getLabel(COMPETITION_LABELS, r.competition_level)}</div>
                  <div className="text-zinc-500">Конкуренция</div>
                </div>
              </div>

              <div className="flex gap-1 mb-2 flex-wrap">
                {r.top_languages.map(l => <span key={l} className="text-xs bg-blue-500/15 text-blue-400 px-2 py-0.5 rounded">{l}</span>)}
                {r.top_content_types.map(t => <span key={t} className="text-xs bg-zinc-800 px-2 py-0.5 rounded">{getLabel(CONTENT_TYPE_LABELS, t)}</span>)}
              </div>

              {r.recommendation && (
                <p className="text-xs text-zinc-400 leading-relaxed border-t border-zinc-800 pt-2 mt-2">
                  {r.recommendation}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Strategy Recommendations */}
      {recommendations && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Рекомендованная стратегия аккаунтов</h3>

          {/* SIM Card Strategy */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h4 className="font-semibold text-violet-400 mb-3">Стратегия SIM</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {Object.entries(recommendations.strategy.sim_card_strategy).map(([key, val]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-zinc-400">{getLabel(SIM_STRATEGY_LABELS, key)}:</span>
                  <span className="text-right max-w-xs">{val}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Account Warming */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h4 className="font-semibold text-green-400 mb-3">Прогрев аккаунта</h4>
            <div className="space-y-2">
              {Object.entries(recommendations.strategy.account_warming).map(([period, action]) => (
                <div key={period} className="flex items-center gap-4 text-sm">
                  <span className="w-24 text-zinc-500 font-mono text-xs">{getLabel(WARMING_LABELS, period)}</span>
                  <span>{action}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recommended Accounts */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h4 className="font-semibold text-yellow-400 mb-3">Какие аккаунты создать</h4>
            <div className="space-y-2">
              {recommendations.strategy.recommended_accounts.map((acc, i) => (
                <div key={i} className="flex items-center justify-between bg-zinc-800 rounded-lg p-3">
                  <div className="flex items-center gap-3">
                    <span className="text-xs bg-zinc-700 px-2 py-0.5 rounded">{getLabel(PLATFORM_LABELS, acc.platform)}</span>
                    <span className="text-sm font-medium">{getLabel(ACCOUNT_TYPE_LABELS, acc.type)}</span>
                    <span className="text-xs text-zinc-400">{getLabel(REGION_LABELS, acc.region)} ({getLabel(LANGUAGE_LABELS, acc.language)})</span>
                    {acc.streamers_per_account && <span className="text-xs bg-violet-500/15 text-violet-400 px-2 py-0.5 rounded">{acc.streamers_per_account} стримеров</span>}
                  </div>
                  <span className="text-xs text-zinc-400 max-w-sm text-right">{acc.reason}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
