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

  return (
    <div className="flex flex-col h-full overflow-hidden shadow-lg transition-colors duration-200 bento-card rounded-[var(--radius-panel)] border border-[var(--border-subtle)] bg-[var(--bg-canvas)]">
      {/* Header Toolbar */}
      <div
        className={`min-h-11 h-auto py-2 px-3.5 border-b flex flex-wrap gap-2 items-center justify-between shrink-0 transition-colors duration-200 ${
          isDark
            ? 'border-[var(--border-main)] bg-[var(--bg-panel-alt)]'
            : 'border-[var(--border-subtle)] bg-[var(--bg-panel-alt)]'
        }`}
      >
        <div className="flex flex-wrap items-center gap-2.5 shrink-0 min-w-0">
          <div className="flex items-center gap-1.5 font-bold text-xs text-[var(--text-heading)]">
            <BookOpen className="w-4 h-4 text-[var(--accent-primary)]" aria-hidden="true" />
            <span>Sequential SQL Cells</span>
          </div>

          {/* Cell Counter Pill */}
          {blocks.length > 0 && (
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30">
              {blocks.length} {blocks.length === 1 ? 'Command' : 'Commands'}
            </span>
          )}

          {/* Auto Dialect Indicator with Hover Reason */}
          {isAuto ? (
            <div className="relative group/dialect inline-flex items-center">
              <span
                className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-[var(--radius-pill)] whitespace-nowrap shrink-0 cursor-help flex items-center gap-1 border transition-all ${
                  isDark
                    ? 'bg-[var(--accent-primary)]/15 border-[var(--accent-primary)]/40 text-[var(--accent-primary)] font-bold'
                    : 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] border-[var(--btn-primary-bg)] font-bold'
                }`}
              >
                <Zap className="w-3 h-3" />
                <span>
                  {hasResult
                    ? `Auto -> ${resolvedDialect.toUpperCase()}`
                    : 'Auto (Awaiting Prompt)'}
                </span>
                <Info className="w-2.5 h-2.5 opacity-80" />
              </span>

              {/* Hover Tooltip with selection reason */}
              <div className="absolute top-full left-0 mt-1.5 hidden group-hover/dialect:flex flex-col z-50 w-72 p-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] text-[var(--text-heading)] shadow-xl text-[11px] leading-relaxed pointer-events-none animate-in fade-in zoom-in-95 duration-150">
                <div className="font-bold text-[10px] uppercase tracking-wider text-[var(--accent-primary)] mb-0.5 flex items-center gap-1">
                  <span>💡 Target Dialect Selection</span>
                </div>
                <p className="font-normal text-[11px] text-[var(--text-body)]">
                  {dialectReason}
                </p>
              </div>
            </div>
          ) : (
            <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-[var(--radius-pill)] whitespace-nowrap shrink-0 ${
              isDark
                ? 'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-main)]'
                : 'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-subtle)]'
            }`}>
              {targetDialect} Dialect
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* View Mode Toggle: Cells vs Raw Editor */}
          <div className="flex items-center rounded-lg p-0.5 border border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <button
              onClick={() => setViewMode('notebook')}
              className={`flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-md transition-all cursor-pointer ${
                viewMode === 'notebook'
                  ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                  : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
              }`}
              title="Sequential Cells: One command per block with purpose hover pop-up"
            >
              <BookOpen className="w-3 h-3" />
              <span>Cells</span>
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={`flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-md transition-all cursor-pointer ${
                viewMode === 'raw'
                  ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                  : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
              }`}
              title="Raw Editor: Unified SQL script view"
            >
              <FileCode className="w-3 h-3" />
              <span>Raw</span>
            </button>
          </div>

          {/* Copy Entire Script Button */}
          {sql && (
            <button
              onClick={handleCopyAll}
              className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer shrink-0 whitespace-nowrap bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-body)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-heading)] shadow-xs"
              title="Copy entire script to clipboard"
            >
              {copiedAll ? (
                <>
                  <Check aria-hidden="true" className="w-3.5 h-3.5 text-[var(--success)]" />
                  <span className="text-[var(--success)] font-medium">Copied Script</span>
                </>
              ) : (
                <>
                  <Copy aria-hidden="true" className="w-3.5 h-3.5" />
                  <span>Copy Script</span>
                </>
              )}
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
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
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
