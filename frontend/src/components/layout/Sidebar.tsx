import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Share2,
  AlertTriangle,
  FolderKanban,
  Wallet,
  ArrowLeftRight,
  FileText,
  UploadCloud,
  Database
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Investigation Graph', path: '/investigation', icon: Share2 },
    { label: 'Alert Triage Feed', path: '/alerts', icon: AlertTriangle },
    { label: 'Case Management', path: '/cases', icon: FolderKanban },
    { label: 'Wallet Explorer', path: '/wallets', icon: Wallet },
    { label: 'Transaction Explorer', path: '/transactions', icon: ArrowLeftRight },
    { label: 'Forensic Reports', path: '/reports', icon: FileText },
    { label: 'Ingestion Pipeline', path: '/ingestion', icon: UploadCloud },
  ];

  return (
    <aside className="w-56 bg-[#0B0D11] border-r border-[#1E2330] flex flex-col justify-between select-none shrink-0">
      <div className="p-3 space-y-1">
        <div className="text-[10px] uppercase font-mono text-slate-500 px-3 py-1.5 tracking-wider font-semibold">
          Investigative Modules
        </div>
        <nav className="space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `flex items-center space-x-2.5 px-3 py-2 rounded text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-[#181C26] text-blue-400 border-l-2 border-blue-500 font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#12151C]'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Node & Hardware telemetry footer */}
      <div className="p-3 m-3 bg-[#111318] border border-[#1E2330] rounded text-[11px] text-slate-400 space-y-1.5 font-mono">
        <div className="flex items-center justify-between text-slate-300">
          <span className="flex items-center space-x-1.5">
            <Database className="w-3.5 h-3.5 text-blue-400" />
            <span>LOCAL ENGINE</span>
          </span>
          <span className="text-emerald-400 text-[10px]">READY</span>
        </div>
        <div className="text-[10px] text-slate-500 leading-tight">
          P2P Telemetry: Active<br />
          Graph Projection: Loaded<br />
          Model Ensemble: PyOD 3.6
        </div>
      </div>
    </aside>
  );
};
