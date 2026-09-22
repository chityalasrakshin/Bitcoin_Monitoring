import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import { GraphData, CytoscapeNodeData } from '../../types';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw } from 'lucide-react';

interface InvestigationGraphProps {
  data: GraphData;
  selectedNodeId?: string | null;
  onSelectNode: (node: CytoscapeNodeData | null) => void;
  onExpandNode?: (nodeId: string) => void;
}

export const InvestigationGraph: React.FC<InvestigationGraphProps> = ({
  data,
  selectedNodeId,
  onSelectNode,
  onExpandNode,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Convert data to Cytoscape elements
    const elements: cytoscape.ElementDefinition[] = [
      ...data.nodes.map((n) => ({
        group: 'nodes' as const,
        data: {
          id: n.data.id,
          label: n.data.label,
          type: n.data.type,
          risk_score: n.data.risk_score,
          cluster_id: n.data.cluster_id,
          tags: n.data.tags || [],
          extra: n.data.extra || {},
        },
      })),
      ...data.edges.map((e) => ({
        group: 'edges' as const,
        data: {
          id: e.data.id,
          source: e.data.source,
          target: e.data.target,
          label: e.data.label,
          amount: e.data.amount,
          latency_ms: e.data.latency_ms,
        },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        // Node base style
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#E2E8F0',
            'font-size': '10px',
            'font-family': 'JetBrains Mono, monospace',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'background-color': '#475569',
            'border-width': 1.5,
            'border-color': '#1E293B',
            'width': 28,
            'height': 28,
          },
        },
        // Wallets
        {
          selector: 'node[type = "wallet"]',
          style: {
            'shape': 'ellipse',
            'background-color': (ele) => {
              const risk = ele.data('risk_score') || 0;
              if (risk >= 0.7) return '#DC2626'; // High risk crimson
              if (risk >= 0.4) return '#D97706'; // Medium risk amber
              return '#334155'; // Low risk slate
            },
            'border-color': (ele) => {
              const risk = ele.data('risk_score') || 0;
              if (risk >= 0.7) return '#EF4444';
              if (risk >= 0.4) return '#F59E0B';
              return '#475569';
            },
            'border-width': 2,
          },
        },
        // Transactions
        {
          selector: 'node[type = "transaction"]',
          style: {
            'shape': 'diamond',
            'background-color': '#1E293B',
            'border-color': '#3B82F6',
            'border-width': 2,
            'width': 32,
            'height': 32,
          },
        },
        // IP observations
        {
          selector: 'node[type = "ip"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': '#0F172A',
            'border-color': '#06B6D4',
            'border-width': 1.5,
            'width': 38,
            'height': 24,
          },
        },
        // Selected node highlight
        {
          selector: ':selected',
          style: {
            'border-color': '#60A5FA',
            'border-width': 3,
            'underlay-color': '#3B82F6',
            'underlay-padding': 4,
            'underlay-opacity': 0.5,
          },
        },
        // Edge base style
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#334155',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
          },
        },
        // FIRST_RELAYED_BY network edge
        {
          selector: 'edge[label = "FIRST_RELAYED_BY"]',
          style: {
            'line-style': 'dashed',
            'line-color': '#06B6D4',
            'target-arrow-color': '#06B6D4',
            'width': 1.5,
          },
        },
        // SAME_ENTITY_AS cluster edge
        {
          selector: 'edge[label = "SAME_ENTITY_AS"]',
          style: {
            'line-style': 'dotted',
            'line-color': '#A855F7',
            'target-arrow-shape': 'none',
            'width': 2,
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 50,
        nodeRepulsion: () => 8000,
        idealEdgeLength: () => 60,
      },
    });

    // Event listeners
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      onSelectNode(node.data());
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        onSelectNode(null);
      }
    });

    cy.on('dbltap', 'node', (evt) => {
      const nodeId = evt.target.id();
      if (onExpandNode) {
        onExpandNode(nodeId);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [data]);

  // Select node programmatically if selectedNodeId changes
  useEffect(() => {
    if (!cyRef.current) return;
    cyRef.current.nodes().unselect();
    if (selectedNodeId) {
      const ele = cyRef.current.getElementById(selectedNodeId);
      if (ele && ele.length > 0) {
        ele.select();
      }
    }
  }, [selectedNodeId]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 40);
  const handleLayoutReset = () => {
    cyRef.current?.layout({
      name: 'cose',
      animate: true,
      animationDuration: 400,
      padding: 50,
    }).run();
  };

  return (
    <div className="relative w-full h-full bg-[#080A0E] overflow-hidden flex flex-col">
      {/* Canvas */}
      <div ref={containerRef} className="cytoscape-canvas flex-1 cursor-crosshair" />

      {/* Control overlay toolbar */}
      <div className="absolute top-4 right-4 flex items-center space-x-1 bg-[#12151C]/90 backdrop-blur border border-[#1E2330] rounded p-1 shadow-lg z-10">
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="p-1.5 hover:bg-[#1C212D] text-slate-300 hover:text-white rounded"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="p-1.5 hover:bg-[#1C212D] text-slate-300 hover:text-white rounded"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleFit}
          title="Fit Graph to View"
          className="p-1.5 hover:bg-[#1C212D] text-slate-300 hover:text-white rounded"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
        <div className="w-[1px] h-4 bg-[#1E2330] mx-1" />
        <button
          onClick={handleLayoutReset}
          title="Re-run Force-Directed Layout"
          className="p-1.5 hover:bg-[#1C212D] text-slate-300 hover:text-white rounded"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Legend overlay */}
      <div className="absolute bottom-4 left-4 bg-[#111318]/90 backdrop-blur border border-[#1E2330] rounded px-3 py-2 text-[10px] font-mono text-slate-400 space-y-1 shadow-lg z-10">
        <div className="text-[9px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Graph Legend</div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-red-600 border border-red-400" />
          <span>High-Risk Wallet (&ge; 0.70)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-amber-300" />
          <span>Medium-Risk Wallet</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rotate-45 bg-[#1E293B] border border-blue-500 inline-block" />
          <span>Transaction (TXID)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-2 rounded bg-slate-900 border border-cyan-500 inline-block" />
          <span>Peer IP Telemetry</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-4 border-b border-dashed border-cyan-400 inline-block" />
          <span>Relay Telemetry Edge</span>
        </div>
      </div>
    </div>
  );
};
