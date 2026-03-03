import { useState, useEffect, useCallback } from "react";
import {
  Activity, TrendingUp, Calendar, MessageCircle, Brain, Shield,
  RefreshCw, Play, Zap, Clock, Hash, CheckCircle2, XCircle,
  AlertTriangle, ChevronRight, Instagram, Sparkles, BarChart3,
  Target, Globe, Loader2, Music
} from "lucide-react";
import { api, AIProfile } from "@/hooks/useApi";

/* eslint-disable @typescript-eslint/no-explicit-any */

type Tab = "dashboard" | "trends" | "plan" | "queue" | "engage" | "learning" | "chain";

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "dashboard", label: "Dashboard", icon: Activity },
  { id: "trends", label: "Trends", icon: TrendingUp },
  { id: "plan", label: "Content Plan", icon: Calendar },
  { id: "queue", label: "Post Queue", icon: Play },
  { id: "engage", label: "Engagement", icon: MessageCircle },
  { id: "learning", label: "Learning", icon: Brain },
  { id: "chain", label: "Chain Health", icon: Shield },
];

const PLATFORMS = ["instagram", "tiktok"];
const FORMATS: Record<string, string[]> = {
  instagram: ["reels", "stories", "posts"],
  tiktok: ["video", "stories"],
};
const NICHES = ["gaming", "lifestyle", "beauty", "fitness", "tech"];

export default function SmartSocialEnginePage() {
  const [profiles, setProfiles] = useState<AIProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [loading, setLoading] = useState(false);
  const [initLoading, setInitLoading] = useState(false);
  const [dashboard, setDashboard] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [comments, setComments] = useState<any[]>([]);
  const [learning, setLearning] = useState<any[]>([]);
  const [chainStatus, setChainStatus] = useState<any>(null);
  const [trendPlatform, setTrendPlatform] = useState("instagram");
  const [trendFormat, setTrendFormat] = useState("reels");
  const [niche, setNiche] = useState("gaming");
  const [commentStyle, setCommentStyle] = useState<string | null>(null);

  useEffect(() => { api.getProfiles().then(setProfiles).catch(() => {}); }, []);

  const loadDashboard = useCallback(async (pid: number) => {
    setLoading(true);
    try { setDashboard(await api.sseDashboard(pid)); } catch { setDashboard(null); }
    setLoading(false);
  }, []);
  const loadTrends = useCallback(async (pid: number) => {
    try { const t = await api.sseGetTrends(pid); setTrends(Array.isArray(t) ? t : []); } catch { setTrends([]); }
  }, []);
  const loadQueue = useCallback(async (pid: number) => {
    try { const q = await api.sseGetQueue(pid); setQueue(Array.isArray(q) ? q : []); } catch { setQueue([]); }
  }, []);
  const loadLearning = useCallback(async (pid: number) => {
    try { const l = await api.sseGetLearning(pid); setLearning(Array.isArray(l) ? l : []); } catch { setLearning([]); }
  }, []);
  const loadChain = useCallback(async (pid: number) => {
    try { setChainStatus(await api.sseChainHealth(pid)); } catch { setChainStatus(null); }
  }, []);

  useEffect(() => {
    if (!selectedProfile) return;
    const pid = selectedProfile;
    if (activeTab === "dashboard") loadDashboard(pid);
    if (activeTab === "trends") loadTrends(pid);
    if (activeTab === "plan" || activeTab === "queue") loadQueue(pid);
    if (activeTab === "learning") loadLearning(pid);
    if (activeTab === "chain") loadChain(pid);
  }, [selectedProfile, activeTab, loadDashboard, loadTrends, loadQueue, loadLearning, loadChain]);

  const handleInitialize = async () => {
    if (!selectedProfile) return;
    setInitLoading(true);
    try { await api.sseInitialize(selectedProfile, niche, "US"); await loadDashboard(selectedProfile); } catch (e) { console.error(e); }
    setInitLoading(false);
  };
  const handleAnalyzeTrends = async () => {
    if (!selectedProfile) return; setLoading(true);
    try { await api.sseAnalyzeTrends(selectedProfile, trendPlatform, trendFormat, niche); await loadTrends(selectedProfile); } catch (e) { console.error(e); }
    setLoading(false);
  };
  const handleGeneratePlan = async () => {
    if (!selectedProfile) return; setLoading(true);
    try { await api.sseGeneratePlan(selectedProfile, 7, niche); await loadQueue(selectedProfile); } catch (e) { console.error(e); }
    setLoading(false);
  };
  const handlePrePostAnalysis = async (queueId: number) => {
    if (!selectedProfile) return; setLoading(true);
    try {
      const result = await api.ssePrePostAnalysis(selectedProfile, queueId) as any;
      const passed = result.pass || result.approved || result.passed || result.status === "approved";
      const recs = result.recommendations || result.issues || [];
      alert(passed ? "Pre-post analysis PASSED! Ready to post." : "Pre-post analysis BLOCKED:\n" + (Array.isArray(recs) ? recs.join("\n") : JSON.stringify(recs)));
      await loadQueue(selectedProfile);
    } catch (e) { console.error(e); }
    setLoading(false);
  };
  const handleExecutePost = async (queueId: number) => {
    if (!selectedProfile) return; setLoading(true);
    try {
      const result = await api.sseExecutePost(selectedProfile, queueId) as any;
      alert("Post " + (result.status || "done") + ": " + (result.message || JSON.stringify(result)));
      await loadQueue(selectedProfile);
    } catch (e) { console.error(e); }
    setLoading(false);
  };
  const handleGenerateComments = async () => {
    if (!selectedProfile) return; setLoading(true);
    try { const c = await api.sseGenerateComments(selectedProfile, niche, 10, commentStyle ?? undefined); setComments(Array.isArray(c) ? c : []); } catch (e) { console.error(e); }
    setLoading(false);
  };
  const handleHealChain = async () => {
    if (!selectedProfile) return; setLoading(true);
    try { await api.sseHealChain(selectedProfile); await loadChain(selectedProfile); } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (!selectedProfile) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Zap className="h-7 w-7 text-emerald-400" />
          <div>
            <h1 className="text-2xl font-bold">Smart Social Engine</h1>
            <p className="text-sm text-zinc-400">Intelligent social media autopilot for real girls — US market</p>
          </div>
        </div>
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Select a Profile</h2>
          {profiles.length === 0 ? (
            <p className="text-zinc-500">No profiles found. Create one in the Girls tab first.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {profiles.map((p) => (
                <button key={p.id} onClick={() => setSelectedProfile(p.id)}
                  className="flex items-center gap-3 p-4 bg-zinc-800/50 rounded-lg border border-zinc-700 hover:border-emerald-500/50 hover:bg-zinc-800 transition-all text-left">
                  {(p as any).photo_url ? (
                    <img src={(p as any).photo_url} alt={p.name} className="w-10 h-10 rounded-full object-cover" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-zinc-700 flex items-center justify-center text-zinc-400 text-sm font-bold">{p.name[0]}</div>
                  )}
                  <div className="min-w-0">
                    <p className="font-medium truncate">{p.name}</p>
                    <p className="text-xs text-zinc-500 truncate">{(p.personality as any)?.type || p.style || "No type"}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-zinc-600 ml-auto shrink-0" />
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            { icon: TrendingUp, title: "Trend Intelligence", desc: "Per-platform trend analysis for US market (IG reels/stories/posts, TT videos)", color: "text-blue-400" },
            { icon: Calendar, title: "Content Strategy", desc: "AI-generated 7-day content plans per platform", color: "text-purple-400" },
            { icon: Play, title: "Posting Orchestrator", desc: "Mandatory pre-post analysis gate with 5 checks", color: "text-green-400" },
            { icon: MessageCircle, title: "Engagement Engine", desc: "Smart comments localized for US audience", color: "text-pink-400" },
            { icon: Brain, title: "Learning Engine", desc: "Adapts strategy from performance data over time", color: "text-amber-400" },
            { icon: Shield, title: "Chain Guard", desc: "Self-healing pipeline blocks posts if chain broken", color: "text-red-400" },
          ].map((e) => (
            <div key={e.title} className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
              <e.icon className={`h-6 w-6 ${e.color} mb-2`} />
              <h3 className="font-semibold text-sm">{e.title}</h3>
              <p className="text-xs text-zinc-500 mt-1">{e.desc}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const profile = profiles.find((p) => p.id === selectedProfile);
  const isEngineActive = dashboard?.engine_active;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={() => { setSelectedProfile(null); setDashboard(null); }} className="text-zinc-400 hover:text-white transition-colors text-sm">&larr; Back</button>
        <Zap className="h-6 w-6 text-emerald-400" />
        <h1 className="text-xl font-bold">SSE: {profile?.name || "Profile #" + selectedProfile}</h1>
        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">{dashboard?.target_region || "US"} Market</span>
        {isEngineActive && <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 border border-green-500/30">Active</span>}
        {!isEngineActive && (
          <button onClick={handleInitialize} disabled={initLoading}
            className="ml-auto px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
            {initLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />} Initialize Engine
          </button>
        )}
      </div>
      <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-hide">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" : "text-zinc-400 hover:bg-zinc-800 hover:text-white border border-transparent"
              }`}>
              <Icon className="h-3.5 w-3.5" /> {tab.label}
            </button>
          );
        })}
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <Target className="h-4 w-4 text-zinc-500" />
        <span className="text-xs text-zinc-500">Niche:</span>
        {NICHES.map((n) => (
          <button key={n} onClick={() => setNiche(n)}
            className={`px-2 py-0.5 rounded text-xs capitalize transition-colors ${niche === n ? "bg-emerald-500/20 text-emerald-400" : "text-zinc-500 hover:text-zinc-300"}`}>
            {n}
          </button>
        ))}
      </div>
      <div className="space-y-4">
        {activeTab === "dashboard" && <DashboardTab dashboard={dashboard} loading={loading} onRefresh={() => loadDashboard(selectedProfile)} />}
        {activeTab === "trends" && <TrendsTab trends={trends} loading={loading} platform={trendPlatform} format={trendFormat} onPlatformChange={setTrendPlatform} onFormatChange={setTrendFormat} onAnalyze={handleAnalyzeTrends} />}
        {activeTab === "plan" && <PlanTab queue={queue} loading={loading} onGenerate={handleGeneratePlan} />}
        {activeTab === "queue" && <QueueTab queue={queue} loading={loading} onPrePost={handlePrePostAnalysis} onExecute={handleExecutePost} onRefresh={() => loadQueue(selectedProfile)} />}
        {activeTab === "engage" && <EngageTab comments={comments} loading={loading} style={commentStyle} onStyleChange={setCommentStyle} onGenerate={handleGenerateComments} />}
        {activeTab === "learning" && <LearningTab learning={learning} loading={loading} />}
        {activeTab === "chain" && <ChainTab chainStatus={chainStatus} loading={loading} onHeal={handleHealChain} onRefresh={() => loadChain(selectedProfile)} />}
      </div>
    </div>
  );
}

function DashboardTab({ dashboard, loading, onRefresh }: { dashboard: any; loading: boolean; onRefresh: () => void }) {
  if (loading) return <LoadingSpinner />;
  if (!dashboard) return <EmptyState text="Engine not initialized. Click Initialize Engine above." />;
  const chainOverall = dashboard.chain_status?.overall || "unknown";
  const chainHealthy = chainOverall === "healthy";
  const components = dashboard.chain_status?.components || {};
  const componentCount = Object.keys(components).length;
  const qs = dashboard.queue_summary || {};
  const perf = dashboard.performance || {};
  const stats = [
    { label: "Trends Cached", value: dashboard.trends_count || 0, sub: (dashboard.latest_trends || []).length + " latest", icon: TrendingUp, color: "text-blue-400" },
    { label: "Queue Items", value: qs.total || 0, sub: (qs.planned || 0) + " planned", icon: Calendar, color: "text-purple-400" },
    { label: "Engagements", value: dashboard.engagement_actions || 0, sub: "actions logged", icon: MessageCircle, color: "text-pink-400" },
    { label: "Learned Patterns", value: dashboard.learning_patterns || 0, sub: (perf.total_posts || 0) + " posts tracked", icon: Brain, color: "text-amber-400" },
  ];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Engine Dashboard</h2>
        <button onClick={onRefresh} className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"><RefreshCw className="h-4 w-4" /></button>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
            <div className="flex items-center gap-2 mb-2"><s.icon className={`h-4 w-4 ${s.color}`} /><span className="text-xs text-zinc-500">{s.label}</span></div>
            <p className="text-2xl font-bold">{s.value}</p>
            <p className="text-xs text-zinc-500 mt-1">{s.sub}</p>
          </div>
        ))}
      </div>
      <div className={`rounded-xl border p-4 flex items-center gap-3 ${chainHealthy ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}>
        {chainHealthy ? <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" /> : <XCircle className="h-5 w-5 text-red-400 shrink-0" />}
        <div>
          <p className={`font-medium text-sm ${chainHealthy ? "text-emerald-400" : "text-red-400"}`}>Chain: {chainOverall}</p>
          <p className="text-xs text-zinc-500">{componentCount} components monitored</p>
        </div>
      </div>
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Globe className="h-4 w-4 text-zinc-400" /> Active Platforms</h3>
        <div className="flex gap-3">
          {(dashboard.platforms || []).map((p: string) => (
            <span key={p} className="px-3 py-1.5 bg-zinc-800 rounded-lg text-xs font-medium capitalize flex items-center gap-1.5">
              {p === "instagram" ? <Instagram className="h-3.5 w-3.5 text-pink-400" /> : <Sparkles className="h-3.5 w-3.5 text-cyan-400" />}{p}
            </span>
          ))}
        </div>
      </div>
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><BarChart3 className="h-4 w-4 text-zinc-400" /> Queue Breakdown</h3>
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
          {[
            { label: "Planned", val: qs.planned || 0, color: "bg-blue-500" },
            { label: "Analyzed", val: qs.analyzed || 0, color: "bg-amber-500" },
            { label: "Ready", val: qs.ready_to_post || 0, color: "bg-green-500" },
            { label: "Posted", val: qs.posted || 0, color: "bg-emerald-500" },
            { label: "Blocked", val: qs.blocked || 0, color: "bg-red-500" },
          ].map((q) => (
            <div key={q.label} className="text-center">
              <div className={`h-1.5 rounded-full ${q.color} mb-2 mx-auto`} style={{ width: Math.max(20, (q.val / Math.max(qs.total || 1, 1)) * 100) + "%" }} />
              <p className="text-lg font-bold">{q.val}</p>
              <p className="text-xs text-zinc-500">{q.label}</p>
            </div>
          ))}
        </div>
      </div>
      {perf.total_posts > 0 && (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <h3 className="text-sm font-semibold mb-3">Performance</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div><p className="text-xs text-zinc-500">Views</p><p className="text-lg font-bold">{perf.total_views?.toLocaleString()}</p></div>
            <div><p className="text-xs text-zinc-500">Likes</p><p className="text-lg font-bold">{perf.total_likes?.toLocaleString()}</p></div>
            <div><p className="text-xs text-zinc-500">Comments</p><p className="text-lg font-bold">{perf.total_comments?.toLocaleString()}</p></div>
            <div><p className="text-xs text-zinc-500">Avg ER</p><p className="text-lg font-bold">{perf.avg_engagement_rate?.toFixed(1)}%</p></div>
          </div>
        </div>
      )}
    </div>
  );
}

function TrendsTab({ trends, loading, platform, format, onPlatformChange, onFormatChange, onAnalyze }: {
  trends: any[]; loading: boolean; platform: string; format: string;
  onPlatformChange: (p: string) => void; onFormatChange: (f: string) => void; onAnalyze: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold flex items-center gap-2"><TrendingUp className="h-5 w-5 text-blue-400" /> Trend Intelligence</h2>
        <button onClick={onAnalyze} disabled={loading} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Analyze Now
        </button>
      </div>
      <div className="flex gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Platform:</span>
          {PLATFORMS.map((p) => (
            <button key={p} onClick={() => { onPlatformChange(p); onFormatChange(FORMATS[p][0]); }}
              className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${platform === p ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" : "text-zinc-400 hover:bg-zinc-800"}`}>{p}</button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Format:</span>
          {(FORMATS[platform] || []).map((f) => (
            <button key={f} onClick={() => onFormatChange(f)}
              className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${format === f ? "bg-purple-500/20 text-purple-400 border border-purple-500/30" : "text-zinc-400 hover:bg-zinc-800"}`}>{f}</button>
          ))}
        </div>
      </div>
      {loading ? <LoadingSpinner /> : trends.length === 0 ? <EmptyState text="No trend data yet. Click Analyze Now to run analysis." /> : (
        <div className="space-y-3">
          {trends.map((t: any) => {
            const hashtags: string[] = Array.isArray(t.top_hashtags) ? t.top_hashtags : [];
            const pt = t.best_posting_times;
            const hoursUtc: number[] = pt?.hours_utc || (Array.isArray(pt) ? pt : []);
            const bestDays: string[] = pt?.days || [];
            const topics: string[] = Array.isArray(t.trending_topics) ? t.trending_topics : [];
            const sounds: string[] = Array.isArray(t.trending_sounds) ? t.trending_sounds : [];
            const bm = t.engagement_benchmarks || t.trend_data?.engagement_benchmarks || {};
            const rec = t.trend_data?.recommendation || "";
            return (
              <div key={t.id} className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
                <div className="flex items-center gap-2 mb-3">
                  {t.platform === "instagram" ? <Instagram className="h-4 w-4 text-pink-400" /> : <Sparkles className="h-4 w-4 text-cyan-400" />}
                  <span className="text-sm font-medium capitalize">{t.platform}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 capitalize">{t.content_format}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">{t.region || "US"}</span>
                  <span className="text-xs text-zinc-600 ml-auto">{new Date(t.analyzed_at).toLocaleString()}</span>
                </div>
                {rec && <div className="mb-3 p-2 bg-emerald-500/5 border border-emerald-500/20 rounded-lg"><p className="text-xs text-emerald-400">{rec}</p></div>}
                {hashtags.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-zinc-500 mb-1.5 flex items-center gap-1"><Hash className="h-3 w-3" /> Top Hashtags ({hashtags.length})</p>
                    <div className="flex flex-wrap gap-1.5">{hashtags.slice(0, 15).map((h: string, i: number) => <span key={i} className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-xs">{h}</span>)}</div>
                  </div>
                )}
                {hoursUtc.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-zinc-500 mb-1.5 flex items-center gap-1"><Clock className="h-3 w-3" /> Best Posting Times (UTC)</p>
                    <div className="flex flex-wrap gap-1.5">{hoursUtc.map((h: number, i: number) => <span key={i} className="px-2 py-0.5 bg-green-500/10 text-green-400 rounded text-xs">{h}:00</span>)}</div>
                    {bestDays.length > 0 && <p className="text-xs text-zinc-500 mt-1">Best days: <span className="text-green-400 capitalize">{bestDays.join(", ")}</span></p>}
                  </div>
                )}
                {sounds.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-zinc-500 mb-1.5 flex items-center gap-1"><Music className="h-3 w-3" /> Trending Sounds</p>
                    <div className="flex flex-wrap gap-1.5">{sounds.slice(0, 6).map((s: string, i: number) => <span key={i} className="px-2 py-0.5 bg-pink-500/10 text-pink-400 rounded text-xs">{s}</span>)}</div>
                  </div>
                )}
                {topics.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-zinc-500 mb-1.5 flex items-center gap-1"><Sparkles className="h-3 w-3" /> Trending Topics</p>
                    <div className="flex flex-wrap gap-1.5">{topics.map((topic: string, i: number) => <span key={i} className="px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded text-xs">{topic}</span>)}</div>
                  </div>
                )}
                {bm.avg_views && (
                  <div className="grid grid-cols-4 gap-2 pt-2 border-t border-zinc-800">
                    <div><p className="text-xs text-zinc-600">Avg Views</p><p className="text-sm font-medium">{bm.avg_views?.toLocaleString()}</p></div>
                    <div><p className="text-xs text-zinc-600">Avg Likes</p><p className="text-sm font-medium">{bm.avg_likes?.toLocaleString()}</p></div>
                    <div><p className="text-xs text-zinc-600">Avg Comments</p><p className="text-sm font-medium">{bm.avg_comments}</p></div>
                    <div><p className="text-xs text-zinc-600">Avg ER</p><p className="text-sm font-medium">{bm.avg_er}%</p></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function PlanTab({ queue, loading, onGenerate }: { queue: any[]; loading: boolean; onGenerate: () => void }) {
  const byDate: Record<string, any[]> = {};
  queue.forEach((item: any) => {
    const date = item.scheduled_at ? new Date(item.scheduled_at).toLocaleDateString() : "Unscheduled";
    if (!byDate[date]) byDate[date] = [];
    byDate[date].push(item);
  });
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold flex items-center gap-2"><Calendar className="h-5 w-5 text-purple-400" /> Content Strategy</h2>
        <button onClick={onGenerate} disabled={loading} className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Generate 7-Day Plan
        </button>
      </div>
      {loading ? <LoadingSpinner /> : queue.length === 0 ? <EmptyState text="No content plan yet. Generate one to see your posting schedule." /> : (
        <div className="space-y-4">
          {Object.entries(byDate).map(([date, items]) => (
            <div key={date}>
              <h3 className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2"><Calendar className="h-3.5 w-3.5" /> {date} <span className="text-zinc-600">({items.length} posts)</span></h3>
              <div className="space-y-2">
                {items.map((item: any) => {
                  const ht: string[] = Array.isArray(item.hashtags) ? item.hashtags : [];
                  const sc = item.status === "posted" ? "bg-emerald-400" : item.status === "planned" ? "bg-blue-400" : item.status === "ready_to_post" ? "bg-green-400" : item.status === "blocked" ? "bg-red-400" : "bg-zinc-500";
                  return (
                    <div key={item.id} className="bg-zinc-900 rounded-xl border border-zinc-800 p-3 flex items-start gap-3">
                      <div className={`w-2 h-2 rounded-full shrink-0 mt-1.5 ${sc}`} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                          {item.platform === "instagram" ? <Instagram className="h-3 w-3 text-pink-400" /> : <Sparkles className="h-3 w-3 text-cyan-400" />}
                          <span className="text-xs font-medium capitalize">{item.platform}</span>
                          <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 capitalize">{item.content_format}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded capitalize ${
                            item.status === "posted" ? "bg-emerald-500/20 text-emerald-400" : item.status === "planned" ? "bg-blue-500/20 text-blue-400" : item.status === "ready_to_post" ? "bg-green-500/20 text-green-400" : item.status === "blocked" ? "bg-red-500/20 text-red-400" : "bg-zinc-800 text-zinc-400"
                          }`}>{item.status}</span>
                          {item.scheduled_at && <span className="text-xs text-zinc-600 ml-auto">{new Date(item.scheduled_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>}
                        </div>
                        {item.caption && <p className="text-xs text-zinc-400 mt-1">{item.caption}</p>}
                        {ht.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {ht.slice(0, 6).map((h: string, i: number) => <span key={i} className="text-xs text-blue-400/60">{h.startsWith("#") ? h : "#" + h}</span>)}
                            {ht.length > 6 && <span className="text-xs text-zinc-600">+{ht.length - 6}</span>}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function QueueTab({ queue, loading, onPrePost, onExecute, onRefresh }: {
  queue: any[]; loading: boolean; onPrePost: (id: number) => void; onExecute: (id: number) => void; onRefresh: () => void;
}) {
  const actionable = queue.filter((q: any) => ["planned", "queued", "ready_to_post"].includes(q.status));
  const posted = queue.filter((q: any) => q.status === "posted");
  const blocked = queue.filter((q: any) => ["blocked", "failed"].includes(q.status));
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold flex items-center gap-2"><Play className="h-5 w-5 text-green-400" /> Posting Queue</h2>
        <button onClick={onRefresh} className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"><RefreshCw className="h-4 w-4" /></button>
      </div>
      {loading ? <LoadingSpinner /> : queue.length === 0 ? <EmptyState text="Queue is empty. Generate a content plan first." /> : (
        <>
          {actionable.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-2">Ready to Process ({actionable.length})</h3>
              <div className="space-y-2">
                {actionable.slice(0, 10).map((item: any) => (
                  <div key={item.id} className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      {item.platform === "instagram" ? <Instagram className="h-3.5 w-3.5 text-pink-400" /> : <Sparkles className="h-3.5 w-3.5 text-cyan-400" />}
                      <span className="text-sm font-medium capitalize">{item.platform} / {item.content_format}</span>
                      <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs capitalize">{item.status}</span>
                      {item.scheduled_at && <span className="text-xs text-zinc-600 ml-auto">{new Date(item.scheduled_at).toLocaleString()}</span>}
                    </div>
                    {item.caption && <p className="text-xs text-zinc-400 mb-2">{item.caption}</p>}
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => onPrePost(item.id)} className="px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 rounded-lg text-xs font-medium transition-colors flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" /> Pre-Post Check
                      </button>
                      <button onClick={() => onExecute(item.id)} className="px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 rounded-lg text-xs font-medium transition-colors flex items-center gap-1">
                        <Play className="h-3 w-3" /> Execute
                      </button>
                    </div>
                  </div>
                ))}
                {actionable.length > 10 && <p className="text-xs text-zinc-600 text-center">+{actionable.length - 10} more</p>}
              </div>
            </div>
          )}
          {posted.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-emerald-400 mb-2">Posted ({posted.length})</h3>
              <div className="space-y-2">{posted.map((item: any) => (
                <div key={item.id} className="bg-zinc-900/50 rounded-xl border border-zinc-800/50 p-3 flex items-center gap-3">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  <div className="min-w-0 flex-1"><span className="text-xs capitalize">{item.platform} / {item.content_format}</span>{item.caption && <p className="text-xs text-zinc-500 truncate">{item.caption}</p>}</div>
                  <span className="text-xs text-zinc-600">{item.posted_at ? new Date(item.posted_at).toLocaleDateString() : ""}</span>
                </div>
              ))}</div>
            </div>
          )}
          {blocked.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-red-400 mb-2">Blocked / Failed ({blocked.length})</h3>
              <div className="space-y-2">{blocked.map((item: any) => (
                <div key={item.id} className="bg-red-500/5 rounded-xl border border-red-500/20 p-3 flex items-center gap-3">
                  <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                  <div className="min-w-0 flex-1"><span className="text-xs capitalize">{item.platform} / {item.content_format}</span>{item.error_log && <p className="text-xs text-red-400/70 truncate">{item.error_log}</p>}</div>
                  <button onClick={() => onExecute(item.id)} className="px-2 py-1 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded text-xs">Retry</button>
                </div>
              ))}</div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function EngageTab({ comments, loading, style, onStyleChange, onGenerate }: {
  comments: any[]; loading: boolean; style: string | null; onStyleChange: (s: string | null) => void; onGenerate: () => void;
}) {
  const styles = [null, "hype", "supportive", "engaging", "question", "casual"];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold flex items-center gap-2"><MessageCircle className="h-5 w-5 text-pink-400" /> Smart Engagement</h2>
        <button onClick={onGenerate} disabled={loading} className="px-4 py-2 bg-pink-600 hover:bg-pink-500 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Generate Comments
        </button>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-zinc-500">Style:</span>
        {styles.map((s) => (
          <button key={s || "all"} onClick={() => onStyleChange(s)}
            className={`px-2 py-0.5 rounded text-xs capitalize transition-colors ${style === s ? "bg-pink-500/20 text-pink-400" : "text-zinc-500 hover:text-zinc-300"}`}>
            {s || "mixed"}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 px-3 py-2 bg-zinc-900 rounded-lg border border-zinc-800">
        <Globe className="h-4 w-4 text-blue-400" />
        <span className="text-xs text-zinc-400">Region: <span className="text-white font-medium">USA</span> — Comments localized for US audience</span>
      </div>
      {loading ? <LoadingSpinner /> : comments.length === 0 ? <EmptyState text="No comments generated yet. Click Generate Comments." /> : (
        <div className="space-y-2">
          {comments.map((c: any, i: number) => (
            <div key={c.id || i} className="bg-zinc-900 rounded-xl border border-zinc-800 p-3 flex items-start gap-3">
              <MessageCircle className="h-4 w-4 text-pink-400 mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm">{c.content || c.comment || c.text}</p>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 capitalize">{c.style || c.action_type || "mixed"}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 capitalize">{c.niche || ""}</span>
                  <span className="text-xs text-zinc-600">{c.platform || "instagram"}</span>
                  <span className="text-xs text-zinc-600 ml-auto">{c.region || "US"}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function LearningTab({ learning, loading }: { learning: any[]; loading: boolean }) {
  if (loading) return <LoadingSpinner />;
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold flex items-center gap-2"><Brain className="h-5 w-5 text-amber-400" /> Learning Engine</h2>
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
        <p className="text-xs text-zinc-400">The Learning Engine analyzes performance data to discover patterns. Optimal posting times, best hashtags, top content formats. Patterns grow in confidence as more data points are collected.</p>
      </div>
      {learning.length === 0 ? <EmptyState text="No learned patterns yet. Record performance data to start learning." /> : (
        <div className="space-y-3">
          {learning.map((entry: any) => (
            <div key={entry.id} className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium capitalize">{entry.platform}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-400">{entry.learning_type}</span>
                <span className="text-xs text-zinc-500 ml-auto">{entry.data_points} data points</span>
              </div>
              <p className="text-xs text-zinc-400 mb-2">Pattern: <span className="text-white">{entry.pattern_key}</span></p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full transition-all" style={{ width: ((entry.confidence || 0) * 100) + "%" }} />
                </div>
                <span className="text-xs text-amber-400 font-medium">{((entry.confidence || 0) * 100).toFixed(0)}%</span>
              </div>
              <p className="text-xs text-zinc-600 mt-2">Updated: {new Date(entry.last_updated).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ChainTab({ chainStatus, loading, onHeal, onRefresh }: {
  chainStatus: any; loading: boolean; onHeal: () => void; onRefresh: () => void;
}) {
  if (loading) return <LoadingSpinner />;
  const overall = chainStatus?.overall || "unknown";
  const healthy = overall === "healthy";
  const components: Record<string, any> = chainStatus?.components || {};
  const entries = Object.entries(components);
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold flex items-center gap-2"><Shield className="h-5 w-5 text-red-400" /> Chain Guard — Self-Healing Pipeline</h2>
        <div className="flex gap-2">
          <button onClick={onRefresh} className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"><RefreshCw className="h-4 w-4" /></button>
          <button onClick={onHeal} disabled={loading} className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"><Zap className="h-4 w-4" /> Self-Heal</button>
        </div>
      </div>
      {!chainStatus ? <EmptyState text="No chain data. Initialize the engine first." /> : (
        <>
          <div className={`rounded-xl border p-4 ${healthy ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}>
            <div className="flex items-center gap-3">
              {healthy ? <CheckCircle2 className="h-6 w-6 text-emerald-400" /> : <AlertTriangle className="h-6 w-6 text-red-400" />}
              <div>
                <p className={`font-semibold ${healthy ? "text-emerald-400" : "text-red-400"}`}>Pipeline: {overall}</p>
                <p className="text-xs text-zinc-500">{healthy ? "All components healthy. Posts can be executed." : "Some components unhealthy. Posts BLOCKED until healed."}</p>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            {entries.map(([name, comp]: [string, any]) => {
              const cs = comp.status || "unknown";
              const ih = cs === "healthy";
              return (
                <div key={name} className={`bg-zinc-900 rounded-xl border p-4 flex items-center gap-3 ${ih ? "border-zinc-800" : "border-red-500/30"}`}>
                  <div className={`w-3 h-3 rounded-full shrink-0 ${cs === "healthy" ? "bg-emerald-400" : cs === "degraded" ? "bg-amber-400" : cs === "not_initialized" ? "bg-zinc-500" : "bg-red-400"}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium capitalize">{name.replace(/_/g, " ")}</p>
                    <p className="text-xs text-zinc-500">Status: <span className={ih ? "text-emerald-400" : cs === "not_initialized" ? "text-zinc-400" : "text-red-400"}>{cs}</span>
                      {comp.error_count > 0 && <span className="ml-2 text-red-400">{comp.error_count} errors</span>}
                    </p>
                    {comp.message && <p className="text-xs text-zinc-600 mt-0.5">{comp.message}</p>}
                  </div>
                  <div className="text-right shrink-0">
                    {comp.last_check && <p className="text-xs text-zinc-600">{new Date(comp.last_check).toLocaleTimeString()}</p>}
                    {comp.consecutive_failures > 0 && <p className="text-xs text-red-400">{comp.consecutive_failures} fails</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function LoadingSpinner() {
  return <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 text-emerald-400 animate-spin" /></div>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="text-center py-12 text-zinc-500 text-sm">{text}</div>;
}
