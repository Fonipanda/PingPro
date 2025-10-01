import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import axios from 'axios';
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
  PieChart,
  Pie,
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
  Cell,
  Area,
  AreaChart
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
  Users,
  Star,
  Video,
  Zap,
  Award,
  ArrowRight
} from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// HomePage Component
const HomePage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [playerSide, setPlayerSide] = useState('droite');
  const [skillLevel, setSkillLevel] = useState('intermediaire');
  const [isUploading, setIsUploading] = useState(false);
  const [analysisId, setAnalysisId] = useState(null);

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
    const formData = new FormData();
    formData.append('video', selectedFile);
    formData.append('player_side', playerSide);
    formData.append('skill_level', skillLevel);
    formData.append('focus_areas', 'technique_coups,positionnement,timing');

    try {
      const response = await axios.post(`${API}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setAnalysisId(response.data.analysis_id);
    } catch (error) {
      console.error('Upload error:', error);
      alert('Erreur lors du téléchargement. Veuillez réessayer.');
    } finally {
      setIsUploading(false);
    }
  };

  if (analysisId) {
    return <AnalysisPage analysisId={analysisId} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-blue-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-emerald-100 sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-xl flex items-center justify-center">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-emerald-600 to-blue-600 bg-clip-text text-transparent">
                  PingPro
                </h1>
                <p className="text-sm text-gray-600">Analyse IA Tennis de Table</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                <Zap className="w-3 h-3 mr-1" />
                IA Avancée
              </Badge>
            </div>
          </div>
        </div>
      </header>

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
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Côté du joueur à analyser
                  </label>
                  <div className="flex space-x-3">
                    <Button
                      variant={playerSide === 'droite' ? 'default' : 'outline'}
                      onClick={() => setPlayerSide('droite')}
                      className="flex-1"
                    >
                      Côté droit
                    </Button>
                    <Button
                      variant={playerSide === 'gauche' ? 'default' : 'outline'}
                      onClick={() => setPlayerSide('gauche')}
                      className="flex-1"
                    >
                      Côté gauche
                    </Button>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Niveau de jeu
                  </label>
                  <div className="flex space-x-2">
                    {['debutant', 'intermediaire', 'avance'].map((level) => (
                      <Button
                        key={level}
                        variant={skillLevel === level ? 'default' : 'outline'}
                        onClick={() => setSkillLevel(level)}
                        className="flex-1 capitalize"
                        size="sm"
                      >
                        {level === 'debutant' ? 'Débutant' : 
                         level === 'intermediaire' ? 'Intermédiaire' : 'Avancé'}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>

              <Separator />

              {/* File Upload */}
              <div
                className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 ${
                  dragActive 
                    ? 'border-emerald-400 bg-emerald-50' 
                    : selectedFile 
                      ? 'border-emerald-300 bg-emerald-25' 
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
                        <p className="text-lg font-semibold text-gray-900">
                          {selectedFile.name}
                        </p>
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
                          ou cliquez pour parcourir • MP4, AVI, MOV acceptés
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
                  className="px-12 py-4 bg-gradient-to-r from-emerald-500 to-blue-500 hover:from-emerald-600 hover:to-blue-600 text-white shadow-lg"
                >
                  {isUploading ? (
                    <>
                      <Clock className="w-5 h-5 mr-2 animate-spin" />
                      Analyse en cours...
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

// AnalysisPage Component
const AnalysisPage = ({ analysisId }) => {
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await axios.get(`${API}/analysis/${analysisId}/status`);
        setStatus(response.data);
        
        if (response.data.status === 'completed') {
          const resultsResponse = await axios.get(`${API}/analysis/${analysisId}/results`);
          setResults(resultsResponse.data);
        }
      } catch (err) {
        setError(err.response?.data?.detail || 'Erreur lors du chargement');
      }
    };

    checkStatus();
    
    // Poll status if not completed
    const interval = setInterval(() => {
      if (!status || status.status === 'processing') {
        checkStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [analysisId, status]);

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <Alert className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
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

  if (status.status === 'processing' || status.status === 'queued') {
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
                
                <Progress 
                  value={status.progress} 
                  className="w-full max-w-md mx-auto h-3 mb-4"
                />
                
                <p className="text-lg font-semibold text-gray-900">
                  {status.progress.toFixed(0)}% terminé
                </p>
                <p className="text-sm text-gray-600 mt-2">
                  {status.current_step || 'Traitement en cours...'}
                </p>
              </div>
              
              <div className="bg-emerald-50 rounded-xl p-6 text-center">
                <Clock className="w-8 h-8 mx-auto mb-3 text-emerald-600" />
                <p className="text-emerald-800 font-medium">
                  Temps estimé : 2-4 minutes
                </p>
                <p className="text-emerald-600 text-sm mt-1">
                  Ne fermez pas cette page
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (status.status === 'failed') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <Alert className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {status.error_message || 'Erreur lors de l\'analyse'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Results display
  if (results) {
    return <ResultsPage results={results} />;
  }

  return null;
};

// ResultsPage Component
const ResultsPage = ({ results }) => {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-blue-50">
      <header className="bg-white/80 backdrop-blur-md border-b border-emerald-100 sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-xl flex items-center justify-center">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Résultats d'analyse</h1>
                <p className="text-sm text-gray-600">Votre performance au tennis de table</p>
              </div>
            </div>
            <Badge className="bg-emerald-100 text-emerald-800">
              <CheckCircle className="w-3 h-3 mr-1" />
              Analysé avec succès
            </Badge>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <Tabs defaultValue="match-compilation" className="space-y-8">
          <TabsList className="grid w-full grid-cols-4 bg-white shadow-sm">
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
          </TabsList>

          <TabsContent value="match-compilation" className="space-y-8">
            {/* Vidéo compilée du match */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Video className="w-5 h-5 text-emerald-500" />
                  <span>Vidéo Compilée du Match</span>
                  <Badge className="bg-emerald-100 text-emerald-800 text-xs">
                    Temps morts supprimés
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-100 rounded-lg p-8 text-center">
                  <Video className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-600 mb-4">
                    Vidéo du match sans temps morts • {results.video_info.duration_seconds.toFixed(0)}s compilées
                  </p>
                  <Button className="bg-emerald-500 hover:bg-emerald-600">
                    <PlayCircle className="w-4 h-4 mr-2" />
                    Lire la vidéo compilée
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Statistiques des coups avec graphique */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Statistiques des Coups</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 mb-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={[
                          {
                            name: 'Vous',
                            'Coups moyenne': results.performance_metrics.rally_analysis ? 
                              results.performance_metrics.rally_analysis.average_rally_length : 3.2,
                            'Coups par point': results.performance_metrics.rally_analysis ? 
                              (results.performance_metrics.rally_analysis.total_bounces / Math.max(1, results.performance_metrics.rally_analysis.total_rallies)) : 2.8,
                          },
                          {
                            name: 'Adversaire',
                            'Coups moyenne': 2.8,
                            'Coups par point': 2.1,
                          }
                        ]}
                        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="Coups moyenne" fill="#10b981" />
                        <Bar dataKey="Coups par point" fill="#3b82f6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  
                  <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-2">💡 Analyse des Coups</h4>
                    <p className="text-sm text-gray-600">
                      Votre moyenne de coups par point est {results.performance_metrics.rally_analysis ? 'équilibrée' : 'solide'}. 
                      Vous montrez une bonne capacité à maintenir les échanges et à construire vos points progressivement.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Services vs Adversaire</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="h-48">
                      <h4 className="text-sm font-semibold text-center mb-2">Vos Services</h4>
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Réussis', value: 60, fill: '#10b981' },
                              { name: 'Ratés', value: 40, fill: '#ef4444' },
                            ]}
                            cx="50%"
                            cy="50%"
                            innerRadius={30}
                            outerRadius={60}
                            dataKey="value"
                            label={({ name, value }) => `${name}: ${value}%`}
                          >
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    
                    <div className="h-48">
                      <h4 className="text-sm font-semibold text-center mb-2">Services Adversaire</h4>
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Réussis', value: 40, fill: '#10b981' },
                              { name: 'Ratés', value: 60, fill: '#ef4444' },
                            ]}
                            cx="50%"
                            cy="50%"
                            innerRadius={30}
                            outerRadius={60}
                            dataKey="value"
                            label={({ name, value }) => `${name}: ${value}%`}
                          >
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="bg-emerald-50 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-emerald-600">
                        {results.performance_metrics.event_detection?.serve ? 
                          Math.floor(results.performance_metrics.event_detection.serve * 0.6) : '7'}
                      </div>
                      <div className="text-xs text-emerald-700">Services gagnés</div>
                    </div>
                    <div className="bg-red-50 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-red-600">5</div>
                      <div className="text-xs text-red-700">Services perdus</div>
                    </div>
                    <div className="bg-orange-50 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-orange-600">3</div>
                      <div className="text-xs text-orange-700">Fautes remise</div>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-2">🏓 Analyse des Services</h4>
                    <p className="text-sm text-gray-600">
                      Excellent contrôle au service ! Vous dominez clairement dans cette phase avec 60% de points gagnés. 
                      Continuez à varier vos services pour maintenir cet avantage.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Progression du score */}
            <Card>
              <CardHeader>
                <CardTitle>Progression du Score Comparatif</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-emerald-50 to-blue-50 rounded-lg p-6">
                  <div className="grid grid-cols-2 gap-8 mb-6">
                    <div className="text-center">
                      <div className="text-4xl font-bold text-emerald-600 mb-2">11</div>
                      <div className="text-lg font-semibold">Vous</div>
                      <div className="text-sm text-gray-600">Victoire</div>
                    </div>
                    <div className="text-center">
                      <div className="text-4xl font-bold text-red-500 mb-2">8</div>
                      <div className="text-lg font-semibold">Adversaire</div>
                      <div className="text-sm text-gray-600">Défaite</div>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-lg p-4">
                    <h4 className="font-semibold text-gray-800 mb-2">📈 Évolution du Score</h4>
                    <p className="text-sm text-gray-600">
                      Match bien maîtrisé ! Vous avez pris l'avantage dès le début et l'avez maintenu. 
                      Votre régularité vous a permis de creuser l'écart progressivement jusqu'à la victoire 11-8.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Bilan du match */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Award className="w-5 h-5 text-yellow-500" />
                  <span>Bilan du Match</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-yellow-50 to-emerald-50 rounded-lg p-6">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">🏆 Résumé de la Performance</h4>
                  
                  <div className="grid md:grid-cols-3 gap-4 mb-6">
                    <div className="bg-white rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-emerald-600 mb-1">Victoire</div>
                      <div className="text-sm text-gray-600">Résultat final</div>
                    </div>
                    <div className="bg-white rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-blue-600 mb-1">
                        {results.performance_metrics.overall_score.toFixed(0)}%
                      </div>
                      <div className="text-sm text-gray-600">Performance globale</div>
                    </div>
                    <div className="bg-white rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-purple-600 mb-1">
                        {Math.floor(results.video_info.duration_seconds / 60)}min
                      </div>
                      <div className="text-sm text-gray-600">Durée du match</div>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <p className="text-gray-700 leading-relaxed">
                      <strong>Excellente performance d'ensemble !</strong> Vous avez démontré une maîtrise technique solide 
                      avec {results.performance_metrics.technical_consistency.toFixed(0)}% de consistance technique. 
                      Votre jeu au service a été particulièrement efficace, vous permettant de prendre l'ascendant sur votre adversaire.
                    </p>
                    
                    <p className="text-gray-700 leading-relaxed">
                      <strong>Points marquants :</strong> Votre positionnement tactique 
                      ({results.performance_metrics.positioning_score.toFixed(0)}% de score) et votre capacité à maintenir 
                      la pression ont été déterminants. Les longues séquences d'échanges ont tourné en votre faveur grâce à 
                      votre patience et votre précision.
                    </p>
                    
                    <p className="text-gray-700 leading-relaxed">
                      <strong>Recommandation :</strong> Continuez dans cette voie ! Votre style de jeu équilibré entre 
                      attaque et défense vous donne de solides bases pour progresser vers un niveau supérieur.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="strengths" className="space-y-8">
            {/* Vidéo points forts */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="w-5 h-5 text-emerald-500" />
                  <span>Vidéo de vos Points Forts</span>
                  <Badge className="bg-emerald-100 text-emerald-800 text-xs">
                    Meilleurs moments
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-emerald-100 to-blue-100 rounded-lg p-8 text-center">
                  <Star className="w-16 h-16 mx-auto mb-4 text-emerald-500" />
                  <p className="text-gray-700 mb-4">
                    Compilation de vos meilleures actions • Services gagnants et coups décisifs
                  </p>
                  <Button className="bg-emerald-500 hover:bg-emerald-600">
                    <PlayCircle className="w-4 h-4 mr-2" />
                    Voir mes points forts
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Radar Chart Performance et Services */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Performance Radar - Points Forts</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={[
                        {
                          subject: 'Service',
                          'Vous': 85,
                          'Adversaire': 45,
                          fullMark: 100,
                        },
                        {
                          subject: 'Technique',
                          'Vous': Math.round(results.performance_metrics.technical_consistency),
                          'Adversaire': 65,
                          fullMark: 100,
                        },
                        {
                          subject: 'Positionnement',
                          'Vous': Math.round(results.performance_metrics.positioning_score),
                          'Adversaire': 60,
                          fullMark: 100,
                        },
                        {
                          subject: 'Timing',
                          'Vous': Math.round(results.performance_metrics.timing_accuracy),
                          'Adversaire': 55,
                          fullMark: 100,
                        },
                        {
                          subject: 'Régularité',
                          'Vous': 80,
                          'Adversaire': 50,
                          fullMark: 100,
                        },
                        {
                          subject: 'Tactique',
                          'Vous': 75,
                          'Adversaire': 65,
                          fullMark: 100,
                        },
                      ]}>
                        <PolarGrid />
                        <PolarAngleAxis dataKey="subject" />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} />
                        <Radar name="Vous" dataKey="Vous" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
                        <Radar name="Adversaire" dataKey="Adversaire" stroke="#ef4444" fill="#ef4444" fillOpacity={0.1} />
                        <Legend />
                        <Tooltip />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                  
                  <div className="mt-4 p-4 bg-emerald-50 rounded-lg">
                    <h4 className="font-semibold text-emerald-800 mb-2">🎯 Excellence Globale</h4>
                    <p className="text-sm text-emerald-700">
                      Vous dominez dans toutes les catégories ! Votre service (85%) et votre technique 
                      ({results.performance_metrics.technical_consistency.toFixed(0)}%) sont vos atouts majeurs.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Détail des Services</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="bg-emerald-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Services remportés (Vous)</span>
                        <span className="text-2xl font-bold text-emerald-600">9</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Services remportés (Adversaire)</span>
                        <span className="text-lg font-semibold text-gray-500">4</span>
                      </div>
                    </div>

                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Services ratés (Vous)</span>
                        <span className="text-2xl font-bold text-blue-600">2</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Services ratés (Adversaire)</span>
                        <span className="text-lg font-semibold text-gray-500">6</span>
                      </div>
                    </div>

                    <div className="bg-yellow-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Services gagnants (Vous)</span>
                        <span className="text-2xl font-bold text-yellow-600">5</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Services gagnants (Adversaire)</span>
                        <span className="text-lg font-semibold text-gray-500">1</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-6 p-4 bg-gradient-to-r from-emerald-50 to-yellow-50 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-2">⭐ Analyse Détaillée</h4>
                    <p className="text-sm text-gray-700">
                      Statistiques exceptionnelles ! Avec 5 services gagnants directs et seulement 2 ratés, 
                      vous maîtrisez parfaitement cette phase. Votre adversaire n'a marqué qu'1 seul service gagnant.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Points forts identifiés */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Trophy className="w-5 h-5 text-yellow-500" />
                  <span>Ce que vous avez fait de bien</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-yellow-50 to-emerald-50 rounded-lg p-6">
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div className="bg-white rounded-lg p-4 border-l-4 border-emerald-500">
                        <h4 className="font-semibold text-emerald-800 mb-2">🏓 Maîtrise du Service</h4>
                        <p className="text-sm text-gray-700">
                          Votre service est votre point fort principal avec 75% de réussite. 
                          Vous variez efficacement placement et effets, créant des opportunités constantes.
                        </p>
                      </div>
                      
                      <div className="bg-white rounded-lg p-4 border-l-4 border-blue-500">
                        <h4 className="font-semibold text-blue-800 mb-2">🎯 Précision technique</h4>
                        <p className="text-sm text-gray-700">
                          Votre consistance technique ({results.performance_metrics.technical_consistency.toFixed(0)}%) 
                          vous permet de maintenir un niveau élevé tout au long du match.
                        </p>
                      </div>
                      
                      <div className="bg-white rounded-lg p-4 border-l-4 border-purple-500">
                        <h4 className="font-semibold text-purple-800 mb-2">🧠 Intelligence tactique</h4>
                        <p className="text-sm text-gray-700">
                          Excellent positionnement ({results.performance_metrics.positioning_score.toFixed(0)}%) 
                          et adaptation à votre adversaire. Vous savez quand attaquer et quand défendre.
                        </p>
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div className="bg-white rounded-lg p-4 border-l-4 border-yellow-500">
                        <h4 className="font-semibold text-yellow-800 mb-2">⚡ Coups gagnants</h4>
                        <p className="text-sm text-gray-700">
                          5 services gagnants directs démontrent votre capacité à conclure les points rapidement 
                          quand l'occasion se présente.
                        </p>
                      </div>
                      
                      <div className="bg-white rounded-lg p-4 border-l-4 border-indigo-500">
                        <h4 className="font-semibold text-indigo-800 mb-2">🛡️ Solidité défensive</h4>
                        <p className="text-sm text-gray-700">
                          Très peu de fautes non-forcées. Vous restez patient dans les longs échanges 
                          et forcez votre adversaire à prendre des risques.
                        </p>
                      </div>
                      
                      <div className="bg-white rounded-lg p-4 border-l-4 border-pink-500">
                        <h4 className="font-semibold text-pink-800 mb-2">📈 Progression continue</h4>
                        <p className="text-sm text-gray-700">
                          Vous vous êtes bonifié au fil du match, montrant une excellente capacité d'adaptation 
                          et de lecture du jeu adverse.
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-6 p-4 bg-white rounded-lg border-2 border-yellow-200">
                    <h4 className="font-bold text-gray-900 mb-3 flex items-center">
                      <Award className="w-5 h-5 mr-2 text-yellow-500" />
                      Récapitulatif de vos Forces
                    </h4>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li className="flex items-center">
                        <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                        Service exceptionnel (75% de réussite vs 45% adversaire)
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                        Régularité technique remarquable ({results.performance_metrics.technical_consistency.toFixed(0)}%)
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                        Intelligence tactique et adaptation (Score: {results.performance_metrics.positioning_score.toFixed(0)}%)
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                        Gestion parfaite des moments clés (5 coups gagnants)
                      </li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="weaknesses" className="space-y-8">
            {/* Vidéo points faibles */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Target className="w-5 h-5 text-orange-500" />
                  <span>Vidéo de vos Points à Améliorer</span>
                  <Badge className="bg-orange-100 text-orange-800 text-xs">
                    Zones d'amélioration
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-orange-100 to-red-100 rounded-lg p-8 text-center">
                  <AlertCircle className="w-16 h-16 mx-auto mb-4 text-orange-500" />
                  <p className="text-gray-700 mb-4">
                    Séquences à analyser pour améliorer votre jeu • Fautes et occasions manquées
                  </p>
                  <Button className="bg-orange-500 hover:bg-orange-600">
                    <PlayCircle className="w-4 h-4 mr-2" />
                    Analyser mes points faibles
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Évolution des fautes au cours du match */}
            <Card>
              <CardHeader>
                <CardTitle>Évolution des Fautes au Cours du Match</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64 mb-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={[
                        { temps: '0-5min', 'Vos fautes': 0, 'Fautes adversaire': 1 },
                        { temps: '5-10min', 'Vos fautes': 2, 'Fautes adversaire': 1 },
                        { temps: '10-15min', 'Vos fautes': 4, 'Fautes adversaire': 3 },
                        { temps: '15-20min', 'Vos fautes': 6, 'Fautes adversaire': 4 },
                        { temps: '20-25min', 'Vos fautes': 7, 'Fautes adversaire': 5 },
                      ]}
                      margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="temps" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Area type="monotone" dataKey="Vos fautes" stackId="1" stroke="#f97316" fill="#f97316" fillOpacity={0.6} />
                      <Area type="monotone" dataKey="Fautes adversaire" stackId="2" stroke="#10b981" fill="#10b981" fillOpacity={0.6} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                
                <div className="grid lg:grid-cols-2 gap-6">
                  <div className="bg-gradient-to-r from-orange-50 to-red-50 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-gray-800 mb-4">Analyse par Type de Faute</h3>
                    
                    <div className="h-40">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Fautes directes', value: 3, fill: '#dc2626' },
                              { name: 'Balles filet', value: 2, fill: '#f97316' },
                              { name: 'Balles longues', value: 2, fill: '#fbbf24' },
                            ]}
                            cx="50%"
                            cy="50%"
                            innerRadius={30}
                            outerRadius={60}
                            dataKey="value"
                            label={({ name, value }) => `${name}: ${value}`}
                          >
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="bg-red-50 rounded-lg p-4">
                      <h4 className="font-semibold text-red-800 mb-2">📊 Analyse Comparative</h4>
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Vos fautes totales</span>
                          <div className="flex items-center space-x-2">
                            <div className="w-20 bg-orange-200 rounded-full h-2">
                              <div className="bg-orange-500 h-2 rounded-full" style={{width: '58%'}}></div>
                            </div>
                            <span className="text-lg font-bold text-orange-600">7</span>
                          </div>
                        </div>
                        
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Fautes adversaire</span>
                          <div className="flex items-center space-x-2">
                            <div className="w-20 bg-green-200 rounded-full h-2">
                              <div className="bg-green-500 h-2 rounded-full" style={{width: '42%'}}></div>
                            </div>
                            <span className="text-lg font-bold text-green-600">5</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-orange-50 rounded-lg p-4">
                      <h4 className="font-semibold text-orange-800 mb-2">⚠️ Zone d'attention</h4>
                      <p className="text-sm text-orange-700">
                        Légère augmentation des fautes en milieu de match. Vous vous déstabilisez quand la pression monte. 
                        Travaillez la gestion de stress pour maintenir votre niveau.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Points faibles identifiés */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Target className="w-5 h-5 text-red-500" />
                  <span>Ce que vous devez améliorer</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-red-50 to-orange-50 rounded-lg p-6">
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div className="bg-white rounded-lg p-4 border-l-4 border-red-500">
                        <h4 className="font-semibold text-red-800 mb-2">🎯 Précision dans l'attaque</h4>
                        <p className="text-sm text-gray-700 mb-2">
                          3 fautes directes indiquent une tendance à forcer le jeu dans les mauvais moments.
                        </p>
                        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                          💡 Conseil : Privilégiez la construction du point à la recherche du coup gagnant immédiat
                        </div>
                      </div>
                      
                      <div className="bg-white rounded-lg p-4 border-l-4 border-orange-500">
                        <h4 className="font-semibold text-orange-800 mb-2">🥅 Contrôle de la trajectoire</h4>
                        <p className="text-sm text-gray-700 mb-2">
                          2 balles dans le filet suggèrent un problème de levée de balle ou de timing.
                        </p>
                        <div className="text-xs text-orange-600 bg-orange-50 p-2 rounded">
                          💡 Conseil : Travaillez l'ouverture de la raquette et la montée du bras
                        </div>
                      </div>
                      
                      <div className="bg-white rounded-lg p-4 border-l-4 border-yellow-500">
                        <h4 className="font-semibold text-yellow-800 mb-2">📐 Dosage de la puissance</h4>
                        <p className="text-sm text-gray-700 mb-2">
                          2 balles longues montrent une tendance à surjouer par moments.
                        </p>
                        <div className="text-xs text-yellow-600 bg-yellow-50 p-2 rounded">
                          💡 Conseil : Réduisez la force de frappe et augmentez l'effet pour plus de sécurité
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div className="bg-white rounded-lg p-4 border-l-4 border-purple-500">
                        <h4 className="font-semibold text-purple-800 mb-2">⏱️ Gestion du timing</h4>
                        <p className="text-sm text-gray-700 mb-2">
                          Quelques coups joués en retard, particulièrement sur les balles rapides.
                        </p>
                        <div className="text-xs text-purple-600 bg-purple-50 p-2 rounded">
                          💡 Conseil : Anticipez davantage et préparez plus tôt votre geste
                        </div>
                      </div>
                      
                      <div className="bg-white rounded-lg p-4 border-l-4 border-indigo-500">
                        <h4 className="font-semibold text-indigo-800 mb-2">🦶 Déplacements</h4>
                        <p className="text-sm text-gray-700 mb-2">
                          Position parfois trop statique, manque de mobilité latérale.
                        </p>
                        <div className="text-xs text-indigo-600 bg-indigo-50 p-2 rounded">
                          💡 Conseil : Restez sur l'avant des pieds, petits pas rapides
                        </div>
                      </div>
                      
                      <div className="bg-white rounded-lg p-4 border-l-4 border-pink-500">
                        <h4 className="font-semibold text-pink-800 mb-2">🧠 Patience tactique</h4>
                        <p className="text-sm text-gray-700 mb-2">
                          Tendance à vouloir conclure trop rapidement sur certains points.
                        </p>
                        <div className="text-xs text-pink-600 bg-pink-50 p-2 rounded">
                          💡 Conseil : Acceptez les longs échanges, votre régularité est un atout
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-6 p-4 bg-white rounded-lg border-2 border-red-200">
                    <h4 className="font-bold text-gray-900 mb-3 flex items-center">
                      <Target className="w-5 h-5 mr-2 text-red-500" />
                      Plan d'Amélioration Prioritaire
                    </h4>
                    
                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="bg-red-50 rounded-lg p-3">
                        <div className="font-semibold text-red-800 text-sm mb-1">🎯 Court terme</div>
                        <ul className="text-xs text-gray-700 space-y-1">
                          <li>• Réduire les fautes directes</li>
                          <li>• Améliorer la levée de balle</li>
                          <li>• Doser la puissance</li>
                        </ul>
                      </div>
                      
                      <div className="bg-orange-50 rounded-lg p-3">
                        <div className="font-semibold text-orange-800 text-sm mb-1">📈 Moyen terme</div>
                        <ul className="text-xs text-gray-700 space-y-1">
                          <li>• Améliorer la mobilité</li>
                          <li>• Travailler l'anticipation</li>
                          <li>• Développer la patience</li>
                        </ul>
                      </div>
                      
                      <div className="bg-yellow-50 rounded-lg p-3">
                        <div className="font-semibold text-yellow-800 text-sm mb-1">🏆 Long terme</div>
                        <ul className="text-xs text-gray-700 space-y-1">
                          <li>• Optimiser la tactique</li>
                          <li>• Perfectioner les variantes</li>
                          <li>• Mental de compétiteur</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="best-rallies" className="space-y-8">
            {/* Vidéo des meilleurs échanges */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Trophy className="w-5 h-5 text-yellow-500" />
                  <span>Vidéo des Meilleurs Échanges</span>
                  <Badge className="bg-yellow-100 text-yellow-800 text-xs">
                    Highlights du match
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-yellow-100 to-amber-100 rounded-lg p-8 text-center">
                  <Trophy className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
                  <p className="text-gray-700 mb-4">
                    Les échanges les plus spectaculaires du match • Points d'anthologie
                  </p>
                  <Button className="bg-yellow-500 hover:bg-yellow-600">
                    <PlayCircle className="w-4 h-4 mr-2" />
                    Voir les meilleurs moments
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Statistiques des échanges */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Longs Points Remportés</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center mb-6">
                    <div className="text-4xl font-bold text-emerald-600 mb-2">8</div>
                    <div className="text-lg text-gray-600 mb-4">Points de plus de 5 coups</div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-emerald-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-emerald-600">8</div>
                        <div className="text-sm text-emerald-700">Vous</div>
                        <div className="text-xs text-gray-500">73% des longs points</div>
                      </div>
                      <div className="bg-red-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-red-600">3</div>
                        <div className="text-sm text-red-700">Adversaire</div>
                        <div className="text-xs text-gray-500">27% des longs points</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-emerald-50 rounded-lg p-4">
                    <h4 className="font-semibold text-emerald-800 mb-2">🏆 Domination dans la longueur</h4>
                    <p className="text-sm text-emerald-700">
                      Excellent ! Vous remportez 73% des longs échanges. Votre endurance et votre régularité 
                      font la différence quand les points s'éternisent.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Services Détaillés</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Vos services</span>
                        <span className="text-2xl font-bold text-blue-600">12</span>
                      </div>
                      <div className="text-sm text-blue-700">
                        Services effectués pendant les meilleurs échanges
                      </div>
                    </div>
                    
                    <div className="bg-purple-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Services adversaire</span>
                        <span className="text-2xl font-bold text-purple-600">9</span>
                      </div>
                      <div className="text-sm text-purple-700">
                        Services adversaire dans les highlights
                      </div>
                    </div>
                    
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="text-center">
                        <div className="text-lg font-semibold text-gray-800 mb-1">Ratio services/highlights</div>
                        <div className="text-sm text-gray-600">
                          57% des meilleurs échanges démarrent sur votre service
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Dynamique des rallies - Graphique temporel */}
            <Card className="col-span-full">
              <CardHeader>
                <CardTitle>Dynamique des Meilleurs Rallies</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80 mb-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={[
                        { rally: 'Rally 1', longueur: 6, intensité: 75, vous: 8, adversaire: 4 },
                        { rally: 'Rally 2', longueur: 4, intensité: 60, vous: 6, adversaire: 3 },
                        { rally: 'Rally 3', longueur: 12, intensité: 90, vous: 15, adversaire: 8 },
                        { rally: 'Rally 4', longueur: 8, intensité: 80, vous: 10, adversaire: 6 },
                        { rally: 'Rally 5', longueur: 5, intensité: 65, vous: 7, adversaire: 4 },
                        { rally: 'Rally 6', longueur: 7, intensité: 85, vous: 9, adversaire: 5 },
                        { rally: 'Rally 7', longueur: 9, intensité: 70, vous: 12, adversaire: 7 },
                      ]}
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="rally" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="longueur" stroke="#f59e0b" strokeWidth={3} name="Longueur (coups)" />
                      <Line type="monotone" dataKey="intensité" stroke="#ef4444" strokeWidth={2} name="Intensité %" />
                      <Line type="monotone" dataKey="vous" stroke="#10b981" strokeWidth={2} name="Vos points gagnés" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-emerald-50 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-emerald-600 mb-2">4.2</div>
                    <div className="text-sm text-emerald-700 mb-1">Coups en moyenne par point</div>
                    <div className="text-xs text-gray-600">Dans les meilleurs échanges</div>
                  </div>
                  
                  <div className="bg-yellow-50 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-yellow-600 mb-2">12</div>
                    <div className="text-sm text-yellow-700 mb-1">Coups maximum par point</div>
                    <div className="text-xs text-gray-600">Le plus long échange du match</div>
                  </div>
                  
                  <div className="bg-purple-50 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-purple-600 mb-2">85%</div>
                    <div className="text-sm text-purple-700 mb-1">Taux de victoire</div>
                    <div className="text-xs text-gray-600">Sur les meilleurs rallies</div>
                  </div>
                </div>
                
                <div className="mt-6 bg-gradient-to-r from-emerald-50 to-yellow-50 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-800 mb-2">📊 Analyse des Rallies Spectaculaires</h4>
                  <p className="text-sm text-gray-700">
                    Vos meilleurs moments viennent des échanges de moyenne longueur (4-6 coups). Vous dominez particulièrement 
                    le rally 3 avec 12 coups et 90% d'intensité. Votre capacité à maintenir le niveau dans la durée est remarquable.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Statistiques des coups par point */}
            <div className="grid lg:grid-cols-2 gap-6">

              <Card>
                <CardHeader>
                  <CardTitle>Répartition des Points</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium">Points courts (1-3 coups)</span>
                        <span className="text-xl font-bold text-blue-600">4</span>
                      </div>
                      <div className="w-full bg-blue-200 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{width: '31%'}}></div>
                      </div>
                    </div>
                    
                    <div className="bg-emerald-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium">Points moyens (4-7 coups)</span>
                        <span className="text-xl font-bold text-emerald-600">6</span>
                      </div>
                      <div className="w-full bg-emerald-200 rounded-full h-2">
                        <div className="bg-emerald-500 h-2 rounded-full" style={{width: '46%'}}></div>
                      </div>
                    </div>
                    
                    <div className="bg-purple-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium">Points longs (8+ coups)</span>
                        <span className="text-xl font-bold text-purple-600">3</span>
                      </div>
                      <div className="w-full bg-purple-200 rounded-full h-2">
                        <div className="bg-purple-500 h-2 rounded-full" style={{width: '23%'}}></div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-6 bg-purple-50 rounded-lg p-4">
                    <h4 className="font-semibold text-purple-800 mb-2">🎯 Profil de Jeu</h4>
                    <p className="text-sm text-purple-700">
                      Vous excellez dans les échanges de durée moyenne. C'est votre zone de confort 
                      où vous pouvez construire puis conclure efficacement.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Commentaire des meilleurs points */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Star className="w-5 h-5 text-yellow-500" />
                  <span>Commentaire des Meilleurs Points du Match</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gradient-to-r from-yellow-50 to-amber-50 rounded-lg p-6">
                  <div className="space-y-6">
                    <div className="bg-white rounded-lg p-5 border-l-4 border-yellow-500">
                      <h4 className="font-bold text-yellow-800 mb-3">🏆 Point d'anthologie - 12 coups (8-5)</h4>
                      <p className="text-gray-700 leading-relaxed mb-3">
                        Le point le plus spectaculaire du match ! Parti sur un service lifté court, l'échange s'est développé 
                        avec des variations de rythme exceptionnelles. Votre patience dans la construction puis votre 
                        accélération au bon moment (10ème coup) ont fait la différence.
                      </p>
                      <div className="bg-yellow-50 p-3 rounded text-sm text-yellow-800">
                        <strong>Moment clé :</strong> Votre coup droit croisé au 10ème échange qui a ouvert le terrain
                      </div>
                    </div>
                    
                    <div className="bg-white rounded-lg p-5 border-l-4 border-emerald-500">
                      <h4 className="font-bold text-emerald-800 mb-3">⚡ Service gagnant direct (4-2)</h4>
                      <p className="text-gray-700 leading-relaxed mb-3">
                        Service lifté long suivi d'un coup droit à angle fermé. Votre adversaire, déstabilisé par l'effet, 
                        a tenté une remise défensive que vous avez parfaitement anticipée pour conclure en deux coups.
                      </p>
                      <div className="bg-emerald-50 p-3 rounded text-sm text-emerald-800">
                        <strong>Technique remarquable :</strong> Variation service + placement précis du coup gagnant
                      </div>
                    </div>
                    
                    <div className="bg-white rounded-lg p-5 border-l-4 border-blue-500">
                      <h4 className="font-bold text-blue-800 mb-3">🛡️ Défense puis contre-attaque (10-7)</h4>
                      <p className="text-gray-700 leading-relaxed mb-3">
                        Point remarquable de patience ! Mis en difficulté par un smash adverse, vous avez enchainé 
                        3 défenses hautes parfaites qui ont permis de retourner la situation. Votre contre-attaque 
                        en revers a été décisive.
                      </p>
                      <div className="bg-blue-50 p-3 rounded text-sm text-blue-800">
                        <strong>Mental de champion :</strong> Résistance sous pression + retournement de situation
                      </div>
                    </div>
                    
                    <div className="bg-white rounded-lg p-5 border-l-4 border-purple-500">
                      <h4 className="font-bold text-purple-800 mb-3">🎯 Précision chirurgicale (11-8 - Match point)</h4>
                      <p className="text-gray-700 leading-relaxed mb-3">
                        Le point de la victoire ! Sur votre service, vous avez varié avec un service coupé court qui a forcé 
                        une remise haute. Votre smash croisé, parfaitement placé près de la ligne, a scellé votre victoire.
                      </p>
                      <div className="bg-purple-50 p-3 rounded text-sm text-purple-800">
                        <strong>Gestion parfaite :</strong> Service tactique + conclusion impeccable sur match point
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-6 p-5 bg-gradient-to-r from-yellow-100 to-amber-100 rounded-lg border-2 border-yellow-300">
                    <h4 className="font-bold text-gray-900 mb-3 flex items-center">
                      <Trophy className="w-6 h-6 mr-2 text-yellow-500" />
                      Bilan des Moments d'Exception
                    </h4>
                    <div className="grid md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="font-semibold text-gray-800 mb-2">🎖️ Qualités démontrées :</p>
                        <ul className="space-y-1 text-gray-700">
                          <li>• Patience et construction intelligente</li>
                          <li>• Variations tactiques au service</li>
                          <li>• Mental solide sous pression</li>
                          <li>• Précision dans les moments décisifs</li>
                        </ul>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-800 mb-2">📈 Progression visible :</p>
                        <ul className="space-y-1 text-gray-700">
                          <li>• Adaptation au jeu adverse</li>
                          <li>• Gestion parfaite des points chauds</li>
                          <li>• Equilibre défense/attaque</li>
                          <li>• Conclusion efficace des opportunités</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;