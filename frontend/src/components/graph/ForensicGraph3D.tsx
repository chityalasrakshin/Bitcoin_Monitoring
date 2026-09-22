import React, { useEffect, useRef, useState, useCallback } from 'react';
import ForceGraph3D, { ForceGraph3DInstance } from '3d-force-graph';
import * as THREE from 'three';
import { GraphData, CytoscapeNodeData } from '../../types';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  Box,
  Layers,
  RotateCw,
  Sliders,
  Compass
} from 'lucide-react';

interface ForensicGraph3DProps {
  data: GraphData;
  selectedNodeId?: string | null;
  onSelectNode: (node: CytoscapeNodeData | null) => void;
  onExpandNode?: (nodeId: string) => void;
}

export const ForensicGraph3D: React.FC<ForensicGraph3DProps> = ({
  data,
  selectedNodeId,
  onSelectNode,
  onExpandNode,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<ForceGraph3DInstance | null>(null);

  const [is3DMode, setIs3DMode] = useState<boolean>(true);
  const [autoRotate, setAutoRotate] = useState<boolean>(false);
  const [minRiskFilter, setMinRiskFilter] = useState<number>(0);
  const [showFilterBar, setShowFilterBar] = useState<boolean>(false);

  // Helper to create text sprite badge for 3D nodes
  const createTextSprite = (text: string, color: string = '#E2E8F0') => {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    if (!ctx) return new THREE.Object3D();

    ctx.fillStyle = 'rgba(10, 12, 18, 0.85)';
    ctx.strokeStyle = '#1E2330';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(4, 4, 248, 56, 12);
    ctx.fill();
    ctx.stroke();

    ctx.font = 'bold 22px "JetBrains Mono", monospace';
    ctx.fillStyle = color;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const spriteMaterial = new THREE.SpriteMaterial({
      map: texture,
      depthWrite: false,
      transparent: true,
    });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(22, 5.5, 1);
    return sprite;
  };

  // Convert GraphData into 3D Force Graph format
  const getFormattedData = useCallback(() => {
    const nodes = data.nodes
      .filter((n) => (n.data.risk_score || 0) >= minRiskFilter)
      .map((n) => ({
        id: n.data.id,
        label: n.data.label,
        type: n.data.type,
        risk_score: n.data.risk_score || 0.0,
        cluster_id: n.data.cluster_id,
        tags: n.data.tags || [],
        extra: n.data.extra || {},
        rawNodeData: n.data,
      }));

    const validNodeIds = new Set(nodes.map((n) => n.id));

    const links = data.edges
      .filter((e) => validNodeIds.has(e.data.source) && validNodeIds.has(e.data.target))
      .map((e) => ({
        id: e.data.id,
        source: e.data.source,
        target: e.data.target,
        label: e.data.label,
        amount: e.data.amount || 0.1,
        latency_ms: e.data.latency_ms,
        confidence: e.data.confidence,
      }));

    return { nodes, links };
  }, [data, minRiskFilter]);

  // Initialize and mount 3D Force Graph
  useEffect(() => {
    if (!containerRef.current) return;

    const graph = new ForceGraph3D(containerRef.current, { controlType: 'orbit' })
      .backgroundColor('#07090E')
      .showNavInfo(false)
      .nodeRelSize(5)
      .linkWidth((link: any) => {
        const amt = link.amount || 0.1;
        return Math.min(3.5, Math.max(1.2, amt * 0.4));
      })
      .linkColor((link: any) => {
        if (link.label === 'FIRST_RELAYED_BY') return 'rgba(6, 182, 212, 0.7)';
        if (link.label === 'SAME_ENTITY_AS') return 'rgba(168, 85, 247, 0.8)';
        return 'rgba(71, 85, 105, 0.6)';
      })
      .linkCurvature(0.12)
      .linkDirectionalArrowLength(3.5)
      .linkDirectionalArrowRelPos(0.9)
      .linkDirectionalArrowColor(() => 'rgba(148, 163, 184, 0.8)')
      // Directional Flowing Particle System for UTXO movement
      .linkDirectionalParticles((link: any) => {
        if (link.label === 'FIRST_RELAYED_BY') return 1;
        return 3;
      })
      .linkDirectionalParticleWidth((link: any) => {
        const amt = link.amount || 0.1;
        return Math.min(2.8, Math.max(1.5, amt * 0.3));
      })
      .linkDirectionalParticleSpeed((link: any) => {
        const amt = link.amount || 0.1;
        return Math.min(0.015, Math.max(0.004, amt * 0.002));
      })
      .linkDirectionalParticleColor((link: any) => {
        if (link.label === 'FIRST_RELAYED_BY') return '#06B6D4';
        if (link.amount && link.amount >= 1.0) return '#F59E0B'; // High value gold particle
        return '#60A5FA'; // Normal flow neon blue
      })
      // Custom 3D Object Rendering for Nodes
      .nodeThreeObject((node: any) => {
        const group = new THREE.Group();
        const isSelected = selectedNodeId === node.id;

        if (node.type === 'wallet') {
          // Sphere with risk coloring
          const radius = isSelected ? 6.5 : 5.0;
          const risk = node.risk_score || 0;
          let color = 0x38bdf8; // Low risk cyan-slate
          let emissive = 0x0369a1;

          if (risk >= 0.7) {
            color = 0xef4444; // High risk crimson
            emissive = 0x991b1b;
          } else if (risk >= 0.4) {
            color = 0xf59e0b; // Medium risk amber
            emissive = 0xb45309;
          }

          const geometry = new THREE.SphereGeometry(radius, 24, 24);
          const material = new THREE.MeshStandardMaterial({
            color,
            emissive,
            emissiveIntensity: isSelected ? 0.9 : 0.4,
            roughness: 0.2,
            metalness: 0.6,
          });
          const mesh = new THREE.Mesh(geometry, material);
          group.add(mesh);

          // Aura glow ring if high risk or selected
          if (risk >= 0.7 || isSelected) {
            const ringGeo = new THREE.RingGeometry(radius + 1.2, radius + 2.5, 32);
            const ringMat = new THREE.MeshBasicMaterial({
              color: isSelected ? 0x60a5fa : 0xef4444,
              side: THREE.DoubleSide,
              transparent: true,
              opacity: 0.6,
            });
            const ring = new THREE.Mesh(ringGeo, ringMat);
            group.add(ring);
          }
        } else if (node.type === 'transaction') {
          // Neon blue 3D Octahedron / Diamond
          const size = isSelected ? 7.0 : 5.5;
          const geometry = new THREE.OctahedronGeometry(size);
          const material = new THREE.MeshStandardMaterial({
            color: 0x3b82f6,
            emissive: 0x1d4ed8,
            emissiveIntensity: isSelected ? 0.9 : 0.5,
            roughness: 0.3,
            metalness: 0.7,
          });
          const mesh = new THREE.Mesh(geometry, material);
          group.add(mesh);
        } else if (node.type === 'ip') {
          // Cyan Box / Cylinder for peer network relay
          const geometry = new THREE.CylinderGeometry(4, 4, 6, 16);
          const material = new THREE.MeshStandardMaterial({
            color: 0x06b6d4,
            emissive: 0x0e7490,
            emissiveIntensity: 0.6,
            roughness: 0.3,
            metalness: 0.5,
          });
          const mesh = new THREE.Mesh(geometry, material);
          group.add(mesh);
        }

        // Add 3D text badge above node
        const labelText = node.label || node.id.slice(0, 10);
        let badgeColor = '#94A3B8';
        if (node.type === 'wallet' && node.risk_score >= 0.7) badgeColor = '#F87171';
        else if (node.type === 'transaction') badgeColor = '#60A5FA';
        else if (node.type === 'ip') badgeColor = '#22D3EE';

        const sprite = createTextSprite(labelText, badgeColor);
        sprite.position.set(0, 10, 0);
        group.add(sprite);

        return group;
      })
      .nodeThreeObjectExtend(false)
      // Custom Tooltip
      .nodeLabel((node: any) => {
        const riskPercent = ((node.risk_score || 0) * 100).toFixed(1);
        const tags = node.tags?.length ? node.tags.join(', ') : 'None';
        return `
          <div style="background: rgba(14, 17, 24, 0.95); border: 1px solid #1E2330; border-radius: 6px; padding: 8px 10px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #E2E8F0; box-shadow: 0 8px 24px rgba(0,0,0,0.6);">
            <div style="font-size: 9px; text-transform: uppercase; color: #64748B; margin-bottom: 2px;">${node.type} Entity</div>
            <div style="font-weight: 600; color: #F8FAFC; margin-bottom: 4px;">${node.id}</div>
            <div style="display: flex; gap: 8px;">
              <span>Risk: <strong style="color: ${node.risk_score >= 0.7 ? '#EF4444' : node.risk_score >= 0.4 ? '#F59E0B' : '#38BDF8'}">${riskPercent}%</strong></span>
              ${node.cluster_id ? `<span style="color: #C084FC;">Cluster: ${node.cluster_id}</span>` : ''}
            </div>
            <div style="font-size: 10px; color: #94A3B8; margin-top: 4px;">Tags: ${tags}</div>
          </div>
        `;
      })
      // Link Tooltip
      .linkLabel((link: any) => {
        return `
          <div style="background: rgba(14, 17, 24, 0.95); border: 1px solid #1E2330; border-radius: 6px; padding: 6px 8px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #E2E8F0;">
            <div style="color: #38BDF8; font-weight: 600;">${link.label}</div>
            ${link.amount ? `<div>Value: <strong>${link.amount.toFixed(6)} BTC</strong></div>` : ''}
            ${link.latency_ms ? `<div>Latency: <strong>${link.latency_ms.toFixed(1)} ms</strong></div>` : ''}
          </div>
        `;
      })
      // Event Listeners
      .onNodeClick((node: any) => {
        onSelectNode(node.rawNodeData);
        // Smooth camera fly-to focus
        const distance = 80;
        const distRatio = 1 + distance / Math.hypot(node.x || 1, node.y || 1, node.z || 1);
        graph.cameraPosition(
          { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
          node,
          1000
        );
      })
      .onBackgroundClick(() => {
        onSelectNode(null);
      })
      .onNodeRightClick((node: any) => {
        if (onExpandNode) {
          onExpandNode(node.id);
        }
      });

    // Configure Lighting for glossy forensic aesthetic
    const scene = graph.scene();
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x60a5fa, 0.8);
    dirLight1.position.set(100, 150, 100);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xa855f7, 0.5);
    dirLight2.position.set(-100, -150, -100);
    scene.add(dirLight2);

    graphRef.current = graph;

    // Handle Window Resize
    const handleResize = () => {
      if (containerRef.current && graphRef.current) {
        graphRef.current.width(containerRef.current.clientWidth);
        graphRef.current.height(containerRef.current.clientHeight);
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      graph._destructor();
    };
  }, []);

  // Update Graph Data when dependencies change
  useEffect(() => {
    if (!graphRef.current) return;
    const formatted = getFormattedData();
    graphRef.current.graphData(formatted);

    // Initial zoom to fit after simulation starts
    const timer = setTimeout(() => {
      graphRef.current?.zoomToFit(600, 30);
    }, 400);

    return () => clearTimeout(timer);
  }, [getFormattedData]);

  // Handle Dimension Mode (3D vs 2D)
  useEffect(() => {
    if (!graphRef.current) return;
    graphRef.current.numDimensions(is3DMode ? 3 : 2);
    graphRef.current.d3ReheatSimulation();
  }, [is3DMode]);

  // Handle Auto-Rotate
  useEffect(() => {
    if (!graphRef.current) return;
    const controls = graphRef.current.controls() as any;
    if (controls) {
      controls.autoRotate = autoRotate;
      controls.autoRotateSpeed = 1.0;
    }
  }, [autoRotate]);

  // Programmatic selection highlight & focus
  useEffect(() => {
    if (!graphRef.current) return;
    if (selectedNodeId) {
      const formatted = getFormattedData();
      const targetNode: any = formatted.nodes.find((n) => n.id === selectedNodeId);
      if (targetNode && targetNode.x !== undefined) {
        const distance = 80;
        const distRatio = 1 + distance / Math.hypot(targetNode.x || 1, targetNode.y || 1, targetNode.z || 1);
        graphRef.current.cameraPosition(
          {
            x: (targetNode.x || 0) * distRatio,
            y: (targetNode.y || 0) * distRatio,
            z: (targetNode.z || 0) * distRatio,
          },
          targetNode,
          800
        );
      }
    }
  }, [selectedNodeId, getFormattedData]);

  // Camera Controls
  const handleZoomIn = () => {
    if (!graphRef.current) return;
    const { x, y, z } = graphRef.current.cameraPosition();
    graphRef.current.cameraPosition({ x: x * 0.8, y: y * 0.8, z: z * 0.8 }, undefined, 400);
  };

  const handleZoomOut = () => {
    if (!graphRef.current) return;
    const { x, y, z } = graphRef.current.cameraPosition();
    graphRef.current.cameraPosition({ x: x * 1.25, y: y * 1.25, z: z * 1.25 }, undefined, 400);
  };

  const handleFit = () => {
    graphRef.current?.zoomToFit(800, 40);
  };

  const handleReheat = () => {
    graphRef.current?.d3ReheatSimulation();
  };

  return (
    <div className="relative w-full h-full bg-[#07090E] overflow-hidden flex flex-col">
      {/* 3D WebGL Canvas */}
      <div ref={containerRef} className="flex-1 cursor-grab active:cursor-grabbing" />

      {/* Control Overlay Toolbar */}
      <div className="absolute top-4 right-4 flex items-center space-x-1 bg-[#10131B]/90 backdrop-blur border border-[#1E2330] rounded p-1 shadow-2xl z-10">
        {/* 2D / 3D Toggle */}
        <button
          onClick={() => setIs3DMode(!is3DMode)}
          title={is3DMode ? 'Switch to 2D Planar Mode' : 'Switch to 3D Spatial Mode'}
          className={`px-2 py-1 rounded text-[11px] font-mono flex items-center space-x-1 transition ${
            is3DMode
              ? 'bg-blue-600 text-white font-semibold'
              : 'bg-[#181C26] text-slate-300 hover:text-white'
          }`}
        >
          <Box className="w-3.5 h-3.5" />
          <span>{is3DMode ? '3D' : '2D'}</span>
        </button>

        {/* Auto Rotate (Cinematic Orbit) */}
        <button
          onClick={() => setAutoRotate(!autoRotate)}
          title="Toggle Cinematic Orbit Rotation"
          className={`p-1.5 rounded transition ${
            autoRotate
              ? 'bg-purple-600 text-white'
              : 'hover:bg-[#1C212D] text-slate-400 hover:text-white'
          }`}
        >
          <RotateCw className={`w-4 h-4 ${autoRotate ? 'animate-spin' : ''}`} />
        </button>

        <div className="w-[1px] h-4 bg-[#1E2330] mx-0.5" />

        {/* Zoom In */}
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="p-1.5 hover:bg-[#1C212D] text-slate-300 hover:text-white rounded transition"
        >
          <ZoomIn className="w-4 h-4" />
        </button>

        {/* Zoom Out */}
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="p-1.5 hover:bg-[#1C212D] text-slate-300 hover:text-white rounded transition"
        >
          <ZoomOut className="w-4 h-4" />
        </button>

        {/* Fit to View */}
        <button
          onClick={handleFit}
          title="Fit Graph to View"
          className="p-1.5 hover:bg-[#1C212D] text-slate-300 hover:text-white rounded transition"
        >
          <Maximize2 className="w-4 h-4" />
        </button>

        {/* Re-run force simulation */}
        <button
          onClick={handleReheat}
          title="Relax / Reheat Force Layout"
          className="p-1.5 hover:bg-[#1C212D] text-slate-300 hover:text-white rounded transition"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        <div className="w-[1px] h-4 bg-[#1E2330] mx-0.5" />

        {/* Toggle Risk Filter */}
        <button
          onClick={() => setShowFilterBar(!showFilterBar)}
          title="Filter Risk Threshold"
          className={`p-1.5 rounded transition ${
            showFilterBar || minRiskFilter > 0
              ? 'bg-amber-600 text-white'
              : 'hover:bg-[#1C212D] text-slate-400 hover:text-white'
          }`}
        >
          <Sliders className="w-4 h-4" />
        </button>
      </div>

      {/* Expandable Risk Threshold Slider */}
      {showFilterBar && (
        <div className="absolute top-16 right-4 bg-[#10131B]/95 backdrop-blur border border-[#1E2330] rounded p-3 shadow-2xl z-10 w-64 space-y-2">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-300">
            <span>Min Risk Filter</span>
            <span className="font-semibold text-amber-400">
              {(minRiskFilter * 100).toFixed(0)}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="0.8"
            step="0.05"
            value={minRiskFilter}
            onChange={(e) => setMinRiskFilter(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-[#1E2330] rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <div className="flex justify-between text-[9px] font-mono text-slate-500">
            <span>All (0%)</span>
            <span>Suspicious (&ge; 40%)</span>
            <span>Critical (&ge; 70%)</span>
          </div>
        </div>
      )}

      {/* Floating 3D Graph Legend */}
      <div className="absolute bottom-4 left-4 bg-[#0F121A]/90 backdrop-blur border border-[#1E2330] rounded px-3 py-2.5 text-[10px] font-mono text-slate-400 space-y-1.5 shadow-2xl z-10 pointer-events-none select-none">
        <div className="text-[9px] uppercase tracking-wider text-slate-500 font-semibold mb-1 flex items-center space-x-1.5">
          <Compass className="w-3 h-3 text-blue-400" />
          <span>3D Forensic Topology</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
          <span>High-Risk Wallet (&ge; 0.70)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(245,158,11,0.6)]" />
          <span>Medium-Risk Wallet (0.40 - 0.69)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
          <span>Low-Risk Wallet</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rotate-45 bg-blue-500 inline-block shadow-[0_0_6px_rgba(59,130,246,0.6)]" />
          <span>Transaction (TXID)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-2 rounded-sm bg-cyan-400 inline-block" />
          <span>Peer Relay Observation</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-0.5 bg-blue-400 inline-block" />
          <span>UTXO Fund Flow Beam</span>
        </div>
      </div>
    </div>
  );
};
