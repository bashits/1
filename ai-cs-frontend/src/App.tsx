import { useState } from "react";
import {
  LayoutDashboard, Film, TrendingUp, Radio, UserCircle, Clapperboard, Menu, X
} from "lucide-react";
import Dashboard from "@/pages/Dashboard";
import ClipsPage from "@/pages/ClipsPage";
import TrendsPage from "@/pages/TrendsPage";
import StreamsPage from "@/pages/StreamsPage";
import AIProfilesPage from "@/pages/AIProfilesPage";
import MontagePage from "@/pages/MontagePage";

const NAV_ITEMS = [
  { id: "dashboard", label: "Главная", icon: LayoutDashboard },
  { id: "montage", label: "Монтаж", icon: Clapperboard },
  { id: "clips", label: "Клипы", icon: Film },
  { id: "trends", label: "Тренды", icon: TrendingUp },
  { id: "streams", label: "Стримы", icon: Radio },
  { id: "ai-profiles", label: "Девушки", icon: UserCircle },
];

const PAGES: Record<string, React.FC> = {
  dashboard: Dashboard,
  montage: MontagePage,
  clips: ClipsPage,
  trends: TrendsPage,
  streams: StreamsPage,
  "ai-profiles": AIProfilesPage,
};

function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const ActiveComponent = PAGES[activePage] || Dashboard;

  const navigateTo = (id: string) => {
    setActivePage(id);
    setMobileMenuOpen(false);
  };

  return (
    <div className="flex flex-col md:flex-row h-[100dvh] bg-zinc-950 text-white">
      {/* ── Mobile Header ── */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-zinc-900 border-b border-zinc-800 shrink-0 z-50">
        <h1 className="text-base font-bold bg-gradient-to-r from-violet-400 to-pink-400 bg-clip-text text-transparent">
          CS2 Движок
        </h1>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
          aria-label="Меню"
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>

      {/* ── Mobile Slide-down Menu (overlay) ── */}
      {mobileMenuOpen && (
        <>
          <div className="md:hidden fixed inset-0 top-[52px] bg-black/60 z-40" onClick={() => setMobileMenuOpen(false)} />
          <div className="md:hidden fixed left-0 right-0 top-[52px] bg-zinc-900 border-b border-zinc-800 px-2 py-2 space-y-1 z-50 max-h-[70vh] overflow-y-auto">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => navigateTo(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-violet-500/15 text-violet-400"
                      : "text-zinc-400 active:bg-zinc-800 hover:text-white"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* ── Desktop Sidebar ── */}
      <aside className="hidden md:flex w-56 bg-zinc-900 border-r border-zinc-800 flex-col shrink-0">
        <div className="px-4 py-5 border-b border-zinc-800">
          <h1 className="text-lg font-bold bg-gradient-to-r from-violet-400 to-pink-400 bg-clip-text text-transparent">
            CS2 Контент Движок
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">AI Медиа Машина</p>
        </div>
        <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => navigateTo(item.id)}
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
        <div className="px-4 py-3 border-t border-zinc-800 text-xs text-zinc-600">
          v2.1.0 &middot; AI CS Движок
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-7xl mx-auto px-3 py-3 sm:px-4 sm:py-4 md:p-6 pb-20 md:pb-6">
          <ActiveComponent />
        </div>
      </main>

      {/* ── Mobile Bottom Nav ── */}
      <nav className="md:hidden flex items-center justify-around bg-zinc-900 border-t border-zinc-800 shrink-0 z-50" style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => navigateTo(item.id)}
              className={`flex flex-col items-center gap-0.5 px-1.5 py-2 text-[10px] transition-colors min-w-0 flex-1 ${
                isActive
                  ? "text-violet-400"
                  : "text-zinc-500 active:text-zinc-300"
              }`}
            >
              <Icon className={`h-5 w-5 ${isActive ? "text-violet-400" : ""}`} />
              <span className="truncate w-full text-center">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}

export default App;
