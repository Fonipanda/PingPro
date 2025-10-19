import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Play, Square, RotateCcw, Camera, Wifi, WifiOff } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL;

const RealTimeAnalysis = () => {
  // WebSocket and connection state
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  
  // Video and analysis data
  const [videoFrame, setVideoFrame] = useState(null);
  const [statistics, setStatistics] = useState({
    game_duration: 0,
    score: { player1: 0, player2: 0 },
    current_rally: { length: 0, duration: 0 },
    rally_stats: { total_rallies: 0, average_length: 0, longest_rally: 0 },
    ball_stats: { current_position: null, velocity: null, average_speed: 0, max_speed: 0 },
    events_last_minute: {},
    detection_quality: { ball_detection_rate: 0, avg_confidence: 0 }
  });
  
  // Real-time events
  const [recentEvents, setRecentEvents] = useState([]);
  const [ballDetection, setBallDetection] = useState(null);
  const [players, setPlayers] = useState([]);
  
  // UI state
  const [videoSource, setVideoSource] = useState('0'); // '0' for webcam
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState(null);
  
  // Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const eventsRef = useRef(null);
  
  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    try {
      // Fix WebSocket URL construction for production
      const wsProtocol = API.startsWith('https') ? 'wss:' : 'ws:';
      const wsHost = API.replace('https://', '').replace('http://', '');
      const wsUrl = `${wsProtocol}//${wsHost}/ws/realtime/client_${Date.now()}`;
      console.log('Connecting to WebSocket:', wsUrl);
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setConnected(true);
        setError(null);
        console.log('Connected to real-time analysis server');
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };
      
      ws.onclose = () => {
        setConnected(false);
        setAnalyzing(false);
        console.log('Disconnected from real-time analysis server');
      };
      
      ws.onerror = (error) => {
        setError('WebSocket connection error');
        console.error('WebSocket error:', error);
      };
      
      setSocket(ws);
    } catch (err) {
      setError('Failed to connect to analysis server');
    }
  }, [API]);
  
  // Handle WebSocket messages
  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'frame_analysis':
        // Update video frame
        if (data.frame_data) {
          setVideoFrame(`data:image/jpeg;base64,${data.frame_data}`);
        }
        
        // Update analysis data
        if (data.analysis) {
          if (data.analysis.ball) {
            setBallDetection(data.analysis.ball);
          }
          
          if (data.analysis.players) {
            setPlayers(data.analysis.players);
          }
          
          if (data.analysis.events && data.analysis.events.length > 0) {
            setRecentEvents(prev => [...prev, ...data.analysis.events].slice(-10));
          }
          
          if (data.analysis.statistics) {
            setStatistics(data.analysis.statistics);
          }
        }
        break;
        
      case 'status':
        console.log('Status:', data.message);
        break;
        
      case 'analysis_status':
        if (data.status === 'started') {
          setAnalyzing(true);
        } else if (data.status === 'stopped') {
          setAnalyzing(false);
        }
        break;
        
      case 'error':
        setError(data.message);
        break;
        
      default:
        console.log('Unknown message type:', data.type);
    }
  };
  
  // Component lifecycle
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, [connectWebSocket]);
  
  // Control functions
  const startAnalysis = async () => {
    if (!connected || !socket) {
      setError('Not connected to analysis server');
      return;
    }
    
    try {
      socket.send(JSON.stringify({
        type: 'start_analysis',
        video_source: videoSource
      }));
      
      setError(null);
    } catch (err) {
      setError('Failed to start analysis');
    }
  };
  
  const stopAnalysis = () => {
    if (socket) {
      socket.send(JSON.stringify({
        type: 'stop_analysis'
      }));
    }
  };
  
  const resetGame = () => {
    if (socket) {
      socket.send(JSON.stringify({
        type: 'reset_game'
      }));
      
      // Reset local state
      setStatistics({
        game_duration: 0,
        score: { player1: 0, player2: 0 },
        current_rally: { length: 0, duration: 0 },
        rally_stats: { total_rallies: 0, average_length: 0, longest_rally: 0 },
        ball_stats: { current_position: null, velocity: null, average_speed: 0, max_speed: 0 },
        events_last_minute: {},
        detection_quality: { ball_detection_rate: 0, avg_confidence: 0 }
      });
      setRecentEvents([]);
      setBallDetection(null);
      setPlayers([]);
    }
  };
  
  const toggleRecording = async () => {
    try {
      const endpoint = recording ? '/api/recording/stop' : '/api/recording/start';
      const response = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        setRecording(!recording);
        if (recording) {
          const data = await response.json();
          console.log('Recording stopped, match data:', data.match_data);
        }
      }
    } catch (err) {
      setError('Recording operation failed');
    }
  };
  
  // Format time helper
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          PingPro - Analyse Temps Réel
        </h1>
        <p className="text-gray-600 text-lg">
          Analyse en direct de votre match de tennis de table avec IA avancée
        </p>
      </div>
      
      {/* Connection Status */}
      <div className="mb-6 flex justify-center">
        <Badge variant={connected ? "default" : "destructive"} className="flex items-center space-x-2">
          {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          <span>{connected ? 'Connecté au serveur d\'analyse' : 'Déconnecté'}</span>
        </Badge>
      </div>
      
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">{error}</p>
        </div>
      )}
      
      {/* Control Panel */}
      <div className="grid lg:grid-cols-4 gap-6 mb-8">
        {/* Video Controls */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Camera className="w-5 h-5" />
              <span>Contrôles Vidéo</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Source Vidéo
              </label>
              <select 
                value={videoSource} 
                onChange={(e) => setVideoSource(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md"
                disabled={analyzing}
              >
                <option value="0">Webcam</option>
                <option value="1">Caméra USB</option>
              </select>
            </div>
            
            <div className="space-y-2">
              <Button 
                onClick={startAnalysis}
                disabled={!connected || analyzing}
                className="w-full"
              >
                <Play className="w-4 h-4 mr-2" />
                Démarrer Analyse
              </Button>
              
              <Button 
                onClick={stopAnalysis}
                disabled={!analyzing}
                variant="outline"
                className="w-full"
              >
                <Square className="w-4 h-4 mr-2" />
                Arrêter
              </Button>
              
              <Button 
                onClick={resetGame}
                disabled={!connected}
                variant="outline"
                className="w-full"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset Match
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Score Display */}
        <Card>
          <CardHeader>
            <CardTitle>Score en Direct</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-4">
              <div className="flex justify-center items-center space-x-8">
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-600">
                    {statistics.score.player1}
                  </div>
                  <div className="text-sm text-gray-600">Joueur 1</div>
                </div>
                <div className="text-2xl font-bold text-gray-400">-</div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-600">
                    {statistics.score.player2}
                  </div>
                  <div className="text-sm text-gray-600">Joueur 2</div>
                </div>
              </div>
              
              <div className="text-center">
                <div className="text-lg font-semibold">
                  Temps: {formatTime(statistics.game_duration)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Current Rally */}
        <Card>
          <CardHeader>
            <CardTitle>Échange Actuel</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Coups:</span>
                <span className="font-bold text-lg">{statistics.current_rally.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Durée:</span>
                <span className="font-bold">{formatTime(statistics.current_rally.duration)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Échanges totaux:</span>
                <span className="font-bold">{statistics.rally_stats.total_rallies}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Longueur moy.:</span>
                <span className="font-bold">{statistics.rally_stats.average_length.toFixed(1)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Detection Quality */}
        <Card>
          <CardHeader>
            <CardTitle>Qualité Détection</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Taux détection:</span>
                <span className="font-bold">
                  {(statistics.detection_quality.ball_detection_rate * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Confiance moy.:</span>
                <span className="font-bold">
                  {(statistics.detection_quality.avg_confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Vitesse balle:</span>
                <span className="font-bold">
                  {statistics.ball_stats.average_speed.toFixed(0)} px/s
                </span>
              </div>
              <Button 
                onClick={toggleRecording}
                variant={recording ? "destructive" : "default"}
                size="sm"
                className="w-full"
              >
                {recording ? 'Arrêter Enregistrement' : 'Enregistrer Match'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Video and Analysis Display */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Live Video Feed */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Vidéo en Direct avec Annotations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden">
              {videoFrame ? (
                <img 
                  src={videoFrame} 
                  alt="Live analysis feed"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <div className="text-center">
                    <Camera className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-600">
                      {analyzing ? 'Initialisation de l\'analyse...' : 'Cliquez sur "Démarrer Analyse" pour commencer'}
                    </p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Ball Position Info */}
            {ballDetection && (
              <div className="mt-4 p-3 bg-green-50 rounded-lg">
                <h4 className="font-semibold text-green-800 mb-2">Position Balle Détectée</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-green-600">X:</span> {ballDetection.x.toFixed(0)}
                  </div>
                  <div>
                    <span className="text-green-600">Y:</span> {ballDetection.y.toFixed(0)}
                  </div>
                  <div>
                    <span className="text-green-600">Confiance:</span> {(ballDetection.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
        
        {/* Events and Statistics */}
        <Card>
          <CardHeader>
            <CardTitle>Événements en Temps Réel</CardTitle>
          </CardHeader>
          <CardContent>
            <div ref={eventsRef} className="space-y-2 max-h-96 overflow-y-auto">
              {recentEvents.length > 0 ? (
                recentEvents.slice(-10).reverse().map((event, index) => (
                  <div key={index} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex justify-between items-center">
                      <Badge 
                        variant={
                          event.type === 'bounce' ? 'default' :
                          event.type === 'serve' ? 'secondary' :
                          event.type === 'net_hit' ? 'destructive' : 'outline'
                        }
                      >
                        {event.type === 'bounce' ? '🏓 Rebond' :
                         event.type === 'serve' ? '🎾 Service' :
                         event.type === 'net_hit' ? '🥅 Filet' :
                         event.type === 'rally_end' ? '🏁 Fin Échange' : event.type}
                      </Badge>
                      <span className="text-xs text-gray-500">
                        {(event.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      {new Date(event.timestamp * 1000).toLocaleTimeString()}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  Aucun événement détecté
                </div>
              )}
            </div>
            
            {/* Events Summary */}
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <h4 className="font-semibold text-blue-800 mb-3">Événements (dernière minute)</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(statistics.events_last_minute).map(([eventType, count]) => (
                  <div key={eventType} className="flex justify-between">
                    <span className="capitalize">{eventType}:</span>
                    <span className="font-bold">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default RealTimeAnalysis;