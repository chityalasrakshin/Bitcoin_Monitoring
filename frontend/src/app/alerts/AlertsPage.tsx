import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Filter, Search, ArrowUpRight, CheckCircle2, XCircle } from 'lucide-react';
import { fetchAlerts, updateAlertStatus, fetchCases } from '../../lib/api';
import { Alert, Case } from '../../types';

export const AlertsPage: React.FC = () => {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [alertsData, casesData] = await Promise.all([
        fetchAlerts({ status: filterStatus || undefined }),
        fetchCases(),
      ]);
      setAlerts(alertsData);
      setCases(casesData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filterStatus]);

  const handleStatusChange = async (alertId: string, newStatus: string) => {
    try {
      await updateAlertStatus(alertId, newStatus);
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: newStatus as any } : a))
      );
    } catch (err) {
      alert('Failed to update status');
    }
  };

  const filteredAlerts = alerts.filter((a) =>
    a.entity_ref.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (a.narrative && a.narrative.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto overflow-y-auto h-full text-xs">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            <span>Forensic Alert Triage Queue</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            RANKED BY MULTI-SIGNAL AI ANOMALY FUSION AND GRAPH RISK PROPAGATION
          </p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex items-center space-x-2">
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Filter by TXID or address..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#111318] border border-[#1E2330] rounded pl-8 pr-3 py-1 text-xs font-mono text-slate-200 focus:outline-none"
            />
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-[#111318] border border-[#1E2330] rounded px-3 py-1 text-xs font-mono text-slate-300 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="reviewing">Reviewing</option>
            <option value="confirmed">Confirmed</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </div>
      </div>

      {/* Alert Feed Table */}
      <div className="bg-[#111318] border border-[#1E2330] rounded overflow-hidden shadow-xl">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#1E2330] bg-[#0E1015] text-[10px] uppercase font-mono text-slate-400 tracking-wider">
              <th className="p-3">Confidence</th>
              <th className="p-3">Entity Reference</th>
              <th className="p-3">Detected Typologies</th>
              <th className="p-3">Findings & Indicators</th>
              <th className="p-3">Status</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1A1E29]">
            {filteredAlerts.map((alert) => (
              <tr key={alert.id} className="hover:bg-[#151821] transition">
                {/* Confidence */}
                <td className="p-3 font-mono">
                  <div className="text-red-400 font-bold text-sm">
                    {(alert.combined_confidence * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono">
                    A: {alert.anomaly_score.toFixed(2)} | R: {alert.risk_score.toFixed(2)}
                  </div>
                </td>

                {/* Entity */}
                <td className="p-3">
                  <div className="font-mono text-slate-200 font-medium truncate max-w-xs select-text">
                    {alert.entity_ref}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 uppercase mt-0.5">
                    {alert.entity_type}
                  </div>
                </td>

                {/* Typologies */}
                <td className="p-3 space-y-1">
                  {alert.fired_patterns.map((p, i) => (
                    <span
                      key={i}
                      className="inline-block font-mono text-[10px] px-1.5 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 mr-1"
                    >
                      {p.pattern}
                    </span>
                  ))}
                  {alert.fired_patterns.length === 0 && (
                    <span className="text-[10px] font-mono text-slate-500">Unsupervised Outlier</span>
                  )}
                </td>

                {/* Narrative */}
                <td className="p-3 text-slate-300 max-w-md">
                  <p className="line-clamp-2 leading-relaxed text-[11px]">
                    {alert.narrative || 'High anomaly score detected by feature ensemble'}
                  </p>
                </td>

                {/* Status Dropdown */}
                <td className="p-3">
                  <select
                    value={alert.status}
                    onChange={(e) => handleStatusChange(alert.id, e.target.value)}
                    className={`text-[11px] font-mono rounded px-2 py-1 border bg-[#111318] focus:outline-none ${
                      alert.status === 'confirmed'
                        ? 'border-red-600 text-red-400'
                        : alert.status === 'reviewing'
                        ? 'border-amber-600 text-amber-400'
                        : alert.status === 'dismissed'
                        ? 'border-slate-700 text-slate-500'
                        : 'border-blue-600 text-blue-400'
                    }`}
                  >
                    <option value="new">NEW</option>
                    <option value="reviewing">REVIEWING</option>
                    <option value="confirmed">CONFIRMED</option>
                    <option value="dismissed">DISMISSED</option>
                  </select>
                </td>

                {/* Action */}
                <td className="p-3 text-right">
                  <button
                    onClick={() => navigate(`/investigation?entity=${encodeURIComponent(alert.entity_ref)}`)}
                    className="px-2.5 py-1 bg-[#1E2330] hover:bg-blue-600 text-slate-200 hover:text-white rounded text-xs font-mono inline-flex items-center space-x-1 transition"
                  >
                    <span>Inspect</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}

            {filteredAlerts.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-500 font-mono">
                  No alerts match criteria
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
