import React from 'react';
import { GitBranch, ExternalLink, RefreshCw, Play, BookOpen, Clock, Layers, Plus } from 'lucide-react';
import { api } from '../services/api';

export function RepositoryList({ repositories, onSelectRepo, onOpenConnectModal, onRefresh }) {
  async function handleQuickAnalyze(e, repoId) {
    e.stopPropagation();
    try {
      await api.analyzeRepository(repoId, null, true);
      onRefresh();
    } catch (err) {
      alert(`Analysis failed: ${err.message}`);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>Connected Repositories</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
            Monitored backend repositories with automated OpenAPI tracking and synchronization.
          </p>
        </div>

        <button onClick={onOpenConnectModal} className="btn btn-primary">
          <Plus size={16} />
          Connect Repository
        </button>
      </div>

      {repositories.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ background: 'rgba(99, 102, 241, 0.1)', width: '60px', height: '60px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <GitBranch size={28} color="var(--primary)" />
          </div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '8px' }}>No Repositories Connected</h3>
          <p style={{ color: 'var(--text-muted)', maxWidth: '450px', margin: '0 auto 20px', fontSize: '0.9rem' }}>
            Connect a FastAPI backend repository to automatically track API changes from code commits and generate synchronized OpenAPI docs.
          </p>
          <button onClick={onOpenConnectModal} className="btn btn-primary">
            <Plus size={16} />
            Connect Your First Repository
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '20px' }}>
          {repositories.map((repo) => (
            <div
              key={repo.id}
              className="card"
              style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
              onClick={() => onSelectRepo(repo.id)}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      {repo.full_name}
                    </h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <GitBranch size={12} />
                        {repo.default_branch}
                      </span>
                      <span>•</span>
                      <span style={{ textTransform: 'uppercase', fontWeight: 600, color: 'var(--info)' }}>
                        {repo.framework}
                      </span>
                    </div>
                  </div>

                  <span
                    className="status-pill"
                    style={{
                      background: repo.status === 'SYNCED' ? 'var(--success-bg)' : repo.status === 'PROCESSING' ? 'var(--info-bg)' : 'var(--warning-bg)',
                      color: repo.status === 'SYNCED' ? 'var(--success)' : repo.status === 'PROCESSING' ? 'var(--info)' : 'var(--warning)',
                    }}
                  >
                    <span className="pulse-dot"></span>
                    {repo.status}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', padding: '12px 0', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)', margin: '12px 0' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>API Changes</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '2px' }}>
                      {repo.api_changes_count}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Documentation</span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '2px' }}>
                      {repo.latest_documentation_version ? `v${repo.latest_documentation_version}` : 'None'}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Clock size={12} />
                  <span>Last Commit: {repo.last_processed_commit ? repo.last_processed_commit.substring(0, 7) : 'Not analyzed'}</span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <a
                  href={api.getSwaggerUrl(repo.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary btn-sm"
                  style={{ flex: 1 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <BookOpen size={14} />
                  Swagger UI
                  <ExternalLink size={12} />
                </a>

                <button
                  onClick={(e) => handleQuickAnalyze(e, repo.id)}
                  className="btn btn-primary btn-sm"
                  title="Run API Analysis Pipeline"
                >
                  <Play size={14} />
                  Analyze
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
