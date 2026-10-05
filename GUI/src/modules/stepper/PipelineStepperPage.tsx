// src/modules/stepper/PipelineStepperPage.tsx
import React, { useState } from 'react';
import { Play, ArrowRight, CheckCircle2, AlertTriangle, Layers, Cpu, Database, Network, ShieldCheck, Activity, Terminal } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';

const SAMPLE_QUERIES = [
  "Find all completed orders placed by customers in Germany with total amount > $100",
  "Show 3 hops and connection paths between user Alice and Bob",
  "Increase all product prices in the Electronics category by 10%",
  "Add a discount_code column to the orders table",
  "Fetch document where customer.profile.address is nested in MongoDB format",
];

export const PipelineStepperPage: React.FC = () => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const [queryText, setQueryText] = useState(SAMPLE_QUERIES[0]);
  const [isRunning, setIsRunning] = useState(false);
  const [activeStep, setActiveStep] = useState<number>(6);
  const [traceData, setTraceData] = useState<any>(null);

  const runPipelineTrace = async () => {
    setIsRunning(true);
    setActiveStep(1);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/pipeline/trace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_text: queryText }),
      });
      if (res.ok) {
        const data = await res.json();
        setTraceData(data);
        setActiveStep(6);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsRunning(false);
    }
  };

  const stepsMeta = [
    { num: 1, title: "1. Intent & CLEF Paradigm Routing", icon: Network, color: "text-blue-400" },
    { num: 2, title: "2. Schema Linker & Steiner Minimal Tree", icon: Database, color: "text-indigo-400" },
    { num: 3, title: "3. Qwen2.5-Coder + LoRA Generation", icon: Cpu, color: "text-purple-400" },
    { num: 4, title: "4. Deterministic Multi-Dialect Transpiler", icon: Layers, color: "text-cyan-400" },
    { num: 5, title: "5. 6-Layer Static AST Validator", icon: ShieldCheck, color: "text-emerald-400" },
    { num: 6, title: "6. Heuristic Cost & Execution Gate", icon: Activity, color: "text-amber-400" },
  ];

  return (
    <div className="flex-1 min-h-0 flex flex-col p-6 overflow-y-auto space-y-6">
      {/* Header Banner */}
      <div className={`p-5 rounded-2xl border ${isDark ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200 shadow-sm'}`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                End-to-End Visualizer
              </span>
              <h1 className="text-xl font-bold tracking-tight">CLEF + Qwen LoRA + Universal AST Pipeline Stepper</h1>
            </div>
            <p className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Inspect full stage-by-stage inputs, intermediate representations, and outputs across all 6 core modules.
            </p>
          </div>

          <button
            onClick={runPipelineTrace}
            disabled={isRunning}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>{isRunning ? "Executing Pipeline..." : "Execute & Trace Steps"}</span>
          </button>
        </div>

        {/* Query Input Box */}
        <div className="mt-4 flex flex-col gap-2">
          <label className="text-xs font-semibold text-slate-400">Natural Language Query:</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              className={`flex-1 px-3.5 py-2 rounded-xl text-sm font-medium border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                isDark ? 'bg-slate-800/80 border-slate-700 text-slate-100' : 'bg-slate-50 border-slate-300 text-slate-900'
              }`}
            />
          </div>
          {/* Quick Preset Badges */}
          <div className="flex flex-wrap gap-1.5 mt-1">
            {SAMPLE_QUERIES.map((q, i) => (
              <button
                key={i}
                onClick={() => setQueryText(q)}
                className={`text-[11px] px-2.5 py-1 rounded-lg border transition-all cursor-pointer ${
                  queryText === q
                    ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300 font-semibold'
                    : isDark
                    ? 'bg-slate-800/50 border-slate-700/60 text-slate-400 hover:text-slate-200'
                    : 'bg-slate-100 border-slate-200 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {q.length > 45 ? q.slice(0, 45) + '...' : q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Interactive Step Accordions */}
      <div className="space-y-4">
        {stepsMeta.map((meta, idx) => {
          const stepData = traceData?.steps?.[idx];
          const IconComponent = meta.icon;
          const isPassed = !!stepData;

          return (
            <div
              key={meta.num}
              className={`rounded-2xl border transition-all ${
                isDark ? 'bg-slate-900/70 border-slate-800' : 'bg-white border-slate-200 shadow-xs'
              }`}
            >
              {/* Step Title Header */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl bg-slate-800 border border-slate-700 ${meta.color}`}>
                    <IconComponent className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                      <span>{meta.title}</span>
                      {stepData && (
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {stepData.duration_ms} ms
                        </span>
                      )}
                    </h3>
                  </div>
                </div>

                {isPassed ? (
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Completed</span>
                  </span>
                ) : (
                  <span className="text-xs font-mono text-slate-500">Ready</span>
                )}
              </div>

              {/* Step Body Content Preview */}
              {stepData && (
                <div className="px-5 pb-5 pt-1 border-t border-slate-800/80 space-y-3 text-xs">
                  {meta.num === 1 && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                        <span className="text-slate-400 block font-medium">Paradigm:</span>
                        <span className="font-bold text-sm text-indigo-300 font-mono">{stepData.output.paradigm}</span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                        <span className="text-slate-400 block font-medium">Confidence:</span>
                        <span className="font-bold text-sm text-emerald-400 font-mono">{(stepData.output.confidence * 100).toFixed(1)}%</span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                        <span className="text-slate-400 block font-medium">Target Recommendation:</span>
                        <span className="font-bold text-sm text-cyan-300">{stepData.output.recommended_engines.join(', ')}</span>
                      </div>
                    </div>
                  )}

                  {meta.num === 2 && (
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2 font-mono">
                      <div><span className="text-slate-400">Selected Tables:</span> <span className="text-indigo-300 font-bold">{stepData.output.selected_tables.join(', ')}</span></div>
                      <div><span className="text-slate-400">Grounded Trie Values:</span> <span className="text-amber-300">{JSON.stringify(stepData.output.grounded_values)}</span></div>
                      <div><span className="text-slate-400">Steiner FK Bridges:</span> <span className="text-emerald-400">{stepData.output.foreign_key_bridges.join(' | ') || 'Single entity direct scope'}</span></div>
                    </div>
                  )}

                  {meta.num === 3 && (
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                      <div className="text-slate-400 font-medium">Canonical AST SQL (PostgreSQL Standard):</div>
                      <pre className="p-3 rounded-lg bg-slate-900 font-mono text-emerald-300 text-xs overflow-x-auto border border-slate-800">
                        {stepData.output.canonical_sql}
                      </pre>
                    </div>
                  )}

                  {meta.num === 4 && (
                    <div className="space-y-2">
                      <div className="text-slate-400 font-medium">Transpiled Multi-Dialect Queries:</div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {Object.entries(stepData.output.transpiled_queries).map(([d, info]: [string, any]) => (
                          <div key={d} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                            <div className="flex justify-between items-center mb-1">
                              <span className="font-bold text-xs uppercase text-cyan-400 font-mono">[{d}]</span>
                              <span className="text-[10px] text-slate-500 font-mono">{info.execution_time_ms} ms</span>
                            </div>
                            <pre className="text-[11px] font-mono text-slate-200 overflow-x-auto whitespace-pre-wrap max-h-28">
                              {typeof info.query === 'object' ? JSON.stringify(info.query, null, 2) : info.query}
                            </pre>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {meta.num === 5 && (
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                      <div className="flex items-center gap-3">
                        <span className="text-slate-400 font-medium">Status:</span>
                        <span className={`px-2 py-0.5 rounded font-mono font-bold ${stepData.output.status === 'valid' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                          {stepData.output.status.toUpperCase()}
                        </span>
                        <span className="text-slate-400 font-medium">Statement Type:</span>
                        <span className="font-mono text-indigo-300 font-bold">{stepData.output.statement_type}</span>
                      </div>
                      {stepData.output.issues.length === 0 ? (
                        <p className="text-emerald-400">✓ All 6 static validation layers passed with 0 errors and 0 warnings.</p>
                      ) : (
                        <div className="space-y-1 mt-2">
                          {stepData.output.issues.map((iss: any, i: number) => (
                            <div key={i} className="text-amber-300 font-mono">
                              [{iss.code}] {iss.severity.toUpperCase()}: {iss.message}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {meta.num === 6 && (
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div>
                        <span className="text-slate-400 block font-medium">Cost Gate Decision:</span>
                        <span className="font-bold text-sm text-emerald-400 font-mono">{stepData.output.decision}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block font-medium">Execution Route:</span>
                        <span className="font-bold text-sm text-indigo-300 font-mono">{stepData.output.execution_route}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block font-medium">Human Approval Required:</span>
                        <span className="font-bold text-sm text-slate-200 font-mono">{stepData.output.requires_human_approval ? 'YES' : 'NO'}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
