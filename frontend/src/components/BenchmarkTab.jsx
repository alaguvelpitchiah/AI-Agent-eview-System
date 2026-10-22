import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis 
} from 'recharts';
import { Award, TrendingUp, ExternalLink, ShieldCheck, CheckCircle2 } from 'lucide-react';

const COMPARISON_DATA = [
  { metric: 'Root-Cause Match', proposed: 100, baseline: 26, lift: '+74%' },
  { metric: 'Blame Precision', proposed: 100, baseline: 26, lift: '+74%' },
  { metric: 'Correct Fix Rate', proposed: 92, baseline: 33, lift: '+67%' },
  { metric: 'Regression Rate', proposed: 0, baseline: 63, lift: '-63%' },
  { metric: 'Conflict Recall', proposed: 100, baseline: 0, lift: '+100%' },
  { metric: 'Unsafe Deploy Rate', proposed: 0, baseline: 67, lift: '-67%' },
];

const RADAR_DATA = [
  { subject: 'Exact Match', proposed: 100, baseline: 26 },
  { subject: 'Precision', proposed: 100, baseline: 26 },
  { subject: 'Fix Rate', proposed: 92, baseline: 33 },
  { subject: 'Zero Regress', proposed: 100, baseline: 37 },
  { subject: 'Conflict Trap', proposed: 100, baseline: 0 },
  { subject: 'Safe Deploy', proposed: 100, baseline: 33 },
];

export default function BenchmarkTab() {
  return (
    <div className="benchmark-tab-container">
      {/* Banner */}
      <div className="glass-panel" style={{ padding: 22, marginBottom: 24, borderLeft: '4px solid #34d399' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 14 }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, color: '#fff' }}>
              <Award size={20} color="#34d399" />
              Benchmark Evaluation: Proposed Reviewer vs Heuristic Baseline
            </h3>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: 4 }}>
              Evaluated across 39 benchmark scenarios covering single faults, held-out faults, conflict traps, double synergistic faults, and independent decoys.
            </p>
          </div>

          <a 
            href="http://127.0.0.1:8501" 
            target="_blank" 
            rel="noreferrer" 
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <ExternalLink size={16} /> Open Streamlit Stats (Port 8501)
          </a>
        </div>
      </div>

      {/* Headline Metric Comparison Table */}
      <div className="glass-panel" style={{ padding: 22, marginBottom: 24 }}>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 16 }}>
          Statistical Headline Metrics with Wilson 95% Confidence Intervals
        </h4>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Evaluation Metric</th>
                <th>Our Proposed Reviewer (95% CI)</th>
                <th>Heuristic Baseline (95% CI)</th>
                <th>Statistical Lift</th>
                <th>Safety Implication</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>1. Root-Cause Exact Match</strong></td>
                <td><span className="badge badge-pass">100% [0.91 - 1.00]</span></td>
                <td><span className="badge badge-fail">26% [0.15 - 0.41]</span></td>
                <td style={{ color: '#34d399', fontWeight: 700 }}>+74% Absolute Lift 🚀</td>
                <td>Exact stage pinpointing</td>
              </tr>
              <tr>
                <td><strong>2. Blame Precision</strong></td>
                <td><span className="badge badge-pass">100% [0.91 - 1.00]</span></td>
                <td><span className="badge badge-fail">26% [0.15 - 0.41]</span></td>
                <td style={{ color: '#34d399', fontWeight: 700 }}>+74% Absolute Lift 🚀</td>
                <td>No innocent stages blamed</td>
              </tr>
              <tr>
                <td><strong>3. Correct Fix Rate</strong></td>
                <td><span className="badge badge-pass">92% - 100%</span></td>
                <td><span className="badge badge-fail">33% [0.20 - 0.49]</span></td>
                <td style={{ color: '#34d399', fontWeight: 700 }}>+67% Absolute Lift 🚀</td>
                <td>True root-cause fixes</td>
              </tr>
              <tr>
                <td><strong>4. Regression Rate</strong></td>
                <td><span className="badge badge-pass">0.00% [0.00 - 0.09]</span></td>
                <td><span className="badge badge-fail">63% [0.47 - 0.76]</span></td>
                <td style={{ color: '#34d399', fontWeight: 700 }}>-63% Safer 🛡️</td>
                <td>Zero regression traps</td>
              </tr>
              <tr>
                <td><strong>5. Conflict Trap Recall</strong></td>
                <td><span className="badge badge-pass">100% [0.61 - 1.00]</span></td>
                <td><span className="badge badge-fail">0% [0.00 - 0.39]</span></td>
                <td style={{ color: '#34d399', fontWeight: 700 }}>100% Traps Caught 🎯</td>
                <td>Catches pairwise conflicts</td>
              </tr>
              <tr>
                <td><strong>6. Unsafe Deployment Rate</strong></td>
                <td><span className="badge badge-pass">0.00% [0.00 - 0.09]</span></td>
                <td><span className="badge badge-fail">67% [0.51 - 0.79]</span></td>
                <td style={{ color: '#34d399', fontWeight: 700 }}>Zero Unsafe Fixes 🛡️</td>
                <td>Enforced by 8 Hard Gates</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Visual Charts: Side-by-Side Bar Chart & Multi-Axial Radar */}
      <div className="split-2">
        <div className="glass-panel" style={{ padding: 22 }}>
          <h4 style={{ fontSize: '0.92rem', fontWeight: 700, marginBottom: 16 }}>
            Metric Lift Comparison (%)
          </h4>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={COMPARISON_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="metric" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis unit="%" stroke="#64748b" />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                <Legend />
                <Bar dataKey="proposed" name="Proposed Reviewer" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="baseline" name="Heuristic Baseline" fill="#f43f5e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 22 }}>
          <h4 style={{ fontSize: '0.92rem', fontWeight: 700, marginBottom: 16 }}>
            Multi-Dimensional Capability Radar
          </h4>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart outerRadius={90} data={RADAR_DATA}>
                <PolarGrid stroke="rgba(255,255,255,0.1)" />
                <PolarAngleAxis dataKey="subject" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#64748b" />
                <Radar name="Proposed Reviewer" dataKey="proposed" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.4} />
                <Radar name="Heuristic Baseline" dataKey="baseline" stroke="#f43f5e" fill="#f43f5e" fillOpacity={0.25} />
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
