import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Cpu,
  RefreshCw,
  FolderOpen,
  Network,
  Share2,
  Sparkles,
  Layers,
  Database
} from 'lucide-react';
import { fetchAlerts, fetchCases, fetchGraphStats, runSamplePipeline, liveTraceBlockchain } from '../../lib/api';
import { Alert, Case } from '../../types';
import { RiskDistributionChart } from '../../components/charts/RiskDistributionChart';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [stats, setStats] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [quickTraceInput, setQuickTraceInput] = useState('');
  const [tracingLive, setTracingLive] = useState(false);

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
      console.error('Failed to load dashboard data:', err);
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

  const handleQuickTrace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTraceInput.trim()) return;
    setTracingLive(true);
    try {
      await liveTraceBlockchain(quickTraceInput.trim());
      navigate(`/investigation?entity=${encodeURIComponent(quickTraceInput.trim())}`);
    } catch (err: any) {
      // If live trace fails or entity isn't live, navigate to investigation anyway to attempt local lookup
      navigate(`/investigation?entity=${encodeURIComponent(quickTraceInput.trim())}`);
    } finally {
      setTracingLive(false);
    }
  };

  const riskScores = alerts.map((a) => a.combined_confidence || 0);

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <span>Forensic Surveillance & Intelligence Dashboard</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            CORRELATING P2P NETWORK TELEMETRY &bull; BITCOIN UTXO MOVEMENT &bull; 3D SPATIAL TOPOLOGY
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <form onSubmit={handleQuickTrace} className="flex items-center space-x-1.5">
            <input
              type="text"
              placeholder="Live trace address or txid..."
              value={quickTraceInput}
              onChange={(e) => setQuickTraceInput(e.target.value)}
              className="bg-[#111318] border border-[#1E2330] rounded px-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500 w-52 md:w-64"
            />
            <button
              type="submit"
              disabled={tracingLive || !quickTraceInput.trim()}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-950 text-white rounded text-xs font-mono font-medium flex items-center space-x-1 transition"
            >
              <Sparkles className={`w-3 h-3 ${tracingLive ? 'animate-spin' : ''}`} />
              <span>{tracingLive ? 'Tracing...' : 'Trace'}</span>
            </button>
          </form>

          <button
            onClick={handleRunSample}
            disabled={pipelineRunning}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white rounded text-xs font-mono font-medium transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${pipelineRunning ? 'animate-spin' : ''}`} />
            <span>{pipelineRunning ? 'CORRELATING...' : 'RUN PIPELINE'}</span>
          </button>
        </div>
      </div>

      {/* Metrics Row - 100% Dynamic */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">On-Chain Transactions</span>
            <Database className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
            {stats.transactions_count ?? 0}
          </div>
          <div className="text-[10px] text-emerald-400 font-mono mt-1 flex items-center space-x-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Persisted in Relational DB</span>
          </div>
        </div>

        <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">P2P Network Relays</span>
            <Network className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {stats.ips_count ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">
            Sub-second Latency Mapping
          </div>
        </div>

        <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">Flagged Typologies</span>
            <ShieldAlert className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-red-400 mt-1">
            {alerts.length}
          </div>
          <div className="text-[10px] text-red-400 font-mono mt-1">
            AI Anomaly & Risk Fused
          </div>
        </div>

        <div className="bg-[#111318] border border-[#1E2330] rounded p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 uppercase">3D Graph Topologies</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-purple-400 mt-1">
            {stats.total_nodes ?? 0}
          </div>
          <div className="text-[10px] text-purple-400 font-mono mt-1">
            {stats.clusters_count ?? 0} Clustered Entities
          </div>
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
              <span>View All Alerts ({alerts.length})</span>
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
                  <button className="px-2.5 py-1 bg-[#1E2330] hover:bg-blue-600 text-slate-300 hover:text-white rounded text-[11px] font-mono">
                    3D Trace
                  </button>
                </div>
              </div>
            ))}

            {alerts.length === 0 && (
              <div className="p-8 text-center text-slate-500 font-mono text-xs">
                No alerts currently in queue. Ingest a dataset or run on-chain trace above.
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
                Investigative Cases ({cases.length})
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
                    <span>{c.alert_count ?? 0} Linked Leads</span>
                  </div>
                </div>
              ))}

              {cases.length === 0 && (
                <div className="p-4 text-center text-slate-500 font-mono text-xs">
                  No active cases open.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
