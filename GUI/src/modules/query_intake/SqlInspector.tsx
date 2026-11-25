// src/modules/query_intake/SqlInspector.tsx — Sequential Command Cells with Reason Pop-ups
import React, { useState, useMemo } from 'react';
import Editor from '@monaco-editor/react';
import {
  Copy,
  Check,
  Code2,
  Zap,
  Info,
  BookOpen,
  FileCode,
} from 'lucide-react';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { EmptyState } from '../../shared/EmptyState';
import { splitSqlIntoCommandBlocks, SqlCommandBlock } from '../../utils/sqlSplitter';

export const SqlInspector: React.FC = () => {
  const lastResponse = useQueryStore((s) => s.lastResponse);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const [copiedAll, setCopiedAll] = useState(false);
  const [copiedCellId, setCopiedCellId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'notebook' | 'raw'>('notebook');
  const [activeCellId, setActiveCellId] = useState<string | null>(null);

  const sql = lastResponse?.generated_sql || '';
  const isAuto = targetDialect === 'auto';
  const hasResult = Boolean(lastResponse?.selected_dialect);
  const resolvedDialect = lastResponse?.selected_dialect || (isAuto ? 'auto' : targetDialect);
  const dialectReason = lastResponse?.dialect_reason || (isAuto
    ? 'Auto mode is active: enter a prompt and the classifier will analyze your intent to select and compile the optimal dialect.'
    : `Code compiled specifically for ${targetDialect.toUpperCase()} dialect.`);

  // Parse SQL into sequential command blocks with model-generated reasons
  const blocks: SqlCommandBlock[] = useMemo(() => {
    return splitSqlIntoCommandBlocks(sql, lastResponse?.command_blocks);
  }, [sql, lastResponse?.command_blocks]);

  const handleCopyAll = () => {
    if (!sql) return;
    navigator.clipboard.writeText(sql);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  const handleCopyCell = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCellId(id);
    setTimeout(() => setCopiedCellId(null), 2000);
  };

  const tabCls = (active: boolean) =>
    `relative h-full px-[10px] text-[12.5px] font-medium cursor-pointer bg-transparent border-0 border-b-2 transition-colors flex items-center gap-1.5 ${
      active
        ? 'text-[var(--text-heading)] font-semibold border-b-[var(--accent-primary)]'
        : 'text-[var(--text-recessive)] border-b-transparent hover:text-[var(--text-heading)]'
    }`;

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[var(--bg-canvas)]">
      {/* 36px Primer Toolbar */}
      <div className="h-9 shrink-0 px-3 border-b border-[var(--border-hairline)] bg-[var(--bg-panel)] flex items-stretch justify-between gap-2">
        <div className="flex items-stretch">
          <button onClick={() => setViewMode('notebook')} className={tabCls(viewMode === 'notebook')} title="Sequential command cells">
            <span>SQL Cells</span>
            {blocks.length > 0 && (
              <span className="font-mono text-[10px] px-1.5 py-[1px] rounded-[10px] bg-[var(--bg-inset)] border border-[var(--border-hairline)] text-[var(--text-body)]">
                {blocks.length}
              </span>
            )}
          </button>
          <button onClick={() => setViewMode('raw')} className={tabCls(viewMode === 'raw')} title="Raw compiled SQL">
            <span>Raw SQL</span>
          </button>
        </div>

        <div className="flex items-center gap-2 pr-1">
          <span className="font-mono text-[11px] text-[var(--text-recessive)] truncate max-w-[180px]">
            {isAuto
              ? hasResult ? `AUTO -> ${resolvedDialect.toUpperCase()}` : 'AUTO'
              : targetDialect.toUpperCase()}
          </span>

          {sql && (
            <button
              onClick={handleCopyAll}
              className="h-6 px-2 rounded-[6px] border border-[var(--border-hairline)] bg-[var(--bg-canvas)] text-[11px] font-medium text-[var(--text-body)] hover:bg-[var(--bg-hover)] cursor-pointer inline-flex items-center gap-1"
              title="Copy entire SQL script"
            >
              {copiedAll ? <Check className="w-3 h-3 text-[var(--success)]" /> : <Copy className="w-3 h-3" />}
              <span>{copiedAll ? 'Copied' : 'Copy'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 relative overflow-y-auto p-3 sm:p-4 bg-[var(--bg-canvas)]">
        {!sql ? (
          <EmptyState
            icon={<Code2 aria-hidden="true" className="w-8 h-8" />}
            title="Awaiting Model Generation"
            description="Enter a natural language prompt to generate individual sequential SQL commands with purpose explanations."
          />
        ) : viewMode === 'raw' ? (
          /* Raw Monaco Editor View */
          <div className="h-full rounded-xl overflow-hidden border border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <Editor
              height="100%"
              language="sql"
              theme={isDark ? 'vs-dark' : 'light'}
              value={sql}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                padding: { top: 12, bottom: 12 },
                renderLineHighlight: 'none',
              }}
            />
          </div>
        ) : (
          /* Sequential Command Cells with Reason Pop-ups */
          <div className="space-y-3.5 max-w-5xl mx-auto">
            {blocks.map((block) => {
              const isSelected = activeCellId === block.id;

              return (
                <div
                  key={block.id}
                  onClick={() => setActiveCellId(block.id)}
                  className={`group relative rounded-xl border transition-all duration-200 overflow-hidden shadow-xs ${
                    isSelected
                      ? 'border-[var(--accent-primary)] ring-2 ring-[var(--accent-primary)]/20 shadow-md'
                      : 'border-[var(--border-hairline)] hover:border-[var(--accent-primary)]/40 bg-[var(--bg-card)]'
                  }`}
                >
                  {/* Cell Header Strip */}
                  <div className="px-3.5 py-2 border-b border-[var(--border-hairline)] bg-[var(--bg-panel-alt)] flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2.5">
                      {/* Serial Number Gutter */}
                      <span className="font-mono text-xs font-bold text-sky-600 dark:text-sky-400 select-none">
                        Cell [{block.index}]
                      </span>

                      {/* Command Type Badge */}
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-tight border ${
                        block.isMutating
                          ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30'
                          : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                      }`}>
                        {block.commandType}
                      </span>

                      {/* Short Information Icon with Purpose Hover Pop-up */}
                      <div className="relative group/info inline-flex items-center">
                        <button
                          type="button"
                          className="p-1 rounded-full text-[var(--text-recessive)] hover:text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/10 transition-colors cursor-help"
                          title="View why this command was generated"
                        >
                          <Info className="w-3.5 h-3.5" />
                        </button>

                        {/* Hover Popover Tooltip */}
                        <div className="absolute left-0 top-full mt-1.5 hidden group-hover/info:flex flex-col z-50 w-80 p-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] text-[var(--text-heading)] shadow-xl text-xs leading-relaxed pointer-events-none animate-in fade-in zoom-in-95 duration-150">
                          <div className="flex items-center gap-1.5 font-bold text-[11px] text-[var(--accent-primary)] mb-1 uppercase tracking-wider">
                            <Info className="w-3.5 h-3.5 shrink-0" />
                            <span>Command Intent & Purpose</span>
                          </div>
                          <p className="font-normal text-xs text-[var(--text-body)]">
                            {block.reason}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Copy Cell Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopyCell(block.commandText, block.id);
                        }}
                        className="flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-md bg-[var(--bg-canvas)] border border-[var(--border-subtle)] text-[var(--text-body)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-hover)] transition-all cursor-pointer shadow-2xs"
                        title="Copy this specific SQL command"
                      >
                        {copiedCellId === block.id ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-[var(--success)]" />
                            <span className="text-[var(--success)] font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy Cell</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Cell Code Body */}
                  <div className="p-3.5 bg-[var(--bg-card)]">
                    <pre className="font-mono text-xs leading-relaxed text-[var(--text-heading)] overflow-x-auto select-text whitespace-pre-wrap">
                      <code>{block.commandText}</code>
                    </pre>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
