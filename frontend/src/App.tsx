import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { DashboardPage } from './app/dashboard/DashboardPage';
import { InvestigationPage } from './app/investigation/InvestigationPage';
import { AlertsPage } from './app/alerts/AlertsPage';
import { CasesPage } from './app/cases/CasesPage';
import { ReportsPage } from './app/reports/ReportsPage';
import { IngestionPage } from './app/ingestion/IngestionPage';
import { WalletExplorer } from './app/explorer/WalletExplorer';
import { TransactionExplorer } from './app/explorer/TransactionExplorer';
import { LoginPage } from './app/auth/LoginPage';
import { getCurrentUser } from './lib/api';

const ProtectedLayout: React.FC = () => {
  const user = getCurrentUser();
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0A0B0D]">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-hidden bg-[#07090C]">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/investigation" element={<InvestigationPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/cases" element={<CasesPage />} />
            <Route path="/wallets" element={<WalletExplorer />} />
            <Route path="/transactions" element={<TransactionExplorer />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/ingestion" element={<IngestionPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={<ProtectedLayout />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
