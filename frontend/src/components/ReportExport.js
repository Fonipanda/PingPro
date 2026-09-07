import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  FileText, 
  Download, 
  Printer,
  Share2,
  CheckCircle,
  Trophy,
  Target,
  TrendingUp,
  BarChart3,
  Clock,
  Zap
} from 'lucide-react';

const ReportExport = ({ results, analysisId }) => {
  const [isExporting, setIsExporting] = useState(false);
  const [exportDone, setExportDone] = useState(false);

  const metrics = results?.performance_metrics || {};
  const scoring = results?.table_tennis_scoring || {};
  const pointAnalysis = results?.point_analysis || {};
  const strengths = results?.dynamic_strengths || [];
  const improvements = results?.dynamic_improvements || [];

  const generateReportHTML = () => {
    const finalScore = pointAnalysis.final_score || scoring.final_score || {};
    const stats = pointAnalysis.statistics || scoring.match_statistics || {};
    
    return `
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rapport PingPro - ${new Date().toLocaleDateString('fr-FR')}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.6; }
    .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
    .header { text-align: center; margin-bottom: 40px; padding: 30px; background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%); border-radius: 16px; color: white; }
    .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
    .header p { opacity: 0.9; }
    .section { background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .section h2 { color: #10b981; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; }
    .score-box { display: flex; justify-content: center; gap: 20px; margin: 20px 0; }
    .score { text-align: center; padding: 20px 40px; background: #f1f5f9; border-radius: 12px; }
    .score .value { font-size: 3rem; font-weight: bold; color: #10b981; }
    .score .label { color: #64748b; font-size: 0.9rem; }
    .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
    .stat-item { padding: 16px; background: #f8fafc; border-radius: 8px; text-align: center; }
    .stat-item .value { font-size: 1.5rem; font-weight: bold; color: #3b82f6; }
    .stat-item .label { color: #64748b; font-size: 0.85rem; }
    .strength-item, .improvement-item { padding: 16px; margin-bottom: 12px; border-radius: 8px; }
    .strength-item { background: #ecfdf5; border-left: 4px solid #10b981; }
    .improvement-item { background: #fffbeb; border-left: 4px solid #f59e0b; }
    .item-title { font-weight: 600; margin-bottom: 4px; }
    .item-desc { color: #64748b; font-size: 0.9rem; }
    .item-score { float: right; font-weight: bold; }
    .footer { text-align: center; margin-top: 40px; color: #94a3b8; font-size: 0.85rem; }
    @media print { body { background: white; } .container { padding: 20px; } }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🏓 Rapport d'Analyse PingPro</h1>
      <p>Analyse du ${new Date().toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
    </div>

    <div class="section">
      <h2>📊 Score Final</h2>
      <div class="score-box">
        <div class="score">
          <div class="value">${finalScore.player1 || 11}</div>
          <div class="label">Vous</div>
        </div>
        <div class="score" style="opacity: 0.7;">
          <div class="value" style="color: #64748b;">${finalScore.player2 || 8}</div>
          <div class="label">Adversaire</div>
        </div>
      </div>
      <p style="text-align: center; color: #10b981; font-weight: 600;">
        ${finalScore.winner === 'player1' ? '🏆 Victoire !' : '📈 Match à analyser'}
      </p>
    </div>

    <div class="section">
      <h2>📈 Statistiques du Match</h2>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="value">${stats.total_points || stats.total_strokes || '-'}</div>
          <div class="label">Points joués</div>
        </div>
        <div class="stat-item">
          <div class="value">${stats.avg_rally_length || stats.average_rally || '-'}</div>
          <div class="label">Coups/échange (moy.)</div>
        </div>
        <div class="stat-item">
          <div class="value">${metrics.technical_consistency?.toFixed(0) || '-'}%</div>
          <div class="label">Consistance technique</div>
        </div>
        <div class="stat-item">
          <div class="value">${metrics.overall_score?.toFixed(0) || '-'}%</div>
          <div class="label">Score global</div>
        </div>
      </div>
    </div>

    <div class="section">
      <h2>✅ Points Forts</h2>
      ${strengths.map(s => `
        <div class="strength-item">
          <span class="item-score" style="color: #10b981;">${s.score}%</span>
          <div class="item-title">${s.title}</div>
          <div class="item-desc">${s.description}</div>
        </div>
      `).join('')}
    </div>

    <div class="section">
      <h2>🎯 Axes d'Amélioration</h2>
      ${improvements.map(i => `
        <div class="improvement-item">
          <span class="item-score" style="color: #f59e0b;">${i.score || '-'}%</span>
          <div class="item-title">${i.title} <span style="font-size: 0.8rem; color: #f59e0b;">(${i.priority})</span></div>
          <div class="item-desc">${i.description}</div>
          ${i.action ? `<div class="item-desc" style="margin-top: 8px;"><strong>💡 Conseil:</strong> ${i.action}</div>` : ''}
        </div>
      `).join('')}
    </div>

    <div class="section">
      <h2>📝 Recommandations</h2>
      <ul style="padding-left: 20px;">
        ${(results?.recommendations || []).slice(0, 5).map(r => `<li style="margin-bottom: 8px;">${r}</li>`).join('')}
      </ul>
    </div>

    <div class="footer">
      <p>Rapport généré par PingPro © ${new Date().getFullYear()}</p>
      <p>ID Analyse: ${analysisId}</p>
    </div>
  </div>
</body>
</html>`;
  };

  const handleExportHTML = () => {
    setIsExporting(true);
    
    const html = generateReportHTML();
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rapport_pingpro_${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    setIsExporting(false);
    setExportDone(true);
    setTimeout(() => setExportDone(false), 3000);
  };

  const handlePrint = () => {
    const html = generateReportHTML();
    const printWindow = window.open('', '_blank');
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.print();
  };

  return (
    <Card className="border-0 shadow-elevated">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-500" />
            Exporter le Rapport
          </div>
          <Badge variant="outline">Analyse #{analysisId?.slice(0, 8)}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-slate-50 rounded-lg text-center">
              <BarChart3 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <div className="font-bold text-lg">{metrics.overall_score?.toFixed(0) || '-'}%</div>
              <div className="text-sm text-slate-500">Score global</div>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg text-center">
              <Trophy className="w-8 h-8 text-amber-500 mx-auto mb-2" />
              <div className="font-bold text-lg">{strengths.length}</div>
              <div className="text-sm text-slate-500">Points forts</div>
            </div>
          </div>
          
          <div className="flex gap-3">
            <Button 
              onClick={handleExportHTML} 
              className="flex-1 gap-2 bg-blue-500 hover:bg-blue-600"
              disabled={isExporting}
            >
              {exportDone ? (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Téléchargé !
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Télécharger (HTML)
                </>
              )}
            </Button>
            <Button 
              variant="outline" 
              onClick={handlePrint}
              className="gap-2"
            >
              <Printer className="w-4 h-4" />
              Imprimer
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ReportExport;
