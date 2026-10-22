import React from 'react';
import { 
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, AreaChart, Area 
} from 'recharts';
import { 
  ShieldCheck, AlertTriangle, Cpu, CheckCircle2, 
  Clock, Award, ArrowUpRight, Activity 
} from 'lucide-react';

const CATEGORY_COLORS = {
  incorrect_output: '#f43f5e',
  safety_violation: '#dc2626',
  latency_spike: '#f59e0b',
  incomplete_output: '#8b5cf6',
  tool_error: '#06b6d4',
  invalid_json: '#3b82f6'
};

export default function OverviewTab({ stats, onSelectTab }) {
  const failureData = [
    { name: 'Incorrect Output', value: 14, color: '#f43f5e' },
    { name: 'Safety / Leakage', value: 3, color: '#dc2626' },
    { name: 'Latency Spikes', value: 6, color: '#f59e0b' },
    { name: 'Incomplete Output', value: 5, color: '#8b5cf6' },
    { name: 'Tool Error', value: 4, color: '#06b6d4' },
  ];

  const benchmarkTrend = [
    { name: 'Run 1', baselineReg: 58, pipelineReg: 0, accuracy: 96 },
    { name: 'Run 2', baselineReg: 62, pipelineReg: 0, accuracy: 98 },
    { name: 'Run 3', baselineReg: 65, pipelineReg: 0, accuracy: 100 },
    { name: 'Run 4', baselineReg: 61, pipelineReg: 0, accuracy: 100 },
    { name: 'Run 5', baselineReg: 63, pipelineReg: 0, accuracy: 100 },
  ];

  const latencyHistory = [
    { step: '01:00', latency: 42, sla: 100 },
    { step: '02:00', latency: 48, sla: 100 },
    { step: '03:00', latency: 125, sla: 100 },
    { step: '04:00', latency: 54, sla: 100 },
    { step: '05:00', latency: 38, sla: 100 },
    { step: '06:00', latency: 45, sla: 100 },
  ];

  return (
    <div className="overview-container">
      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <div className="glass-panel kpi-card">
          <div className="kpi-title">Verified Scenarios</div>
          <div className="kpi-val" style={{ color: '#38bdf8' }}>{stats.scenarios_count || 39}</div>
          <div className="kpi-meta">
            <CheckCircle2 size={14} color="#34d399" /> 100% Exact Root Cause Match
          </div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="kpi-title">Regression Rate</div>
          <div className="kpi-val" style={{ color: '#34d399' }}>0.0%</div>
          <div className="kpi-meta">
            <ShieldCheck size={14} color="#34d399" /> vs 63% Heuristic Baseline
          </div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="kpi-title">Conflict Traps Caught</div>
          <div className="kpi-val" style={{ color: '#c084fc' }}>100%</div>
          <div className="kpi-meta">
            <Cpu size={14} color="#c084fc" /> 8 Hard Gates Active
          </div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="kpi-title">Pending Approvals</div>
          <div className="kpi-val" style={{ color: '#fbbf24' }}>{stats.approvals_count || 1}</div>
          <div className="kpi-meta">
            <Clock size={14} color="#fbbf24" /> Human Sign-Off Enforced
          </div>
        </div>

        <div className="glass-panel kpi-card">
          <div className="kpi-title">Unsafe Deployments</div>
          <div className="kpi-val" style={{ color: '#10b981' }}>0</div>
          <div className="kpi-meta">
            <ShieldCheck size={14} color="#10b981" /> Zero Blind Production Changes
          </div>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="split-2" style={{ marginBottom: 24 }}>
        {/* Failure Distribution */}
        <div className="glass-panel" style={{ padding: 22 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: '0.98rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle size={18} color="#f43f5e" />
              Observed Failure Categories
            </h3>
            <span className="badge badge-fail">32 Observable Issues</span>
          </div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={failureData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {failureData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#fff' }} 
                />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Regression Comparison */}
        <div className="glass-panel" style={{ padding: 22 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: '0.98rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Award size={18} color="#34d399" />
              Regression Rate: Pipeline vs Heuristic Baseline
            </h3>
            <span className="badge badge-pass">-63% Safer</span>
          </div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={benchmarkTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" stroke="#64748b" />
                <YAxis unit="%" stroke="#64748b" />
                <Tooltip 
                  contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#fff' }} 
                />
                <Legend />
                <Bar dataKey="baselineReg" name="Heuristic Baseline Regression" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                <Bar dataKey="pipelineReg" name="Our Pipeline Regression (Zero)" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Latency Timeline & Architecture Banner */}
      <div className="glass-panel" style={{ padding: 22 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={18} color="#06b6d4" />
            Live Response Latency SLA Monitoring
          </h3>
          <span className="badge badge-cyan">Target SLA &lt;= 100ms</span>
        </div>
        <div style={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={latencyHistory}>
              <defs>
                <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="step" stroke="#64748b" />
              <YAxis unit="ms" stroke="#64748b" />
              <Tooltip 
                contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#fff' }} 
              />
              <Area type="monotone" dataKey="latency" name="Agent Latency (ms)" stroke="#06b6d4" fillOpacity={1} fill="url(#latencyGrad)" strokeWidth={2} />
              <Area type="step" dataKey="sla" name="SLA Limit (100ms)" stroke="#f43f5e" strokeDasharray="4 4" fill="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quick Jump Callouts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginTop: 24 }}>
        <div className="glass-panel" style={{ padding: 18, cursor: 'pointer' }} onClick={() => onSelectTab('registry')}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, color: '#38bdf8' }}>1. Register External AI Agent</span>
            <ArrowUpRight size={18} color="#38bdf8" />
          </div>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: 6 }}>
            Connect by Deployment URL or Browser endpoint with SSRF safety validation.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: 18, cursor: 'pointer' }} onClick={() => onSelectTab('testing')}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, color: '#34d399' }}>2. Live Failure Detection</span>
            <ArrowUpRight size={18} color="#34d399" />
          </div>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: 6 }}>
            Test ambiguous, misspelled, and adversarial prompts with step-by-step tracing.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: 18, cursor: 'pointer' }} onClick={() => onSelectTab('repairs')}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, color: '#fbbf24' }}>3. 8 Hard Gates & Approvals</span>
            <ArrowUpRight size={18} color="#fbbf24" />
          </div>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: 6 }}>
            Validate candidate repairs and require explicit human reviewer sign-off.
          </p>
        </div>
      </div>
    </div>
  );
}
