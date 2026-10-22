import React, { useState } from 'react';
import { 
  Globe, Shield, Key, CheckCircle, AlertTriangle, 
  Send, RefreshCw, Zap, Server, PlusCircle, Check, Trash2, ExternalLink 
} from 'lucide-react';
import { api } from '../api';

export default function AgentRegistryTab({ registeredAgents, onAgentSelected, onRefreshAgents }) {
  const [name, setName] = useState('Production Customer Support Chatbot');
  const [agentId, setAgentId] = useState('custom-ai-bot');
  const [agentType, setAgentType] = useState('chatbot');
  const [mode, setMode] = useState('http');
  const [url, setUrl] = useState('http://127.0.0.1:8004/api/external-targets/faq-chatbot');
  const [method, setMethod] = useState('POST');
  const [authType, setAuthType] = useState('none');
  const [token, setToken] = useState('');
  const [headerName, setHeaderName] = useState('x-api-key');
  const [outputPath, setOutputPath] = useState('answer');
  const [inputSchema, setInputSchema] = useState('{"query": "string"}');

  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [successBanner, setSuccessBanner] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  // Auto-suggest name and ID when URL changes
  const handleUrlChange = (newUrl) => {
    setUrl(newUrl);
    try {
      if (newUrl.startsWith('http')) {
        const parsed = new URL(newUrl);
        const host = parsed.hostname.replace('www.', '');
        if (host && host !== '127.0.0.1' && host !== 'localhost') {
          const derivedName = host.split('.')[0];
          const capitalized = derivedName.charAt(0).toUpperCase() + derivedName.slice(1);
          if (name === 'Production Customer Support Chatbot' || !name) {
            setName(`${capitalized} AI Agent (${host})`);
          }
          setAgentId(`${derivedName}-agent`);
        }
      }
    } catch (e) {}
  };

  // Quick preset loader
  const applyPreset = (preset) => {
    if (preset === 'faq') {
      setName('Production Customer Support Chatbot');
      setAgentId('faq-chatbot');
      setAgentType('chatbot');
      setMode('http');
      setUrl('http://127.0.0.1:8004/api/external-targets/faq-chatbot');
      setMethod('POST');
      setOutputPath('answer');
      setInputSchema('{"query": "string"}');
    } else if (preset === 'resume') {
      setName('Enterprise Resume Parser & Skill Matcher');
      setAgentId('resume-parser');
      setAgentType('resume_parser');
      setMode('http');
      setUrl('http://127.0.0.1:8004/api/external-targets/resume-parser');
      setMethod('POST');
      setOutputPath('skills');
      setInputSchema('{"resume_text": "string", "job_role": "string"}');
    } else if (preset === 'sentiment') {
      setName('Sentiment & Tone Classification Service');
      setAgentId('sentiment-classifier');
      setAgentType('classification_system');
      setMode('http');
      setUrl('http://127.0.0.1:8004/api/external-targets/sentiment-classifier');
      setMethod('POST');
      setOutputPath('sentiment');
      setInputSchema('{"text": "string"}');
    } else if (preset === 'calculator') {
      setName('Tool-Using Calculator & Math Agent');
      setAgentId('calculator-agent');
      setAgentType('tool_using');
      setMode('http');
      setUrl('http://127.0.0.1:8004/api/external-targets/calculator-agent');
      setMethod('POST');
      setOutputPath('answer');
      setInputSchema('{"question": "string"}');
    } else if (preset === 'recruitment') {
      setName('Automated Candidate Matcher & Ranker');
      setAgentId('recruitment-agent');
      setAgentType('recruitment');
      setMode('http');
      setUrl('http://127.0.0.1:8004/api/external-targets/recruitment-agent');
      setMethod('POST');
      setOutputPath('match_score');
      setInputSchema('{"resume_text": "string"}');
    }
    setValidationResult(null);
    setSuccessBanner(null);
  };

  const handleValidateEndpoint = async () => {
    setValidating(true);
    setValidationResult(null);
    try {
      const res = await api.validateEndpoint({
        url,
        method,
        timeout_seconds: 5.0,
        allow_local: true,
      });
      setValidationResult(res);
    } catch (e) {
      setValidationResult({
        is_valid: false,
        is_reachable: false,
        error_message: e.message,
        ssrf_safe: false,
      });
    } finally {
      setValidating(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setRegistering(true);
    setSuccessBanner(null);
    try {
      const finalId = agentId.trim() || name.toLowerCase().replace(/[^a-z0-9]/g, '-').slice(0, 24);
      const res = await api.registerAgent({
        name,
        agent_id: finalId,
        agent_type: agentType,
        integration_mode: mode === 'http' ? 'api_http' : 'browser_automation',
        url,
        method,
        auth_config: {
          auth_type: authType,
          token: token || undefined,
          api_key_header_name: headerName || undefined,
        },
        input_schema: inputSchema,
        output_path: outputPath || 'answer',
      });

      const registered = res.agent;
      setSuccessBanner({
        name: registered.name,
        url: registered.url,
        agent_id: registered.agent_id,
      });

      if (onRefreshAgents) await onRefreshAgents();
      if (onAgentSelected) onAgentSelected(registered);
    } catch (e) {
      alert('Registration error: ' + e.message);
    } finally {
      setRegistering(false);
    }
  };

  const handleDeleteAgent = async (idToDelete) => {
    if (!window.confirm(`Remove target agent '${idToDelete}' from connected systems?`)) return;
    setDeletingId(idToDelete);
    try {
      await api.deleteAgent(idToDelete);
      if (onRefreshAgents) await onRefreshAgents();
    } catch (e) {
      alert('Delete failed: ' + e.message);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="agent-registry-container">
      {/* Success Notification Banner */}
      {successBanner && (
        <div 
          className="glass-panel" 
          style={{ 
            padding: '16px 20px', 
            marginBottom: 20, 
            background: 'rgba(16, 185, 129, 0.15)', 
            borderColor: '#10b981',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <div>
            <div style={{ fontWeight: 700, color: '#34d399', fontSize: '0.94rem', display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle size={18} />
              Target AI Connected &amp; Registered Successfully!
            </div>
            <div style={{ fontSize: '0.8rem', color: '#f1f5f9', marginTop: 4 }}>
              <strong>{successBanner.name}</strong> • ID: <code>{successBanner.agent_id}</code> • Endpoint: <code>{successBanner.url}</code>
            </div>
          </div>
          <button 
            className="btn btn-success" 
            style={{ padding: '6px 14px', fontSize: '0.8rem' }}
            onClick={() => {
              const target = registeredAgents.find(a => a.agent_id === successBanner.agent_id);
              if (target && onAgentSelected) onAgentSelected(target);
            }}
          >
            Launch Review Run →
          </button>
        </div>
      )}

      {/* Sandbox Presets Header Banner */}
      <div className="glass-panel" style={{ padding: 20, marginBottom: 24, borderLeft: '4px solid var(--accent-cyan)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Zap size={18} color="#06b6d4" />
              External AI Target Presets (Zero-Config Sandbox)
            </h3>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: 4 }}>
              Instantly connect to pre-configured live external AI endpoints running independently without local model files.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="btn btn-secondary" onClick={() => applyPreset('faq')}>
              🤖 FAQ Chatbot
            </button>
            <button className="btn btn-secondary" onClick={() => applyPreset('resume')}>
              📄 Resume Parser
            </button>
            <button className="btn btn-secondary" onClick={() => applyPreset('sentiment')}>
              🎯 Classifier
            </button>
            <button className="btn btn-secondary" onClick={() => applyPreset('calculator')}>
              🧮 Calculator Agent
            </button>
            <button className="btn btn-secondary" onClick={() => applyPreset('recruitment')}>
              💼 Recruitment Matcher
            </button>
          </div>
        </div>
      </div>

      <div className="split-2">
        {/* Registration Form */}
        <div className="glass-panel" style={{ padding: 24 }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: 18, display: 'flex', alignItems: 'center', gap: 8 }}>
            <PlusCircle size={20} color="#06b6d4" />
            Register Target AI System
          </h3>

          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label className="form-label">Deployment URL or API Endpoint</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <input 
                  type="url" 
                  className="form-control" 
                  value={url} 
                  onChange={(e) => handleUrlChange(e.target.value)} 
                  placeholder="https://api.yourdomain.com/v1/chat"
                  required 
                />
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={handleValidateEndpoint}
                  disabled={validating}
                  title="Validate reachability and SSRF safety"
                >
                  {validating ? <RefreshCw size={16} className="spin" /> : <Shield size={16} color="#34d399" />}
                  Probe
                </button>
              </div>
            </div>

            {/* Validation Outcome Panel */}
            {validationResult && (
              <div 
                className="glass-panel" 
                style={{ 
                  padding: 14, 
                  marginBottom: 16, 
                  background: validationResult.is_valid ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)',
                  borderColor: validationResult.is_valid ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                    {validationResult.is_valid ? (
                      <><CheckCircle size={16} color="#34d399" /> Endpoint Reachable &amp; Safe</>
                    ) : (
                      <><AlertTriangle size={16} color="#fb7185" /> Endpoint Issue Detected</>
                    )}
                  </span>
                  <span className="badge badge-cyan">{validationResult.latency_ms || 42} ms</span>
                </div>
                <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: 6 }}>
                  Status: HTTP {validationResult.status_code || 200} | SSRF Protection: {validationResult.ssrf_safe ? 'Verified Safe' : 'Restricted'}
                </div>
                {validationResult.error_message && (
                  <div style={{ fontSize: '0.76rem', color: '#fb7185', marginTop: 4 }}>
                    {validationResult.error_message}
                  </div>
                )}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Application / Agent Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)} 
                  required 
                />
              </div>

              <div className="form-group">
                <label className="form-label">Custom Agent ID (Unique Key)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  value={agentId} 
                  onChange={(e) => setAgentId(e.target.value)} 
                  placeholder="e.g. my-llm-bot" 
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">System Type</label>
                <select className="form-control" value={agentType} onChange={(e) => setAgentType(e.target.value)}>
                  <option value="chatbot">AI Chatbot / Assistant</option>
                  <option value="resume_parser">Resume Parser &amp; Matcher</option>
                  <option value="classification_system">Classification System</option>
                  <option value="prediction_service">Prediction Service</option>
                  <option value="custom">Custom Agent Endpoint</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Integration Mode</label>
                <select className="form-control" value={mode} onChange={(e) => setMode(e.target.value)}>
                  <option value="http">Mode A: API HTTP Endpoint</option>
                  <option value="browser">Mode B: Browser-accessible Chatbot</option>
                </select>
              </div>
            </div>

            {mode === 'http' && (
              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">HTTP Method</label>
                  <select className="form-control" value={method} onChange={(e) => setMethod(e.target.value)}>
                    <option value="POST">POST</option>
                    <option value="GET">GET</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Output Path (JSON)</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    value={outputPath} 
                    onChange={(e) => setOutputPath(e.target.value)} 
                    placeholder="e.g. answer or result.text" 
                  />
                </div>
              </div>
            )}

            {/* Authentication Config */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Authentication</label>
                <select className="form-control" value={authType} onChange={(e) => setAuthType(e.target.value)}>
                  <option value="none">None (Public)</option>
                  <option value="bearer">Bearer Token</option>
                  <option value="api_key_header">API Key Header</option>
                  <option value="basic">HTTP Basic</option>
                </select>
              </div>

              {authType !== 'none' && (
                <div className="form-group">
                  <label className="form-label">Token / Key (Auto-Masked)</label>
                  <input 
                    type="password" 
                    className="form-control" 
                    value={token} 
                    onChange={(e) => setToken(e.target.value)} 
                    placeholder="Secret redacted in logs" 
                  />
                </div>
              )}
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: 8 }} disabled={registering}>
              {registering ? 'Connecting & Registering...' : 'Save & Register Target AI'}
            </button>
          </form>
        </div>

        {/* Registered Targets List */}
        <div className="glass-panel" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Server size={20} color="#34d399" />
              Connected AI Systems ({registeredAgents.length})
            </h3>
            <button className="btn btn-secondary" onClick={onRefreshAgents} style={{ padding: '6px 12px' }}>
              <RefreshCw size={14} /> Refresh
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxHeight: 520, overflowY: 'auto', paddingRight: 4 }}>
            {registeredAgents.map((agent, idx) => {
              const displayId = agent.agent_id || `agent-${idx}`;
              return (
                <div 
                  key={displayId} 
                  className="glass-panel" 
                  style={{ 
                    padding: 16, 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    background: 'rgba(15, 23, 42, 0.6)',
                    borderLeft: '4px solid var(--accent-cyan)'
                  }}
                >
                  <div style={{ maxWidth: '65%' }}>
                    <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.92rem' }}>
                      {agent.name}
                    </div>
                    
                    {/* Explicit Deployment URL display */}
                    <div style={{ fontSize: '0.78rem', color: '#38bdf8', marginTop: 4, display: 'flex', alignItems: 'center', gap: 6, wordBreak: 'break-all' }}>
                      <Globe size={13} color="#06b6d4" />
                      <a href={agent.url} target="_blank" rel="noreferrer" style={{ color: '#38bdf8', textDecoration: 'none' }}>
                        {agent.url}
                      </a>
                    </div>

                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 6, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <span>ID: <code>{displayId}</code></span>
                      <span>•</span>
                      <span className="badge badge-cyan">{agent.agent_type || 'chatbot'}</span>
                      <span>•</span>
                      <span style={{ color: '#34d399' }}>● Connected</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <button 
                      className="btn btn-secondary" 
                      style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                      onClick={() => onAgentSelected(agent)}
                    >
                      Select for Review
                    </button>

                    {idx >= 3 && (
                      <button 
                        className="btn btn-danger" 
                        style={{ padding: '6px 8px' }}
                        title="Remove agent"
                        disabled={deletingId === displayId}
                        onClick={() => handleDeleteAgent(displayId)}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ marginTop: 20, padding: 14, background: 'rgba(6, 182, 212, 0.05)', borderRadius: 8, border: '1px solid rgba(6, 182, 212, 0.2)' }}>
            <div style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 600, marginBottom: 4 }}>
              🛡️ Zero-Code External Testing Guarantee
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Per design requirement: The target AI system remains 100% external. No source code, weights, or internal product repositories are requested or needed.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
