import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileText, Download, Copy, Check, Shield } from 'lucide-react';
import { fetchCases, fetchCaseMarkdownReport } from '../../lib/api';
import { Case } from '../../types';

export const ReportsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [reportMarkdown, setReportMarkdown] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchCases().then((cList) => {
      setCases(cList);
      const targetId = searchParams.get('case_id') || (cList.length > 0 ? cList[0].id : '');
      setSelectedCaseId(targetId);
    });
  }, []);

  useEffect(() => {
    if (!selectedCaseId) return;
    setLoading(true);
    fetchCaseMarkdownReport(selectedCaseId)
      .then(setReportMarkdown)
      .catch((err) => setReportMarkdown(`# Error generating report: ${err.message}`))
      .finally(() => setLoading(false));
  }, [selectedCaseId]);

  const handleCopy = () => {
    navigator.clipboard.writeText(reportMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([reportMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chainsentry_case_report_${selectedCaseId.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto overflow-y-auto h-full text-xs">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <FileText className="w-5 h-5 text-blue-400" />
            <span>Forensic Evidence Dossiers & Reports</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            EXPORTABLE CHAIN-OF-CUSTODY AUDITABLE REPORTS FOR LAW ENFORCEMENT
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={selectedCaseId}
            onChange={(e) => {
              setSelectedCaseId(e.target.value);
              setSearchParams({ case_id: e.target.value });
            }}
            className="bg-[#111318] border border-[#1E2330] rounded px-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none"
          >
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>

          <button
            onClick={handleCopy}
            className="flex items-center space-x-1 px-3 py-1.5 bg-[#181C26] hover:bg-[#222736] text-slate-300 rounded font-mono text-xs transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'COPIED' : 'COPY'}</span>
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center space-x-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded font-mono text-xs transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>DOWNLOAD .MD</span>
          </button>
        </div>
      </div>

      {/* Report Document Paper */}
      <div className="bg-[#111318] border border-[#1E2330] rounded p-8 shadow-2xl font-mono text-slate-300 select-text whitespace-pre-wrap leading-relaxed">
        {loading ? (
          <div className="text-center py-12 text-slate-500">Generating forensic case report...</div>
        ) : (
          reportMarkdown
        )}
      </div>
    </div>
  );
};
