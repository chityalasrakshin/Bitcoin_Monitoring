import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderKanban, Plus, FileText, ArrowRight, ShieldCheck } from 'lucide-react';
import { fetchCases, createCase } from '../../lib/api';
import { Case } from '../../types';

export const CasesPage: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');

  const loadCases = async () => {
    try {
      const data = await fetchCases();
      setCases(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      await createCase({
        title: newTitle.trim(),
        description: newDesc.trim(),
        status: 'open',
      });
      setShowModal(false);
      setNewTitle('');
      setNewDesc('');
      loadCases();
    } catch (err) {
      alert('Failed to create case');
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto h-full text-xs">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <FolderKanban className="w-5 h-5 text-blue-500" />
            <span>Forensic Case Management</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            CHAIN-OF-CUSTODY INVESTIGATION DOSSIERS & EVIDENCE
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-mono font-medium transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>NEW FORENSIC CASE</span>
        </button>
      </div>

      {/* Case Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cases.map((c) => (
          <div
            key={c.id}
            className="bg-[#111318] border border-[#1E2330] hover:border-slate-600 rounded p-4 flex flex-col justify-between space-y-3 transition"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-400">ID: {c.id.slice(0, 8)}</span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                    c.status === 'escalated'
                      ? 'bg-red-950 text-red-400 border border-red-800'
                      : c.status === 'in_review'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-blue-950 text-blue-400 border border-blue-800'
                  }`}
                >
                  {c.status}
                </span>
              </div>

              <h3 className="font-semibold text-slate-100 text-sm mt-2 line-clamp-2">
                {c.title}
              </h3>

              <p className="text-slate-400 text-xs mt-1.5 line-clamp-3 leading-relaxed">
                {c.description || 'No description provided.'}
              </p>
            </div>

            <div className="pt-3 border-t border-[#1A1E29] flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-400">
                {c.alert_count || 0} Linked Leads
              </span>

              <button
                onClick={() => navigate(`/reports?case_id=${c.id}`)}
                className="flex items-center space-x-1 text-blue-400 hover:text-blue-300 font-mono text-xs"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>View Dossier</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* New Case Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#111318] border border-[#222736] rounded p-5 w-full max-w-md space-y-4 shadow-2xl">
            <h2 className="text-sm font-bold text-slate-100 font-mono uppercase">
              Open New Forensic Investigation Case
            </h2>

            <form onSubmit={handleCreateCase} className="space-y-3">
              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Case Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. OPERATION DARK-TRAIL: Lazarus Hot Wallet Tracking"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-[#161B24] border border-[#1E2330] rounded p-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Description / Scope</label>
                <textarea
                  rows={3}
                  placeholder="Details on suspect wallets, laundering typology, or observed P2P IPs..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full bg-[#161B24] border border-[#1E2330] rounded p-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3 py-1.5 bg-[#1A1E29] text-slate-300 hover:text-white rounded text-xs font-mono"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-mono font-medium"
                >
                  Create Case
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
