import React, { useState } from 'react';
import { Header } from './components/Header';
import { SubmissionForm } from './components/SubmissionForm';
import { ReelCard } from './components/ReelCard';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { useReelTracker } from './hooks/useReelTracker';
import { BarChart3, Grid3X3, Plus } from 'lucide-react';

function App() {
  const {
    reels,
    user,
    isLoading,
    error,
    submitReel,
    bulkSubmitReels,
    deleteReel,
    getAnalytics,
    forceUpdate,
    clearError
  } = useReelTracker();

  const [activeTab, setActiveTab] = useState<'dashboard' | 'reels' | 'submit'>('dashboard');

  const analytics = getAnalytics();

  return (
    <div className="min-h-screen bg-gray-50">
      <Header 
        user={user} 
        onForceUpdate={forceUpdate}
        isUpdating={isLoading}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Tabs */}
        <div className="bg-white rounded-xl shadow-lg mb-8">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'dashboard'
                    ? 'border-purple-500 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <BarChart3 className="h-4 w-4" />
                  <span>Dashboard</span>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('reels')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'reels'
                    ? 'border-purple-500 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Grid3X3 className="h-4 w-4" />
                  <span>All Reels ({reels.length})</span>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('submit')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'submit'
                    ? 'border-purple-500 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Plus className="h-4 w-4" />
                  <span>Submit Reels</span>
                </div>
              </button>
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'dashboard' && (
          <AnalyticsDashboard analytics={analytics} />
        )}

        {activeTab === 'reels' && (
          <div>
            {reels.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {reels.map((reel) => (
                  <ReelCard
                    key={reel.id}
                    reel={reel}
                    onDelete={deleteReel}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="bg-gray-100 rounded-full w-24 h-24 flex items-center justify-center mx-auto mb-4">
                  <Grid3X3 className="h-12 w-12 text-gray-400" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No reels yet</h3>
                <p className="text-gray-500 mb-6">Start by submitting your first Instagram reel for tracking</p>
                <button
                  onClick={() => setActiveTab('submit')}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
                >
                  Submit Your First Reel
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'submit' && (
          <div className="max-w-2xl mx-auto">
            <SubmissionForm
              onSubmit={submitReel}
              onBulkSubmit={bulkSubmitReels}
              isLoading={isLoading}
              error={error}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;