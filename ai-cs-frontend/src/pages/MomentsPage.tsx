import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Crosshair, Clock, Zap, Loader2 } from "lucide-react";
import { api, Moment, Stream } from "@/hooks/useApi";

const TYPE_COLORS: Record<string, string> = {
  clutch: "bg-red-500/20 text-red-400",
  ace: "bg-yellow-500/20 text-yellow-400",
  multi_kill: "bg-orange-500/20 text-orange-400",
  headshot_sequence: "bg-purple-500/20 text-purple-400",
  emotional_reaction: "bg-pink-500/20 text-pink-400",
  toxic_moment: "bg-green-500/20 text-green-400",
  meme_fail: "bg-cyan-500/20 text-cyan-400",
  insane_spray: "bg-blue-500/20 text-blue-400",
  knife_kill: "bg-zinc-500/20 text-zinc-300",
  wallbang: "bg-violet-500/20 text-violet-400",
};

const MOMENT_TYPE_LABELS: Record<string, string> = {
  clutch: "Клатч",
  ace: "Эйс",
  multi_kill: "Мульти-килл",
  headshot_sequence: "Серия хедшотов",
  emotional_reaction: "Эмоция",
  toxic_moment: "Токсик",
  meme_fail: "Фейл/мем",
  insane_spray: "Безумный спрей",
  knife_kill: "Нож",
  wallbang: "Воллбэнг",
};

export default function MomentsPage() {
  const [moments, setMoments] = useState<Moment[]>([]);
  const [streams, setStreams] = useState<Stream[]>([]);
  const [selectedStream, setSelectedStream] = useState<string>("all");
  const [detecting, setDetecting] = useState(false);
  const [generating, setGenerating] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getStreams().then(setStreams).catch(console.error);
    loadMoments();
  }, []);

  const loadMoments = (streamId?: string) => {
    setLoading(true);
    const params = new URLSearchParams();
    if (streamId && streamId !== "all") params.set("stream_id", streamId);
    params.set("limit", "100");
    api.getMoments(params.toString()).then(setMoments).catch(console.error).finally(() => setLoading(false));
  };

  const handleDetect = async () => {
    if (selectedStream === "all") return;
    setDetecting(true);
    try {
      await api.detectMoments(parseInt(selectedStream));
      loadMoments(selectedStream);
    } catch (e) {
      console.error(e);
    } finally {
      setDetecting(false);
    }
  };

  const handleGenerateVariants = async (momentId: number) => {
    setGenerating(momentId);
    try {
      await api.createABTest({ name: `AB Test Moment #${momentId}`, moment_id: momentId });
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(null);
    }
  };

  const handleStreamChange = (val: string) => {
    setSelectedStream(val);
    loadMoments(val);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Детекция моментов</h2>
          <p className="text-sm text-zinc-400">Находи и управляй ключевыми моментами со стримов</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedStream} onValueChange={handleStreamChange}>
            <SelectTrigger className="w-64 bg-zinc-800 border-zinc-700 text-white">
              <SelectValue placeholder="Выбери стрим" />
            </SelectTrigger>
            <SelectContent className="bg-zinc-800 border-zinc-700">
              <SelectItem value="all">Все стримы</SelectItem>
              {streams.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>{s.title}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={handleDetect}
            disabled={detecting || selectedStream === "all"}
            className="bg-violet-600 hover:bg-violet-700"
          >
            {detecting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Crosshair className="h-4 w-4 mr-2" />}
            Найти моменты
          </Button>
        </div>
      </div>

      {/* Moments Grid */}
      {loading ? (
        <div className="text-zinc-400 text-center py-8">Загрузка...</div>
      ) : moments.length === 0 ? (
        <div className="text-zinc-400 text-center py-8">Моментов нет. Выбери стрим и нажми «Найти моменты».</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {moments.map((moment) => {
            const meta = moment.metadata as Record<string, unknown>;
            return (
              <Card key={moment.id} className="bg-zinc-900 border-zinc-800 hover:border-zinc-700 transition-colors">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <Badge className={TYPE_COLORS[moment.moment_type] || "bg-zinc-500/20 text-zinc-400"}>
                        {MOMENT_TYPE_LABELS[moment.moment_type] || moment.moment_type.replace(/_/g, " ")}
                      </Badge>
                      <span className="ml-2 text-xs text-zinc-500">#{moment.id}</span>
                    </div>
                    <div className="flex items-center gap-1 text-yellow-400">
                      <Zap className="h-3 w-3" />
                      <span className="text-sm font-bold">{(moment.score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <p className="text-sm text-white mb-2">{moment.description}</p>
                  <div className="flex items-center gap-4 text-xs text-zinc-500 mb-3">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatTime(moment.timestamp_start)} - {formatTime(moment.timestamp_end)}
                    </span>
                    {meta.weapon ? <span>Оружие: {String(meta.weapon)}</span> : null}
                    {meta.map ? <span>Карта: {String(meta.map)}</span> : null}
                    {meta.kills ? <span>Киллы: {String(meta.kills)}</span> : null}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleGenerateVariants(moment.id)}
                    disabled={generating === moment.id}
                    className="w-full border-violet-500/50 text-violet-400 hover:bg-violet-500/10"
                  >
                    {generating === moment.id ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Zap className="h-4 w-4 mr-2" />
                    )}
                    Сгенерировать A/B варианты
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
