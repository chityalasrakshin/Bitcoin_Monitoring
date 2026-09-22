import React from 'react';
import ReactECharts from 'echarts-for-react';

interface RiskDistributionProps {
  scores: number[];
}

export const RiskDistributionChart: React.FC<RiskDistributionProps> = ({ scores }) => {
  const buckets = [0, 0, 0, 0, 0];
  scores.forEach((s) => {
    if (s < 0.2) buckets[0]++;
    else if (s < 0.4) buckets[1]++;
    else if (s < 0.6) buckets[2]++;
    else if (s < 0.8) buckets[3]++;
    else buckets[4]++;
  });

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#111318',
      borderColor: '#1E2330',
      textStyle: { color: '#E2E8F0', fontFamily: 'JetBrains Mono', fontSize: 11 },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: ['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0'],
      axisLine: { lineStyle: { color: '#1E2330' } },
      axisLabel: { color: '#64748B', fontFamily: 'JetBrains Mono', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#161B24' } },
      axisLabel: { color: '#64748B', fontFamily: 'JetBrains Mono', fontSize: 10 },
    },
    series: [
      {
        name: 'Entities',
        type: 'bar',
        barWidth: '55%',
        data: [
          { value: buckets[0], itemStyle: { color: '#10B981' } },
          { value: buckets[1], itemStyle: { color: '#3B82F6' } },
          { value: buckets[2], itemStyle: { color: '#F59E0B' } },
          { value: buckets[3], itemStyle: { color: '#F97316' } },
          { value: buckets[4], itemStyle: { color: '#EF4444' } },
        ],
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: '180px', width: '100%' }} />;
};
