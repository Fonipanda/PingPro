import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Progress } from './components/ui/progress';
import { Alert, AlertDescription } from './components/ui/alert';
import { Separator } from './components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  Upload,
  PlayCircle,
  BarChart3,
  Target,
  Trophy,
  Clock,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Video,
  Zap,
  Award,
  Activity,
  Star,
  RotateCcw,
  ArrowRight,
} from 'lucide-react';
import './App.css';
import PoseAnalysis from './PoseAnalysis';
import { analyzeVideo, getAnalysisStatus, getAnalysisResults, getVideoUrl } from './api';

const pct = (value) => `${Math.round(Number(value) || 0)}%`;
const num = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};
// 243 -> "4:03" ; 62.5 -> "1:03"
const formatDuration = (seconds) => {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const m = Math.floor(total / 60);
  const s = String(total % 60).padStart(2, '0');
  return `${m}:${s}`;
};

// Shared header for analysis pages
const PageHeader = ({ title, subtitle, right }) => (
  <header className="bg-white/80 backdrop-blur-md border-b border-emerald-100 sticky top-0 z-50">
    <div className="container mx-auto px-6 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-xl flex items-center justify-center shrink-0">
            <Trophy className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">{title}</h1>
            <p className="text-sm text-gray-600">{subtitle}</p>
          </div>
        </div>
        {right}
      </div>
    </div>
  </header>
);

// Video compilation card with inline player (or clean empty state)
const VideoCard = ({ title, badge, description, videoType, compilations, analysisId, iconColor }) => {
  const available = Boolean(compilations && compilations[videoType]);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2 flex-wrap">
          <Video className={`w-5 h-5 ${iconColor}`} />
          <span>{title}</span>
          {badge && <Badge className="bg-emerald-100 text-emerald-800 text-xs">{badge}</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {available ? (
          <video
            controls
            preload="metadata"
            src={getVideoUrl(analysisId, videoType)}
            className="w-full rounded-lg bg-black"
          />
        ) : (
          <div className="bg-gray-100 rounded-lg p-8 text-center">
            <Video className="w-14 h-14 mx-auto mb-3 text-gray-400" />
            <p className="text-gray-600 font-medium">Compilation vidéo indisponible</p>
            <p className="text-sm text-gray-500 mt-1">
              Le serveur ne dispose pas de FFmpeg pour générer les extraits vidéo.
            </p>
          </div>
        )}
        {description && <p className="text-sm text-gray-500 mt-3 text-center">{description}</p>}
      </CardContent>
    </Card>
  );
};

// Stat tile
const StatTile = ({ value, label, colorClass = 'text-emerald-600', bgClass = 'bg-emerald-50' }) => (
  <div className={`${bgClass} rounded-lg p-4 text-center`}>
    <div className={`text-2xl font-bold ${colorClass} mb-1`}>{value}</div>
    <div className="text-sm text-gray-600">{label}</div>
  </div>
);

// HomePage Component
// TableCalibratorModal — calibrage manuel de la table (4 coins cliqués sur une frame)
// Garantit l'homographie quand l'auto-détection échoue (plan de caméra difficile).
const CORNER_LABELS = [
  'Coin gauche proche (votre côté, à gauche)',
  'Coin droit proche (votre côté, à droite)',
  'Coin droit éloigné',
  'Coin gauche éloigné',
];

const TableCalibratorModal = ({ file, onValidate, onClose }) => {
  const [points, setPoints] = useState([]);
  const [seeked, setSeeked] = useState(false);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const drawCanvas = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    points.forEach((p, i) => {
      if (i > 0) {
        const prev = points[i - 1];
        ctx.beginPath();
        ctx.moveTo(prev[0] * canvas.width, prev[1] * canvas.height);
        ctx.lineTo(p[0] * canvas.width, p[1] * canvas.height);
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 3;
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.arc(p[0] * canvas.width, p[1] * canvas.height, 8, 0, 2 * Math.PI);
      ctx.fillStyle = i === points.length - 1 ? '#ef4444' : '#10b981';
      ctx.fill();
    });
  };

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return undefined;
    const onSeek = () => {
      setSeeked(true);
      drawCanvas();
    };
    video.addEventListener('seeked', onSeek);
    video.addEventListener('loadeddata', onSeek);
    return () => {
      video.removeEventListener('seeked', onSeek);
      video.removeEventListener('loadeddata', onSeek);
    };
  });

  const handleClick = (e) => {
    if (points.length >= 4) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    const next = [...points, [Math.min(1, Math.max(0, x)), Math.min(1, Math.max(0, y))]];
    setPoints(next);
    setTimeout(drawCanvas, 0);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl p-6 max-w-3xl w-full max-h-full overflow-auto">
        <h3 className="text-lg font-semibold mb-1">Calibrage de la table</h3>
        <p className="text-sm text-gray-600 mb-4">
          Cliquez les <strong>4 coins de la surface de jeu</strong> dans l'ordre indiqué
          ({points.length}/4). Le calibrage garantit la carte de placement et l'incrustation
          vidéo, même quand la détection automatique échoue.
        </p>
        <video
          ref={videoRef}
          src={URL.createObjectURL(file)}
          muted
          className="hidden"
          onLoadedMetadata={(e) => {
            e.target.currentTime = Math.min(2, (e.target.duration || 4) / 2);
          }}
        />
        <canvas
          ref={canvasRef}
          onClick={handleClick}
          className="w-full rounded-lg border border-gray-300 cursor-crosshair"
          style={{ display: seeked ? 'block' : 'none' }}
        />
        {!seeked && (
          <p className="text-sm text-gray-400 py-10 text-center">Chargement de la frame...</p>
        )}
        <ol className="text-xs text-gray-500 mt-3 space-y-1">
          {CORNER_LABELS.map((label, i) => (
            <li key={i} className={points.length === i ? 'font-semibold text-emerald-600' : ''}>
              {i + 1}. {label}
            </li>
          ))}
        </ol>
        <div className="flex justify-end space-x-3 mt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Annuler
          </button>
          <button
            type="button"
            onClick={() => setPoints([])}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Recommencer
          </button>
          <button
            type="button"
            disabled={points.length !== 4}
            onClick={() => onValidate(points)}
            className="px-4 py-2 text-sm rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 disabled:opacity-40"
          >
            Valider le calibrage
          </button>
        </div>
      </div>
    </div>
  );
};

const HomePage = ({ onAnalysisStarted }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [playerSide, setPlayerSide] = useState('droite');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [tableQuad, setTableQuad] = useState(null);
  const [showCalibrator, setShowCalibrator] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('video/')) {
        setSelectedFile(file);
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setTableQuad(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append('video', selectedFile);
      formData.append('player_side', playerSide);
      formData.append('skill_level', 'intermediaire');
      formData.append('focus_areas', 'technique_coups,positionnement,timing');
      if (tableQuad && tableQuad.length === 4) {
        formData.append('table_quad', JSON.stringify(tableQuad));
      }

      const data = await analyzeVideo(formData);
      if (data?.analysis_id) {
        onAnalysisStarted(data.analysis_id);
      } else {
        setUploadError('Réponse inattendue du serveur. Veuillez réessayer.');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(
        error.response?.data?.detail ||
          'Erreur lors du téléchargement. Veuillez réessayer.'
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-blue-50">
      <PageHeader
        title="PingPro"
        subtitle="Analyse IA Tennis de Table"
        right={
          <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
            <Zap className="w-3 h-3 mr-1" />
            IA Avancée
          </Badge>
        }
      />

      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto text-center">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
              Améliorez votre jeu avec l'
              <span className="bg-gradient-to-r from-emerald-500 to-blue-500 bg-clip-text text-transparent">
                analyse IA
              </span>
            </h2>
            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Analysez vos performances au tennis de table grâce à l'intelligence artificielle.
              Obtenez des conseils personnalisés et suivez vos progrès comme un pro.
            </p>

            {/* Features Grid */}
            <div className="grid md:grid-cols-3 gap-8 mb-12">
              <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-6 border border-emerald-100">
                <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center mb-4 mx-auto">
                  <Video className="w-6 h-6 text-emerald-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Analyse Vidéo</h3>
                <p className="text-gray-600">Analysez vos techniques et mouvements frame par frame</p>
              </div>

              <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-6 border border-blue-100">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4 mx-auto">
                  <BarChart3 className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Statistiques</h3>
                <p className="text-gray-600">Suivez vos performances avec des métriques détaillées</p>
              </div>

              <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-6 border border-purple-100">
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4 mx-auto">
                  <Target className="w-6 h-6 text-purple-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Conseils Personnalisés</h3>
                <p className="text-gray-600">Recevez des recommandations adaptées à votre niveau</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Upload Section */}
      <section className="py-16 px-6">
        <div className="container mx-auto max-w-4xl">
          <Card className="border-0 shadow-xl bg-white/80 backdrop-blur-sm">
            <CardHeader className="text-center pb-8">
              <CardTitle className="text-3xl font-bold text-gray-900 mb-4">
                Commencez votre analyse
              </CardTitle>
              <p className="text-gray-600 text-lg">
                Téléchargez votre vidéo de match ou d'entraînement
              </p>
            </CardHeader>
            <CardContent className="space-y-8">
              {/* Configuration */}
              <div className="max-w-md mx-auto">
                <label className="block text-sm font-semibold text-gray-700 mb-3">
                  Joueur à analyser
                </label>
                <div className="flex space-x-3">
                  <Button
                    variant={playerSide === 'gauche' ? 'default' : 'outline'}
                    onClick={() => setPlayerSide('gauche')}
                    className="flex-1"
                  >
                    Côté gauche
                  </Button>
                  <Button
                    variant={playerSide === 'droite' ? 'default' : 'outline'}
                    onClick={() => setPlayerSide('droite')}
                    className="flex-1"
                  >
                    Côté droit
                  </Button>
                </div>
              </div>

              {/* Calibrage de table (optionnel mais recommandé) */}
              {selectedFile && (
                <div className="max-w-md mx-auto flex items-center justify-between bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <div>
                    <p className="text-sm font-semibold text-gray-800">Calibrage de la table</p>
                    <p className="text-xs text-gray-500">
                      {tableQuad
                        ? 'Calibré : placement et incrustation garantis.'
                        : 'Recommandé si la table est mal détectée automatiquement.'}
                    </p>
                  </div>
                  <Button
                    variant={tableQuad ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setShowCalibrator(true)}
                  >
                    {tableQuad ? 'Modifier' : 'Calibrer'}
                  </Button>
                </div>
              )}

              {uploadError && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-center">
                  {uploadError}
                </div>
              )}

              {/* File Upload */}
              <div
                className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 ${
                  dragActive
                    ? 'border-emerald-400 bg-emerald-50'
                    : selectedFile
                      ? 'border-emerald-300 bg-emerald-50'
                      : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />

                <div className="space-y-4">
                  {selectedFile ? (
                    <>
                      <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
                        <CheckCircle className="w-8 h-8 text-emerald-600" />
                      </div>
                      <div>
                        <p className="text-lg font-semibold text-gray-900">{selectedFile.name}</p>
                        <p className="text-sm text-gray-500">
                          {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
                        <Upload className="w-8 h-8 text-gray-400" />
                      </div>
                      <div>
                        <p className="text-lg font-semibold text-gray-700">
                          Glissez votre vidéo ici
                        </p>
                        <p className="text-sm text-gray-500">
                          ou cliquez pour parcourir • MP4, AVI, MOV, MKV acceptés
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Upload Button */}
              <div className="flex justify-center">
                <Button
                  onClick={handleUpload}
                  disabled={!selectedFile || isUploading}
                  size="lg"
                  className="px-12 py-4 text-white shadow-lg bg-gradient-to-r from-emerald-500 to-blue-500 hover:from-emerald-600 hover:to-blue-600"
                >
                  {isUploading ? (
                    <>
                      <Clock className="w-5 h-5 mr-2 animate-spin" />
                      Envoi en cours...
                    </>
                  ) : (
                    <>
                      <PlayCircle className="w-5 h-5 mr-2" />
                      Commencer l'analyse
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {showCalibrator && selectedFile && (
        <TableCalibratorModal
          file={selectedFile}
          onValidate={(pts) => {
            setTableQuad(pts);
            setShowCalibrator(false);
          }}
          onClose={() => setShowCalibrator(false)}
        />
      )}

      {/* Footer */}
      <footer className="bg-gray-50 py-12 px-6 mt-20">
        <div className="container mx-auto text-center">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-lg flex items-center justify-center">
              <Trophy className="w-4 h-4 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">PingPro</span>
          </div>
          <p className="text-gray-600">
            Améliorez votre tennis de table avec l'intelligence artificielle
          </p>
        </div>
      </footer>
    </div>
  );
};

// AnalysisPage Component (polling while queued or processing)
const AnalysisPage = ({ analysisId, onReset }) => {
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;
    let cancelled = false;

    const checkStatus = async () => {
      if (stoppedRef.current) return;
      try {
        const statusData = await getAnalysisStatus(analysisId);
        if (cancelled) return;
        setStatus(statusData);

        if (statusData.status === 'completed') {
          stoppedRef.current = true;
          const resultsData = await getAnalysisResults(analysisId);
          if (!cancelled) setResults(resultsData);
        } else if (statusData.status === 'failed') {
          stoppedRef.current = true;
        }
      } catch (err) {
        if (cancelled) return;
        stoppedRef.current = true;
        setError(err.response?.data?.detail || 'Erreur lors du chargement de l\'analyse');
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [analysisId]);

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="space-y-4 text-center">
          <Alert className="max-w-md">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button variant="outline" onClick={onReset}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Nouvelle analyse
          </Button>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Clock className="w-12 h-12 mx-auto mb-4 animate-spin text-emerald-500" />
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    );
  }

  if (status.status === 'failed') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="space-y-4 text-center">
          <Alert className="max-w-md">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {status.error_message || "Erreur lors de l'analyse"}
            </AlertDescription>
          </Alert>
          <Button variant="outline" onClick={onReset}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Réessayer
          </Button>
        </div>
      </div>
    );
  }

  if (results) {
    return <ResultsPage results={results} onReset={onReset} />;
  }

  // Queued or processing
  const progress = Math.min(100, Math.max(0, num(status.progress, 0)));

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-blue-50 p-6">
      <div className="container mx-auto max-w-4xl">
        <Card className="shadow-xl">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold text-gray-900 mb-2">
              Analyse en cours...
            </CardTitle>
            <p className="text-gray-600">
              Votre vidéo est en cours d'analyse par notre IA
            </p>
          </CardHeader>
          <CardContent className="space-y-8">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-6 relative">
                <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 to-blue-400 rounded-full animate-pulse"></div>
                <div className="absolute inset-2 bg-white rounded-full flex items-center justify-center">
                  <BarChart3 className="w-8 h-8 text-emerald-500" />
                </div>
              </div>

              <Progress value={progress} className="w-full max-w-md mx-auto h-3 mb-4" />

              <p className="text-lg font-semibold text-gray-900">
                {progress.toFixed(0)}% terminé
              </p>
              <p className="text-sm text-gray-600 mt-2">
                {status.current_step || 'Traitement en cours...'}
              </p>
            </div>

            <div className="bg-emerald-50 rounded-xl p-6 text-center">
              <Clock className="w-8 h-8 mx-auto mb-3 text-emerald-600" />
              <p className="text-emerald-800 font-medium">Temps estimé : 2-4 minutes</p>
              <p className="text-emerald-600 text-sm mt-1">Ne fermez pas cette page</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// ResultsPage Component — wired to the real backend payload
const ResultsPage = ({ results, onReset }) => {
  const metrics = results?.performance_metrics || {};
  const technical = results?.technical_analysis || {};
  const scoring = results?.table_tennis_scoring || {};
  const finalScore = scoring.final_score || {};
  const matchStats = scoring.match_statistics || {};
  const events = metrics.event_detection || {};
  const rally = metrics.rally_analysis || {};
  const stroke = technical.stroke_analysis || {};
  const positioning = technical.positioning_analysis || {};
  const matchAnalysis = results?.match_analysis || null;
  const compilations = results?.video_compilations || {};
  const videoInfo = results?.video_info || {};
  const analysisId = results?.analysis_id;
  const [statsView, setStatsView] = useState('you');
  const [selectedMoment, setSelectedMoment] = useState(null);

  const recommendations = Array.isArray(results?.recommendations)
    ? results.recommendations
    : [];
  const improvementAreas = Array.isArray(metrics.improvement_areas)
    ? metrics.improvement_areas
    : [];

  const won = finalScore.winner !== 'player2';

  // Deterministic score progression (real data when available)
  const scoreData = useMemo(() => {
    if (Array.isArray(scoring.score_progression) && scoring.score_progression.length > 0) {
      return scoring.score_progression;
    }
    const p1 = num(finalScore.player1, 0);
    const p2 = num(finalScore.player2, 0);
    const points = Math.max(11, p1 + p2 || 19);
    return Array.from({ length: points }, (_, i) => ({
      point: i + 1,
      player1: Math.round((p1 * (i + 1)) / points),
      player2: Math.round((p2 * (i + 1)) / points),
    }));
  }, [scoring.score_progression, finalScore.player1, finalScore.player2]);

  // Radar from real metrics, compared to a fixed target level
  const radarData = useMemo(() => {
    const rows = [
      ['Technique', metrics.technical_consistency],
      ['Tactique', metrics.positioning_score],
      ['Précision', metrics.timing_accuracy],
      ['Global', metrics.overall_score],
    ];
    if (metrics.posture_score != null) rows.push(['Posture', metrics.posture_score]);
    if (metrics.kinetic_chain_quality != null)
      rows.push(['Chaîne cinétique', metrics.kinetic_chain_quality]);
    return rows.map(([subject, value]) => ({
      subject,
      Vous: Math.round(num(value, 0)),
      'Niveau cible': 75,
    }));
  }, [metrics]);

  const strokeList = Array.isArray(stroke.identified_strokes) ? stroke.identified_strokes : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-blue-50">
      <PageHeader
        title="Résultats d'analyse"
        subtitle="Votre performance au tennis de table"
        right={
          <div className="flex items-center gap-3">
            <Badge className="bg-emerald-100 text-emerald-800">
              <CheckCircle className="w-3 h-3 mr-1" />
              Analysé avec succès
            </Badge>
            <Button variant="outline" size="sm" onClick={onReset}>
              <RotateCcw className="w-4 h-4 mr-1" />
              Nouvelle analyse
            </Button>
          </div>
        }
      />

      <div className="container mx-auto px-6 py-8">
        <Tabs defaultValue="match-compilation" className="space-y-8">
          <TabsList className="grid w-full grid-cols-3 md:grid-cols-6 bg-white shadow-sm">
            <TabsTrigger value="match-compilation" className="flex items-center space-x-2">
              <Video className="w-4 h-4" />
              <span>Match Compilé</span>
            </TabsTrigger>
            <TabsTrigger value="strengths" className="flex items-center space-x-2">
              <TrendingUp className="w-4 h-4" />
              <span>Points Forts</span>
            </TabsTrigger>
            <TabsTrigger value="weaknesses" className="flex items-center space-x-2">
              <Target className="w-4 h-4" />
              <span>Points Faibles</span>
            </TabsTrigger>
            <TabsTrigger value="best-rallies" className="flex items-center space-x-2">
              <Trophy className="w-4 h-4" />
              <span>Meilleurs Échanges</span>
            </TabsTrigger>
            <TabsTrigger value="ball-impacts" className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4" />
              <span>Impacts Balle & Placement</span>
            </TabsTrigger>
            <TabsTrigger value="pose-analysis" className="flex items-center space-x-2">
              <Activity className="w-4 h-4" />
              <span>Coach IA Pose</span>
            </TabsTrigger>
          </TabsList>

          {/* ---------------- Match Compilé ---------------- */}
          <TabsContent value="match-compilation" className="space-y-8">
            {compilations.auto_edit && (
              <VideoCard
                title="Montage Auto — Échanges sans temps morts"
                badge="Échanges détectés par IA"
                description="Compilation des échanges réellement détectés par le suivi de balle"
                videoType="auto_edit"
                compilations={compilations}
                analysisId={analysisId}
                iconColor="text-blue-500"
              />
            )}
            {compilations.placement_overlay && (
              <VideoCard
                title="Placement des coups — incrustation"
                badge="Rebonds incrustés"
                description="Chaque rebond détecté est incrusté dans la vidéo (couleur = type de coup estimé)"
                videoType="placement_overlay"
                compilations={compilations}
                analysisId={analysisId}
                iconColor="text-purple-500"
              />
            )}
            <VideoCard
              title="Vidéo Compilée du Match"
              badge="Temps morts supprimés"
              description={`Analyse de ${formatDuration(videoInfo.duration_seconds)} de vidéo${videoInfo.resolution ? ` • ${videoInfo.resolution}` : ''}`}
              videoType="match_compilation"
              compilations={compilations}
              analysisId={analysisId}
              iconColor="text-emerald-500"
            />

            {/* Real rally / event statistics */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between flex-wrap gap-2">
                    <span>Statistiques des Échanges</span>
                    <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs font-normal">
                      {[
                        ['you', 'Vous'],
                        ['opponent', 'Adversaire'],
                      ].map(([key, label]) => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => setStatsView(key)}
                          className={`px-3 py-1.5 transition-colors ${
                            statsView === key
                              ? 'bg-emerald-500 text-white'
                              : 'bg-white text-gray-600 hover:bg-gray-50'
                          }`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {statsView === 'you' ? (
                    <>
                      <div className="h-64 mb-4">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={[
                              {
                                name: 'Longueur moyenne',
                                Coups: Number(num(rally.average_rally_length, 0).toFixed(1)),
                              },
                              {
                                name: 'Services détectés',
                                Coups: num(events.serve, 0),
                              },
                              {
                                name: 'Rebonds détectés',
                                Coups: num(events.ball_bounce, 0),
                              },
                              {
                                name: 'Frappes détectées',
                                Coups: num(events.hit, 0),
                              },
                            ]}
                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                            <YAxis />
                            <Tooltip />
                            <Bar dataKey="Coups" fill="#10b981" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <StatTile
                          value={num(rally.average_rally_length, 0).toFixed(1)}
                          label="Coups par échange (moy.)"
                        />
                        <StatTile
                          value={num(rally.total_serves, 0)}
                          label="Services détectés"
                          colorClass="text-blue-600"
                          bgClass="bg-blue-50"
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <p className="text-xs text-gray-500 mb-3">
                        Le suivi ne distingue pas encore les deux joueurs : les chiffres adverses
                        sont déduits de la répartition des impacts par moitié de table (camp estimé
                        selon le côté déclaré à l'upload).
                      </p>
                      <div className="h-64 mb-4">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={[
                              {
                                name: 'Frappes adverses (impacts votre camp)',
                                Coups:
                                  (matchAnalysis?.placement?.heatmap_grid || []).length > 0
                                    ? matchAnalysis.placement.heatmap_grid.flat(2).reduce((a, b) => a + b, 0) -
                                      (matchAnalysis.placement.heatmap_grid[0] || []).flat().reduce((a, b) => a + b, 0)
                                    : 0,
                              },
                              {
                                name: 'Impacts camp adverse (vos frappes)',
                                Coups: (matchAnalysis?.placement?.heatmap_grid?.[0] || [])
                                  .flat()
                                  .reduce((a, b) => a + b, 0),
                              },
                            ]}
                            layout="vertical"
                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis type="number" allowDecimals={false} />
                            <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 10 }} />
                            <Tooltip />
                            <Bar dataKey="Coups" fill="#ef4444" radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <StatTile
                          value={
                            matchAnalysis?.ball_speed?.max_speed_ms != null
                              ? `${matchAnalysis.ball_speed.max_speed_ms} m/s`
                              : 'N/A'
                          }
                          label="Vitesse max de balle"
                          colorClass="text-purple-600"
                          bgClass="bg-purple-50"
                        />
                        <StatTile
                          value={num(matchAnalysis?.rally_summary?.total_rallies, 0)}
                          label="Échanges contre adversaire"
                          colorClass="text-blue-600"
                          bgClass="bg-blue-50"
                        />
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Qualité de l'analyse</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium">Score global</span>
                        <span className="text-2xl font-bold text-emerald-600">
                          {pct(metrics.overall_score)}
                        </span>
                      </div>
                      <Progress value={num(metrics.overall_score, 0)} className="h-2" />
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium">Consistance technique</span>
                        <span className="text-2xl font-bold text-blue-600">
                          {pct(metrics.technical_consistency)}
                        </span>
                      </div>
                      <Progress value={num(metrics.technical_consistency, 0)} className="h-2" />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <StatTile
                        value={metrics.ball_tracking_quality || 'N/A'}
                        label="Suivi de balle"
                        colorClass="text-purple-600"
                        bgClass="bg-purple-50"
                      />
                      <StatTile
                        value={pct(num(metrics.confidence ?? results?.confidence_score, 0) * 100)}
                        label="Confiance détection"
                        colorClass="text-orange-600"
                        bgClass="bg-orange-50"
                      />
                    </div>
                    {videoInfo.resolution && (
                      <p className="text-xs text-gray-500 text-center">
                        Vidéo : {videoInfo.resolution}
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Real score progression (estimation) */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 flex-wrap">
                  <span>Progression du Score au Cours du Match</span>
                  <Badge variant="outline" className="text-amber-600 border-amber-300 bg-amber-50">
                    Estimation
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-gray-500 mb-4">
                  {scoring.attribution_quality === 'par_échange' ? (
                    <>
                      Score <strong>reconstruit échange par échange</strong> à partir du dernier
                      rebond détecté de chaque échange ({' '}
                      {num(scoring.points_attributed, 0)}/{num(scoring.points_total_detected, 0)}{' '}
                      points attribués). Restez prudent : la détection reste imparfaite.
                    </>
                  ) : (
                    <>
                      La vidéo ne permet pas de savoir qui marque chaque point (les joueurs ne sont
                      pas identifiés) : ce score est une <strong>estimation</strong> basée sur les{' '}
                      {num(matchStats.detected_rallies, num(rally.total_serves, 0))} échanges
                      réellement détectés, répartis selon la qualité de détection. Utilisez le
                      calibrage de table à l'upload pour une attribution par échange.
                    </>
                  )}
                </p>
                <div className="h-64 mb-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={scoreData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="point"
                        label={{ value: 'Points joués (est.)', position: 'insideBottom', offset: -2, fontSize: 11 }}
                      />
                      <YAxis allowDecimals={false} />
                      <Tooltip
                        labelFormatter={(label) => `Après le point ${label} (estimation)`}
                        formatter={(value, name) => [
                          value,
                          name === 'player1' ? 'Vous (est.)' : 'Adversaire (est.)',
                        ]}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="player1"
                        stroke="#10b981"
                        strokeWidth={3}
                        name="Vous (est.)"
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="player2"
                        stroke="#ef4444"
                        strokeWidth={3}
                        name="Adversaire (est.)"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-gradient-to-r from-emerald-50 to-blue-50 rounded-lg p-6">
                  <div className="grid grid-cols-2 gap-8 mb-6">
                    <div className="text-center">
                      <div className="text-4xl font-bold text-emerald-600 mb-2">
                        {num(finalScore.player1, 0)}
                      </div>
                      <div className="text-lg font-semibold">Vous</div>
                      <div className="text-sm text-gray-600">
                        {won ? 'Victoire (est.)' : 'Défaite (est.)'}
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-4xl font-bold text-red-500 mb-2">
                        {num(finalScore.player2, 0)}
                      </div>
                      <div className="text-lg font-semibold">Adversaire</div>
                      <div className="text-sm text-gray-600">
                        {won ? 'Défaite (est.)' : 'Victoire (est.)'}
                      </div>
                    </div>
                  </div>

                  <div className="bg-white rounded-lg p-4">
                    <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                      <TrendingUp className="w-4 h-4 mr-2 text-emerald-500" />
                      Lecture du match
                    </h4>
                    <p className="text-sm text-gray-600">
                      Score <strong>estimé</strong> à partir des {num(matchStats.detected_rallies, 0)}{' '}
                      échanges détectés dans la vidéo — un échange détecté compte pour un point.
                      Longueur moyenne d'échange : {num(rally.average_rally_length, 0).toFixed(1)}{' '}
                      coups
                      {num(matchStats.longest_rally, 0) > 0
                        ? `, plus long échange : ${num(matchStats.longest_rally, 0)} coups`
                        : ''}
                      . Les {num(events.serve, 0)} services détectés correspondent aux débuts
                      d'échange identifiés par le moteur ; chaque échange ne compte qu'une fois,
                      c'est pourquoi ce nombre peut être inférieur au nombre de points. Pour un
                      score exact, saisissez-le manuellement après le match (fonction à venir).
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Bilan */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Award className="w-5 h-5 text-yellow-500" />
                  <span>Bilan du Match</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-yellow-50 to-emerald-50 rounded-lg p-6">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">
                    Résumé de la Performance
                  </h4>

                  <div className="grid md:grid-cols-3 gap-4 mb-6">
                    <StatTile
                      value={won ? 'Victoire (est.)' : 'Défaite (est.)'}
                      label="Résultat final (score estimé)"
                      colorClass={won ? 'text-emerald-600' : 'text-red-600'}
                      bgClass="bg-white"
                    />
                    <StatTile
                      value={pct(metrics.overall_score)}
                      label="Performance globale"
                      colorClass="text-blue-600"
                      bgClass="bg-white"
                    />
                    <StatTile
                      value={formatDuration(videoInfo.duration_seconds)}
                      label="Durée de la vidéo"
                      colorClass="text-purple-600"
                      bgClass="bg-white"
                    />
                  </div>

                  <div className="space-y-3">
                    <p className="text-gray-700 leading-relaxed">
                      <strong>Consistance technique : {pct(metrics.technical_consistency)}</strong>{' '}
                      • Positionnement tactique : {pct(metrics.positioning_score)} • Précision /
                      variété : {pct(metrics.timing_accuracy)}.
                    </p>
                    {stroke.stroke_consistency && (
                      <p className="text-gray-700 leading-relaxed">
                        <strong>Analyse des coups :</strong> {stroke.stroke_consistency} •{' '}
                        {stroke.power_vs_control || 'Équilibre puissance / contrôle non évalué'}.
                      </p>
                    )}
                    {stroke.technique_quality && (
                      <p className="text-gray-700 leading-relaxed">
                        <strong>Qualité technique estimée :</strong> {stroke.technique_quality}/10.
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ---------------- Points Forts ---------------- */}
          <TabsContent value="strengths" className="space-y-8">
            <VideoCard
              title="Vidéo de vos Points Forts"
              badge="Meilleurs moments"
              videoType="strengths"
              compilations={compilations}
              analysisId={analysisId}
              iconColor="text-emerald-500"
            />

            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Performance Radar</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarData}>
                        <PolarGrid />
                        <PolarAngleAxis dataKey="subject" />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} />
                        <Radar
                          name="Vous"
                          dataKey="Vous"
                          stroke="#10b981"
                          fill="#10b981"
                          fillOpacity={0.3}
                        />
                        <Radar
                          name="Niveau cible"
                          dataKey="Niveau cible"
                          stroke="#94a3b8"
                          fill="#94a3b8"
                          fillOpacity={0.1}
                        />
                        <Legend />
                        <Tooltip />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="mt-4 p-4 bg-emerald-50 rounded-lg">
                    <h4 className="font-semibold text-emerald-800 mb-2">Lecture du radar</h4>
                    <p className="text-sm text-emerald-700">
                      Vos scores au-dessus du niveau cible (75) représentent vos points forts
                      actuels. Travaillez en priorité les axes en dessous de ce seuil.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Analyse Technique par l'IA</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {strokeList.length > 0 && (
                      <div className="bg-blue-50 rounded-lg p-4">
                        <h4 className="font-semibold text-blue-800 mb-2">Coups identifiés</h4>
                        <div className="flex flex-wrap gap-2">
                          {strokeList.map((s, i) => (
                            <Badge key={i} variant="secondary" className="capitalize">
                              {s}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {Array.isArray(stroke.strengths) && stroke.strengths.length > 0 && (
                      <div className="bg-emerald-50 rounded-lg p-4">
                        <h4 className="font-semibold text-emerald-800 mb-3">Points forts détectés</h4>
                        <div className="space-y-3">
                          {stroke.strengths.map((s, i) => (
                            <p key={i} className="text-sm text-gray-700 leading-relaxed flex items-start">
                              <CheckCircle className="w-4 h-4 mr-2 text-green-500 mt-0.5 shrink-0" />
                              <span>{s}</span>
                            </p>
                          ))}
                        </div>
                      </div>
                    )}

                    {positioning.tactical_positioning && (
                      <div className="bg-purple-50 rounded-lg p-4">
                        <h4 className="font-semibold text-purple-800 mb-2">Positionnement</h4>
                        <p className="text-sm text-gray-700">{positioning.tactical_positioning}</p>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                      <StatTile
                        value={pct(metrics.technical_consistency)}
                        label="Consistance technique"
                      />
                      <StatTile
                        value={pct(metrics.positioning_score)}
                        label="Positionnement tactique"
                        colorClass="text-purple-600"
                        bgClass="bg-purple-50"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Key strengths summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Star className="w-5 h-5 text-yellow-500" />
                  <span>Ce que vous avez fait de bien</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-white rounded-lg p-4 border-l-4 border-emerald-500">
                    <h4 className="font-semibold text-emerald-800 mb-2">Technique</h4>
                    <p className="text-sm text-gray-700">
                      {pct(metrics.technical_consistency)} de consistance technique sur l'ensemble
                      de la vidéo analysée.
                    </p>
                  </div>
                  <div className="bg-white rounded-lg p-4 border-l-4 border-blue-500">
                    <h4 className="font-semibold text-blue-800 mb-2">Tactique</h4>
                    <p className="text-sm text-gray-700">
                      {pct(metrics.positioning_score)} de score de positionnement, basé sur la
                      lecture du jeu détectée par l'IA.
                    </p>
                  </div>
                  <div className="bg-white rounded-lg p-4 border-l-4 border-purple-500">
                    <h4 className="font-semibold text-purple-800 mb-2">Précision</h4>
                    <p className="text-sm text-gray-700">
                      {pct(metrics.timing_accuracy)} de précision / variété dans l'exécution de vos
                      coups.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ---------------- Points Faibles ---------------- */}
          <TabsContent value="weaknesses" className="space-y-8">
            <VideoCard
              title="Vidéo de vos Points à Améliorer"
              badge="Zones d'amélioration"
              videoType="weaknesses"
              compilations={compilations}
              analysisId={analysisId}
              iconColor="text-orange-500"
            />

            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Target className="w-5 h-5 text-orange-500" />
                    <span>Axes d'amélioration identifiés</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {improvementAreas.length > 0 ? (
                    <div className="space-y-3">
                      {improvementAreas.map((area, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-3 bg-orange-50 rounded-lg"
                        >
                          <span className="text-sm font-medium text-gray-800">{area}</span>
                          <AlertCircle className="w-4 h-4 text-orange-500 shrink-0" />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm">
                      Aucun axe d'amélioration spécifique identifié.
                    </p>
                  )}

                  {Array.isArray(stroke.weaknesses) && stroke.weaknesses.length > 0 && (
                    <div className="mt-6">
                      <Separator className="mb-6" />
                      <h4 className="font-semibold mb-3">Observations techniques</h4>
                      <div className="space-y-3">
                        {stroke.weaknesses.map((w, i) => (
                          <p key={i} className="text-sm text-gray-700 leading-relaxed flex items-start">
                            <Target className="w-4 h-4 mr-2 text-orange-500 mt-0.5 shrink-0" />
                            <span>{w}</span>
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <TrendingUp className="w-5 h-5 text-blue-500" />
                    <span>Recommandations du Coach IA</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {recommendations.length > 0 ? (
                    <ul className="space-y-3">
                      {recommendations.map((rec, i) => (
                        <li
                          key={i}
                          className="flex items-start p-3 bg-blue-50 rounded-lg text-sm text-gray-700"
                        >
                          <ArrowRight className="w-4 h-4 mr-2 text-blue-500 mt-0.5 shrink-0" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-gray-500 text-sm">Aucune recommandation disponible.</p>
                  )}

                  {num(matchStats.unforced_errors, 0) > 0 && (
                    <div className="mt-6">
                      <Separator className="mb-6" />
                      <div className="grid grid-cols-2 gap-3">
                        <StatTile
                          value={num(matchStats.unforced_errors, 0)}
                          label="Fautes directes estimées"
                          colorClass="text-red-600"
                          bgClass="bg-red-50"
                        />
                        <StatTile
                          value={num(matchStats.aces_served, 0)}
                          label="Services gagnants estimés"
                          colorClass="text-yellow-600"
                          bgClass="bg-yellow-50"
                        />
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* ---------------- Meilleurs Échanges ---------------- */}
          <TabsContent value="best-rallies" className="space-y-8">
            <VideoCard
              title="Vidéo des Meilleurs Échanges"
              badge="Highlights du match"
              videoType="best_rallies"
              compilations={compilations}
              analysisId={analysisId}
              iconColor="text-yellow-500"
            />

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatTile
                value={num(matchStats.longest_rally, 0) || num(rally.average_rally_length, 0).toFixed(1)}
                label={num(matchStats.longest_rally, 0) > 0 ? 'Plus long échange (coups)' : 'Échange moyen (coups)'}
              />
              <StatTile
                value={num(rally.average_rally_length, 0).toFixed(1)}
                label="Coups par échange (moy.)"
                colorClass="text-blue-600"
                bgClass="bg-blue-50"
              />
              <StatTile
                value={num(rally.total_bounces, 0)}
                label="Rebonds détectés"
                colorClass="text-purple-600"
                bgClass="bg-purple-50"
              />
              <StatTile
                value={num(rally.max_ball_speed, 0) || 'N/A'}
                label="Vitesse balle max (px/frame)"
                colorClass="text-orange-600"
                bgClass="bg-orange-50"
              />
            </div>

            {(() => {
              const moments = [];
              const km = matchAnalysis?.key_moments || {};
              if (km.longest_rally) {
                moments.push({
                  label: 'Plus long échange',
                  detail: `${km.longest_rally.stroke_count} coups`,
                  t: km.longest_rally.start_time,
                });
              }
              if (km.fastest_frame_speed_ms) {
                moments.push({
                  label: 'Frappe la plus rapide',
                  detail: `${km.fastest_frame_speed_ms} m/s`,
                });
              }
              (matchAnalysis?.rallies || [])
                .filter((r) => (r.stroke_count || 0) >= 8)
                .slice(0, 5)
                .forEach((r, i) =>
                  moments.push({
                    label: `Échange long ${i + 1}`,
                    detail: `${r.stroke_count} coups`,
                    t: r.start_time,
                  })
                );
              if (moments.length === 0) return null;
              return (
                <Card>
                  <CardHeader>
                    <CardTitle>Moments Clés — à revoir en vidéo</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-gray-500 mb-4">
                      Chaque moment clé est ancré sur la compilation des échanges détectés :
                      cliquez sur « Voir » pour lancer la lecture au bon endroit.
                    </p>
                    <div className="grid md:grid-cols-2 gap-3">
                      {moments.map((m, i) => (
                        <div
                          key={`moment-${i}`}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                        >
                          <div>
                            <div className="text-sm font-medium text-gray-800">{m.label}</div>
                            <div className="text-xs text-gray-500">
                              {m.detail}
                              {m.t != null ? ` • ${formatDuration(m.t)}` : ''}
                            </div>
                          </div>
                          {m.t != null && compilations.auto_edit && (
                            <button
                              type="button"
                              onClick={() => setSelectedMoment(m.t)}
                              className="px-3 py-1.5 text-xs rounded-md bg-emerald-500 text-white hover:bg-emerald-600 transition-colors"
                            >
                              Voir
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    {selectedMoment != null && compilations.auto_edit && (
                      <div className="mt-4">
                        <video
                          key={selectedMoment}
                          src={`${getVideoUrl(analysisId, 'auto_edit')}#t=${selectedMoment}`}
                          controls
                          autoPlay
                          className="w-full rounded-lg border border-gray-200"
                        />
                        <p className="text-xs text-gray-400 mt-2 text-center">
                          Lecture depuis {formatDuration(selectedMoment)} dans la compilation.
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })()}

            <Card>
              <CardHeader>
                <CardTitle>Événements détectés — de quoi parle-t-on ?</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-1">Service</h4>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      Début d'un échange : la balle est lancée puis frappée vers la table. Le
                      moteur identifie un service quand le premier impact d'un échange est suivi
                      d'un passage au-dessus du filet.
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-1">Rebond</h4>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      Contact de la balle avec la table : la trajectoire verticale s'inverse
                      (descente puis remontée). Chaque rebond incrusté dans la vidéo correspond à
                      ce point d'inversion, projeté sur le gabarit de la table.
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-1">Frappes</h4>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      Traversées de la zone de jeu estimées comme des coups de raquette. Le nombre
                      de frappes d'un échange détermine sa longueur (coups par échange).
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Analyse des Échanges</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={[
                        { name: 'Services', value: num(events.serve, 0) },
                        { name: 'Rebonds', value: num(events.ball_bounce, 0) },
                        { name: 'Frappes', value: num(events.hit, 0) },
                      ]}
                      layout="vertical"
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" allowDecimals={false} />
                      <YAxis type="category" dataKey="name" width={80} />
                      <Tooltip />
                      <Bar dataKey="value" name="Événements" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-sm text-gray-600 mt-4 text-center">
                  Volume d'événements détectés par l'IA au cours du match — base des compilations
                  de meilleurs échanges.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ---------------- Impacts Balle & Placement ---------------- */}
          <TabsContent value="ball-impacts" className="space-y-8">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Target className="w-5 h-5 text-blue-500" />
                  <span>Carte de placement des coups (rebonds réellement détectés)</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(matchAnalysis?.bounces || []).length > 0 ? (
                  <>
                    <div className="flex justify-center">
                      <svg
                        width="600"
                        height="334"
                        viewBox="-10 -10 294 172.5"
                        className="rounded"
                        role="img"
                        aria-label="Placement réel des rebonds détectés sur la table"
                      >
                        {/* Table ITTF 2,74 x 1,525 m — coordonnées : x longueur (-1,37 à 1,37), y largeur (-0,7625 à 0,7625) */}
                        <rect x="0" y="0" width="274" height="152.5" fill="#1e4d2b" stroke="#111" strokeWidth="1.5" rx="2" />
                        {/* Filet (au milieu de la longueur) */}
                        <line x1="137" y1="0" x2="137" y2="152.5" stroke="#fff" strokeWidth="2" />
                        {/* Lignes médianes (simples / doubles) */}
                        <line x1="0" y1="76.25" x2="274" y2="76.25" stroke="#fff" strokeWidth="0.8" strokeDasharray="4,4" opacity="0.6" />
                        {/* Rebonds */}
                        {matchAnalysis.bounces.map((b, idx) => {
                          const sx = ((b.table_x + 1.37) / 2.74) * 274;
                          const sy = ((b.table_y + 0.7625) / 1.525) * 152.5;
                          const colorMap = {
                            topspin_coup_droit: '#f59e0b',
                            topspin_revers: '#3b82f6',
                            coup_droit: '#eab308',
                            revers: '#22c55e',
                            inconnu: '#e5e7eb',
                          };
                          const fill = colorMap[b.stroke_side] || colorMap.inconnu;
                          return (
                            <g key={`bounce-${idx}`}>
                              <circle cx={sx} cy={sy} r="4.5" fill={fill} opacity="0.9" stroke="#111" strokeWidth="0.5">
                                <title>
                                  {`Rebond à ${formatDuration(b.timestamp)} • ${b.stroke_side?.replace(/_/g, ' ') || 'inconnu'}${b.speed_ms ? ` • ${b.speed_ms} m/s` : ''}`}
                                </title>
                              </circle>
                            </g>
                          );
                        })}
                      </svg>
                    </div>

                    <div className="mt-6 flex flex-wrap justify-center gap-x-6 gap-y-2">
                      <div className="flex items-center space-x-2">
                        <div className="w-3.5 h-3.5 rounded-full" style={{ background: '#f59e0b' }}></div>
                        <span className="text-sm text-gray-700">Topspin en coup droit (est.)</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="w-3.5 h-3.5 rounded-full" style={{ background: '#3b82f6' }}></div>
                        <span className="text-sm text-gray-700">Topspin en revers (est.)</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="w-3.5 h-3.5 rounded-full" style={{ background: '#eab308' }}></div>
                        <span className="text-sm text-gray-700">Coup en coup droit (est.)</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="w-3.5 h-3.5 rounded-full" style={{ background: '#22c55e' }}></div>
                        <span className="text-sm text-gray-700">Coup en revers (est.)</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="w-3.5 h-3.5 rounded-full" style={{ background: '#e5e7eb' }}></div>
                        <span className="text-sm text-gray-700">Coup inconnu</span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-400 text-center mt-3">
                      Chaque point est un rebond détecté par le suivi de balle, projeté sur le
                      gabarit ITTF (2,74 × 1,525 m) via l'homographie de la table. Survolez un
                      point pour l'horodatage et la vitesse. Le type de coup (topspin, coup
                      droit / revers) est une estimation : incrusté dans la{' '}
                      <strong>vidéo « Placement des coups »</strong> de l'onglet Match Compilé.
                    </p>
                  </>
                ) : (
                  <div className="text-center py-10 text-gray-500">
                    <p className="mb-2">
                      Aucun rebond projeté sur la table pour cette analyse.
                    </p>
                    <p className="text-xs text-gray-400">
                      La table doit être entièrement visible et bien éclairée pour que
                      l'homographie soit calculée. {num(events.ball_bounce, 0)} rebonds ont quand
                      même été détectés (sans position sur la table).
                    </p>
                  </div>
                )}

                <div className="grid md:grid-cols-4 gap-4 mt-6">
                  <StatTile
                    value={num(matchAnalysis?.bounces?.length, 0)}
                    label="Rebonds sur table"
                    colorClass="text-blue-600"
                    bgClass="bg-blue-50"
                  />
                  <StatTile
                    value={num(events.serve, 0)}
                    label="Services détectés"
                    colorClass="text-emerald-600"
                  />
                  <StatTile
                    value={num(events.hit, 0)}
                    label="Frappes détectées"
                    colorClass="text-purple-600"
                    bgClass="bg-purple-50"
                  />
                  <StatTile
                    value={pct(num(results?.confidence_score, 0) * 100)}
                    label="Taux de détection balle"
                    colorClass="text-orange-600"
                    bgClass="bg-orange-50"
                  />
                </div>
              </CardContent>
            </Card>

            {matchAnalysis ? (
              <>
                {(matchAnalysis.player_stats && Object.keys(matchAnalysis.player_stats).length > 0) && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Activity className="w-5 h-5 text-emerald-500" />
                        <span>Rebonds par camp (gauche / droite de l'image)</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid md:grid-cols-2 gap-4">
                        {['gauche', 'droite'].map((side) => {
                          const s = matchAnalysis.player_stats[side] || {};
                          const isUser = (scoring.user_side || 'droite') === side;
                          return (
                            <div
                              key={side}
                              className={`p-4 rounded-lg border ${isUser ? 'border-emerald-300 bg-emerald-50' : 'border-gray-200 bg-gray-50'}`}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-semibold text-gray-800">
                                  Camp {side} {isUser ? '(vous)' : '(adversaire)'}
                                </span>
                                {results.players_analysis?.summary && (
                                  <Badge variant="secondary">
                                    {side === 'gauche'
                                      ? pct(num(results.players_analysis.summary.left_detection_ratio, 0) * 100)
                                      : pct(num(results.players_analysis.summary.right_detection_ratio, 0) * 100)}{' '}
                                    présence
                                  </Badge>
                                )}
                              </div>
                              <div className="grid grid-cols-2 gap-3">
                                <StatTile value={num(s.bounces, 0)} label="Rebonds subis" />
                                <StatTile
                                  value={s.avg_speed_ms != null ? `${s.avg_speed_ms} m/s` : 'N/A'}
                                  label="Vitesse moy. des balles reçues"
                                  colorClass="text-purple-600"
                                  bgClass="bg-white"
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <p className="text-xs text-gray-400 mt-3">
                        « Votre côté » est déduit du choix fait à l'upload. La présence (%) vient du
                        suivi de joueurs YOLO — sans modèle, les camps restent estimés par la table
                        seule.
                      </p>
                    </CardContent>
                  </Card>
                )}
                <div className="grid md:grid-cols-4 gap-4">
                  <StatTile
                    value={num(matchAnalysis.rally_summary?.total_rallies, 0)}
                    label="Échanges détectés"
                    colorClass="text-blue-600"
                    bgClass="bg-blue-50"
                  />
                  <StatTile
                    value={num(matchAnalysis.rally_summary?.average_strokes, 0)}
                    label="Coups / échange (moy.)"
                    colorClass="text-green-600"
                    bgClass="bg-green-50"
                  />
                  <StatTile
                    value={
                      matchAnalysis.ball_speed?.max_speed_ms != null
                        ? `${matchAnalysis.ball_speed.max_speed_ms} m/s`
                        : num(matchAnalysis.ball_speed?.max_speed_pixels_per_frame, 0)
                    }
                    label="Vitesse max de balle"
                    colorClass="text-purple-600"
                    bgClass="bg-purple-50"
                  />
                  <StatTile
                    value={num(matchAnalysis.bounces?.length, 0)}
                    label="Rebonds sur table"
                    colorClass="text-orange-600"
                    bgClass="bg-orange-50"
                  />
                </div>

                {matchAnalysis.placement?.available && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Target className="w-5 h-5 text-blue-500" />
                        <span>Heatmap par zones de la table</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap justify-center gap-8">
                        {matchAnalysis.placement.heatmap_grid.map((half, h) => (
                          <div key={`half-${h}`} className="text-center">
                            <svg width="240" height="160" viewBox="0 0 240 160" className="border border-gray-300 rounded">
                              <rect x="0" y="0" width="240" height="160" fill="#2563eb" opacity="0.08" />
                              {half.map((row, l) =>
                                row.map((count, w) => {
                                  const maxCount = Math.max(1, ...matchAnalysis.placement.heatmap_grid.flat(2));
                                  const intensity = count / maxCount;
                                  return (
                                    <rect
                                      key={`z-${h}-${l}-${w}`}
                                      x={l * 80}
                                      y={w * 53.3}
                                      width="80"
                                      height="53.3"
                                      fill={count > 0 ? '#3b82f6' : 'transparent'}
                                      opacity={count > 0 ? 0.15 + 0.75 * intensity : 0}
                                      stroke="#fff"
                                      strokeWidth="1"
                                    />
                                  );
                                })
                              )}
                              <line x1="0" y1="80" x2="240" y2="80" stroke="#fff" strokeWidth="2" />
                            </svg>
                            <p className="text-sm text-gray-600 mt-2">
                              {h === 0 ? 'Moitié 1' : 'Moitié 2'} — colonnes : fond → près du filet
                            </p>
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 flex flex-wrap justify-center gap-2">
                        {Object.entries(matchAnalysis.placement.zones || {}).map(
                          ([zone, count]) => (
                            <Badge key={zone} variant="secondary">
                              {zone} : {count}
                            </Badge>
                          )
                        )}
                      </div>
                      {!matchAnalysis.table_detected && (
                        <p className="text-xs text-gray-400 text-center mt-3">
                          Table non détectée : vitesse estimée en pixels, placement indisponible.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                )}

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <BarChart3 className="w-5 h-5 text-green-500" />
                      <span>Longueur des échanges</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="p-4 bg-gray-50 rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-800">
                          {num(matchAnalysis.rally_summary?.courts_1_3_coups, 0)}
                        </div>
                        <div className="text-sm text-gray-600">Échanges courts (1-3 coups)</div>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-800">
                          {num(matchAnalysis.rally_summary?.moyens_4_7_coups, 0)}
                        </div>
                        <div className="text-sm text-gray-600">Échanges moyens (4-7 coups)</div>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-800">
                          {num(matchAnalysis.rally_summary?.longs_8_plus, 0)}
                        </div>
                        <div className="text-sm text-gray-600">Échanges longs (8+ coups)</div>
                      </div>
                    </div>
                    {matchAnalysis.key_moments?.longest_rally && (
                      <p className="text-sm text-gray-600 mt-4">
                        Plus long échange : <strong>{matchAnalysis.key_moments.longest_rally.stroke_count} coups</strong> à{' '}
                        {formatDuration(matchAnalysis.key_moments.longest_rally.start_time)} — visible dans l'onglet
                        Meilleurs Échanges.
                      </p>
                    )}
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card>
                <CardContent className="py-10 text-center text-gray-500">
                  Aucune analyse de match disponible pour cette vidéo.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* ---------------- Coach IA Pose ---------------- */}
          <TabsContent value="pose-analysis" className="space-y-8">
            {compilations.pose_overlay && (
              <VideoCard
                title="Squelette superposé — vidéo compilée"
                badge="Pose incrustée"
                description="Le squelette du joueur analysé est incrusté en continu sur la compilation des échanges"
                videoType="pose_overlay"
                compilations={compilations}
                analysisId={analysisId}
                iconColor="text-green-500"
              />
            )}
            <PoseAnalysis results={results} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [analysisId, setAnalysisId] = useState(null);

  return (
    <div className="App min-h-screen bg-gray-50">
      {analysisId ? (
        <AnalysisPage
          analysisId={analysisId}
          onReset={() => setAnalysisId(null)}
        />
      ) : (
        <HomePage onAnalysisStarted={setAnalysisId} />
      )}
    </div>
  );
}

export default App;
