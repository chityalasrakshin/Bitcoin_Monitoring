import React, { useState } from 'react';
import { UploadCloud, FileSpreadsheet, CheckCircle2, Play, AlertCircle } from 'lucide-react';
import { uploadDataset, runSamplePipeline } from '../../lib/api';
import { IngestStats } from '../../types';

export const IngestionPage: React.FC = () => {
  const [txFile, setTxFile] = useState<File | null>(null);
  const [obsFile, setObsFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<IngestStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunSample = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await runSamplePipeline();
      setStats(res);
    } catch (err: any) {
      setError(err.message || 'Pipeline run failed');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!txFile) return;
    setLoading(true);
    setError(null);
    try {
      const res = await uploadDataset(txFile, obsFile || undefined);
      setStats(res);
    } catch (err: any) {
      setError(err.message || 'Upload and correlation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto overflow-y-auto h-full text-xs">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
          <UploadCloud className="w-5 h-5 text-blue-500" />
          <span>Batch Ingestion & Network Correlation Pipeline</span>
        </h1>
        <p className="text-xs text-slate-400 font-mono mt-0.5">
          INGEST RAW BLOCKCHAIN TRANSACTION METADATA AND FIRST-SEEN P2P PEER OBSERVATIONS
        </p>
      </div>

      {/* Built-in Reference Seed Card */}
      <div className="bg-[#111318] border border-blue-900/40 rounded p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Reference SIH26146 Dataset (Seed-42)
            </h2>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              109 On-Chain Transactions &middot; 368 P2P Relay Observations &middot; Peeling Chains &middot; CoinJoin Mixers
            </p>
          </div>

          <button
            onClick={handleRunSample}
            disabled={loading}
            className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-950 text-white rounded text-xs font-mono font-medium transition shadow-lg"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{loading ? 'EXECUTING PIPELINE...' : 'EXECUTE SEED-42 PIPELINE'}</span>
          </button>
        </div>
      </div>

      {/* Custom Dataset Upload */}
      <div className="bg-[#111318] border border-[#1E2330] rounded p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-100 font-mono uppercase">
          Ingest Custom Forensic Metadata
        </h2>

        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Transactions File */}
            <div className="border border-dashed border-[#262D3D] hover:border-blue-500 rounded p-4 text-center space-y-2 bg-[#141822]">
              <FileSpreadsheet className="w-6 h-6 mx-auto text-blue-400" />
              <div className="font-mono text-xs text-slate-200">
                {txFile ? txFile.name : 'Transactions (.csv, .json, .xml)'}
              </div>
              <p className="text-[10px] text-slate-500 font-mono">
                Contains txid, timestamp, inputs, outputs, amounts
              </p>
              <input
                type="file"
                accept=".csv,.json,.xml"
                required
                onChange={(e) => setTxFile(e.target.files?.[0] || null)}
                className="text-xs text-slate-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-slate-800 file:text-slate-300 hover:file:bg-slate-700 cursor-pointer"
              />
            </div>

            {/* Network Observations File */}
            <div className="border border-dashed border-[#262D3D] hover:border-cyan-500 rounded p-4 text-center space-y-2 bg-[#141822]">
              <UploadCloud className="w-6 h-6 mx-auto text-cyan-400" />
              <div className="font-mono text-xs text-slate-200">
                {obsFile ? obsFile.name : 'Network Observations (.csv, .json)'}
              </div>
              <p className="text-[10px] text-slate-500 font-mono">
                Optional: src_ip, dst_ip, ports, observation_ts
              </p>
              <input
                type="file"
                accept=".csv,.json"
                onChange={(e) => setObsFile(e.target.files?.[0] || null)}
                className="text-xs text-slate-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-slate-800 file:text-slate-300 hover:file:bg-slate-700 cursor-pointer"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!txFile || loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white rounded text-xs font-mono font-medium transition"
            >
              {loading ? 'PROCESSING...' : 'UPLOAD & CORRELATE'}
            </button>
          </div>
        </form>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded flex items-center space-x-2 font-mono text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Execution Results */}
      {stats && (
        <div className="bg-[#111318] border border-emerald-800/60 rounded p-5 space-y-3">
          <div className="flex items-center space-x-2 text-emerald-400 font-mono text-sm font-semibold">
            <CheckCircle2 className="w-4 h-4" />
            <span>Pipeline Execution Complete in {stats.duration_seconds}s</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2 font-mono">
            <div className="bg-[#161B24] p-2.5 rounded border border-[#1E2330]">
              <div className="text-[10px] text-slate-400">Transactions</div>
              <div className="text-lg font-bold text-slate-100">{stats.total_transactions_ingested}</div>
            </div>

            <div className="bg-[#161B24] p-2.5 rounded border border-[#1E2330]">
              <div className="text-[10px] text-slate-400">Observations</div>
              <div className="text-lg font-bold text-cyan-400">{stats.total_observations_ingested}</div>
            </div>

            <div className="bg-[#161B24] p-2.5 rounded border border-[#1E2330]">
              <div className="text-[10px] text-slate-400">P2P Correlated</div>
              <div className="text-lg font-bold text-blue-400">{stats.total_correlations_found}</div>
            </div>

            <div className="bg-[#161B24] p-2.5 rounded border border-[#1E2330]">
              <div className="text-[10px] text-slate-400">Entities Clustered</div>
              <div className="text-lg font-bold text-purple-400">{stats.total_entities_clustered}</div>
            </div>

            <div className="bg-[#161B24] p-2.5 rounded border border-[#1E2330]">
              <div className="text-[10px] text-slate-400">Alerts Generated</div>
              <div className="text-lg font-bold text-red-400">{stats.total_alerts_generated}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
