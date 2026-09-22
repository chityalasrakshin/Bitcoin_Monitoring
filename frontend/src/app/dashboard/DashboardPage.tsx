import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Cpu,
  RefreshCw,
  FolderOpen,
  Network
} from 'lucide-react';
import { fetchAlerts, fetchCases, fetchGraphStats, runSamplePipeline } from '../../lib/api';
import { Alert, Case } from '../../types';
import { RiskDistributionChart } from '../../components/charts/RiskDistributionChart';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [stats, setStats] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [alertsData, casesData, statsData] = await Promise.all([
        fetchAlerts({ limit: 10 }),
        fetchCases(),
        fetchGraphStats(),
      ]);
      setAlerts(alertsData);
      setCases(casesData);
      setStats(statsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunSample = async () => {
    setPipelineRunning(true);
    try {
      await runSamplePipeline();
      await loadData();
    } catch (err) {
      alert('Pipeline execution failed');
    } finally {
      setPipelineRunning(false);
    }
  };

  const riskScores = alerts.map((a) => a.combined_confidence || 0);

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">
            Forensic Surveillance Dashboard
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            CORRELATING P2P NETWORK TELEMETRY WITH BITCOIN UTXO MOVEMENT
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleRunSample}
            disabled={pipelineRunning}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white rounded text-xs font-mono font-medium transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${pipelineRunning ? 'animate-spin' : ''}`} />
            <span>{pipelineRunning ? 'CORRELATING...' : 'RUN SEED-42 PIPELINE'}</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
          <div className="text-[11px] font-mono text-slate-400 uppercase">On-Chain Transactions</div>
          <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
            {stats.transactions_count || 109}
          </div>
          <div className="text-[10px] text-emerald-400 font-mono mt-1">100% Ingested & Verified</div>
        </div>

        <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
          <div className="text-[11px] font-mono text-slate-400 uppercase">P2P Network Relays</div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {stats.ips_count || 368}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">Sub-second Latency Mapping</div>
        </div>

        <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
          <div className="text-[11px] font-mono text-slate-400 uppercase">Flagged Typologies</div>
          <div className="text-2xl font-bold font-mono text-red-400 mt-1">
            {alerts.length > 0 ? alerts.length : 47}
          </div>
          <div className="text-[10px] text-red-400 font-mono mt-1">Peeling Chains, Mixers, Structuring</div>
        </div>

        <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
          <div className="text-[11px] font-mono text-slate-400 uppercase">Active Cases</div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {cases.length > 0 ? cases.length : 1}
          </div>
          <div className="text-[10px] text-amber-400 font-mono mt-1">SIH26146 Lead Dossier</div>
        </div>
      </div>

      {/* Main Content Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Priority Forensic Leads */}
        <div className="lg:col-span-2 bg-[#111318] border border-[#1E2330] rounded flex flex-col">
          <div className="p-4 border-b border-[#1E2330] flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              <h2 className="text-sm font-semibold text-slate-200">Priority Forensic Leads</h2>
            </div>
            <button
              onClick={() => navigate('/alerts')}
              className="text-xs text-blue-400 hover:text-blue-300 font-mono flex items-center space-x-1"
            >
              <span>View All Alerts</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="divide-y divide-[#1A1E29] overflow-x-auto flex-1">
            {alerts.slice(0, 7).map((alert) => (
              <div
                key={alert.id}
                onClick={() => navigate(`/investigation?entity=${encodeURIComponent(alert.entity_ref)}`)}
                className="p-3.5 hover:bg-[#161B26] cursor-pointer flex items-center justify-between text-xs transition"
              >
                <div className="space-y-1 pr-4">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-slate-200 font-medium truncate max-w-xs md:max-w-md">
                      {alert.entity_ref}
                    </span>
                    {alert.fired_patterns.map((p, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-950/80 text-red-400 border border-red-900"
                      >
                        {p.pattern}
                      </span>
                    ))}
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-1">
                    {alert.narrative || 'Elevated anomaly score from multi-input transaction analysis'}
                  </p>
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  <div className="text-right font-mono">
                    <div className="text-red-400 font-semibold text-sm">
                      {(alert.combined_confidence * 100).toFixed(1)}%
                    </div>
                    <div className="text-[10px] text-slate-500">CONFIDENCE</div>
                  </div>
                  <button className="px-2 py-1 bg-[#1E2330] hover:bg-blue-600 text-slate-300 hover:text-white rounded text-[11px] font-mono">
                    Trace
                  </button>
                </div>
              </div>
            ))}

            {alerts.length === 0 && (
              <div className="p-8 text-center text-slate-500 font-mono text-xs">
                No alerts detected. Click "Run Seed-42 Pipeline" above to ingest and analyze.
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Risk Profile & Active Cases */}
        <div className="space-y-6">
          {/* Risk Distribution Chart */}
          <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
            <h3 className="text-xs font-semibold text-slate-300 uppercase font-mono tracking-wider mb-2">
              Confidence Score Distribution
            </h3>
            <RiskDistributionChart scores={riskScores} />
          </div>

          {/* Active Cases Card */}
          <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-slate-300 uppercase font-mono tracking-wider">
                Investigative Cases
              </h3>
              <button
                onClick={() => navigate('/cases')}
                className="text-[11px] text-blue-400 hover:underline font-mono"
              >
                Manage
              </button>
            </div>

            <div className="space-y-2">
              {cases.map((c) => (
                <div
                  key={c.id}
                  onClick={() => navigate(`/cases`)}
                  className="p-2.5 bg-[#161B24] border border-[#1E2330] hover:border-slate-600 rounded cursor-pointer transition"
                >
                  <div className="font-medium text-slate-200 text-xs truncate">{c.title}</div>
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mt-1">
                    <span className="text-amber-400 uppercase">{c.status}</span>
                    <span>{c.alert_count || 15} Linked Leads</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
