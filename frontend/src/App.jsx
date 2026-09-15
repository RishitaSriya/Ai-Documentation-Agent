import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { RepositoryList } from './components/RepositoryList';
import { RepositoryDetail } from './components/RepositoryDetail';
import { ConnectRepoModal } from './components/ConnectRepoModal';
import { ChangeDetailModal } from './components/ChangeDetailModal';
import { api } from './services/api';

export function App() {
  const [health, setHealth] = useState(null);
  const [repositories, setRepositories] = useState([]);
  const [selectedRepoId, setSelectedRepoId] = useState(null);
  const [selectedChange, setSelectedChange] = useState(null);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadInitialData();
  }, []);

  async function loadInitialData() {
    try {
      const [healthData, reposData] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getRepositories().catch(() => []),
      ]);
      setHealth(healthData);
      setRepositories(reposData);
    } catch (err) {
      console.error('Failed to load initial dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }

  function handleRepoConnected(newRepo) {
    setRepositories((prev) => [newRepo, ...prev]);
    setSelectedRepoId(newRepo.id);
  }

  return (
    <div className="app-container">
      <Navbar
        health={health}
        onRefresh={loadInitialData}
        onHomeClick={() => setSelectedRepoId(null)}
      />

      <main className="main-content">
        {selectedRepoId ? (
          <RepositoryDetail
            repoId={selectedRepoId}
            onBack={() => setSelectedRepoId(null)}
            onSelectChange={(ch) => setSelectedChange(ch)}
          />
        ) : (
          <RepositoryList
            repositories={repositories}
            onSelectRepo={(id) => setSelectedRepoId(id)}
            onOpenConnectModal={() => setIsConnectModalOpen(true)}
            onRefresh={loadInitialData}
          />
        )}
      </main>

      {/* Connect Repository Modal */}
      <ConnectRepoModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        onConnected={handleRepoConnected}
      />

      {/* API Change Inspection Modal */}
      <ChangeDetailModal
        change={selectedChange}
        onClose={() => setSelectedChange(null)}
      />
    </div>
  );
}

export default App;
