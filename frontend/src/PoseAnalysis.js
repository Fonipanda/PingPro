import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Badge } from './components/ui/badge';
import { Separator } from './components/ui/separator';
import { Activity, Bone, Move, FileText, GitCompare } from 'lucide-react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { getPoseFrameUrl } from './api';

const JOINT_LABELS = {
  elbow: 'Coude',
  shoulder_elbow: 'Épaule-coude',
  knee: 'Genou',
  hip_flexion: 'Flexion hanche',
  shoulder_abduction: 'Abduction épaule',
  hip_abduction: 'Abduction hanche',
  trunk_forward_lean: 'Inclinaison avant',
  trunk_rotation: 'Rotation du tronc',
  center_of_mass_height_ratio: 'Hauteur CdM',
};

const SKELETON_CONNECTIONS = [
  ['LEFT_SHOULDER', 'RIGHT_SHOULDER'],
  ['LEFT_SHOULDER', 'LEFT_ELBOW'],
  ['RIGHT_SHOULDER', 'RIGHT_ELBOW'],
  ['LEFT_ELBOW', 'LEFT_WRIST'],
  ['RIGHT_ELBOW', 'RIGHT_WRIST'],
  ['LEFT_SHOULDER', 'LEFT_HIP'],
  ['RIGHT_SHOULDER', 'RIGHT_HIP'],
  ['LEFT_HIP', 'RIGHT_HIP'],
  ['LEFT_HIP', 'LEFT_KNEE'],
  ['RIGHT_HIP', 'RIGHT_KNEE'],
  ['LEFT_KNEE', 'LEFT_ANKLE'],
  ['RIGHT_KNEE', 'RIGHT_ANKLE'],
];

const LANDMARK_INDICES = {
  NOSE: 0,
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
};

function Skeleton3D({ landmarks, color = '#00ff88' }) {
  const points = useMemo(() => {
    return (landmarks || []).map((lm) => new THREE.Vector3(lm.x * 2 - 1, -(lm.y * 2 - 1), lm.z || 0));
  }, [landmarks]);

  const linePositions = useMemo(() => {
    const coords = [];
    SKELETON_CONNECTIONS.forEach(([a, b]) => {
      const ia = LANDMARK_INDICES[a];
      const ib = LANDMARK_INDICES[b];
      if (ia < points.length && ib < points.length) {
        coords.push(points[ia].x, points[ia].y, points[ia].z);
        coords.push(points[ib].x, points[ib].y, points[ib].z);
      }
    });
    return new Float32Array(coords);
  }, [points]);

  if (points.length === 0) return null;

  return (
    <group>
      {points.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.03, 16, 16]} />
          <meshStandardMaterial color={color} />
        </mesh>
      ))}
      {linePositions.length > 0 && (
        <lineSegments>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[linePositions, 3]}
            />
          </bufferGeometry>
          <lineBasicMaterial color={color} linewidth={2} />
        </lineSegments>
      )}
    </group>
  );
}

export default function PoseAnalysis({ results }) {
  const [activeFrame, setActiveFrame] = useState(0);

  const poseAnalysis = results?.technical_analysis?.pose_analysis;
  const comparison = results?.pose_reference_comparison;
  const report = results?.pose_report;
  const overlayFrames = results?.overlay_frames || [];
  const metrics = results?.performance_metrics || {};

  if (!poseAnalysis) {
    return (
      <div className="p-8 text-center text-gray-500">
        Aucune analyse de pose disponible pour cette vidéo.
      </div>
    );
  }

  const angles = poseAnalysis.contact_angles || {};
  const phases = poseAnalysis.phases || {};
  const kinetic = poseAnalysis.kinetic_chain || {};
  const heatmap = poseAnalysis.player_heatmap || {};

  const referenceLandmarks = comparison?.reference_landmarks?.[0];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-5 h-5 text-blue-600" />
              <span className="text-sm text-gray-600">Score de posture</span>
            </div>
            <div className="text-3xl font-bold">{metrics.posture_score ?? 'N/A'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-2">
              <Move className="w-5 h-5 text-green-600" />
              <span className="text-sm text-gray-600">Chaîne cinétique</span>
            </div>
            <div className="text-3xl font-bold">{metrics.kinetic_chain_quality ?? 'N/A'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-2">
              <GitCompare className="w-5 h-5 text-purple-600" />
              <span className="text-sm text-gray-600">Similarité référence</span>
            </div>
            <div className="text-3xl font-bold">{comparison?.similarity_score ?? 'N/A'}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="angles" className="w-full">
        <TabsList className="grid w-full grid-cols-2 md:grid-cols-5">
          <TabsTrigger value="angles"><Bone className="w-4 h-4 mr-2" />Angles</TabsTrigger>
          <TabsTrigger value="skeleton2d"><Activity className="w-4 h-4 mr-2" />Squelette 2D</TabsTrigger>
          <TabsTrigger value="skeleton3d"><Move className="w-4 h-4 mr-2" />Vue 3D</TabsTrigger>
          <TabsTrigger value="comparison"><GitCompare className="w-4 h-4 mr-2" />Comparaison</TabsTrigger>
          <TabsTrigger value="report"><FileText className="w-4 h-4 mr-2" />Rapport</TabsTrigger>
        </TabsList>

        {/* Angles */}
        <TabsContent value="angles">
          <Card>
            <CardHeader>
              <CardTitle>Angles articulaires au contact</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(angles).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium">{JOINT_LABELS[key] || key}</span>
                    <Badge variant="secondary">{typeof value === 'number' ? `${value.toFixed(1)}°` : value}</Badge>
                  </div>
                ))}
              </div>

              <Separator className="my-6" />

              <h4 className="font-semibold mb-3">Phases du geste</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <div className="text-sm text-gray-600">Armé</div>
                  <div className="font-bold">{phases.backswing?.start_timestamp?.toFixed(2) ?? 'N/A'}s</div>
                </div>
                <div className="p-3 bg-red-50 rounded-lg">
                  <div className="text-sm text-gray-600">Contact</div>
                  <div className="font-bold">{phases.contact?.timestamp?.toFixed(2) ?? 'N/A'}s</div>
                </div>
                <div className="p-3 bg-green-50 rounded-lg">
                  <div className="text-sm text-gray-600">Accompagnement</div>
                  <div className="font-bold">{phases.follow_through?.end_timestamp?.toFixed(2) ?? 'N/A'}s</div>
                </div>
              </div>

              <Separator className="my-6" />

              <h4 className="font-semibold mb-3">Chaîne cinétique</h4>
              <div className="space-y-2">
                {Object.entries(kinetic)
                  .filter(([_, v]) => typeof v === 'object')
                  .map(([key, value]) => (
                    <div key={key} className="flex justify-between p-2 bg-gray-50 rounded">
                      <span className="capitalize">{key}</span>
                      <span className="text-sm text-gray-600">
                        vitesse max {value.max_speed?.toFixed(2) ?? 'N/A'} @ {value.timestamp?.toFixed(2) ?? 'N/A'}s
                      </span>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Squelette 2D */}
        <TabsContent value="skeleton2d">
          <Card>
            <CardHeader>
              <CardTitle>Squelette superposé à la vidéo</CardTitle>
            </CardHeader>
            <CardContent>
              {overlayFrames.length > 0 ? (
                <div className="space-y-4">
                  <div className="flex gap-2 overflow-x-auto pb-2">
                    {overlayFrames.map((_, idx) => (
                      <button
                        key={idx}
                        onClick={() => setActiveFrame(idx)}
                        className={`px-3 py-1 rounded text-sm whitespace-nowrap ${
                          activeFrame === idx
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        Frame {idx + 1}
                      </button>
                    ))}
                  </div>
                  <img
                    src={getPoseFrameUrl(results.analysis_id, activeFrame)}
                    alt={`Pose overlay frame ${activeFrame}`}
                    className="w-full max-w-2xl mx-auto rounded-lg shadow"
                  />
                </div>
              ) : (
                <p className="text-gray-500">Aucune frame de pose disponible.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Vue 3D */}
        <TabsContent value="skeleton3d">
          <Card>
            <CardHeader>
              <CardTitle>Vue 3D interactive au contact</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[400px] w-full rounded-lg overflow-hidden border">
                <Canvas camera={{ position: [0, 0, 2.5], fov: 50 }}>
                  <ambientLight intensity={0.8} />
                  <directionalLight position={[2, 2, 2]} />
                  <gridHelper args={[4, 20]} />
                  <OrbitControls />
                  {poseAnalysis.frames?.[phases.contact?.frame_idx || 0]?.poses?.[0] && (
                    <Skeleton3D
                      landmarks={
                        poseAnalysis.frames[phases.contact?.frame_idx || 0].poses[0]
                      }
                      color="#00ff88"
                    />
                  )}
                </Canvas>
              </div>
              <p className="text-sm text-gray-500 mt-2">
                Faites glisser pour tourner, utilisez la molette pour zoomer.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Comparaison */}
        <TabsContent value="comparison">
          <Card>
            <CardHeader>
              <CardTitle>Comparaison avec le modèle de référence</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-semibold mb-2">Votre mouvement</h4>
                  <div className="h-[300px] w-full rounded-lg overflow-hidden border">
                    <Canvas camera={{ position: [0, 0, 2.5], fov: 50 }}>
                      <ambientLight intensity={0.8} />
                      <directionalLight position={[2, 2, 2]} />
                      <gridHelper args={[4, 20]} />
                      <OrbitControls />
                      {poseAnalysis.frames?.[phases.contact?.frame_idx || 0]?.poses?.[0] && (
                        <Skeleton3D
                          landmarks={
                            poseAnalysis.frames[phases.contact?.frame_idx || 0].poses[0]
                          }
                          color="#3b82f6"
                        />
                      )}
                    </Canvas>
                  </div>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Modèle de référence</h4>
                  <div className="h-[300px] w-full rounded-lg overflow-hidden border">
                    <Canvas camera={{ position: [0, 0, 2.5], fov: 50 }}>
                      <ambientLight intensity={0.8} />
                      <directionalLight position={[2, 2, 2]} />
                      <gridHelper args={[4, 20]} />
                      <OrbitControls />
                      {referenceLandmarks && (
                        <Skeleton3D landmarks={referenceLandmarks} color="#a855f7" />
                      )}
                    </Canvas>
                  </div>
                </div>
              </div>

              {comparison?.observations?.length > 0 && (
                <div className="mt-6 p-4 bg-purple-50 rounded-lg">
                  <h4 className="font-semibold mb-2">Observations</h4>
                  <ul className="list-disc pl-5 space-y-1">
                    {comparison.observations.map((obs, idx) => (
                      <li key={idx}>{obs}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rapport */}
        <TabsContent value="report">
          <Card>
            <CardHeader>
              <CardTitle>Rapport du Coach IA</CardTitle>
            </CardHeader>
            <CardContent>
              {report ? (
                <div className="prose prose-sm max-w-none whitespace-pre-wrap">
                  {report}
                </div>
              ) : (
                <p className="text-gray-500">Aucun rapport disponible.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
