import React, { useState } from 'react';
import { AuthProvider, useAuth } from './lib/auth-context';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import MediaRationalePage from './pages/MediaRationalePage';
import PremiumRationalePage from './pages/PremiumRationalePage';
import ManualRationalePage from './pages/ManualRationalePage';
import BulkRationalePage from './pages/BulkRationalePage';
import TranscriptRationalePage from './pages/TranscriptRationalePage';
import GenerateChartPage from './pages/GenerateChartPage';
import GenerateYoutubeCaptionPage from './pages/GenerateYoutubeCaptionPage';
import ActivityLogPage from './pages/ActivityLogPage';
import SavedRationalePage from './pages/SavedRationalePage';
import ProfilePage from './pages/ProfilePage';
import ApiKeysPage from './pages/ApiKeysPage';
import UsersPage from './pages/UsersPage';
import PdfTemplatePage from './pages/PdfTemplatePage';
import UploadFilesPage from './pages/UploadFilesPage';
import ChannelLogosPage from './pages/ChannelLogosPage';
import { Toaster } from './components/ui/sonner';

type PageType = 
  | 'login'
  | 'dashboard'
  | 'media-rationale'
  | 'premium-rationale'
  | 'manual-rationale'
  | 'bulk-rationale'
  | 'transcript-rationale'
  | 'generate-chart'
  | 'youtube-caption'
  | 'activity-log'
  | 'saved-rationale'
  | 'profile'
  | 'api-keys'
  | 'users'
  | 'pdf-template'
  | 'upload-files'
  | 'channel-logos'
  | 'settings'
  | 'job-details';

function AppContent() {
  const { isAuthenticated } = useAuth();
  const [currentPage, setCurrentPage] = useState<PageType>('login');
  const [selectedJobId, setSelectedJobId] = useState<string | undefined>();

  const handleNavigate = (page: string, jobId?: string) => {
    setCurrentPage(page as PageType);
    setSelectedJobId(jobId);
  };

  const handleLoginSuccess = () => {
    setCurrentPage('dashboard');
  };

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage onNavigate={handleNavigate} />;
      case 'media-rationale':
        return <MediaRationalePage onNavigate={handleNavigate} selectedJobId={selectedJobId} />;
      case 'premium-rationale':
        return <PremiumRationalePage onNavigate={handleNavigate} selectedJobId={selectedJobId} />;
      case 'manual-rationale':
        return <ManualRationalePage key={selectedJobId} selectedJobId={selectedJobId} onNavigate={handleNavigate} />;
      case 'bulk-rationale':
        return <BulkRationalePage onNavigate={handleNavigate} selectedJobId={selectedJobId} />;
      case 'transcript-rationale':
        return <TranscriptRationalePage onNavigate={handleNavigate} selectedJobId={selectedJobId} />;
      case 'generate-chart':
        return <GenerateChartPage onNavigate={handleNavigate} />;
      case 'youtube-caption':
        return <GenerateYoutubeCaptionPage onNavigate={handleNavigate} />;
      case 'activity-log':
        return <ActivityLogPage />;
      case 'saved-rationale':
        return <SavedRationalePage onNavigate={handleNavigate} />;
      case 'profile':
        return <ProfilePage />;
      case 'api-keys':
        return <ApiKeysPage />;
      case 'users':
        return <UsersPage />;
      case 'pdf-template':
        return <PdfTemplatePage />;
      case 'upload-files':
        return <UploadFilesPage />;
      case 'channel-logos':
        return <ChannelLogosPage />;
      case 'settings':
        return (
          <div className="p-6">
            <h1 className="text-2xl text-foreground mb-1">Settings</h1>
            <p className="text-muted-foreground">System configuration and preferences</p>
          </div>
        );
      case 'job-details':
        return <MediaRationalePage onNavigate={handleNavigate} />;
      default:
        return <DashboardPage onNavigate={handleNavigate} />;
    }
  };

  return (
    <Layout currentPage={currentPage} onNavigate={handleNavigate}>
      {renderPage()}
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
      <Toaster 
        position="top-right"
        toastOptions={{
          classNames: {
            toast: 'bg-slate-800 border-slate-700 text-slate-100',
            title: 'text-slate-100',
            description: 'text-slate-400',
            actionButton: 'bg-blue-600 text-white',
            cancelButton: 'bg-slate-700 text-slate-300',
          },
        }}
      />
    </AuthProvider>
  );
}
