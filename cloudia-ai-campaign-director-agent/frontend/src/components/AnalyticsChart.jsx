import { useMemo } from 'react';

function BarChart({ data, valueKey, labelKey, color = '#3b5bdb', height = 180 }) {
  const max = useMemo(() => Math.max(...data.map((d) => d[valueKey] || 0), 1), [data, valueKey]);

  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {data.map((item, idx) => {
        const pct = ((item[valueKey] || 0) / max) * 100;
        return (
          <div key={idx} className="flex-1 flex flex-col items-center gap-1 group" title={`${item[labelKey]}: ${item[valueKey]?.toLocaleString()}`}>
            <div
              className="w-full rounded-t transition-all duration-300 hover:opacity-80"
              style={{ height: `${Math.max(pct, 2)}%`, backgroundColor: color }}
            />
            <span className="text-xs text-gray-400 rotate-45 origin-left hidden sm:block truncate w-8">
              {item[labelKey]}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function LineChart({ data, series = [], height = 200 }) {
  const allValues = series.flatMap((s) => data.map((d) => d[s.key] || 0));
  const max = Math.max(...allValues, 1);
  const width = 600;
  const padding = 32;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const COLORS = ['#3b5bdb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  const getPoints = (key) =>
    data.map((d, i) => {
      const x = padding + (i / Math.max(data.length - 1, 1)) * chartWidth;
      const y = padding + chartHeight - ((d[key] || 0) / max) * chartHeight;
      return `${x},${y}`;
    });

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        style={{ minHeight: height }}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = padding + chartHeight * (1 - frac);
          return (
            <g key={frac}>
              <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="#e5e7eb" strokeWidth="1" />
              <text x={padding - 4} y={y + 4} fontSize="10" textAnchor="end" fill="#9ca3af">
                {Math.round(max * frac).toLocaleString()}
              </text>
            </g>
          );
        })}

        {data.map((d, i) => {
          const x = padding + (i / Math.max(data.length - 1, 1)) * chartWidth;
          return (
            <text key={i} x={x} y={height - 4} fontSize="9" textAnchor="middle" fill="#9ca3af">
              {d.label || d.date || i}
            </text>
          );
        })}

        {series.map((s, si) => {
          const points = getPoints(s.key);
          const color = s.color || COLORS[si % COLORS.length];
          const d = data.map((item, i) => {
            const x = padding + (i / Math.max(data.length - 1, 1)) * chartWidth;
            const y = padding + chartHeight - ((item[s.key] || 0) / max) * chartHeight;
            return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
          });
          return (
            <g key={s.key}>
              <path d={d.join(' ')} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
              {data.map((item, i) => {
                const x = padding + (i / Math.max(data.length - 1, 1)) * chartWidth;
                const y = padding + chartHeight - ((item[s.key] || 0) / max) * chartHeight;
                return (
                  <circle key={i} cx={x} cy={y} r="3" fill={color}>
                    <title>{`${s.label || s.key}: ${item[s.key]?.toLocaleString()}`}</title>
                  </circle>
                );
              })}
            </g>
          );
        })}
      </svg>

      {series.length > 1 && (
        <div className="flex flex-wrap gap-3 mt-2 justify-center">
          {series.map((s, si) => {
            const COLORS = ['#3b5bdb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
            const color = s.color || COLORS[si % COLORS.length];
            return (
              <div key={s.key} className="flex items-center gap-1.5 text-xs text-gray-600">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                {s.label || s.key}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function AnalyticsChart({ type = 'bar', data = [], series = [], valueKey, labelKey, color, height }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-400 text-sm">
        No data available
      </div>
    );
  }

  if (type === 'line') {
    return <LineChart data={data} series={series} height={height} />;
  }

  return <BarChart data={data} valueKey={valueKey} labelKey={labelKey} color={color} height={height} />;
}
