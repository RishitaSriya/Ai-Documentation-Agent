import React from 'react';
import { Sparkles, Activity, ShieldCheck, RefreshCw } from 'lucide-react';

export function Navbar({ health, onRefresh, onHomeClick }) {
  return (
    <nav className="navbar">
      <div 
        className="nav-brand" 
        onClick={onHomeClick} 
        style={{ cursor: 'pointer' }}
      >
        <div className="brand-icon">
          <Sparkles size={20} />
        </div>
        <div>
          <span>AI API Documentation Agent</span>
          <span style={{ fontSize: '0.75rem', display: 'block', color: 'var(--text-dim)', fontWeight: 400 }}>
            Automated Git → OpenAPI Synchronization
          </span>
        </div>
      </div>

      <div className="nav-status">
        {health ? (
          <div className="status-pill status-healthy" title={`Service: ${health.service} (${health.environment})`}>
            <span className="pulse-dot"></span>
            <span>API Online ({health.llm_provider.toUpperCase()} AI)</span>
          </div>
        ) : (
          <div className="status-pill" style={{ background: 'var(--danger-bg)', color: 'var(--danger)' }}>
            <span className="pulse-dot"></span>
            <span>Backend Offline</span>
          </div>
        )}

        <button 
          onClick={onRefresh} 
          className="btn btn-secondary btn-sm"
          title="Refresh Data"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>
    </nav>
  );
}
