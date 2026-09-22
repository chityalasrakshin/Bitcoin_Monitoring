import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, User, AlertCircle } from 'lucide-react';
import { login } from '../../lib/api';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('chainsentry2026!');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090C] flex flex-col items-center justify-center p-4 select-none">
      <div className="w-full max-w-sm bg-[#111318] border border-[#1E2330] rounded-lg p-6 shadow-2xl space-y-6">
        {/* Brand */}
        <div className="text-center space-y-2">
          <div className="w-10 h-10 rounded bg-[#161B26] border border-[#2B354C] mx-auto flex items-center justify-center text-blue-400">
            <Shield className="w-5 h-5" />
          </div>
          <h1 className="text-lg font-bold text-slate-100 tracking-tight">ChainSentry Forensics</h1>
          <p className="text-[11px] text-slate-400 font-mono">
            SECURE INVESTIGATOR ACCESS &middot; SIH26146
          </p>
        </div>

        {error && (
          <div className="bg-red-950/60 border border-red-800 text-red-300 p-2.5 rounded text-xs flex items-center space-x-2 font-mono">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-[11px] font-mono text-slate-400 mb-1">Investigator Username</label>
            <div className="relative">
              <User className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-[#161B24] border border-[#1E2330] focus:border-blue-500 rounded pl-8 pr-3 py-2 font-mono text-slate-200 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-400 mb-1">Password</label>
            <div className="relative">
              <Lock className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#161B24] border border-[#1E2330] focus:border-blue-500 rounded pl-8 pr-3 py-2 font-mono text-slate-200 focus:outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white rounded font-mono font-medium transition"
          >
            {loading ? 'AUTHENTICATING...' : 'AUTHORIZE SESSION'}
          </button>
        </form>

        <div className="pt-2 border-t border-[#1E2330] text-[10px] text-slate-500 font-mono text-center space-y-1">
          <div>Default Admin: <span className="text-slate-400">admin / chainsentry2026!</span></div>
          <div>Investigator: <span className="text-slate-400">investigator / forensics2026!</span></div>
        </div>
      </div>
    </div>
  );
};
