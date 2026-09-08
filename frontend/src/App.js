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
const HomePage = ({ onAnalysisStarted }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [playerSide, setPlayerSide] = useState('droite');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

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
  const compilations = results?.video_compilations || {};
  const videoInfo = results?.video_info || {};
  const duration = Math.round(num(videoInfo.duration_seconds, 0));
  const analysisId = results?.analysis_id;

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

  // Deterministic ball impact layout on the table (top view)
  const ballImpacts = useMemo(() => {
    const bounces = Math.min(Math.round(num(events.ball_bounce, 0)), 24);
    return Array.from({ length: bounces }, (_, i) => {
      const isPlayer = i % 2 === 0;
      const x = 60 + (i % 4) * 85 + (isPlayer ? 25 : 0);
      const y = 20 + (isPlayer ? 115 : 40) + (i % 3) * 14;
      return {
        x: Math.min(372, x),
        y: Math.min(176, y),
        player: isPlayer ? 'you' : 'opponent',
      };
    });
  }, [events.ball_bounce]);

  const serviceImpacts = useMemo(() => {
    const serves = Math.min(Math.round(num(events.serve, 0)), 10);
    return Array.from({ length: serves }, (_, i) => {
      const isYou = i % 2 === 0;
      return {
        x: 20 + 360 * (0.3 + (i % 5) / 5 * 0.4),
        y: 20 + (isYou ? 160 * 0.8 : 160 * 0.2),
        player: isYou ? 'you' : 'opponent',
      };
    });
  }, [events.serve]);

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
          <TabsList className="grid w-full grid-cols-3 md:grid-cols-7 bg-white shadow-sm">
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
              <Target className="w-4 h-4" />
              <span>Impacts Balle</span>
            </TabsTrigger>
            <TabsTrigger value="match-analysis" className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4" />
              <span>Analyse de Match</span>
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
            <VideoCard
              title="Vidéo Compilée du Match"
              badge="Temps morts supprimés"
              description={`Analyse de ${duration}s de vidéo${videoInfo.resolution ? ` • ${videoInfo.resolution}` : ''}`}
              videoType="match_compilation"
              compilations={compilations}
              analysisId={analysisId}
              iconColor="text-emerald-500"
            />

            {/* Real rally / event statistics */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Statistiques des Échanges</CardTitle>
                </CardHeader>
                <CardContent>
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
                    {videoInfo.fps && (
                      <p className="text-xs text-gray-500 text-center">
                        Vidéo : {videoInfo.resolution || 'résolution inconnue'} •{' '}
                        {num(videoInfo.fps, 0)} fps • {num(videoInfo.frame_count, 0)} frames
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Real score progression */}
            <Card>
              <CardHeader>
                <CardTitle>Progression du Score au Cours du Match</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64 mb-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={scoreData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="point" />
                      <YAxis allowDecimals={false} />
                      <Tooltip
                        labelFormatter={(label) => `Point ${label}`}
                        formatter={(value, name) => [
                          value,
                          name === 'player1' ? 'Vous' : 'Adversaire',
                        ]}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="player1"
                        stroke="#10b981"
                        strokeWidth={3}
                        name="Votre score"
                      />
                      <Line
                        type="monotone"
                        dataKey="player2"
                        stroke="#ef4444"
                        strokeWidth={3}
                        name="Score adversaire"
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
                      <div className="text-sm text-gray-600">{won ? 'Victoire' : 'Défaite'}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-4xl font-bold text-red-500 mb-2">
                        {num(finalScore.player2, 0)}
                      </div>
                      <div className="text-lg font-semibold">Adversaire</div>
                      <div className="text-sm text-gray-600">{won ? 'Défaite' : 'Victoire'}</div>
                    </div>
                  </div>

                  <div className="bg-white rounded-lg p-4">
                    <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
                      <TrendingUp className="w-4 h-4 mr-2 text-emerald-500" />
                      Lecture du match
                    </h4>
                    <p className="text-sm text-gray-600">
                      Score final reconstitué automatiquement à partir des événements détectés
                      ({num(events.serve, 0)} services, {num(events.ball_bounce, 0)} rebonds).
                      Longueur moyenne d'échange : {num(rally.average_rally_length, 0).toFixed(1)}{' '}
                      coups{num(matchStats.longest_rally, 0) > 0 ? `, plus long échange : ${num(matchStats.longest_rally, 0)} coups` : ''}.
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
                      value={won ? 'Victoire' : 'Défaite'}
                      label="Résultat final"
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
                      value={`${duration}min`}
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
                        <h4 className="font-semibold text-emerald-800 mb-2">Points forts détectés</h4>
                        <ul className="space-y-2 text-sm text-gray-700">
                          {stroke.strengths.map((s, i) => (
                            <li key={i} className="flex items-start">
                              <CheckCircle className="w-4 h-4 mr-2 text-green-500 mt-0.5 shrink-0" />
                              {s}
                            </li>
                          ))}
                        </ul>
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
                      <ul className="space-y-2 text-sm text-gray-700">
                        {stroke.weaknesses.map((w, i) => (
                          <li key={i} className="flex items-start">
                            <Target className="w-4 h-4 mr-2 text-orange-500 mt-0.5 shrink-0" />
                            {w}
                          </li>
                        ))}
                      </ul>
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

            {Array.isArray(results?.highlights_timestamps) &&
              results.highlights_timestamps.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Moments Clés Détectés</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {results.highlights_timestamps.map((t, i) => (
                        <Badge key={i} variant="outline" className="text-gray-700">
                          {num(t, 0).toFixed(0)}s
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

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

          {/* ---------------- Impacts Balle ---------------- */}
          <TabsContent value="ball-impacts" className="space-y-8">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Target className="w-5 h-5 text-blue-500" />
                  <span>Visualisation des Impacts de Balle</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-white rounded-lg p-6 border-2 border-gray-200">
                  <h4 className="font-semibold text-gray-800 mb-4 text-center">
                    Table de Tennis de Table - Vue du dessus
                  </h4>

                  <div className="flex justify-center">
                    <svg
                      width="400"
                      height="200"
                      viewBox="0 0 400 200"
                      className="border border-gray-300 rounded"
                      role="img"
                      aria-label="Visualisation des impacts de balle sur la table"
                    >
                      <rect x="20" y="20" width="360" height="160" fill="#2d5016" stroke="#000" strokeWidth="2" />
                      <line x1="200" y1="20" x2="200" y2="180" stroke="#fff" strokeWidth="2" />
                      <line x1="20" y1="100" x2="380" y2="100" stroke="#000" strokeWidth="3" />
                      <text x="40" y="15" fontSize="12" fill="#000" fontWeight="bold">Adversaire</text>
                      <text x="330" y="195" fontSize="12" fill="#000" fontWeight="bold">Vous</text>
                      <line x1="20" y1="60" x2="380" y2="60" stroke="#fff" strokeWidth="1" strokeDasharray="5,5" opacity="0.5" />
                      <line x1="20" y1="140" x2="380" y2="140" stroke="#fff" strokeWidth="1" strokeDasharray="5,5" opacity="0.5" />

                      {ballImpacts.map((impact, idx) => (
                        <circle
                          key={`impact-${idx}`}
                          cx={impact.x}
                          cy={impact.y}
                          r="4"
                          fill={impact.player === 'you' ? '#3b82f6' : '#ef4444'}
                          opacity="0.8"
                        />
                      ))}

                      {serviceImpacts.map((service, idx) => (
                        <polygon
                          key={`service-${idx}`}
                          points={`${service.x - 5},${service.y + 5} ${service.x + 5},${service.y + 5} ${service.x},${service.y - 5}`}
                          fill="#10b981"
                          opacity="0.8"
                        />
                      ))}
                    </svg>
                  </div>

                  <div className="mt-6 flex justify-center space-x-8">
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
                      <span className="text-sm text-gray-700">Vos impacts</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 bg-red-500 rounded-full"></div>
                      <span className="text-sm text-gray-700">Impacts adversaire</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-0 h-0 border-l-2 border-r-2 border-b-4 border-l-transparent border-r-transparent border-b-green-500"></div>
                      <span className="text-sm text-gray-700">Services</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 text-center mt-3">
                    Répartition indicative reconstituée à partir des événements détectés
                    (l'ordre réel des impacts n'est pas encore suivi par l'analyse).
                  </p>
                </div>

                <div className="grid md:grid-cols-4 gap-4 mt-6">
                  <StatTile
                    value={num(events.ball_bounce, 0)}
                    label="Rebonds détectés"
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
          </TabsContent>

          {/* ---------------- Analyse de Match ---------------- */}
          <TabsContent value="match-analysis" className="space-y-8">
            {results.match_analysis ? (
              <>
                <div className="grid md:grid-cols-4 gap-4">
                  <StatTile
                    value={num(results.match_analysis.rally_summary?.total_rallies, 0)}
                    label="Échanges détectés"
                    colorClass="text-blue-600"
                    bgClass="bg-blue-50"
                  />
                  <StatTile
                    value={num(results.match_analysis.rally_summary?.average_strokes, 0)}
                    label="Coups / échange (moy.)"
                    colorClass="text-green-600"
                    bgClass="bg-green-50"
                  />
                  <StatTile
                    value={
                      results.match_analysis.ball_speed?.max_speed_ms != null
                        ? `${results.match_analysis.ball_speed.max_speed_ms} m/s`
                        : num(results.match_analysis.ball_speed?.max_speed_pixels_per_frame, 0)
                    }
                    label="Vitesse max de balle"
                    colorClass="text-purple-600"
                    bgClass="bg-purple-50"
                  />
                  <StatTile
                    value={num(results.match_analysis.bounces?.length, 0)}
                    label="Rebonds sur table"
                    colorClass="text-orange-600"
                    bgClass="bg-orange-50"
                  />
                </div>

                {results.match_analysis.placement?.available && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Target className="w-5 h-5 text-blue-500" />
                        <span>Placement de la balle sur la table</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap justify-center gap-8">
                        {results.match_analysis.placement.heatmap_grid.map((half, h) => (
                          <div key={`half-${h}`} className="text-center">
                            <svg width="240" height="160" viewBox="0 0 240 160" className="border border-gray-300 rounded">
                              <rect x="0" y="0" width="240" height="160" fill="#2563eb" opacity="0.08" />
                              {half.map((row, l) =>
                                row.map((count, w) => {
                                  const maxCount = Math.max(1, ...results.match_analysis.placement.heatmap_grid.flat(2));
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
                        {Object.entries(results.match_analysis.placement.zones || {}).map(
                          ([zone, count]) => (
                            <Badge key={zone} variant="secondary">
                              {zone} : {count}
                            </Badge>
                          )
                        )}
                      </div>
                      {!results.match_analysis.table_detected && (
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
                      <span>Phases et moments clés</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="p-4 bg-gray-50 rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-800">
                          {num(results.match_analysis.rally_summary?.courts_1_3_coups, 0)}
                        </div>
                        <div className="text-sm text-gray-600">Échanges courts (1-3 coups)</div>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-800">
                          {num(results.match_analysis.rally_summary?.moyens_4_7_coups, 0)}
                        </div>
                        <div className="text-sm text-gray-600">Échanges moyens (4-7 coups)</div>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-800">
                          {num(results.match_analysis.rally_summary?.longs_8_plus, 0)}
                        </div>
                        <div className="text-sm text-gray-600">Échanges longs (8+ coups)</div>
                      </div>
                    </div>
                    {results.match_analysis.key_moments?.longest_rally && (
                      <p className="text-sm text-gray-600 mt-4">
                        Plus long échange : <strong>{results.match_analysis.key_moments.longest_rally.stroke_count} coups</strong> à{' '}
                        {results.match_analysis.key_moments.longest_rally.start_time}s.
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
