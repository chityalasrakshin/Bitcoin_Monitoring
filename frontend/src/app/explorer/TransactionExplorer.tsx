import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftRight, Search, ArrowUpRight } from 'lucide-react';
import { searchOmnibox } from '../../lib/api';

export const TransactionExplorer: React.FC = () => {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Initial search for sample txs
    searchOmnibox('b85').then((res) => {
      setTransactions(res.transactions);
    });
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;
    setLoading(true);
    try {
      const res = await searchOmnibox(search.trim());
      setTransactions(res.transactions);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto overflow-y-auto h-full text-xs">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <ArrowLeftRight className="w-5 h-5 text-blue-400" />
            <span>Transaction Explorer</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            ON-CHAIN TRANSACTION LEDGER WITH VALUE BREAKDOWNS AND RELAY CORRELATION
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex space-x-2 w-80">
          <input
            type="text"
            placeholder="Search TXID or hash prefix..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#111318] border border-[#1E2330] rounded px-3 py-1.5 font-mono text-slate-200 focus:outline-none"
          />
          <button
            type="submit"
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded font-mono"
          >
            Find
          </button>
        </form>
      </div>

      <div className="bg-[#111318] border border-[#1E2330] rounded overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#1E2330] bg-[#0E1015] text-[10px] uppercase font-mono text-slate-400">
              <th className="p-3">Transaction ID (TXID)</th>
              <th className="p-3">Total Value</th>
              <th className="p-3">Miner Fee</th>
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
                  {tx.total_value.toFixed(6)} BTC
                </td>
                <td className="p-3 font-mono text-slate-400">
                  {tx.fee ? `${tx.fee.toFixed(6)} BTC` : '0.000000 BTC'}
                </td>
                <td className="p-3 font-mono text-slate-400">
                  {tx.timestamp ? new Date(tx.timestamp).toLocaleString() : 'N/A'}
                </td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => navigate(`/investigation?entity=${encodeURIComponent(tx.txid)}`)}
                    className="px-2.5 py-1 bg-[#1E2330] hover:bg-blue-600 text-slate-200 rounded font-mono inline-flex items-center space-x-1"
                  >
                    <span>Trace</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
            {transactions.length === 0 && (
              <tr>
                <td colSpan={5} className="p-8 text-center text-slate-500 font-mono">
                  No transactions found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
