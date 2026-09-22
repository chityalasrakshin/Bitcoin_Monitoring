import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftRight, Search, ArrowUpRight, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';
import { fetchTransactions } from '../../lib/api';

export const TransactionExplorer: React.FC = () => {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize] = useState(25);
  const [sortBy, setSortBy] = useState('time');
  const [loading, setLoading] = useState(false);

  const loadTransactions = async () => {
    setLoading(true);
    try {
      const res = await fetchTransactions({
        skip: page * pageSize,
        limit: pageSize,
        search: search.trim() || undefined,
        sort_by: sortBy,
      });
      setTransactions(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed loading transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [page, sortBy]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    loadTransactions();
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto overflow-y-auto h-full text-xs">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <ArrowLeftRight className="w-5 h-5 text-blue-400" />
            <span>Transaction Ledger Explorer</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            ON-CHAIN TRANSACTION LEDGER &bull; VALUE BREAKDOWNS &bull; 3D PROPAGATION TRACING
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
              <option value="time" className="bg-[#111318]">Sort: Recent Timestamp</option>
              <option value="value" className="bg-[#111318]">Sort: Highest Value</option>
            </select>
          </div>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="flex space-x-1.5 w-72">
            <input
              type="text"
              placeholder="Search TXID or prefix..."
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

      {/* Header Info */}
      <div className="flex items-center justify-between font-mono text-slate-400 text-[11px] px-1">
        <span>Showing {transactions.length} of {total} verified on-chain transactions</span>
        {loading && <span className="text-blue-400 animate-pulse">Querying ledger...</span>}
      </div>

      <div className="bg-[#111318] border border-[#1E2330] rounded overflow-hidden shadow-xl">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#1E2330] bg-[#0E1015] text-[10px] uppercase font-mono text-slate-400">
              <th className="p-3">Transaction ID (TXID)</th>
              <th className="p-3">Total Value</th>
              <th className="p-3">Miner Fee</th>
              <th className="p-3">Script Type</th>
              <th className="p-3">Timestamp (UTC)</th>
              <th className="p-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1A1E29]">
            {transactions.map((tx) => (
              <tr key={tx.txid} className="hover:bg-[#151821] transition">
                <td className="p-3 font-mono text-slate-200 font-medium select-text">
                  {tx.txid}
                </td>
                <td className="p-3 font-mono text-emerald-400 font-medium">
                  {tx.total_value ? `${tx.total_value.toFixed(6)} BTC` : '0.000000 BTC'}
                </td>
                <td className="p-3 font-mono text-slate-400">
                  {tx.fee ? `${tx.fee.toFixed(6)} BTC` : '0.000000 BTC'}
                </td>
                <td className="p-3 font-mono">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-950/60 text-blue-400 border border-blue-900/60">
                    {tx.script_type || 'UNKNOWN'}
                  </span>
                </td>
                <td className="p-3 font-mono text-slate-400">
                  {tx.timestamp ? new Date(tx.timestamp).toLocaleString() : 'N/A'}
                </td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => navigate(`/investigation?entity=${encodeURIComponent(tx.txid)}`)}
                    className="px-2.5 py-1 bg-[#1E2330] hover:bg-blue-600 text-slate-200 rounded font-mono inline-flex items-center space-x-1 transition"
                  >
                    <span>3D Trace</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
            {transactions.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-500 font-mono">
                  No transactions found. Use search or run the ingestion pipeline.
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
