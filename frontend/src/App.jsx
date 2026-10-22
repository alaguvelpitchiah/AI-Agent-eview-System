import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, Activity, Server, Sliders, Terminal, 
  GitBranch, Network, Wrench, Award, History, Download, 
  RefreshCw, CheckCircle2, User 
} from 'lucide-react';

import { api } from './api';
import OverviewTab from './components/OverviewTab';
import AgentRegistryTab from './components/AgentRegistryTab';
import TestRunnerTab from './components/TestRunnerTab';
import RootCauseTab from './components/RootCauseTab';
import FaultInteractionTab from './components/FaultInteractionTab';
import RepairCenterTab from './components/RepairCenterTab';
import BenchmarkTab from './components/BenchmarkTab';
import AuditTab from './components/AuditTab';
import ReportsTab from './components/ReportsTab';
import ApprovalModal from './components/ApprovalModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [health, setHealth] = useState({
    status: 'ok',
    server_port: 8004,
    streamlit_port: 8501,
    scenarios_count: 39,
    approvals_count: 1,
  });

  const [agents, setAgents] = useState([
    {
      agent_id: 'faq-chatbot',
      name: 'Production Customer Support Chatbot',
      agent_type: 'chatbot',
      url: 'http://127.0.0.1:8004/api/external-targets/faq-chatbot'
    },
    {
      agent_id: 'resume-parser',
      name: 'Enterprise Resume Parser & Skill Matcher',
      agent_type: 'resume_parser',
      url: 'http://127.0.0.1:8004/api/external-targets/resume-parser'
    },
    {
      agent_id: 'sentiment-classifier',
      name: 'Sentiment & Tone Classification Service',
      agent_type: 'classification_system',
      url: 'http://127.0.0.1:8004/api/external-targets/sentiment-classifier'
    },
    {
      agent_id: 'calculator-agent',
      name: 'Tool-Using Calculator & Math Agent',
      agent_type: 'tool_using',
      url: 'http://127.0.0.1:8004/api/external-targets/calculator-agent'
    },
    {
      agent_id: 'recruitment-agent',
      name: 'Automated Candidate Matcher & Ranker',
      agent_type: 'recruitment',
      url: 'http://127.0.0.1:8004/api/external-targets/recruitment-agent'
    }
  ]);

  const [selectedAgent, setSelectedAgent] = useState(agents[0]);
  const [approvalModalRepair, setApprovalModalRepair] = useState(null);

  const fetchHealthAndAgents = async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
      const a = await api.listAgents();
      if (a && a.length > 0) {
        setAgents(a);
        setSelectedAgent(prev => {
          if (!prev) return a[0];
          const matched = a.find(item => item.agent_id === prev.agent_id);
          return matched || a[0];
        });
      }
    } catch (e) {
      console.warn('API health check offline, using local state.');
    }
  };

  useEffect(() => {
    fetchHealthAndAgents();
    const timer = setInterval(fetchHealthAndAgents, 15000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="app-root">
      {/* Top Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon-box">🛡️</div>
          <div>
            <div className="brand-title">AI Agent Review &amp; Performance Improvement System</div>
            <div className="brand-subtitle">Autonomous Black-Box Evaluation • Scientific RCA • 8 Hard Gates • Governance</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Target Agent Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Target AI:</span>
            <select 
              className="form-control" 
              style={{ width: 220, padding: '6px 10px', fontSize: '0.8rem' }}
              value={selectedAgent?.agent_id || ''} 
              onChange={(e) => {
                const found = agents.find(a => a.agent_id === e.target.value);
                if (found) setSelectedAgent(found);
              }}
            >
              {agents.map(a => (
                <option key={a.agent_id} value={a.agent_id}>{a.name}</option>
              ))}
            </select>
          </div>

          {/* Microservice Health Indicators */}
          <div className="health-strip">
            <span className="health-dot" />
            <span style={{ fontSize: '0.76rem', color: '#cbd5e1' }}>Port 8004: <strong>Online</strong></span>
            <span style={{ color: '#475569' }}>|</span>
            <span style={{ fontSize: '0.76rem', color: '#94a3b8' }}>Streamlit: <strong>:8501</strong></span>
          </div>

          {/* User Reviewer Profile */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(255,255,255,0.05)', padding: '6px 12px', borderRadius: 20 }}>
            <User size={16} color="#06b6d4" />
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#f8fafc' }}>Reviewer (Staff)</span>
          </div>
        </div>
      </header>

      {/* Top Navigation Tabs */}
      <nav className="nav-tab-bar">
        <button className={`nav-tab-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
          <Activity size={16} /> Overview &amp; KPIs
        </button>
        <button className={`nav-tab-btn ${activeTab === 'registry' ? 'active' : ''}`} onClick={() => setActiveTab('registry')}>
          <Server size={16} /> 1. Agent Integration &amp; Registry
        </button>
        <button className={`nav-tab-btn ${activeTab === 'testing' ? 'active' : ''}`} onClick={() => setActiveTab('testing')}>
          <Terminal size={16} /> 2. Live Monitoring &amp; Failures
        </button>
        <button className={`nav-tab-btn ${activeTab === 'rca' ? 'active' : ''}`} onClick={() => setActiveTab('rca')}>
          <GitBranch size={16} /> 3. Root-Cause Diagnosis (RCA)
        </button>
        <button className={`nav-tab-btn ${activeTab === 'interactions' ? 'active' : ''}`} onClick={() => setActiveTab('interactions')}>
          <Network size={16} /> 4. Fault Interactions ($2^k$)
        </button>
        <button className={`nav-tab-btn ${activeTab === 'repairs' ? 'active' : ''}`} onClick={() => setActiveTab('repairs')}>
          <Wrench size={16} /> 5. Repairs &amp; 8 Hard Gates
        </button>
        <button className={`nav-tab-btn ${activeTab === 'benchmark' ? 'active' : ''}`} onClick={() => setActiveTab('benchmark')}>
          <Award size={16} /> 6. Evaluation Benchmark
        </button>
        <button className={`nav-tab-btn ${activeTab === 'audit' ? 'active' : ''}`} onClick={() => setActiveTab('audit')}>
          <History size={16} /> Audit Trail &amp; Governance
        </button>
        <button className={`nav-tab-btn ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>
          <Download size={16} /> Download Reports
        </button>
      </nav>

      {/* Main Content Pane */}
      <main className="app-content">
        {activeTab === 'overview' && (
          <OverviewTab stats={health} onSelectTab={(tab) => setActiveTab(tab)} />
        )}
        {activeTab === 'registry' && (
          <AgentRegistryTab 
            registeredAgents={agents} 
            onAgentSelected={(agent) => { setSelectedAgent(agent); setActiveTab('testing'); }}
            onRefreshAgents={fetchHealthAndAgents}
          />
        )}
        {activeTab === 'testing' && (
          <TestRunnerTab 
            selectedAgent={selectedAgent} 
            agents={agents} 
            onSelectAgent={setSelectedAgent} 
          />
        )}
        {activeTab === 'rca' && (
          <RootCauseTab />
        )}
        {activeTab === 'interactions' && (
          <FaultInteractionTab />
        )}
        {activeTab === 'repairs' && (
          <RepairCenterTab onOpenApprovalModal={(rep) => setApprovalModalRepair(rep)} />
        )}
        {activeTab === 'benchmark' && (
          <BenchmarkTab />
        )}
        {activeTab === 'audit' && (
          <AuditTab />
        )}
        {activeTab === 'reports' && (
          <ReportsTab 
            selectedAgent={selectedAgent} 
            agents={agents} 
            onSelectAgent={setSelectedAgent} 
          />
        )}
      </main>

      {/* Human Approval Sign-Off Modal */}
      {approvalModalRepair && (
        <ApprovalModal 
          repair={approvalModalRepair} 
          onClose={() => setApprovalModalRepair(null)} 
          onSuccess={fetchHealthAndAgents}
        />
      )}
    </div>
  );
}
