import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, BookOpen, ExternalLink, Play, RefreshCw, GitCommit, 
  FileCode, Sparkles, ChevronRight, CheckCircle2, AlertCircle, Clock 
} from 'lucide-react';
import { api } from '../services/api';

export function RepositoryDetail({ repoId, onBack, onSelectChange }) {
  const [repo, setRepo] = useState(null);
  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    loadData();
  }, [repoId]);

  async function loadData() {
    setLoading(true);
    try {
      const [repoData, changesData] = await Promise.all([
        api.getRepository(repoId),
        api.getChanges(repoId),
      ]);
      setRepo(repoData);
      setChanges(changesData);
    } catch (err) {
      alert(`Failed to load repository: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyze() {
    setAnalyzing(true);
    try {
      await api.analyzeRepository(repoId, null, true);
      await loadData();
    } catch (err) {
      alert(`Analysis failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    try {
      await api.syncRepository(repoId);
      await loadData();
    } catch (err) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  }

  if (loading || !repo) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0', color: 'var(--text-muted)' }}>
        <RefreshCw size={24} className="spin" style={{ marginBottom: '12px' }} />
        <p>Loading repository details...</p>
      </div>
    );
  }

  return (
    <div>
      {/* Back Button */}
      <button onClick={onBack} className="btn btn-outline btn-sm" style={{ marginBottom: '20px' }}>
        <ArrowLeft size={14} />
        Back to Repositories
      </button>

      {/* Header Card */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h1 style={{ fontSize: '1.6rem', fontWeight: 700 }}>{repo.full_name}</h1>
              <span
                className="status-pill"
                style={{
                  background: repo.status === 'SYNCED' ? 'var(--success-bg)' : 'var(--warning-bg)',
                  color: repo.status === 'SYNCED' ? 'var(--success)' : 'var(--warning)',
                }}
              >
                <span className="pulse-dot"></span>
                {repo.status}
              </span>
            </div>

            <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              <span>Branch: <strong style={{ color: 'var(--text-main)' }}>{repo.default_branch}</strong></span>
              <span>•</span>
              <span>Framework: <strong style={{ color: 'var(--info)' }}>{repo.framework.toUpperCase()}</strong></span>
              <span>•</span>
              <span>Doc Version: <strong style={{ color: 'var(--success)' }}>v{repo.latest_documentation_version || 1}</strong></span>
              <span>•</span>
              <span>Confidence Threshold: <strong style={{ color: 'var(--text-main)' }}>{Math.round(repo.confidence_threshold * 100)}%</strong></span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <a
              href={api.getSwaggerUrl(repo.id)}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary"
            >
              <BookOpen size={16} />
              Open Live Swagger UI
              <ExternalLink size={14} />
            </a>

            <button onClick={handleAnalyze} className="btn btn-secondary" disabled={analyzing}>
              <Play size={16} />
              {analyzing ? 'Analyzing...' : 'Run Analysis'}
            </button>

            <button onClick={handleSync} className="btn btn-secondary" disabled={syncing}>
              <RefreshCw size={16} />
              {syncing ? 'Syncing...' : 'Sync Git'}
            </button>
          </div>
        </div>
      </div>

      {/* API Changes History Section */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Detected API Changes & Reasoning History</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginTop: '2px' }}>
              Semantic change reasoning, impact ratings, and code traceability for each detected API modification.
            </p>
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Total: <strong>{changes.length}</strong> changes
          </span>
        </div>

        {changes.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            <CheckCircle2 size={32} color="var(--success)" style={{ margin: '0 auto 12px' }} />
            <h4 style={{ color: 'var(--text-main)', marginBottom: '4px' }}>API Documentation is Fully Synchronized</h4>
            <p style={{ fontSize: '0.85rem' }}>No pending or unrecorded API changes detected. Click "Run Analysis" to scan new commits.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {changes.map((ch) => {
              const severity = ch.impact_analysis?.severity || 'LOW';
              const confidencePercent = Math.round((ch.confidence || 1.0) * 100);

              return (
                <div
                  key={ch.id}
                  className="card"
                  style={{ padding: '16px 20px', cursor: 'pointer' }}
                  onClick={() => onSelectChange(ch)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span className={`method-badge method-${ch.method}`}>{ch.method}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.95rem' }}>
                        {ch.path}
                      </span>
                      <span className={`type-badge type-${ch.change_type}`}>{ch.change_type}</span>
                      <span className={`impact-badge impact-${severity}`}>{severity}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <FileCode size={13} />
                        <span>{ch.source_file || 'app/main.py'}:{ch.source_line || 1}</span>
                      </div>

                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: confidencePercent >= 85 ? 'var(--success)' : 'var(--warning)' }}>
                        {confidencePercent}% AI Confidence
                      </div>

                      <button className="btn btn-outline btn-sm" style={{ padding: '4px 8px' }}>
                        Inspect
                        <ChevronRight size={14} />
                      </button>
                    </div>
                  </div>

                  <div style={{ marginTop: '10px', fontSize: '0.88rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Sparkles size={14} color="#a5b4fc" />
                    <span>{ch.ai_explanation || ch.summary || 'API structure modified in codebase.'}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
