export const MOCK_ANALYSIS_ID = 'mock-analysis-001';

export const mockStatus = {
  status: 'completed',
  progress: 100,
  current_step: 'Analyse terminée',
};

// Génère un squelette 3D tourné vers la table, bras droit en action
function makePlayerLandmarks({ armExtension = 0.7, kneeBend = 0.25, lean = 0.15 }) {
  const x = (v) => v;
  const y = (v) => v;
  const z = (v) => v * 0.3;
  return [
    { x: x(0.5), y: y(0.28), z: z(0.0) }, // NOSE
    { x: 0, y: 0, z: 0 }, // 1
    { x: 0, y: 0, z: 0 }, // 2
    { x: 0, y: 0, z: 0 }, // 3
    { x: 0, y: 0, z: 0 }, // 4
    { x: 0, y: 0, z: 0 }, // 5
    { x: 0, y: 0, z: 0 }, // 6
    { x: 0, y: 0, z: 0 }, // 7
    { x: 0, y: 0, z: 0 }, // 8
    { x: 0, y: 0, z: 0 }, // 9
    { x: 0, y: 0, z: 0 }, // 10
    { x: x(0.45), y: y(0.35), z: z(0.05) }, // LEFT_SHOULDER
    { x: x(0.55), y: y(0.35), z: z(0.05) }, // RIGHT_SHOULDER
    { x: x(0.4), y: y(0.48), z: z(0.1) }, // LEFT_ELBOW
    { x: x(0.62), y: y(0.45), z: z(0.15) }, // RIGHT_ELBOW
    { x: x(0.35), y: y(0.62), z: z(0.12) }, // LEFT_WRIST
    { x: x(0.72), y: y(0.5), z: z(0.25) }, // RIGHT_WRIST
    { x: 0, y: 0, z: 0 }, // 16
    { x: 0, y: 0, z: 0 }, // 17
    { x: 0, y: 0, z: 0 }, // 18
    { x: 0, y: 0, z: 0 }, // 19
    { x: 0, y: 0, z: 0 }, // 20
    { x: 0, y: 0, z: 0 }, // 22
    { x: x(0.46), y: y(0.7), z: z(0.0) }, // LEFT_HIP
    { x: x(0.54), y: y(0.7), z: z(0.0) }, // RIGHT_HIP
    { x: x(0.44), y: y(0.85), z: z(0.05) }, // LEFT_KNEE
    { x: x(0.58), y: y(0.84), z: z(0.05) }, // RIGHT_KNEE
    { x: x(0.42), y: y(0.98), z: z(0.1) }, // LEFT_ANKLE
    { x: x(0.6), y: y(0.97), z: z(0.1) }, // RIGHT_ANKLE
  ];
}

const contactLandmarks = makePlayerLandmarks({ armExtension: 0.7, kneeBend: 0.25, lean: 0.15 });

// Overlay 2D placeholder : image base64 grise avec texte
const overlayPlaceholder =
  'data:image/svg+xml;base64,' +
  btoa(
    `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
      <rect width="640" height="360" fill="#1f2937"/>
      <text x="50%" y="45%" dominant-baseline="middle" text-anchor="middle" fill="#9ca3af" font-size="24">Frame de pose simulée</text>
      <text x="50%" y="58%" dominant-baseline="middle" text-anchor="middle" fill="#6b7280" font-size="16">Mode démo — aucun backend requis</text>
      <circle cx="320" cy="126" r="6" fill="#34d399"/>
      <line x1="288" y1="126" x2="352" y2="126" stroke="#34d399" stroke-width="3"/>
      <line x1="288" y1="126" x2="256" y2="173" stroke="#34d399" stroke-width="3"/>
      <line x1="352" y1="126" x2="397" y2="162" stroke="#34d399" stroke-width="3"/>
      <line x1="256" y1="173" x2="224" y2="223" stroke="#34d399" stroke-width="3"/>
      <line x1="397" y1="162" x2="461" y2="180" stroke="#34d399" stroke-width="3"/>
      <line x1="288" y1="126" x2="294" y2="252" stroke="#34d399" stroke-width="3"/>
      <line x1="352" y1="126" x2="346" y2="252" stroke="#34d399" stroke-width="3"/>
      <line x1="294" y1="252" x2="346" y2="252" stroke="#34d399" stroke-width="3"/>
      <line x1="294" y1="252" x2="282" y2="306" stroke="#34d399" stroke-width="3"/>
      <line x1="346" y1="252" x2="371" y2="302" stroke="#34d399" stroke-width="3"/>
      <line x1="282" y1="306" x2="269" y2="353" stroke="#34d399" stroke-width="3"/>
      <line x1="371" y1="302" x2="384" y2="349" stroke="#34d399" stroke-width="3"/>
    </svg>
  `
  );

export const mockResults = {
  isMock: true,
  analysis_id: MOCK_ANALYSIS_ID,
  video_info: {
    filename: 'demo_match.mp4',
    duration_seconds: 187,
    width: 1280,
    height: 720,
    fps: 30,
    total_frames: 5610,
  },
  performance_metrics: {
    overall_score: 78,
    technical_consistency: 74,
    positioning_score: 81,
    timing_score: 69,
    anticipation_score: 72,
    posture_score: 76,
    kinetic_chain_quality: 73,
    ball_tracking_quality: 'Good',
    rally_analysis: {
      total_rallies: 24,
      average_rally_length: 4.2,
      longest_rally_frames: 142,
    },
    event_detection: {
      serve: 12,
      ball_bounce: 18,
      hit: 52,
    },
  },
  table_tennis_scoring: {
    match_statistics: {
      your_score: 11,
      opponent_score: 8,
      winner: 'you',
      total_points: 19,
      aces_served: 3,
    },
  },
  technical_analysis: {
    summary:
      'Bonne maîtrise technique globale. Le service est un point fort, avec une bonne variété. Les échanges moyens sont construits efficacement.',
    key_strengths: [
      'Service varié et efficace (60% de points gagnés)',
      'Bonne anticipation du rebond adverse',
      'Positionnement centré et équilibré',
    ],
    areas_for_improvement: [
      'Rotation du tronc plus marquée sur le coup droit',
      'Pliage des genoux plus prononcé en réception de service',
      'Stabilité du poignet en fin d\'accompagnement',
    ],
    recommended_exercises: [
      'Exercices de rotation hanches-épaules sans raquette',
      'Squats partiels en position de prêt',
      'Shadow play avec focus sur le suivi du bras',
    ],
    stroke_analysis: {
      forehand: { frequency: 38, quality: 'Bon', recommendation: 'Utiliser davantage la chaîne cinétique' },
      backhand: { frequency: 32, quality: 'Correct', recommendation: 'Rapprocher le coude du corps' },
      serve: { frequency: 12, quality: 'Très bon', recommendation: 'Maintenir la variété' },
    },
    pose_analysis: {
      contact_angles: {
        elbow: 142.5,
        shoulder_elbow: 68.3,
        knee: 118.7,
        hip_flexion: 108.4,
        shoulder_abduction: 82.1,
        hip_abduction: 15.3,
        trunk_forward_lean: 24.6,
        trunk_rotation: 47.2,
        center_of_mass_height_ratio: 0.52,
      },
      phases: {
        backswing: { start_timestamp: 1.85, end_timestamp: 2.1 },
        contact: { timestamp: 2.18, frame_idx: 65 },
        follow_through: { start_timestamp: 2.22, end_timestamp: 2.55 },
      },
      kinetic_chain: {
        hips: { max_speed: 2.4, timestamp: 2.12 },
        shoulders: { max_speed: 3.1, timestamp: 2.15 },
        forearm: { max_speed: 5.8, timestamp: 2.18 },
      },
      player_heatmap: {
        mean_x: 0.48,
        mean_y: 0.72,
        std_x: 0.12,
        std_y: 0.08,
      },
      frames: [
        { timestamp: 1.85, poses: [makePlayerLandmarks({ armExtension: 0.4, kneeBend: 0.2, lean: 0.1 })] },
        { timestamp: 2.0, poses: [makePlayerLandmarks({ armExtension: 0.55, kneeBend: 0.22, lean: 0.12 })] },
        { timestamp: 2.18, poses: [contactLandmarks] },
        { timestamp: 2.35, poses: [makePlayerLandmarks({ armExtension: 0.8, kneeBend: 0.18, lean: 0.18 })] },
      ],
    },
  },
  pose_reference_comparison: {
    similarity_score: 0.72,
    observations: [
      'Votre coude est légèrement plus déplié que le modèle de référence au contact (+8°).',
      'La rotation du tronc est convenable mais pourrait être accentuée de 10°.',
      'Bonne flexion des genoux, proche du modèle idéal.',
      'L\'accompagnement reste un peu court par rapport au modèle.',
    ],
    reference_landmarks: [
      makePlayerLandmarks({ armExtension: 0.75, kneeBend: 0.28, lean: 0.2 }),
    ],
  },
  pose_report:
    'Coach IA — Mode démo\n\nPoints forts :\n- Posture générale équilibrée avec un bon positionnement des jambes.\n- La chaîne cinétique suit le bon ordre (bassin → épaules → avant-bras).\n- Le contact se fait à une hauteur et une distance cohérentes.\n\nAxes de progrès :\n1. Accentuer la rotation du tronc de 10° pour générer plus de puissance sans forcer sur le bras.\n2. Pliquer davantage les genoux en phase d\'armé pour créer un ressort vers l\'avant.\n3. Prolonger l\'accompagnement vers la cible pour plus de contrôle de direction.\n\nExercice prioritaire : 3 séries de 10 rotations hanches-épaules suivies de shadow play au coup droit, en focus sur l\'enchaînement jambes → tronc → bras.',
  overlay_frames: [overlayPlaceholder, overlayPlaceholder, overlayPlaceholder],
};
