import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Wallet, Search, ArrowUpRight, ChevronLeft, ChevronRight, Layers, ArrowUpDown } from 'lucide-react';
import { fetchWallets } from '../../lib/api';

export const WalletExplorer: React.FC = () => {
  const navigate = useNavigate();
  const [wallets, setWallets] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize] = useState(25);
  const [sortBy, setSortBy] = useState('risk');
  const [loading, setLoading] = useState(false);

  const loadWallets = async () => {
    setLoading(true);
    try {
      const res = await fetchWallets({
        skip: page * pageSize,
        limit: pageSize,
        search: search.trim() || undefined,
        sort_by: sortBy,
      });
      setWallets(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed loading wallets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWallets();
  }, [page, sortBy]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    loadWallets();
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto overflow-y-auto h-full text-xs">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <Wallet className="w-5 h-5 text-purple-400" />
            <span>Wallet & Entity Explorer</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            INSPECT BITCOIN WALLET ADDRESSES &bull; COMMON-INPUT CLUSTERS &bull; PROPAGATED RISK
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {/* Sort Selector */}
          <div className="flex items-center space-x-1.5 bg-[#111318] border border-[#1E2330] rounded px-2.5 py-1.5 text-slate-300">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(0);
              }}
              className="bg-transparent font-mono text-xs text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="risk" className="bg-[#111318]">Sort: Highest Risk</option>
              <option value="address" className="bg-[#111318]">Sort: Address</option>
            </select>
          </div>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="flex space-x-1.5 w-72">
            <input
              type="text"
              placeholder="Search address or prefix..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#111318] border border-[#1E2330] rounded px-3 py-1.5 font-mono text-slate-200 focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded font-mono font-medium transition"
            >
              Find
            </button>
          </form>
        </div>
      </div>

      {/* Table & Header info */}
      <div className="flex items-center justify-between font-mono text-slate-400 text-[11px] px-1">
        <span>Showing {wallets.length} of {total} verified addresses</span>
        {loading && <span className="text-blue-400 animate-pulse">Loading entities...</span>}
      </div>

      <div className="bg-[#111318] border border-[#1E2330] rounded overflow-hidden shadow-xl">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#1E2330] bg-[#0E1015] text-[10px] uppercase font-mono text-slate-400">
              <th className="p-3">Wallet Address</th>
              <th className="p-3">Entity Cluster</th>
              <th className="p-3">Propagated Risk</th>
              <th className="p-3">Attribution Tags</th>
              <th className="p-3 text-right">3D Topology</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1A1E29]">
            {wallets.map((w) => (
              <tr key={w.address} className="hover:bg-[#151821] transition">
                <td className="p-3 font-mono text-slate-200 font-medium select-text">
                  {w.address}
                </td>
                <td className="p-3 font-mono text-purple-400">
                  {w.cluster_id ? (
                    <span className="inline-flex items-center space-x-1 bg-purple-950/40 text-purple-300 border border-purple-900/60 px-2 py-0.5 rounded">
                      <Layers className="w-3 h-3" />
                      <span>{w.cluster_id}</span>
                    </span>
                  ) : (
                    <span className="text-slate-600">unclustered</span>
                  )}
                </td>
                <td className="p-3 font-mono">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      w.risk_score >= 0.7
                        ? 'bg-red-950 text-red-400 border border-red-800'
                        : w.risk_score >= 0.4
                        ? 'bg-amber-950 text-amber-400 border border-amber-800'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {(w.risk_score * 100).toFixed(1)}%
                  </span>
                </td>
                <td className="p-3 font-mono space-x-1">
                  {w.tags && w.tags.map((t: string, i: number) => (
                    <span key={i} className="text-[10px] bg-blue-950 text-blue-300 px-1.5 py-0.5 rounded border border-blue-900">
                      {t}
                    </span>
                  ))}
                  {(!w.tags || w.tags.length === 0) && (
                    <span className="text-slate-600 text-[10px]">None</span>
                  )}
                </td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => navigate(`/investigation?entity=${encodeURIComponent(w.address)}`)}
                    className="px-2.5 py-1 bg-[#1E2330] hover:bg-blue-600 text-slate-200 rounded font-mono inline-flex items-center space-x-1 transition"
                  >
                    <span>3D Trace</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
            {wallets.length === 0 && !loading && (
              <tr>
                <td colSpan={5} className="p-8 text-center text-slate-500 font-mono">
                  No addresses found. Use search or run the pipeline.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="p-3 border-t border-[#1E2330] bg-[#0E1015] flex items-center justify-between text-xs font-mono text-slate-400">
            <div>
              Page {page + 1} of {totalPages}
            </div>
            <div className="flex space-x-1">
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="px-2.5 py-1 bg-[#161B24] border border-[#1E2330] hover:bg-slate-800 disabled:opacity-40 rounded flex items-center space-x-1 transition"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              <button
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
                className="px-2.5 py-1 bg-[#161B24] border border-[#1E2330] hover:bg-slate-800 disabled:opacity-40 rounded flex items-center space-x-1 transition"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
