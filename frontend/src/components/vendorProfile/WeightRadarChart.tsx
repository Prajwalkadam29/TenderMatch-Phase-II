import React, { useEffect, useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { matchingService } from '../../services/matchingService';

interface WeightRadarChartProps {
  vendorProfileId: string;
}

const GLOBAL_DEFAULT_WEIGHTS: Record<string, number> = {
  domain: 0.25,
  geography: 0.15,
  financial: 0.20,
  experience: 0.15,
  certification: 0.10,
  semantic: 0.10,
  confidence: 0.05
};

export const WeightRadarChart: React.FC<WeightRadarChartProps> = ({ vendorProfileId }) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWeights = async () => {
      if (!vendorProfileId) return;
      try {
        const res = await matchingService.getWeights(vendorProfileId);
        const learnedWeights = res.weights;
        
        const chartData = Object.keys(GLOBAL_DEFAULT_WEIGHTS).map((dim) => {
          return {
            dimension: dim.charAt(0).toUpperCase() + dim.slice(1),
            "Learned Weight": (learnedWeights[dim] * 100) || 0,
            "Global Default": (GLOBAL_DEFAULT_WEIGHTS[dim] * 100),
            fullMark: 35 // Max weight to show on radius
          };
        });
        
        setData(chartData);
      } catch (err) {
        console.error("Failed to load weights", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchWeights();
  }, [vendorProfileId]);

  if (loading) {
    return <div className="flex items-center justify-center p-8 text-sm text-gray-500">Loading AI Weights...</div>;
  }

  if (data.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 w-full max-w-lg mx-auto">
      <div className="text-center mb-4">
        <h3 className="text-lg font-semibold text-slate-800">AI Match Dimension Weights</h3>
        <p className="text-sm text-slate-500">Adapted based on your match feedback</p>
      </div>
      
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis dataKey="dimension" tick={{ fill: '#64748b', fontSize: 12 }} />
            <PolarRadiusAxis angle={90} domain={[0, 35]} tick={false} axisLine={false} />
            <Radar 
              name="Learned (Your Profile)" 
              dataKey="Learned Weight" 
              stroke="#6366f1" 
              fill="#818cf8" 
              fillOpacity={0.5} 
            />
            <Radar 
              name="Global Default" 
              dataKey="Global Default" 
              stroke="#94a3b8" 
              fill="#cbd5e1" 
              fillOpacity={0.3} 
            />
            <Tooltip 
              formatter={(value: any) => [typeof value === 'number' ? `${value.toFixed(1)}%` : value, undefined]}
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
            <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
