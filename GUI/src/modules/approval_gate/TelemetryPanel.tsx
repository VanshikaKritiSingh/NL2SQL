// src/modules/m14/TelemetryPanel.tsx
import React, { useState } from 'react';
import { Calculator, ShieldAlert, AlertTriangle, CheckCircle2, Lock, TrendingUp } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import type { CostEstimate, SecurityCheck } from '../../types/approval';

interface TelemetryPanelProps {
  costEstimate: CostEstimate;
  securityCheck: SecurityCheck;
}

interface TimePoint {
  date: string;
  value: number;
  delta: string;
}

const TIME_SERIES_DATA: TimePoint[] = [
  { date: 'Oct 12', value: 120, delta: '+8.2%' },
  { date: 'Oct 13', value: 145, delta: '+12.1%' },
  { date: 'Oct 14', value: 132, delta: '-4.3%' },
  { date: 'Oct 15', value: 178, delta: '+18.4%' },
  { date: 'Oct 16', value: 165, delta: '+3.2%' },
  { date: 'Oct 17', value: 210, delta: '+14.8%' },
  { date: 'Oct 18', value: 195, delta: '+7.5%' },
];

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ costEstimate, securityCheck }) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const [activeIndex, setActiveIndex] = useState<number>(5); // Default to Oct 17
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);

  // SVG Chart Geometry
  const width = 500;
  const height = 150;
  const paddingX = 40;
  const paddingY = 25;
  const chartW = width - paddingX * 2;
  const chartH = height - paddingY * 2;

  const minVal = 100;
  const maxVal = 240;

  const points = TIME_SERIES_DATA.map((pt, i) => {
    const x = paddingX + (i / (TIME_SERIES_DATA.length - 1)) * chartW;
    const y = height - paddingY - ((pt.value - minVal) / (maxVal - minVal)) * chartH;
    return { x, y, ...pt };
  });

  // Generate smooth SVG spline curve path (Cubic Bezier)
  const generateSplinePath = () => {
    if (points.length < 2) return '';
    let d = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i != points.length - 2 ? points[i + 2] : p2;

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
    }
    return d;
  };

  const splineD = generateSplinePath();
  const areaD = `${splineD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${height - paddingY} Z`;

  const activePoint = points[activeIndex] || points[0];

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * width;

    // Find nearest point
    let nearestIdx = 0;
    let minDist = Infinity;
    points.forEach((p, idx) => {
      const dist = Math.abs(p.x - mouseX);
      if (dist < minDist) {
        minDist = dist;
        nearestIdx = idx;
      }
    });
    setActiveIndex(nearestIdx);
    setHoverPos({ x: points[nearestIdx].x, y: points[nearestIdx].y });
  };

  // Segmented radial tick-mark progress circle geometry
  const radialTicksCount = 32;
  const progressPercent = 88; // 88% optimizer safety & cache score
  const activeTicksCount = Math.round((progressPercent / 100) * radialTicksCount);

  return (
    <div className="flex flex-col gap-3 font-sans">
      {/* 2×2 Nested Sub-Card Grid inside parent Bento card */}
      <div
        className="bento-card p-4 transition-all duration-300 shadow-md rounded-none"
        style={{
          backgroundColor: isDark ? 'var(--bg-card)' : 'var(--bg-card)',
          border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid var(--border-subtle)',
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Calculator className={`w-4 h-4 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[#111111]'}`} />
            <span className="text-xs font-bold text-[var(--text-main)]">
              Pre-Flight Telemetry & Concurrency Guardrail
            </span>
          </div>
          <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-none ${
            isDark
              ? 'bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30'
              : 'bg-[#111111] text-white'
          }`}>
            Live Pre-Check
          </span>
        </div>

        {/* 2×2 Grid */}
        <div className="grid grid-cols-2 gap-2.5">
          {/* Sub-Card 1: Relative Cost */}
          <div
            className="p-3 rounded-none flex flex-col justify-between transition-all"
            style={{
              backgroundColor: isDark ? '#14141C' : '#FFFFFF',
              border: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid var(--border-subtle)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium text-[var(--text-muted)]">EXPLAIN Cost</span>
              <span className="text-[10px] font-semibold text-[#2ECC71] flex items-center gap-0.5">
                <TrendingUp className="w-2.5 h-2.5" /> +12.4%
              </span>
            </div>
            <div className="mt-2">
              <span className="text-lg font-bold text-[var(--text-main)]">
                {costEstimate.estimated_cost.toFixed(2)}
              </span>
              <span className="text-[10px] text-[var(--text-muted)] ml-1">units</span>
            </div>
            <div className="mt-1 flex items-center gap-1.5">
              <span className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded-none ${
                costEstimate.scan_type === 'index_only' || costEstimate.scan_type === 'index_scan'
                  ? isDark ? 'bg-emerald-500/10 text-emerald-400' : 'bg-emerald-50 text-emerald-700'
                  : isDark ? 'bg-rose-500/10 text-rose-400' : 'bg-rose-50 text-rose-700'
              }`}>
                {costEstimate.scan_type.replace('_', ' ')}
              </span>
            </div>
          </div>

          {/* Sub-Card 2: Estimated Rows */}
          <div
            className="p-3 rounded-none flex flex-col justify-between transition-all"
            style={{
              backgroundColor: isDark ? '#14141C' : '#FFFFFF',
              border: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid var(--border-subtle)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium text-[var(--text-muted)]">Estimated Rows</span>
              <span className="text-[10px] font-semibold text-[#2ECC71] flex items-center gap-0.5">
                <TrendingUp className="w-2.5 h-2.5" /> +4.8%
              </span>
            </div>
            <div className="mt-2">
              <span className="text-lg font-bold text-[var(--text-main)]">
                {costEstimate.estimated_rows.toLocaleString()}
              </span>
              <span className="text-[10px] text-[var(--text-muted)] ml-1">rows</span>
            </div>
            <div className="mt-1">
              <span className="text-[9px] text-[var(--text-muted)]">
                Cardinality bounded
              </span>
            </div>
          </div>

          {/* Sub-Card 3: Lock Granularity */}
          <div
            className="p-3 rounded-none flex flex-col justify-between transition-all"
            style={{
              backgroundColor: isDark ? '#14141C' : '#FFFFFF',
              border: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid var(--border-subtle)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium text-[var(--text-muted)]">Lock Granularity</span>
              <Lock className="w-3 h-3 text-[var(--text-muted)]" />
            </div>
            <div className="mt-2">
              <span className="text-sm font-bold uppercase text-[var(--text-main)]">
                {securityCheck.lock_level} LOCK
              </span>
            </div>
            <div className="mt-1">
              <span className="text-[9px] text-[var(--text-muted)]">
                Isolated transaction boundary
              </span>
            </div>
          </div>

          {/* Sub-Card 4: Concurrency & Deadlock */}
          <div
            className="p-3 rounded-none flex flex-col justify-between transition-all"
            style={{
              backgroundColor: isDark ? '#14141C' : '#FFFFFF',
              border: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid var(--border-subtle)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium text-[var(--text-muted)]">Deadlock Risk</span>
              <CheckCircle2 className="w-3 h-3 text-[#2ECC71]" />
            </div>
            <div className="mt-2">
              <span className={`text-sm font-bold uppercase ${
                securityCheck.deadlock_risk === 'none' || securityCheck.deadlock_risk === 'low'
                  ? 'text-[#2ECC71]'
                  : 'text-rose-500'
              }`}>
                {securityCheck.deadlock_risk}
              </span>
            </div>
            <div className="mt-1">
              <span className="text-[9px] text-[var(--text-muted)] font-mono">
                Role: AUTHORIZED
              </span>
            </div>
          </div>
        </div>

        {/* Warnings if any */}
        {costEstimate.warnings.length > 0 && (
          <div className="mt-3 space-y-1">
            {costEstimate.warnings.map((w, i) => (
              <div
                key={i}
                className={`flex items-center gap-1.5 text-[11px] p-2 rounded-none border ${
                  isDark
                    ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                    : 'text-amber-700 bg-amber-50 border-amber-200'
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>{w}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Gauges & Donut Row: Segmented Radial Progress Circle + Inverted Jet-Black Donut Card */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Segmented radial tick-mark progress circle */}
        <div
          className="bento-card p-3.5 flex flex-col items-center justify-center transition-all duration-300 shadow-md rounded-none"
          style={{
            backgroundColor: isDark ? 'var(--bg-card)' : 'var(--bg-card)',
            border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid var(--border-subtle)',
          }}
        >
          <div className="w-full flex items-center justify-between text-xs font-bold text-[var(--text-main)] mb-1">
            <span>Safety & Cache Efficiency</span>
            <span className="text-[10px] font-mono text-[#2ECC71]">OPTIMAL</span>
          </div>

          <div className="relative w-36 h-36 flex items-center justify-center my-1">
            <svg viewBox="0 0 120 120" className="w-full h-full transform -rotate-90">
              {Array.from({ length: radialTicksCount }).map((_, i) => {
                const angle = (i / radialTicksCount) * 2 * Math.PI;
                const innerR = 42;
                const outerR = 52;
                const x1 = 60 + innerR * Math.cos(angle);
                const y1 = 60 + innerR * Math.sin(angle);
                const x2 = 60 + outerR * Math.cos(angle);
                const y2 = 60 + outerR * Math.sin(angle);
                const isActive = i < activeTicksCount;

                return (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    strokeWidth={2.5}
                    strokeLinecap="round"
                    stroke={
                      isActive
                        ? isDark
                          ? '#8E94F2'
                          : '#111111'
                        : isDark
                        ? 'rgba(255,255,255,0.08)'
                        : '#E5E8EF'
                    }
                    className="transition-all duration-300"
                  />
                );
              })}
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="text-xl font-extrabold tracking-tight text-[var(--text-main)]">
                {progressPercent}%
              </span>
              <span className="text-[9px] uppercase font-bold text-[var(--text-muted)] tracking-wider">
                Integrity
              </span>
            </div>
          </div>
          <p className="text-[10px] text-[var(--text-muted)] text-center">
            Dual-path sandbox security verified
          </p>
        </div>

        {/* Inverted Jet-Black Card Containing a Grayscale Donut Chart */}
        <div
          className="rounded-none p-4 flex flex-col justify-between transition-all duration-300 shadow-xl"
          style={{
            backgroundColor: '#111111',
            color: '#FFFFFF',
            border: '1px solid rgba(255,255,255,0.12)',
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className="text-xs font-bold text-white tracking-tight">Workload Distribution</span>
              <p className="text-[10px] text-[#888C94]">By query execution mode</p>
            </div>
            <span className="text-[9px] font-mono px-2 py-0.5 rounded-none bg-white/10 text-white border border-white/15">
              Live
            </span>
          </div>

          <div className="flex items-center justify-around my-1">
            {/* SVG Grayscale Donut Chart */}
            <div className="relative w-24 h-24 shrink-0">
              <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
                {/* Segment 1: Read/Select (64%) -> #FFFFFF */}
                <circle
                  cx="50"
                  cy="50"
                  r="36"
                  fill="transparent"
                  stroke="#FFFFFF"
                  strokeWidth="14"
                  strokeDasharray="144 226"
                  strokeDashoffset="0"
                />
                {/* Segment 2: Mutation/DML (22%) -> #A0A0A5 */}
                <circle
                  cx="50"
                  cy="50"
                  r="36"
                  fill="transparent"
                  stroke="#8E8E94"
                  strokeWidth="14"
                  strokeDasharray="50 226"
                  strokeDashoffset="-144"
                />
                {/* Segment 3: DDL/Migration (14%) -> #404048 */}
                <circle
                  cx="50"
                  cy="50"
                  r="36"
                  fill="transparent"
                  stroke="#383840"
                  strokeWidth="14"
                  strokeDasharray="32 226"
                  strokeDashoffset="-194"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-sm font-bold text-white">100%</span>
              </div>
            </div>

            {/* Legend */}
            <div className="space-y-1.5 text-[10px]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-none bg-white shrink-0" />
                <span className="text-white font-medium">Read/Select (64%)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-none bg-[#8E8E94] shrink-0" />
                <span className="text-[#C8C8D0] font-medium">Mutation DML (22%)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-none bg-[#383840] shrink-0" />
                <span className="text-[#888C94] font-medium">DDL Alter (14%)</span>
              </div>
            </div>
          </div>

          <div className="text-[9px] text-[#888C94] text-right font-mono mt-1">
            Total Queries: 1,842 sampled
          </div>
        </div>
      </div>

      {/* Bottom Time-Series Spline Chart */}
      <div
        className="bento-card p-4 transition-all duration-300 shadow-md relative overflow-hidden rounded-none"
        style={{
          backgroundColor: isDark ? 'var(--bg-card)' : 'var(--bg-card)',
          border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid var(--border-subtle)',
        }}
      >
        <div className="flex items-center justify-between mb-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-[var(--text-main)]">
                Query Latency & Cost Time-Series
              </span>
              <span className="text-[10px] font-semibold text-[#2ECC71] px-2 py-0.5 rounded-none bg-[#2ECC71]/10">
                {activePoint.delta}
              </span>
            </div>
            <p className="text-[10px] text-[var(--text-muted)]">
              Historical execution timeline across pipeline checkpoints
            </p>
          </div>

          {/* Time range switcher */}
          <div className={`flex items-center gap-1 p-0.5 rounded-none text-[10px] font-medium ${
            isDark ? 'bg-[var(--bg-subtle)]' : 'bg-[#E5E8EF]'
          }`}>
            <span className={`px-2 py-0.5 rounded-none ${isDark ? 'bg-[var(--accent-primary)] text-white' : 'bg-[#111111] text-white'}`}>
              7D
            </span>
            <span className="px-2 py-0.5 text-[var(--text-muted)] cursor-pointer">
              30D
            </span>
          </div>
        </div>

        {/* Interactive SVG Spline Canvas */}
        <div className="relative w-full h-[150px]">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-full cursor-crosshair overflow-visible select-none"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoverPos(null)}
          >
            <defs>
              {/* Dark Theme Purple Gradient Area Fill */}
              <linearGradient id="darkPurpleAreaGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8E94F2" stopOpacity="0.30" />
                <stop offset="100%" stopColor="#8E94F2" stopOpacity="0.0" />
              </linearGradient>

              {/* Light Theme Subtle Gray Gradient Area Fill */}
              <linearGradient id="lightGrayAreaGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#111111" stopOpacity="0.09" />
                <stop offset="100%" stopColor="#111111" stopOpacity="0.0" />
              </linearGradient>

              {/* Glowing lavender filter for Dark mode */}
              <filter id="splineGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Grid horizontal guidelines */}
            <line x1={paddingX} y1={paddingY} x2={width - paddingX} y2={paddingY} stroke={isDark ? 'rgba(255,255,255,0.05)' : '#E5E8EF'} strokeDasharray="3 3" />
            <line x1={paddingX} y1={height / 2} x2={width - paddingX} y2={height / 2} stroke={isDark ? 'rgba(255,255,255,0.05)' : '#E5E8EF'} strokeDasharray="3 3" />
            <line x1={paddingX} y1={height - paddingY} x2={width - paddingX} y2={height - paddingY} stroke={isDark ? 'rgba(255,255,255,0.08)' : '#E5E8EF'} />

            {/* Gradient Area Fill */}
            <path
              d={areaD}
              fill={isDark ? 'url(#darkPurpleAreaGradient)' : 'url(#lightGrayAreaGradient)'}
            />

            {/* The Spline Curve */}
            <path
              d={splineD}
              fill="none"
              stroke={isDark ? '#E0D8FF' : '#111111'}
              strokeWidth={isDark ? 2.5 : 2.5}
              strokeLinecap="round"
              filter={isDark ? 'url(#splineGlow)' : undefined}
            />

            {/* Vertical dashed drop-line at active hover position */}
            <line
              x1={activePoint.x}
              y1={paddingY}
              x2={activePoint.x}
              y2={height - paddingY}
              stroke={isDark ? '#8E94F2' : '#111111'}
              strokeWidth={1.5}
              strokeDasharray="4 4"
            />

            {/* Glowing Hover Node */}
            {isDark ? (
              <g>
                <circle cx={activePoint.x} cy={activePoint.y} r={8} fill="#8E94F2" fillOpacity={0.3} className="animate-pulse" />
                <circle cx={activePoint.x} cy={activePoint.y} r={4.5} fill="#FFFFFF" stroke="#8E94F2" strokeWidth={2.5} />
              </g>
            ) : (
              <circle cx={activePoint.x} cy={activePoint.y} r={4.5} fill="#111111" stroke="#FFFFFF" strokeWidth={2} />
            )}

            {/* X-Axis Tick Labels */}
            {points.map((pt, i) => (
              <text
                key={i}
                x={pt.x}
                y={height - 8}
                textAnchor="middle"
                fontSize="9"
                fontFamily="sans-serif"
                fill={i === activeIndex ? (isDark ? '#FFFFFF' : '#111111') : '#888C94'}
                fontWeight={i === activeIndex ? 'bold' : 'normal'}
              >
                {pt.date}
              </text>
            ))}
          </svg>

          {/* Light Theme: Black pill label on active X-axis point */}
          {!isDark && (
            <div
              className="absolute pointer-events-none transform -translate-x-1/2"
              style={{
                left: `${(activePoint.x / width) * 100}%`,
                top: `${(activePoint.y / height) * 100 - 28}%`,
              }}
            >
              <div className="bg-[#111111] text-white text-[10px] font-mono px-2 py-0.5 rounded-none shadow-md flex items-center gap-1.5 whitespace-nowrap">
                <span>{activePoint.date}:</span>
                <span className="font-bold">{activePoint.value} ms</span>
              </div>
            </div>
          )}

          {/* Dark Theme: Floating dark tooltip card showing date, value, and green percentage badge */}
          {isDark && (
            <div
              className="absolute pointer-events-none transform -translate-x-1/2 -translate-y-full mb-2 animate-fade-in z-30"
              style={{
                left: `${(activePoint.x / width) * 100}%`,
                top: `${(activePoint.y / height) * 100 - 10}%`,
              }}
            >
              <div className="bg-[#14141C] border border-white/15 text-white p-2 rounded-none shadow-2xl flex items-center gap-2 text-[10px] font-sans whitespace-nowrap">
                <div>
                  <span className="text-[#9A9AA6] block text-[9px]">{activePoint.date}</span>
                  <span className="font-bold text-sm text-white">{activePoint.value} ms</span>
                </div>
                <span className="text-[10px] font-bold text-[#2ECC71] bg-[#2ECC71]/15 border border-[#2ECC71]/30 px-1.5 py-0.5 rounded-none">
                  {activePoint.delta}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
