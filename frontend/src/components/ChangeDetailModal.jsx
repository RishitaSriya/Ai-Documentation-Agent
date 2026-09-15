import React from 'react';
import { X, Sparkles, AlertTriangle, CheckCircle, Code, GitCommit, FileCode } from 'lucide-react';

export function ChangeDetailModal({ change, onClose }) {
  if (!change) return null;

  const severity = change.impact_analysis?.severity || 'LOW';
  const reason = change.impact_analysis?.reason || 'Non-breaking update';
  const confidencePercent = Math.round((change.confidence || 1.0) * 100);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '800px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className={`method-badge method-${change.method}`}>{change.method}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '1rem' }}>{change.path}</span>
            <span className={`type-badge type-${change.change_type}`}>{change.change_type}</span>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* AI Explanation Banner */}
          <div style={{ background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: '8px', padding: '16px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', color: '#a5b4fc', fontWeight: 600, fontSize: '0.85rem' }}>
              <Sparkles size={16} />
              AI Agent Explanation
            </div>
            <p style={{ color: 'var(--text-main)', fontSize: '0.92rem' }}>
              {change.ai_explanation || change.summary || 'Detected change in backend source code.'}
            </p>
          </div>

          {/* Metrics Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '20px' }}>
            <div className="card" style={{ padding: '14px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>
                API Impact
              </span>
              <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`impact-badge impact-${severity}`}>{severity}</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>{reason}</p>
            </div>

            <div className="card" style={{ padding: '14px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>
                AI Confidence
              </span>
              <div style={{ marginTop: '6px', fontSize: '1.25rem', fontWeight: 700, color: confidencePercent >= 85 ? 'var(--success)' : 'var(--warning)' }}>
                {confidencePercent}%
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>Status: {change.status}</p>
            </div>

            <div className="card" style={{ padding: '14px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>
                Source Traceability
              </span>
              <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--info)' }}>
                <FileCode size={14} />
                <span>{change.source_file || 'app/main.py'}:{change.source_line || 1}</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Commit: {change.commit_sha ? change.commit_sha.substring(0, 7) : 'HEAD'}
              </p>
            </div>
          </div>

          {/* Before vs After Diff Section */}
          <div>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px' }}>
              Structural API Snapshot (Before vs After)
            </h4>
            <div className="diff-container">
              <div>
                <div className="diff-header" style={{ color: 'var(--danger)' }}>← Previous API Structure</div>
                <div className="diff-box">
                  <pre style={{ margin: 0 }}>
                    {change.old_structure ? JSON.stringify(change.old_structure, null, 2) : '// No previous structure (New endpoint)'}
                  </pre>
                </div>
              </div>

              <div>
                <div className="diff-header" style={{ color: 'var(--success)' }}>→ Updated API Structure</div>
                <div className="diff-box">
                  <pre style={{ margin: 0 }}>
                    {change.new_structure ? JSON.stringify(change.new_structure, null, 2) : '// Removed'}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
