import React, { useState } from 'react';
import { X, GitBranch, PlusCircle, AlertCircle } from 'lucide-react';
import { api } from '../services/api';

export function ConnectRepoModal({ isOpen, onClose, onConnected }) {
  const [owner, setOwner] = useState('');
  const [name, setName] = useState('');
  const [defaultBranch, setDefaultBranch] = useState('main');
  const [cloneUrl, setCloneUrl] = useState('');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.85);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!owner.trim() || !name.trim()) {
      setError('Owner and Repository Name are required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        owner: owner.trim(),
        name: name.trim(),
        default_branch: defaultBranch.trim() || 'main',
        clone_url: cloneUrl.trim() || undefined,
        framework: 'fastapi',
        confidence_threshold: parseFloat(confidenceThreshold),
      };

      const newRepo = await api.connectRepository(payload);
      onConnected(newRepo);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to connect repository.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <GitBranch size={20} color="var(--primary)" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Connect GitHub Repository</h3>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{ background: 'var(--danger-bg)', border: '1px solid rgba(239, 68, 68, 0.3)', color: 'var(--danger)', padding: '12px', borderRadius: '6px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div className="form-group">
                <label className="form-label">Repository Owner</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. tiangolo or my-org"
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Repository Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. fastapi or backend-api"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Default Branch</label>
              <input
                type="text"
                className="form-input"
                placeholder="main"
                value={defaultBranch}
                onChange={(e) => setDefaultBranch(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Custom Clone URL (Optional)</label>
              <input
                type="text"
                className="form-input"
                placeholder="https://github.com/owner/repo.git or local path"
                value={cloneUrl}
                onChange={(e) => setCloneUrl(e.target.value)}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
                Leave blank to use default standard GitHub HTTPS clone URL.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">AI Auto-Publish Confidence Threshold ({Math.round(confidenceThreshold * 100)}%)</label>
              <input
                type="range"
                min="0.5"
                max="0.99"
                step="0.01"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(e.target.value)}
                style={{ width: '100%', accentColor: 'var(--primary)' }}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'block' }}>
                Changes with AI confidence below {Math.round(confidenceThreshold * 100)}% will be held for REVIEW REQUIRED.
              </span>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              <PlusCircle size={16} />
              {loading ? 'Connecting & Analyzing...' : 'Connect Repository'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
