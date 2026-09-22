import React from 'react';
import ReactECharts from 'echarts-for-react';

interface SankeyNode {
  name: string;
}

interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

interface FundFlowSankeyProps {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export const FundFlowSankey: React.FC<FundFlowSankeyProps> = ({ nodes, links }) => {
  if (!nodes || nodes.length === 0 || !links || links.length === 0) {
    return (
      <div className="h-44 flex items-center justify-center text-xs text-slate-500 font-mono">
        Select a transaction or address to render fund flow Sankey
      </div>
    );
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      backgroundColor: '#111318',
      borderColor: '#1E2330',
      textStyle: { color: '#E2E8F0', fontFamily: 'JetBrains Mono', fontSize: 11 },
    },
    series: [
      {
        type: 'sankey',
        layout: 'none',
        emphasis: { focus: 'adjacency' },
        nodeAlign: 'justify',
        data: nodes.map((n) => ({
          name: n.name,
          itemStyle: {
            color: n.name.startsWith('TX:') ? '#3B82F6' : '#64748B',
            borderColor: '#1E2330',
          },
        })),
        links,
        lineStyle: {
          color: 'source',
          curveness: 0.5,
          opacity: 0.35,
        },
        label: {
          color: '#94A3B8',
          fontFamily: 'JetBrains Mono',
          fontSize: 10,
        },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: '220px', width: '100%' }} />;
};
