import React, { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  PlayCircle, 
  Download, 
  Video, 
  Trophy, 
  Target, 
  Zap, 
  AlertCircle,
  Pause,
  Volume2,
  VolumeX,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  FileVideo,
  CheckCircle
} from 'lucide-react';

const VideoGallery = ({ videos, analysisId, onBack }) => {
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState({});
  const videoRef = useRef(null);

  const videoTypes = [
    {
      key: 'match_compilation',
      title: 'Match Complet',
      description: 'Vidéo compilée du match sans temps morts',
      icon: Video,
      color: 'emerald',
      available: videos?.match_compilation
    },
    {
      key: 'strengths',
      title: 'Points Forts',
      description: 'Vos meilleurs moments et coups réussis',
      icon: Trophy,
      color: 'blue',
      available: videos?.strengths
    },
    {
      key: 'weaknesses',
      title: 'Axes d\'Amélioration',
      description: 'Points à travailler pour progresser',
      icon: Target,
      color: 'amber',
      available: videos?.weaknesses
    },
    {
      key: 'best_rallies',
      title: 'Meilleurs Échanges',
      description: 'Les plus beaux points du match',
      icon: Zap,
      color: 'purple',
      available: videos?.best_rallies
    }
  ];

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8080';

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleDownload = async (videoType) => {
    try {
      setDownloadProgress(prev => ({ ...prev, [videoType]: 'loading' }));
      
      const response = await fetch(
        `${BACKEND_URL}/api/analysis/${analysisId}/video/${videoType}`,
        { method: 'GET' }
      );
      
      if (!response.ok) throw new Error('Téléchargement impossible');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pingpro_${videoType}_${analysisId.slice(0, 8)}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      setDownloadProgress(prev => ({ ...prev, [videoType]: 'done' }));
      setTimeout(() => {
        setDownloadProgress(prev => ({ ...prev, [videoType]: null }));
      }, 3000);
      
    } catch (error) {
      console.error('Download error:', error);
      setDownloadProgress(prev => ({ ...prev, [videoType]: 'error' }));
      setTimeout(() => {
        setDownloadProgress(prev => ({ ...prev, [videoType]: null }));
      }, 3000);
    }
  };

  const getVideoUrl = (videoType) => {
    return `${BACKEND_URL}/api/analysis/${analysisId}/video/${videoType}`;
  };

  const availableCount = videoTypes.filter(v => v.available).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
            <FileVideo className="w-7 h-7 text-emerald-500" />
            Vidéos Générées
          </h2>
          <p className="text-slate-600 mt-1">
            {availableCount > 0 
              ? `${availableCount} vidéo${availableCount > 1 ? 's' : ''} disponible${availableCount > 1 ? 's' : ''}`
              : 'Aucune vidéo générée (FFmpeg requis)'}
          </p>
        </div>
        {onBack && (
          <Button variant="outline" onClick={onBack} className="gap-2">
            <ChevronLeft className="w-4 h-4" />
            Retour aux résultats
          </Button>
        )}
      </div>

      {availableCount === 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <AlertCircle className="w-6 h-6 text-amber-500 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-amber-800">FFmpeg non installé</h3>
                <p className="text-amber-700 text-sm mt-1">
                  Les compilations vidéo nécessitent FFmpeg. Installez-le avec :
                </p>
                <code className="block mt-2 p-2 bg-amber-100 rounded text-sm font-mono">
                  .\scripts\setup_ffmpeg.ps1
                </code>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {videoTypes.map((video) => {
          const IconComponent = video.icon;
          const isSelected = selectedVideo === video.key;
          const progress = downloadProgress[video.key];
          
          return (
            <Card 
              key={video.key}
              className={`cursor-pointer transition-all duration-300 ${
                isSelected 
                  ? `ring-2 ring-${video.color}-500 shadow-lg` 
                  : video.available 
                    ? 'hover:shadow-md hover:scale-[1.02]' 
                    : 'opacity-50'
              }`}
              onClick={() => video.available && setSelectedVideo(video.key)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg bg-${video.color}-100 flex items-center justify-center`}>
                      <IconComponent className={`w-5 h-5 text-${video.color}-600`} />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{video.title}</CardTitle>
                      <p className="text-sm text-slate-500">{video.description}</p>
                    </div>
                  </div>
                  <Badge variant={video.available ? "default" : "secondary"}>
                    {video.available ? "Disponible" : "Non généré"}
                  </Badge>
                </div>
              </CardHeader>
              
              {video.available && (
                <CardContent className="pt-0">
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="flex-1 gap-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedVideo(video.key);
                      }}
                    >
                      <PlayCircle className="w-4 h-4" />
                      Lire
                    </Button>
                    <Button 
                      variant="default" 
                      size="sm" 
                      className={`flex-1 gap-2 bg-${video.color}-500 hover:bg-${video.color}-600`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDownload(video.key);
                      }}
                      disabled={progress === 'loading'}
                    >
                      {progress === 'loading' ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Export...
                        </>
                      ) : progress === 'done' ? (
                        <>
                          <CheckCircle className="w-4 h-4" />
                          Téléchargé
                        </>
                      ) : (
                        <>
                          <Download className="w-4 h-4" />
                          Exporter
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>

      {selectedVideo && videos?.[selectedVideo] && (
        <Card className="overflow-hidden">
          <CardHeader className="bg-slate-900 text-white py-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Video className="w-5 h-5" />
                {videoTypes.find(v => v.key === selectedVideo)?.title}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button 
                  variant="ghost" 
                  size="icon"
                  className="text-white hover:bg-white/20"
                  onClick={() => setIsMuted(!isMuted)}
                >
                  {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                </Button>
                <Button 
                  variant="ghost" 
                  size="icon"
                  className="text-white hover:bg-white/20"
                  onClick={() => videoRef.current?.requestFullscreen()}
                >
                  <Maximize2 className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0 bg-black">
            <video
              ref={videoRef}
              src={getVideoUrl(selectedVideo)}
              className="w-full aspect-video"
              controls
              muted={isMuted}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default VideoGallery;
