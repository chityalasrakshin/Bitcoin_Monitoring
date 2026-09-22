import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Wallet, Search, ArrowUpRight, ShieldAlert } from 'lucide-react';
import { searchOmnibox } from '../../lib/api';

export const WalletExplorer: React.FC = () => {
  const navigate = useNavigate();
  const [wallets, setWallets] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Initial search for sample addresses
    searchOmnibox('sbc').then((res) => {
      setWallets(res.wallets);
    });
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;
    setLoading(true);
    try {
      const res = await searchOmnibox(search.trim());
      setWallets(res.wallets);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto overflow-y-auto h-full text-xs">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <Wallet className="w-5 h-5 text-purple-400" />
            <span>Wallet & Entity Explorer</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            INSPECT BITCOIN WALLET ADDRESSES, COMMON-INPUT CLUSTERS, AND PROPAGATED RISK
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex space-x-2 w-80">
          <input
            type="text"
            placeholder="Search address or prefix..."
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
              <th className="p-3">Wallet Address</th>
              <th className="p-3">Entity Cluster</th>
              <th className="p-3">Propagated Risk</th>
              <th className="p-3">Attribution Tags</th>
              <th className="p-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1A1E29]">
            {wallets.map((w) => (
              <tr key={w.address} className="hover:bg-[#151821] transition">
                <td className="p-3 font-mono text-slate-200 font-medium select-text">
                  {w.address}
                </td>
                <td className="p-3 font-mono text-purple-400">
                  {w.cluster_id || 'unclustered'}
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
                    <span className="text-slate-500 text-[10px]">None</span>
                  )}
                </td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => navigate(`/investigation?entity=${encodeURIComponent(w.address)}`)}
                    className="px-2.5 py-1 bg-[#1E2330] hover:bg-blue-600 text-slate-200 rounded font-mono inline-flex items-center space-x-1"
                  >
                    <span>Trace</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
            {wallets.length === 0 && (
              <tr>
                <td colSpan={5} className="p-8 text-center text-slate-500 font-mono">
                  No addresses found. Use search or run the pipeline.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
