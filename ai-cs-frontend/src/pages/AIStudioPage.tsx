import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import {
  Mic, Image, Video, Wand2, Key, CheckCircle, XCircle,
  Play, Volume2, RefreshCw, Loader2, Download
} from "lucide-react";
import {
  api, GenerationStatus, TTSResult, LegacyPhotoResult, LipsyncResult, PipelineResult,
  Gallery
} from "@/hooks/useApi";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const VOICE_STYLE_LABELS: Record<string, string> = {
  cheerful: "бодрый",
  friendly: "дружелюбный",
  warm: "тёплый",
  british: "британский",
  australian: "австралийский",
  casual: "повседневный",
};

const formatVoiceLabel = (id: string) => {
  const parts = id.split("_");
  const lang = parts[0] === "ru" ? "RU" : parts[0] === "en" ? "EN" : parts[0].toUpperCase();
  const gender = parts[1] === "female" ? "женский" : parts[1] === "male" ? "мужской" : "";
  const styleRaw = parts.slice(2).join("_");
  const style = styleRaw ? (VOICE_STYLE_LABELS[styleRaw] || "пользовательский") : "";
  return [lang, gender, style].filter(Boolean).join(" · ");
};

const PHOTO_MODEL_LABELS: Record<string, string> = {
  "fal-ai/flux/dev": "Флакс Dev — максимум фотореала",
  "fal-ai/quant-sdxl": "SDXL (квантиз.) — бесплатно",
  "fal-ai/flux/schnell": "Флакс Schnell — быстро",
};

const formatPhotoModelLabel = (modelId: string) => PHOTO_MODEL_LABELS[modelId] || "Другая модель";

const LIPSYNC_MODEL_LABELS: Record<string, string> = {
  "veed/lipsync": "VEED — быстро и дёшево",
  "fal-ai/sync-lipsync": "Sync.so 1.9 — качество выше",
};

const formatLipsyncModelLabel = (modelId: string) => LIPSYNC_MODEL_LABELS[modelId] || "Другая модель";

const STEP_LABELS: Record<string, string> = {
  tts: "Голос",
  photo: "Фото",
  lipsync: "Липсинк",
};

const formatPipelineStepLabel = (step: string) => STEP_LABELS[step] || "Шаг";

export default function AIStudioPage() {
  const [status, setStatus] = useState<GenerationStatus | null>(null);
  const [loading, setLoading] = useState(true);

  // API Key
  const [falKey, setFalKey] = useState("");
  const [keySet, setKeySet] = useState(false);

  // TTS
  const [ttsText, setTtsText] = useState("О боже! Ты видел этот клатч? Это было просто безумие!");
  const [ttsVoice, setTtsVoice] = useState("en_female_cheerful");
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsResult, setTtsResult] = useState<TTSResult | null>(null);

  // Photo
  const [photoPrompt, setPhotoPrompt] = useState(
    "красивая молодая женщина, 22 года, длинные каштановые волосы, зелёные глаза, естественный макияж, тёплая улыбка, повседневный образ, золотой час, фото для инстаграма, ультрареализм, 8k"
  );
  const [photoModel, setPhotoModel] = useState("fal-ai/flux/dev");
  const [photoLoading, setPhotoLoading] = useState(false);
  const [photoResult, setPhotoResult] = useState<LegacyPhotoResult | null>(null);

  // Lipsync
  const [lipsyncImageUrl, setLipsyncImageUrl] = useState("");
  const [lipsyncAudioUrl, setLipsyncAudioUrl] = useState("");
  const [lipsyncModel, setLipsyncModel] = useState("veed/lipsync");
  const [lipsyncLoading, setLipsyncLoading] = useState(false);
  const [lipsyncResult, setLipsyncResult] = useState<LipsyncResult | null>(null);

  // Full Pipeline
  const [pipelineText, setPipelineText] = useState("Всем привет! Добро пожаловать в хайлайты со стрима. Этот момент был просто сумасшедший!");
  const [pipelinePrompt, setPipelinePrompt] = useState(
    "красивая молодая женщина, 22 года, длинные каштановые волосы, зелёные глаза, естественный макияж, тёплая улыбка, повседневный образ, золотой час, фото для инстаграма, ультрареализм, 8k"
  );
  const [pipelineVoice, setPipelineVoice] = useState("en_female_cheerful");
  const [pipelineLipsyncModel, setPipelineLipsyncModel] = useState("veed/lipsync");
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<PipelineResult | null>(null);
  const [pipelineStep, setPipelineStep] = useState("");

  // Gallery
  const [gallery, setGallery] = useState<Gallery | null>(null);

  // Error
  const [error, setError] = useState("");

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const s = await api.getGenerationStatus();
      setStatus(s);
      setKeySet(s.fal_api_configured);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadGallery = async () => {
    try {
      const g = await api.getGallery();
      setGallery(g);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSetKey = async () => {
    if (!falKey.trim()) return;
    try {
      await api.setFalKey(falKey.trim());
      setKeySet(true);
      await loadStatus();
    } catch {
      setError("Не удалось сохранить API ключ");
    }
  };

  const handleTTS = async () => {
    setTtsLoading(true);
    setTtsResult(null);
    setError("");
    try {
      const result = await api.generateTTS({ text: ttsText, voice_id: ttsVoice });
      setTtsResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка TTS");
    } finally {
      setTtsLoading(false);
    }
  };

  const handlePhoto = async () => {
    setPhotoLoading(true);
    setPhotoResult(null);
    setError("");
    try {
      const result = await api.generatePhoto({ prompt: photoPrompt, model: photoModel });
      setPhotoResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка генерации фото");
    } finally {
      setPhotoLoading(false);
    }
  };

  const handleLipsync = async () => {
    setLipsyncLoading(true);
    setLipsyncResult(null);
    setError("");
    try {
      const result = await api.generateLipsync({
        image_url: lipsyncImageUrl,
        audio_url: lipsyncAudioUrl,
        model: lipsyncModel,
      });
      setLipsyncResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка lip-sync");
    } finally {
      setLipsyncLoading(false);
    }
  };

  const handlePipeline = async () => {
    setPipelineLoading(true);
    setPipelineResult(null);
    setError("");
    setPipelineStep("Запуск пайплайна...");
    try {
      const result = await api.runFullPipeline({
        text: pipelineText,
        photo_prompt: pipelinePrompt,
        voice_id: pipelineVoice,
        lipsync_model: pipelineLipsyncModel,
      });
      setPipelineResult(result);
      setPipelineStep("Готово!");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка пайплайна");
      setPipelineStep("Ошибка");
    } finally {
      setPipelineLoading(false);
    }
  };

  if (loading) return <div className="text-zinc-400 text-center py-8">Загрузка...</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-violet-400" />
            AI Студия — Генерация контента
          </h2>
          <p className="text-sm text-zinc-400">
            Генерация фото, голоса и видео с липсинком AI‑персонажа
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={status?.tts_available ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}>
            <Volume2 className="h-3 w-3 mr-1" /> TTS {status?.tts_available ? "Готово" : "Выкл"}
          </Badge>
          <Badge className={status?.fal_api_configured ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}>
            <Image className="h-3 w-3 mr-1" /> Фото {status?.fal_api_configured ? "Готово" : "Нужен ключ"}
          </Badge>
          <Badge className={status?.lipsync_available ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}>
            <Video className="h-3 w-3 mr-1" /> Липсинк {status?.lipsync_available ? "Готово" : "Нужен ключ"}
          </Badge>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2">
          <XCircle className="h-4 w-4 flex-shrink-0" />
          {error}
          <button onClick={() => setError("")} className="ml-auto text-xs hover:text-white">скрыть</button>
        </div>
      )}

      {/* API Key Setup */}
      {!keySet && (
        <Card className="bg-zinc-900 border-zinc-800 border-yellow-500/30">
          <CardHeader>
            <CardTitle className="text-lg text-yellow-400 flex items-center gap-2">
              <Key className="h-5 w-5" />
              Нужно настроить: fal.ai API Key
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-zinc-400">
              TTS работает бесплатно. Для генерации фото и липсинка нужен fal.ai API‑ключ.
              Получить ключ можно на <a href="https://fal.ai" target="_blank" rel="noreferrer" className="text-violet-400 underline">fal.ai</a> (обычно дают $10 бесплатных кредитов).
            </p>
            <div className="flex gap-2">
              <Input
                type="password"
                placeholder="Вставь fal.ai API-ключ..."
                value={falKey}
                onChange={(e) => setFalKey(e.target.value)}
                className="bg-zinc-800 border-zinc-700 text-white flex-1"
              />
              <Button onClick={handleSetKey} className="bg-violet-600 hover:bg-violet-700">
                <Key className="h-4 w-4 mr-2" /> Сохранить ключ
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Budget Overview */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="pt-4">
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-xs text-zinc-400">Бюджет</div>
              <div className="text-lg font-bold text-green-400">$9.00</div>
            </div>
            <div>
              <div className="text-xs text-zinc-400">Фото (Flux Dev)</div>
              <div className="text-lg font-bold text-violet-400">~900</div>
              <div className="text-[10px] text-zinc-500">$0.01 за фото</div>
            </div>
            <div>
              <div className="text-xs text-zinc-400">Голос</div>
              <div className="text-lg font-bold text-blue-400">∞</div>
              <div className="text-[10px] text-zinc-500">БЕСПЛАТНО (edge-tts)</div>
            </div>
            <div>
              <div className="text-xs text-zinc-400">Видео 3с (VEED)</div>
              <div className="text-lg font-bold text-pink-400">~450</div>
              <div className="text-[10px] text-zinc-500">$0.02 за видео</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs defaultValue="tts" className="space-y-4">
        <TabsList className="bg-zinc-900 border border-zinc-800">
          <TabsTrigger value="tts" className="data-[state=active]:bg-violet-600">
            <Volume2 className="h-4 w-4 mr-1" /> Голос (бесплатно)
          </TabsTrigger>
          <TabsTrigger value="photo" className="data-[state=active]:bg-violet-600">
            <Image className="h-4 w-4 mr-1" /> Фото
          </TabsTrigger>
          <TabsTrigger value="lipsync" className="data-[state=active]:bg-violet-600">
            <Video className="h-4 w-4 mr-1" /> Липсинк
          </TabsTrigger>
          <TabsTrigger value="pipeline" className="data-[state=active]:bg-violet-600">
            <Wand2 className="h-4 w-4 mr-1" /> Пайплайн
          </TabsTrigger>
          <TabsTrigger value="gallery" className="data-[state=active]:bg-violet-600" onClick={loadGallery}>
            <Download className="h-4 w-4 mr-1" /> Галерея
          </TabsTrigger>
        </TabsList>

        {/* TTS Tab */}
        <TabsContent value="tts">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Mic className="h-5 w-5 text-blue-400" />
                Генерация голоса (edge-tts)
                <Badge className="bg-green-500/20 text-green-400 ml-2">БЕСПЛАТНО</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-zinc-400">Текст для озвучки</Label>
                <textarea
                  value={ttsText}
                  onChange={(e) => setTtsText(e.target.value)}
                  rows={3}
                  className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-md p-3 text-white text-sm resize-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  placeholder="Введи текст для озвучки..."
                />
              </div>
              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <Label className="text-zinc-400">Голос</Label>
                  <Select value={ttsVoice} onValueChange={setTtsVoice}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {(status?.available_voices || []).map(v => (
                        <SelectItem key={v} value={v}>{formatVoiceLabel(v)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleTTS} disabled={ttsLoading || !ttsText.trim()} className="bg-blue-600 hover:bg-blue-700">
                  {ttsLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
                  Сгенерировать голос
                </Button>
              </div>

              {ttsResult && ttsResult.success && (
                <div className="bg-zinc-800 rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 text-green-400">
                    <CheckCircle className="h-4 w-4" /> Сгенерировано!
                  </div>
                  <audio
                    controls
                    src={`${API_URL}/api/generate/files/audio/${ttsResult.filename}`}
                    className="w-full"
                  />
                  <div className="flex gap-4 text-xs text-zinc-400">
                    <span>Голос: {ttsResult.voice}</span>
                    <span>Размер: {(ttsResult.file_size_bytes / 1024).toFixed(1)} KB</span>
                    <span className="text-green-400">Стоимость: $0.00 (БЕСПЛАТНО)</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Photo Tab */}
        <TabsContent value="photo">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Image className="h-5 w-5 text-violet-400" />
                Генерация фото (fal.ai)
                <Badge className="bg-violet-500/20 text-violet-400 ml-2">$0.01/фото</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-zinc-400">Промт фото</Label>
                <textarea
                  value={photoPrompt}
                  onChange={(e) => setPhotoPrompt(e.target.value)}
                  rows={4}
                  className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-md p-3 text-white text-sm resize-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  placeholder="Опиши, какое фото персонажа сгенерировать..."
                />
              </div>
              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <Label className="text-zinc-400">Модель</Label>
                  <Select value={photoModel} onValueChange={setPhotoModel}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {(status?.available_photo_models || []).map(m => (
                        <SelectItem key={m.id} value={m.id}>
                          {formatPhotoModelLabel(m.id)} ({m.cost})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  onClick={handlePhoto}
                  disabled={photoLoading || !photoPrompt.trim() || !keySet}
                  className="bg-violet-600 hover:bg-violet-700"
                >
                  {photoLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Image className="h-4 w-4 mr-2" />}
                  Сгенерировать фото
                </Button>
              </div>

              {!keySet && (
                <p className="text-xs text-yellow-400">Укажи fal.ai API‑ключ выше, чтобы включить генерацию фото.</p>
              )}

              {photoResult && photoResult.success && photoResult.images && (
                <div className="bg-zinc-800 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-2 text-green-400">
                    <CheckCircle className="h-4 w-4" /> Фото готово!
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {photoResult.images.map((img, i) => (
                      <div key={i} className="relative">
                        <img
                          src={img.url || `${API_URL}${img.file_path}`}
                          alt={`Сгенерировано ${i + 1}`}
                          className="rounded-lg w-full object-cover"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-4 text-xs text-zinc-400">
                    <span>Модель: {photoResult.model}</span>
                    <span className="text-violet-400">Стоимость: ~${photoResult.cost_estimate.toFixed(3)}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Lipsync Tab */}
        <TabsContent value="lipsync">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Video className="h-5 w-5 text-pink-400" />
                Липсинк видео
                <Badge className="bg-pink-500/20 text-pink-400 ml-2">$0.02/3с</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-zinc-400">
                Объедини сгенерированное фото и аудио, чтобы получить говорящий ролик с липсинком.
                Используй ссылки из вкладок «Фото» и «Голос» или вставь внешние ссылки.
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-zinc-400">Ссылка на изображение</Label>
                  <Input
                    value={lipsyncImageUrl}
                    onChange={(e) => setLipsyncImageUrl(e.target.value)}
                    placeholder="https://... или вставь ссылку на сгенерированное фото"
                    className="bg-zinc-800 border-zinc-700 text-white"
                  />
                </div>
                <div>
                  <Label className="text-zinc-400">Ссылка на аудио</Label>
                  <Input
                    value={lipsyncAudioUrl}
                    onChange={(e) => setLipsyncAudioUrl(e.target.value)}
                    placeholder="https://... или вставь ссылку на сгенерированное аудио"
                    className="bg-zinc-800 border-zinc-700 text-white"
                  />
                </div>
              </div>
              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <Label className="text-zinc-400">Модель липсинка</Label>
                  <Select value={lipsyncModel} onValueChange={setLipsyncModel}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {(status?.available_lipsync_models || []).map(m => (
                        <SelectItem key={m.id} value={m.id}>
                          {formatLipsyncModelLabel(m.id)} ({m.cost_3s}/3с)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  onClick={handleLipsync}
                  disabled={lipsyncLoading || !lipsyncImageUrl || !lipsyncAudioUrl || !keySet}
                  className="bg-pink-600 hover:bg-pink-700"
                >
                  {lipsyncLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Video className="h-4 w-4 mr-2" />}
                  Сгенерировать видео
                </Button>
              </div>

              {!keySet && (
                <p className="text-xs text-yellow-400">Укажи fal.ai API‑ключ выше, чтобы включить липсинк.</p>
              )}

              {lipsyncResult && lipsyncResult.success && (
                <div className="bg-zinc-800 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-2 text-green-400">
                    <CheckCircle className="h-4 w-4" /> Видео готово!
                  </div>
                  {lipsyncResult.video_url && (
                    <video controls className="rounded-lg w-full max-w-md" src={lipsyncResult.video_url} />
                  )}
                  <div className="text-xs text-zinc-400">
                    <span className="text-pink-400">Стоимость: ~${lipsyncResult.cost_estimate.toFixed(3)}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Full Pipeline Tab */}
        <TabsContent value="pipeline">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Wand2 className="h-5 w-5 text-yellow-400" />
                Пайплайн: текст → голос → фото → 3с видео
                <Badge className="bg-yellow-500/20 text-yellow-400 ml-2">~$0.03/клип</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-zinc-400">
                Одна кнопка: генерируем голос из текста (бесплатно), создаём фото и делаем 3-секундное lip-sync видео.
              </p>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-zinc-400">Текст (что она говорит)</Label>
                  <textarea
                    value={pipelineText}
                    onChange={(e) => setPipelineText(e.target.value)}
                    rows={3}
                    className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-md p-3 text-white text-sm resize-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <Label className="text-zinc-400">Промт фото</Label>
                  <textarea
                    value={pipelinePrompt}
                    onChange={(e) => setPipelinePrompt(e.target.value)}
                    rows={3}
                    className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-md p-3 text-white text-sm resize-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label className="text-zinc-400">Голос</Label>
                  <Select value={pipelineVoice} onValueChange={setPipelineVoice}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {(status?.available_voices || []).map(v => (
                        <SelectItem key={v} value={v}>{formatVoiceLabel(v)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-zinc-400">Модель липсинка</Label>
                  <Select value={pipelineLipsyncModel} onValueChange={setPipelineLipsyncModel}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {(status?.available_lipsync_models || []).map(m => (
                        <SelectItem key={m.id} value={m.id}>
                          {formatLipsyncModelLabel(m.id)} ({m.cost_3s}/3с)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-end">
                  <Button
                    onClick={handlePipeline}
                    disabled={pipelineLoading || !pipelineText.trim() || !pipelinePrompt.trim() || !keySet}
                    className="w-full bg-gradient-to-r from-violet-600 to-pink-600 hover:from-violet-700 hover:to-pink-700"
                  >
                    {pipelineLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                    Запустить пайплайн
                  </Button>
                </div>
              </div>

              {!keySet && (
                <p className="text-xs text-yellow-400">
                  TTS бесплатный, но фото + липсинк требуют fal.ai ключ. Укажи ключ выше.
                </p>
              )}

              {/* Pipeline Progress */}
              {pipelineLoading && (
                <div className="bg-zinc-800 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-2 text-yellow-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {pipelineStep || "Выполняю пайплайн..."}
                  </div>
                  <Progress value={33} className="h-2" />
                  <div className="grid grid-cols-3 gap-2 text-xs text-zinc-500">
                    <div className="text-center">1. TTS (бесплатно)</div>
                    <div className="text-center">2. Фото (~$0.01)</div>
                    <div className="text-center">3. Липсинк (~$0.02)</div>
                  </div>
                </div>
              )}

              {/* Pipeline Result */}
              {pipelineResult && (
                <div className="bg-zinc-800 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-2 text-green-400">
                    <CheckCircle className="h-4 w-4" />
                    Пайплайн завершён!
                    <span className="text-xs text-zinc-400 ml-auto">
                      Итоговая стоимость: <span className="text-green-400">${pipelineResult.total_cost.toFixed(3)}</span>
                    </span>
                  </div>

                  {pipelineResult.steps.map((step, i) => {
                    const r = step.result as Record<string, unknown>;
                    return (
                      <div key={i} className="border border-zinc-700 rounded-lg p-3">
                        <div className="text-sm font-medium text-zinc-300 mb-2">
                          Шаг {i + 1}: {formatPipelineStepLabel(step.step)}
                          {r.success ? (
                            <CheckCircle className="h-3 w-3 text-green-400 inline ml-2" />
                          ) : (
                            <XCircle className="h-3 w-3 text-red-400 inline ml-2" />
                          )}
                        </div>

                        {step.step === "tts" && !!r.filename && (
                          <audio
                            controls
                            src={`${API_URL}/api/generate/files/audio/${String(r.filename)}`}
                            className="w-full h-8"
                          />
                        )}

                        {step.step === "photo" && !!r.images && (
                          <div className="grid grid-cols-2 gap-2">
                            {(r.images as Array<{ url?: string; file_path?: string }>).map((img, j) => (
                              <img
                                key={j}
                                src={img.url || `${API_URL}${img.file_path}`}
                                alt={`Фото ${j + 1}`}
                                className="rounded-lg w-full"
                              />
                            ))}
                          </div>
                        )}

                        {step.step === "lipsync" && !!r.video_url && (
                          <video
                            controls
                            src={String(r.video_url)}
                            className="rounded-lg w-full max-w-md"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Gallery Tab */}
        <TabsContent value="gallery">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Download className="h-5 w-5 text-emerald-400" />
                Галерея сгенерированного контента
              </CardTitle>
              <Button variant="outline" size="sm" onClick={loadGallery} className="border-zinc-700 text-zinc-400 hover:text-white">
                <RefreshCw className="h-3 w-3 mr-1" /> Обновить
              </Button>
            </CardHeader>
            <CardContent>
              {!gallery ? (
                <p className="text-zinc-500 text-center py-4">Нажми «Обновить», чтобы загрузить галерею</p>
              ) : (
                <div className="space-y-6">
                  {/* Photos */}
                  <div>
                    <h3 className="text-sm font-medium text-zinc-300 mb-2">
                      Фото ({gallery.photos.length})
                    </h3>
                    {gallery.photos.length === 0 ? (
                      <p className="text-xs text-zinc-500">Фото пока нет</p>
                    ) : (
                      <div className="grid grid-cols-4 gap-2">
                        {gallery.photos.map((item, i) => (
                          <a key={i} href={`${API_URL}${item.url}`} target="_blank" rel="noreferrer">
                            <img
                              src={`${API_URL}${item.url}`}
                              alt={item.filename}
                              className="rounded-lg w-full h-32 object-cover hover:ring-2 ring-violet-500 transition-all"
                            />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>

                  <Separator className="bg-zinc-800" />

                  {/* Audio */}
                  <div>
                    <h3 className="text-sm font-medium text-zinc-300 mb-2">
                      Аудио ({gallery.audio.length})
                    </h3>
                    {gallery.audio.length === 0 ? (
                      <p className="text-xs text-zinc-500">Аудио пока нет</p>
                    ) : (
                      <div className="space-y-2">
                        {gallery.audio.map((item, i) => (
                          <div key={i} className="flex items-center gap-3 bg-zinc-800 rounded-lg p-2">
                            <Volume2 className="h-4 w-4 text-blue-400" />
                            <audio controls src={`${API_URL}${item.url}`} className="flex-1 h-8" />
                            <span className="text-xs text-zinc-500">
                              {(item.size_bytes / 1024).toFixed(0)} KB
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <Separator className="bg-zinc-800" />

                  {/* Video */}
                  <div>
                    <h3 className="text-sm font-medium text-zinc-300 mb-2">
                      Видео ({gallery.video.length})
                    </h3>
                    {gallery.video.length === 0 ? (
                      <p className="text-xs text-zinc-500">Видео пока нет</p>
                    ) : (
                      <div className="grid grid-cols-2 gap-3">
                        {gallery.video.map((item, i) => (
                          <video key={i} controls className="rounded-lg w-full" src={`${API_URL}${item.url}`} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
