import { useState } from "react";
import {
  LayoutDashboard, Film, TrendingUp, FlaskConical, Crosshair,
  Layers, Radio, Sparkles, UserCircle, Wrench, Globe, Wand2, Clapperboard
} from "lucide-react";
import Dashboard from "@/pages/Dashboard";
import ClipsPage from "@/pages/ClipsPage";
import TrendsPage from "@/pages/TrendsPage";
import ABTestsPage from "@/pages/ABTestsPage";
import MomentsPage from "@/pages/MomentsPage";
import TemplatesPage from "@/pages/TemplatesPage";
import StreamsPage from "@/pages/StreamsPage";
import AIGirlPage from "@/pages/AIGirlPage";
import AIProfilesPage from "@/pages/AIProfilesPage";
import ToolRegistryPage from "@/pages/ToolRegistryPage";
import AccountStrategyPage from "@/pages/AccountStrategyPage";
import AIStudioPage from "@/pages/AIStudioPage";
import MontagePage from "@/pages/MontagePage";

const NAV_ITEMS = [
  { id: "dashboard", label: "Главная", icon: LayoutDashboard },
  { id: "clips", label: "Клипы", icon: Film },
  { id: "trends", label: "Тренды", icon: TrendingUp },
  { id: "ab-tests", label: "A/B Тесты", icon: FlaskConical },
  { id: "moments", label: "Моменты", icon: Crosshair },
  { id: "templates", label: "Шаблоны", icon: Layers },
  { id: "streams", label: "Стримы", icon: Radio },
  { id: "ai-girl", label: "AI Девушка", icon: Sparkles },
  { id: "ai-profiles", label: "AI Профили", icon: UserCircle },
  { id: "tools", label: "Инструменты", icon: Wrench },
  { id: "accounts", label: "Аккаунты и Регионы", icon: Globe },
  { id: "studio", label: "AI Студия", icon: Wand2 },
  { id: "montage", label: "Монтаж", icon: Clapperboard },
];

const PAGES: Record<string, React.FC> = {
  dashboard: Dashboard,
  clips: ClipsPage,
  trends: TrendsPage,
  "ab-tests": ABTestsPage,
  moments: MomentsPage,
  templates: TemplatesPage,
  streams: StreamsPage,
  "ai-girl": AIGirlPage,
  "ai-profiles": AIProfilesPage,
  tools: ToolRegistryPage,
  accounts: AccountStrategyPage,
  studio: AIStudioPage,
  montage: MontagePage,
};

function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const ActiveComponent = PAGES[activePage] || Dashboard;

  return (
    <div className="flex h-screen bg-zinc-950 text-white">
      {/* Sidebar */}
      <aside className="w-56 bg-zinc-900 border-r border-zinc-800 flex flex-col">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-zinc-800">
          <h1 className="text-lg font-bold bg-gradient-to-r from-violet-400 to-pink-400 bg-clip-text text-transparent">
            CS2 Контент Движок
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">AI Медиа Машина</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-violet-500/15 text-violet-400"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-zinc-800 text-xs text-zinc-600">
          v2.0.0 &middot; AI CS Движок
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto p-6">
          <ActiveComponent />
        </div>
      </main>
    </div>
  );
}

export default App;
