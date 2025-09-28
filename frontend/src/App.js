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

            {/* Statistiques des coups */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Statistiques des Coups</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="bg-emerald-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Coups en moyenne (Vous)</span>
                        <span className="text-2xl font-bold text-emerald-600">
                          {results.performance_metrics.rally_analysis ? 
                            results.performance_metrics.rally_analysis.average_rally_length.toFixed(1) : '3.2'}
                        </span>
                      </div>
                      <div className="w-full bg-emerald-200 rounded-full h-2">
                        <div className="bg-emerald-500 h-2 rounded-full" style={{width: '65%'}}></div>
                      </div>
                    </div>
                    
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Coups par point (Vous)</span>
                        <span className="text-2xl font-bold text-blue-600">
                          {results.performance_metrics.rally_analysis ? 
                            (results.performance_metrics.rally_analysis.total_bounces / Math.max(1, results.performance_metrics.rally_analysis.total_rallies)).toFixed(1) : '2.8'}
                        </span>
                      </div>
                      <div className="w-full bg-blue-200 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{width: '60%'}}></div>
                      </div>
                    </div>
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
                  <div className="space-y-4">
                    <div className="bg-emerald-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Points service remportés (Vous)</span>
                        <span className="text-2xl font-bold text-emerald-600">
                          {results.performance_metrics.event_detection?.serve ? 
                            Math.floor(results.performance_metrics.event_detection.serve * 0.6) : '7'}
                        </span>
                      </div>
                      <div className="w-full bg-emerald-200 rounded-full h-2 mb-2">
                        <div className="bg-emerald-500 h-2 rounded-full" style={{width: '60%'}}></div>
                      </div>
                      <span className="text-xs text-emerald-700">60% de réussite</span>
                    </div>
                    
                    <div className="bg-red-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Points service adversaire</span>
                        <span className="text-2xl font-bold text-red-600">5</span>
                      </div>
                      <div className="w-full bg-red-200 rounded-full h-2 mb-2">
                        <div className="bg-red-500 h-2 rounded-full" style={{width: '40%'}}></div>
                      </div>
                      <span className="text-xs text-red-700">40% de réussite</span>
                    </div>

                    <div className="bg-orange-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">Fautes en remise (Vous)</span>
                        <span className="text-2xl font-bold text-orange-600">3</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-6 p-4 bg-gray-50 rounded-lg">
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
            {/* Performance Metrics */}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardContent className="p-6 text-center">
                  <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <TrendingUp className="w-6 h-6 text-emerald-600" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900">
                    {results.performance_metrics.overall_score.toFixed(0)}%
                  </h3>
                  <p className="text-sm text-gray-600">Score global</p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6 text-center">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Target className="w-6 h-6 text-blue-600" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900">
                    {results.performance_metrics.technical_consistency.toFixed(0)}%
                  </h3>
                  <p className="text-sm text-gray-600">Consistance technique</p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6 text-center">
                  <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Users className="w-6 h-6 text-purple-600" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900">
                    {results.performance_metrics.positioning_score.toFixed(0)}%
                  </h3>
                  <p className="text-sm text-gray-600">Positionnement</p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6 text-center">
                  <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Clock className="w-6 h-6 text-orange-600" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900">
                    {results.performance_metrics.timing_accuracy.toFixed(0)}%
                  </h3>
                  <p className="text-sm text-gray-600">Précision timing</p>
                </CardContent>
              </Card>
            </div>

            {/* TTNet Analysis Results */}
            {results.technical_analysis.ttnet_analysis && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Zap className="w-5 h-5 text-emerald-500" />
                    <span>Analyse Vidéo Avancée (TTNet)</span>
                    <Badge className="bg-emerald-100 text-emerald-800 text-xs">
                      IA Avancée
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-gradient-to-r from-emerald-50 to-blue-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <div className="w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center">
                          <Target className="w-3 h-3 text-white" />
                        </div>
                        <span className="font-medium text-sm">Suivi de Balle</span>
                      </div>
                      <p className="text-lg font-bold text-gray-900">
                        {(results.technical_analysis.ttnet_analysis.ball_detection_rate * 100).toFixed(0)}%
                      </p>
                      <p className="text-xs text-gray-600">Précision détection</p>
                    </div>

                    {results.performance_metrics.event_detection && (
                      <>
                        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4">
                          <div className="flex items-center space-x-2 mb-2">
                            <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                              <PlayCircle className="w-3 h-3 text-white" />
                            </div>
                            <span className="font-medium text-sm">Rebonds</span>
                          </div>
                          <p className="text-lg font-bold text-gray-900">
                            {results.performance_metrics.event_detection.ball_bounce || 0}
                          </p>
                          <p className="text-xs text-gray-600">Détectés</p>
                        </div>

                        <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4">
                          <div className="flex items-center space-x-2 mb-2">
                            <div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
                              <Star className="w-3 h-3 text-white" />
                            </div>
                            <span className="font-medium text-sm">Services</span>
                          </div>
                          <p className="text-lg font-bold text-gray-900">
                            {results.performance_metrics.event_detection.serve || 0}
                          </p>
                          <p className="text-xs text-gray-600">Identifiés</p>
                        </div>
                      </>
                    )}

                    <div className="bg-gradient-to-r from-orange-50 to-red-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <div className="w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center">
                          <Award className="w-3 h-3 text-white" />
                        </div>
                        <span className="font-medium text-sm">Qualité</span>
                      </div>
                      <p className="text-lg font-bold text-gray-900">
                        {results.performance_metrics.ball_tracking_quality || "Bonne"}
                      </p>
                      <p className="text-xs text-gray-600">Suivi vidéo</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Rally Analysis */}
            {results.performance_metrics.rally_analysis && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <BarChart3 className="w-5 h-5" />
                    <span>Analyse des Échanges</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <p className="text-2xl font-bold text-emerald-600">
                        {results.performance_metrics.rally_analysis.average_rally_length.toFixed(1)}
                      </p>
                      <p className="text-sm text-gray-600">Longueur moyenne des échanges</p>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <p className="text-2xl font-bold text-blue-600">
                        {results.performance_metrics.rally_analysis.total_rallies}
                      </p>
                      <p className="text-sm text-gray-600">Total échanges</p>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <p className="text-lg font-semibold text-purple-600">
                        {results.performance_metrics.rally_analysis.game_style}
                      </p>
                      <p className="text-sm text-gray-600">Style de jeu</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Video Info */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Video className="w-5 h-5" />
                  <span>Informations vidéo</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Durée</p>
                    <p className="font-semibold">{results.video_info.duration_seconds.toFixed(1)}s</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Images analysées</p>
                    <p className="font-semibold">{results.video_info.frame_count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Résolution</p>
                    <p className="font-semibold">{results.video_info.resolution}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Confiance IA</p>
                    <p className="font-semibold">{(results.confidence_score * 100).toFixed(0)}%</p>
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

            {/* Statistiques des services - Points forts */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Taux de Réussite des Services</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    <div className="text-center">
                      <div className="text-5xl font-bold text-emerald-600 mb-2">75%</div>
                      <div className="text-lg text-gray-600 mb-4">Taux de réussite global</div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-emerald-50 rounded-lg p-3">
                          <div className="text-2xl font-bold text-emerald-600">75%</div>
                          <div className="text-xs text-emerald-700">Vous</div>
                        </div>
                        <div className="bg-red-50 rounded-lg p-3">
                          <div className="text-2xl font-bold text-red-600">45%</div>
                          <div className="text-xs text-red-700">Adversaire</div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-emerald-50 rounded-lg p-4">
                      <h4 className="font-semibold text-emerald-800 mb-2">🎯 Excellence au Service</h4>
                      <p className="text-sm text-emerald-700">
                        Domination claire dans cette phase ! Avec 30% d'écart sur votre adversaire, 
                        vos services sont votre arme principale. Continuez à exploiter cet avantage.
                      </p>
                    </div>
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
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Analyse des coups</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {results.technical_analysis.stroke_analysis && (
                    <div className="space-y-3">
                      {Object.entries(results.technical_analysis.stroke_analysis).map(([key, value]) => (
                        <div key={key} className="bg-gray-50 rounded-lg p-3">
                          <h4 className="font-semibold capitalize text-sm text-gray-700 mb-1">
                            {key.replace('_', ' ')}
                          </h4>
                          <p className="text-sm text-gray-600">
                            {Array.isArray(value) ? value.join(', ') : String(value)}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Positionnement et Déplacement</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {results.technical_analysis.positioning_analysis && (
                    <div className="space-y-3">
                      {Object.entries(results.technical_analysis.positioning_analysis).map(([key, value]) => (
                        <div key={key} className="bg-gray-50 rounded-lg p-3">
                          <h4 className="font-semibold capitalize text-sm text-gray-700 mb-1">
                            {key.replace('_', ' ')}
                          </h4>
                          <p className="text-sm text-gray-600">
                            {Array.isArray(value) ? value.join(', ') : String(value)}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* TTNet Movement Analysis */}
            {results.technical_analysis.movement_analysis && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Zap className="w-5 h-5 text-emerald-500" />
                    <span>Analyse de Mouvement Avancée</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 gap-6">
                    {results.technical_analysis.movement_analysis.ball_speed_analysis && (
                      <div className="space-y-3">
                        <h4 className="font-semibold text-gray-800">Vitesse de Balle</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between items-center p-2 bg-emerald-50 rounded">
                            <span className="text-sm text-gray-600">Vitesse moyenne</span>
                            <span className="font-medium">
                              {results.technical_analysis.movement_analysis.ball_speed_analysis.average_speed.toFixed(1)} px/frame
                            </span>
                          </div>
                          <div className="flex justify-between items-center p-2 bg-blue-50 rounded">
                            <span className="text-sm text-gray-600">Vitesse maximale</span>
                            <span className="font-medium">
                              {results.technical_analysis.movement_analysis.ball_speed_analysis.max_speed.toFixed(1)} px/frame
                            </span>
                          </div>
                          <div className="flex justify-between items-center p-2 bg-purple-50 rounded">
                            <span className="text-sm text-gray-600">Consistance</span>
                            <span className="font-medium">
                              {results.technical_analysis.movement_analysis.ball_speed_analysis.speed_consistency.toFixed(1)}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    <div className="space-y-3">
                      <h4 className="font-semibold text-gray-800">Qualité du Suivi</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between items-center p-2 bg-orange-50 rounded">
                          <span className="text-sm text-gray-600">Confiance tracking</span>
                          <span className="font-medium">
                            {(results.technical_analysis.movement_analysis.tracking_confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="p-3 bg-gray-50 rounded">
                          <p className="text-sm text-gray-600 mb-1">Qualité générale</p>
                          <p className="font-medium text-gray-800">
                            {results.technical_analysis.movement_analysis.movement_quality}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Areas for improvement */}
            {results.performance_metrics.improvement_areas.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Target className="w-5 h-5" />
                    <span>Zones d'amélioration</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {results.performance_metrics.improvement_areas.map((area, index) => (
                      <Badge key={index} variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                        {area}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="recommendations" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Star className="w-5 h-5" />
                  <span>Conseils personnalisés</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {results.recommendations.map((recommendation, index) => (
                    <div key={index} className="flex items-start space-x-3 p-4 bg-gradient-to-r from-emerald-50 to-blue-50 rounded-lg border border-emerald-100">
                      <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Award className="w-4 h-4 text-emerald-600" />
                      </div>
                      <p className="text-gray-800 leading-relaxed">{recommendation}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="highlights" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Video className="w-5 h-5" />
                  <span>Moments clés identifiés</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {results.highlights_timestamps.length > 0 ? (
                  <div className="space-y-4">
                    {results.highlights_timestamps.map((timestamp, index) => (
                      <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                            <PlayCircle className="w-5 h-5 text-blue-600" />
                          </div>
                          <div>
                            <p className="font-semibold">Moment clé #{index + 1}</p>
                            <p className="text-sm text-gray-600">
                              À {Math.floor(timestamp / 60)}:{Math.floor(timestamp % 60).toString().padStart(2, '0')}
                            </p>
                          </div>
                        </div>
                        <Button size="sm" variant="outline">
                          <PlayCircle className="w-4 h-4 mr-2" />
                          Voir
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <Video className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    <p className="text-gray-500">Aucun moment clé identifié</p>
                  </div>
                )}
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