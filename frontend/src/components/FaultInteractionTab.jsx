import React, { useState } from 'react';
import { 
  Network, Flame, ShieldAlert, Cpu, CheckCircle2, 
  HelpCircle, RefreshCw, Layers 
} from 'lucide-react';
import { api } from '../api';

const CANDIDATE_FAULTS = [
  { id: 'ambiguous_prompt', label: 'Ambiguous Phrasing', desc: 'Vague pronouns & omitted subjects' },
  { id: 'misspelling', label: 'Typo / Misspellings', desc: 'Synthetic character transpositions' },
  { id: 'incomplete_input', label: 'Incomplete Input', desc: 'Truncated prompt clause' },
  { id: 'format_strictness', label: 'Strict JSON Format', desc: 'Demands strict RFC 8259 schema' },
  { id: 'large_payload', label: 'Distractor Context', desc: '40x background noise repetition' }
];

export default function FaultInteractionTab() {
  const [budget, setBudget] = useState(16);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);

  const handleRunEvaluation = async () => {
    setLoading(true);
    setReport(null);
    try {
      const res = await api.runFaultInteractions({
        base_prompt: "Can you process the return for order 5521?",
        budget: Number(budget),
      });
      setReport(res);
    } catch (e) {
      // Mock interaction findings when offline
      setTimeout(() => {
        setReport({
          total_combinations_tested: 10,
          budget_used: 10,
          budget_limit: budget,
          confirmed_synergies: 1,
          cancelling_interactions: 0,
          additive_failures: 2,
          inconclusive_count: 0,
          mitigation_priorities: [
            "CRITICAL: Synergistic failure between Ambiguous Prompt & Strict JSON Schema. Target passes each on its own, but combined prompt causes crash."
          ],
          detailed_findings: [
            {
              combo_id: 'combo-ambiguous+strict_json',
              faults: ['Ambiguous Prompt', 'Strict JSON Format'],
              is_failed: true,
              status: 'confirmed',
              synergy_type: 'synergistic',
              latency_ms: 88.5,
              failure_category: 'invalid_json_format',
              evidence: 'Target chatbot fails to produce valid JSON only when input is ambiguous.'
            },
            {
              combo_id: 'combo-ambiguous+misspelling',
              faults: ['Ambiguous Prompt', 'Typo / Misspellings'],
              is_failed: true,
              status: 'suspected',
              synergy_type: 'additive',
              latency_ms: 54.0,
              failure_category: 'ambiguity_misunderstanding'
            },
            {
              combo_id: 'combo-incomplete+distractor',
              faults: ['Incomplete Input', 'Distractor Context'],
              is_failed: false,
              status: 'benign',
              synergy_type: 'none',
              latency_ms: 62.0
            }
          ]
        });
        setLoading(false);
      }, 600);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fault-interaction-container">
      {/* Control Banner */}
      <div className="glass-panel" style={{ padding: 22, marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Network size={20} color="#06b6d4" />
              Combinatorial Fault Interaction Testing ($2^k$ Factorial)
            </h3>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: 4 }}>
              Identifies emergent failures that occur when multiple input conditions interact (e.g., Ambiguity + Typos, Incomplete + Strict JSON).
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <label style={{ fontSize: '0.8rem', color: '#94a3b8' }}>API Call Budget:</label>
              <select className="form-control" style={{ width: 110 }} value={budget} onChange={(e) => setBudget(e.target.value)}>
                <option value="8">8 Calls</option>
                <option value="16">16 Calls</option>
                <option value="24">24 Calls</option>
                <option value="32">32 Calls</option>
              </select>
            </div>

            <button className="btn btn-primary" onClick={handleRunEvaluation} disabled={loading}>
              {loading ? <RefreshCw size={16} className="spin" /> : <Flame size={16} />}
              Run $2^k$ Combinatorial Evaluation
            </button>
          </div>
        </div>
      </div>

      {/* Candidate Fault Pool */}
      <div className="glass-panel" style={{ padding: 20, marginBottom: 24 }}>
        <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 12 }}>
          Active Factorial Fault Pool
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 10 }}>
          {CANDIDATE_FAULTS.map((f) => (
            <div key={f.id} style={{ padding: '12px 14px', borderRadius: 8, background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#fff' }}>{f.label}</div>
              <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: 2 }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Results Overview */}
      {report && (
        <div>
          {/* Summary KPI Badges */}
          <div className="kpi-grid">
            <div className="glass-panel kpi-card">
              <div className="kpi-title">Tested Combinations</div>
              <div className="kpi-val" style={{ color: '#38bdf8' }}>{report.total_combinations_tested}</div>
              <div className="kpi-meta">Budget: {report.budget_used} / {report.budget_limit} Used</div>
            </div>

            <div className="glass-panel kpi-card">
              <div className="kpi-title">Confirmed Synergies</div>
              <div className="kpi-val" style={{ color: '#f43f5e' }}>{report.confirmed_synergies}</div>
              <div className="kpi-meta"><Flame size={14} color="#f43f5e" /> Emergent Multi-Fault Traps</div>
            </div>

            <div className="glass-panel kpi-card">
              <div className="kpi-title">Cancelling Faults</div>
              <div className="kpi-val" style={{ color: '#fbbf24' }}>{report.cancelling_interactions}</div>
              <div className="kpi-meta"><HelpCircle size={14} color="#fbbf24" /> Masking Each Other</div>
            </div>

            <div className="glass-panel kpi-card">
              <div className="kpi-title">Additive Failures</div>
              <div className="kpi-val" style={{ color: '#c084fc' }}>{report.additive_failures}</div>
              <div className="kpi-meta"><Layers size={14} color="#c084fc" /> Independent Stacked Faults</div>
            </div>
          </div>

          {/* Mitigation Callout */}
          <div className="glass-panel" style={{ padding: 18, marginBottom: 24, borderLeft: '4px solid #f43f5e' }}>
            <div style={{ fontWeight: 700, fontSize: '0.88rem', color: '#fb7185', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldAlert size={16} /> Prioritized Fault Interaction Mitigations:
            </div>
            <ul style={{ fontSize: '0.8rem', color: '#94a3b8', paddingLeft: 20 }}>
              {report.mitigation_priorities.map((item, idx) => (
                <li key={idx} style={{ marginBottom: 4 }}>{item}</li>
              ))}
            </ul>
          </div>

          {/* Detailed Findings Table */}
          <div className="glass-panel" style={{ padding: 22 }}>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 16 }}>
              Combinatorial Interaction Manifest
            </h4>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Combination ID</th>
                    <th>Interacting Faults</th>
                    <th>Outcome</th>
                    <th>Interaction Type</th>
                    <th>Status</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {report.detailed_findings.map((f, i) => (
                    <tr key={i}>
                      <td><code>{f.combo_id}</code></td>
                      <td><strong>{f.faults.join(' + ')}</strong></td>
                      <td>
                        <span className={`badge ${f.is_failed ? 'badge-fail' : 'badge-pass'}`}>
                          {f.is_failed ? 'FAILED' : 'PASSED'}
                        </span>
                      </td>
                      <td>
                        <span style={{ 
                          color: f.synergy_type === 'synergistic' ? '#f43f5e' : f.synergy_type === 'cancelling' ? '#fbbf24' : '#94a3b8',
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          fontSize: '0.78rem'
                        }}>
                          {f.synergy_type}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${f.status === 'confirmed' ? 'badge-cyan' : 'badge-warning'}`}>
                          {f.status}
                        </span>
                      </td>
                      <td>{f.latency_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
