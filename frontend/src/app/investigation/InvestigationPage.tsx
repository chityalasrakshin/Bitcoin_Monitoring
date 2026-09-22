import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  Share2,
  Tag,
  Shield,
  Layers,
  Activity,
  Plus,
  ArrowUpRight,
  Maximize2
} from 'lucide-react';
import { InvestigationGraph } from '../../components/graph/InvestigationGraph';
import { FundFlowSankey } from '../../components/charts/FundFlowSankey';
import {
  fetchGraphNeighborhood,
  fetchAddressTags,
  addAddressTag,
  fetchAlerts
} from '../../lib/api';
import { GraphData, CytoscapeNodeData, Alert } from '../../types';

export const InvestigationPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialEntity = searchParams.get('entity') || 'b85038db8d34756615a8c82752b931ded57f99c1911097b5d0e21f0c648e638b';

  const [currentEntity, setCurrentEntity] = useState(initialEntity);
  const [inputEntity, setInputEntity] = useState(initialEntity);
  const [hopDepth, setHopDepth] = useState(2);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<CytoscapeNodeData | null>(null);
  const [tags, setTags] = useState<any[]>([]);
  const [newTag, setNewTag] = useState('');
  const [newCategory, setNewCategory] = useState('other');
  const [loading, setLoading] = useState(false);
  const [alertDetail, setAlertDetail] = useState<Alert | null>(null);

  const loadGraph = async (entity: string, depth: number) => {
    setLoading(true);
    try {
      const data = await fetchGraphNeighborhood(entity, depth);
      setGraphData(data);
      // Auto-select centered entity
      const rootNode = data.nodes.find((n) => n.data.id === entity);
      if (rootNode) {
        setSelectedNode(rootNode.data);
      }
    } catch (err) {
      console.error('Failed to load graph:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const ent = searchParams.get('entity') || initialEntity;
    setCurrentEntity(ent);
    setInputEntity(ent);
    loadGraph(ent, hopDepth);
  }, [searchParams]);

  // Load tags and alert for selected node
  useEffect(() => {
    if (!selectedNode) {
      setTags([]);
      setAlertDetail(null);
      return;
    }

    if (selectedNode.type === 'wallet') {
      fetchAddressTags(selectedNode.id).then(setTags).catch(() => setTags([]));
    } else {
      setTags([]);
    }

    fetchAlerts().then((alerts) => {
      const match = alerts.find((a) => a.entity_ref === selectedNode.id);
      setAlertDetail(match || null);
    });
  }, [selectedNode]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputEntity.trim()) return;
    setSearchParams({ entity: inputEntity.trim() });
  };

  const handleAddTag = async () => {
    if (!newTag.trim() || !selectedNode || selectedNode.type !== 'wallet') return;
    try {
      const created = await addAddressTag({
        address: selectedNode.id,
        tag: newTag.trim(),
        category: newCategory,
      });
      setTags((prev) => [...prev, created]);
      setNewTag('');
    } catch (err) {
      alert('Failed to add tag');
    }
  };

  // Build mini-Sankey for selected node
  const sankeyNodes = [];
  const sankeyLinks = [];
  if (selectedNode) {
    sankeyNodes.push({ name: selectedNode.label });
    const relatedEdges = graphData.edges.filter(
      (e) => e.data.source === selectedNode.id || e.data.target === selectedNode.id
    );
    relatedEdges.forEach((e) => {
      const otherId = e.data.source === selectedNode.id ? e.data.target : e.data.source;
      const otherNode = graphData.nodes.find((n) => n.data.id === otherId);
      const otherName = otherNode?.data.label || otherId.slice(0, 10);
      sankeyNodes.push({ name: otherName });
      sankeyLinks.push({
        source: e.data.source === selectedNode.id ? selectedNode.label : otherName,
        target: e.data.target === selectedNode.id ? selectedNode.label : otherName,
        value: e.data.amount || 0.1,
      });
    });
  }

  return (
    <div className="flex flex-col h-full overflow-hidden select-none">
      {/* Top Search & Filter Bar */}
      <div className="h-11 border-b border-[#1E2330] bg-[#0E1015] px-4 flex items-center justify-between text-xs">
        <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2">
          <span className="text-slate-400 font-mono text-[11px] uppercase">Focal Node:</span>
          <div className="relative w-80">
            <input
              type="text"
              value={inputEntity}
              onChange={(e) => setInputEntity(e.target.value)}
              placeholder="Paste Address or TXID..."
              className="w-full bg-[#141820] border border-[#1E2330] focus:border-blue-500 rounded px-2.5 py-1 text-xs text-slate-200 font-mono focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-mono"
          >
            Trace
          </button>
        </form>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-slate-400 font-mono">
            <span>Hop Depth:</span>
            {[1, 2, 3].map((d) => (
              <button
                key={d}
                onClick={() => {
                  setHopDepth(d);
                  loadGraph(currentEntity, d);
                }}
                className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                  hopDepth === d
                    ? 'bg-blue-600 text-white font-semibold'
                    : 'bg-[#181C26] text-slate-400 hover:text-white'
                }`}
              >
                {d}
              </button>
            ))}
          </div>

          <div className="text-slate-500 font-mono text-[11px]">
            {graphData.nodes.length} Nodes &middot; {graphData.edges.length} Edges
          </div>
        </div>
      </div>

      {/* Main Workspace Split */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Cytoscape Graph Canvas */}
        <div className="flex-1 relative">
          <InvestigationGraph
            data={graphData}
            selectedNodeId={selectedNode?.id}
            onSelectNode={setSelectedNode}
            onExpandNode={(nodeId) => {
              setSearchParams({ entity: nodeId });
            }}
          />
        </div>

        {/* Right: Entity Inspector Panel */}
        <div className="w-96 border-l border-[#1E2330] bg-[#0D0F14] flex flex-col overflow-y-auto shrink-0 text-xs">
          {selectedNode ? (
            <div className="p-4 space-y-4">
              {/* Header */}
              <div className="border-b border-[#1E2330] pb-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider font-mono text-slate-400 font-semibold">
                    {selectedNode.type} Entity
                  </span>
                  <span
                    className={`font-mono text-[10px] px-2 py-0.5 rounded font-semibold ${
                      selectedNode.risk_score >= 0.7
                        ? 'bg-red-950 text-red-400 border border-red-800'
                        : selectedNode.risk_score >= 0.4
                        ? 'bg-amber-950 text-amber-400 border border-amber-800'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    Risk: {(selectedNode.risk_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="font-mono text-slate-100 text-xs break-all mt-1.5 select-text font-medium">
                  {selectedNode.id}
                </div>
              </div>

              {/* Cluster Identity */}
              {selectedNode.cluster_id && (
                <div className="bg-[#12161F] border border-[#1E2330] rounded p-2.5 space-y-1">
                  <div className="flex items-center space-x-1 text-slate-400 text-[10px] uppercase font-mono">
                    <Layers className="w-3 h-3 text-purple-400" />
                    <span>Common Ownership Entity</span>
                  </div>
                  <div className="font-mono text-purple-300 font-medium">
                    {selectedNode.cluster_id}
                  </div>
                </div>
              )}

              {/* Forensic Anomaly & Typology Lead */}
              {alertDetail && (
                <div className="bg-red-950/20 border border-red-900/60 rounded p-3 space-y-2">
                  <div className="flex items-center justify-between text-red-400 font-mono text-[11px] font-semibold">
                    <span className="flex items-center space-x-1">
                      <Shield className="w-3.5 h-3.5" />
                      <span>FLAGGED FORENSIC LEAD</span>
                    </span>
                    <span>{(alertDetail.combined_confidence * 100).toFixed(0)}% CONF</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    {alertDetail.narrative}
                  </p>

                  {alertDetail.fired_patterns.length > 0 && (
                    <div className="space-y-1 pt-1 border-t border-red-900/40">
                      <div className="text-[10px] uppercase font-mono text-slate-400">Typologies Fired:</div>
                      {alertDetail.fired_patterns.map((p, i) => (
                        <div key={i} className="text-[11px] font-mono text-red-300 flex justify-between">
                          <span>&bull; {p.pattern}</span>
                          <span className="text-red-400">{(p.confidence * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {alertDetail.shap_explanation?.top_features && (
                    <div className="space-y-1 pt-1 border-t border-red-900/40">
                      <div className="text-[10px] uppercase font-mono text-slate-400">SHAP Attributions:</div>
                      {alertDetail.shap_explanation.top_features.slice(0, 4).map((f, i) => (
                        <div key={i} className="flex justify-between text-[10px] font-mono text-slate-400">
                          <span className="truncate pr-2">{f.description}</span>
                          <span className="text-blue-400 shrink-0">+{f.contribution.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Fund Flow Sankey */}
              <div className="bg-[#12161F] border border-[#1E2330] rounded p-2.5">
                <div className="text-[10px] uppercase font-mono text-slate-400 mb-1">
                  Fund Flow Distribution
                </div>
                <FundFlowSankey nodes={sankeyNodes} links={sankeyLinks} />
              </div>

              {/* Attribution Tags */}
              {selectedNode.type === 'wallet' && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-mono text-slate-400 font-semibold">
                      Attribution Tags ({tags.length})
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-1">
                    {tags.map((t, idx) => (
                      <span
                        key={idx}
                        className="font-mono text-[10px] px-2 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800"
                      >
                        {t.tag} ({t.category})
                      </span>
                    ))}
                    {tags.length === 0 && (
                      <span className="text-[11px] text-slate-500 font-mono">No tags assigned</span>
                    )}
                  </div>

                  {/* Add Tag */}
                  <div className="pt-2 flex space-x-1.5">
                    <input
                      type="text"
                      placeholder="Add tag (e.g. Mixer, Ransom)"
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      className="flex-1 bg-[#141820] border border-[#1E2330] rounded px-2 py-1 text-xs font-mono text-slate-200 focus:outline-none"
                    />
                    <select
                      value={newCategory}
                      onChange={(e) => setNewCategory(e.target.value)}
                      className="bg-[#141820] border border-[#1E2330] rounded px-1.5 py-1 text-xs font-mono text-slate-300 focus:outline-none"
                    >
                      <option value="mixer">Mixer</option>
                      <option value="exchange">Exchange</option>
                      <option value="ransomware">Ransom</option>
                      <option value="sanctioned">OFAC</option>
                      <option value="other">Other</option>
                    </select>
                    <button
                      onClick={handleAddTag}
                      className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center text-slate-500 font-mono space-y-2">
              <Share2 className="w-8 h-8 text-slate-600" />
              <p className="text-xs">Click any node in the canvas to inspect forensic properties.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
