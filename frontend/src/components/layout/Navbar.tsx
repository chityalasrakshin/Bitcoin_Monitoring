import React, { useState, useEffect, useRef } from 'react';
import { Shield, Search, Terminal, LogOut, User, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { searchOmnibox, logout, getCurrentUser } from '../../lib/api';
import { SearchResult } from '../../types';

interface NavbarProps {
  onSelectEntity?: (id: string, type: 'wallet' | 'transaction') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onSelectEntity }) => {
  const navigate = useNavigate();
  const user = getCurrentUser();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.trim().length >= 2) {
      const timer = setTimeout(() => {
        searchOmnibox(query)
          .then(setResults)
          .catch(() => setResults(null));
        setIsOpen(true);
      }, 200);
      return () => clearTimeout(timer);
    } else {
      setResults(null);
      setIsOpen(false);
    }
  }, [query]);

  // Click outside to close search
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="h-13 border-b border-[#1E2330] bg-[#0A0B0D] px-4 flex items-center justify-between text-xs select-none sticky top-0 z-50">
      {/* Brand & Status */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 cursor-pointer" onClick={() => navigate('/')}>
          <div className="w-7 h-7 rounded bg-[#161B26] border border-[#2B354C] flex items-center justify-center text-blue-400">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="font-semibold text-slate-100 tracking-tight text-sm">ChainSentry</div>
            <div className="text-[10px] text-slate-400 font-mono">BTC FORENSICS v1.0</div>
          </div>
        </div>

        <div className="hidden md:flex items-center space-x-2 pl-3 border-l border-[#1E2330]">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-[11px] text-slate-300 font-mono uppercase tracking-wider">
            Engine: Standalone Offline
          </span>
        </div>
      </div>

      {/* Global Omnibox Search */}
      <div className="relative w-80 lg:w-96" ref={searchRef}>
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search address, TXID, tag, or case..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => { if (results) setIsOpen(true); }}
            className="w-full bg-[#111318] border border-[#1E2330] focus:border-blue-500 rounded px-3 py-1.5 pl-8 text-xs text-slate-100 placeholder-slate-500 focus:outline-none font-mono"
          />
        </div>

        {/* Search Results Dropdown */}
        {isOpen && results && (
          <div className="absolute left-0 right-0 top-full mt-1 bg-[#111318] border border-[#222736] rounded shadow-2xl overflow-hidden z-50 max-h-96 overflow-y-auto">
            {/* Wallets */}
            {results.wallets.length > 0 && (
              <div className="p-2 border-b border-[#1E2330]">
                <div className="text-[10px] uppercase text-slate-400 font-mono px-2 mb-1">Wallets</div>
                {results.wallets.map((w) => (
                  <div
                    key={w.address}
                    onClick={() => {
                      setIsOpen(false);
                      navigate(`/investigation?entity=${encodeURIComponent(w.address)}`);
                    }}
                    className="p-1.5 hover:bg-[#181C26] rounded cursor-pointer flex justify-between items-center"
                  >
                    <span className="font-mono text-slate-200 truncate mr-2">{w.address}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${w.risk_score > 0.5 ? 'bg-red-950 text-red-400 border border-red-800' : 'bg-slate-800 text-slate-300'}`}>
                      Risk: {w.risk_score.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Transactions */}
            {results.transactions.length > 0 && (
              <div className="p-2 border-b border-[#1E2330]">
                <div className="text-[10px] uppercase text-slate-400 font-mono px-2 mb-1">Transactions</div>
                {results.transactions.map((tx) => (
                  <div
                    key={tx.txid}
                    onClick={() => {
                      setIsOpen(false);
                      navigate(`/investigation?entity=${encodeURIComponent(tx.txid)}`);
                    }}
                    className="p-1.5 hover:bg-[#181C26] rounded cursor-pointer flex justify-between items-center"
                  >
                    <span className="font-mono text-slate-200 truncate mr-2">{tx.txid.slice(0, 24)}...</span>
                    <span className="font-mono text-slate-400 text-[10px]">{tx.total_value.toFixed(4)} BTC</span>
                  </div>
                ))}
              </div>
            )}

            {/* Cases */}
            {results.cases.length > 0 && (
              <div className="p-2 border-b border-[#1E2330]">
                <div className="text-[10px] uppercase text-slate-400 font-mono px-2 mb-1">Cases</div>
                {results.cases.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => {
                      setIsOpen(false);
                      navigate(`/cases`);
                    }}
                    className="p-1.5 hover:bg-[#181C26] rounded cursor-pointer flex justify-between items-center"
                  >
                    <span className="text-slate-200 truncate">{c.title}</span>
                    <span className="text-[10px] text-blue-400 uppercase font-mono">{c.status}</span>
                  </div>
                ))}
              </div>
            )}

            {/* No results */}
            {results.wallets.length === 0 && results.transactions.length === 0 && results.cases.length === 0 && (
              <div className="p-4 text-center text-slate-500 font-mono">No matching records found</div>
            )}
          </div>
        )}
      </div>

      {/* User profile & actions */}
      <div className="flex items-center space-x-3">
        {user ? (
          <div className="flex items-center space-x-2 bg-[#12151C] border border-[#1E2330] rounded px-2.5 py-1">
            <User className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-mono text-slate-200">{user.username}</span>
            <span className="text-[10px] text-blue-400 uppercase px-1 bg-blue-950/60 rounded">
              {user.role}
            </span>
          </div>
        ) : (
          <button
            onClick={() => navigate('/login')}
            className="text-xs text-blue-400 hover:text-blue-300 font-mono"
          >
            Log In
          </button>
        )}

        <button
          onClick={handleLogout}
          title="Sign Out"
          className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-[#181C26] rounded"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
