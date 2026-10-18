"""
core/os_engine/context_pager.py — Denning's Working Set Context Pager

Per-user, window=10 queries.

Working set W(t, Δ) = set of tables referenced in the user's last Δ=10 queries.
Tables inside the working set are "paged in" to the LLM prompt frame.
Tables outside are "paged out" (excluded from the SQL generation context).

The pager exposes `active_tables(user_id)` which the schema linker / orchestrator
calls to prune the context before building the prompt.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Set


WINDOW_SIZE = 10  # ponytail: fixed at 10; make adaptive (schema size * 0.5) if large schemas hurt


@dataclass
class UserPageState:
    """Circular reference window for one user session."""
    window: deque = field(default_factory=lambda: deque(maxlen=WINDOW_SIZE))
    # Each slot: frozenset of table names referenced in that query

    def record_query(self, tables_referenced: List[str]):
        self.window.append(frozenset(t.lower() for t in tables_referenced))

    @property
    def working_set(self) -> Set[str]:
        """Union of all tables across the window — the active working set."""
        result: Set[str] = set()
        for slot in self.window:
            result.update(slot)
        return result

    @property
    def reference_counts(self) -> Dict[str, int]:
        """How many recent queries referenced each table — useful for priority ordering."""
        counts: Dict[str, int] = {}
        for slot in self.window:
            for t in slot:
                counts[t] = counts.get(t, 0) + 1
        return counts


class WorkingSetPager:
    """
    Manages per-user working sets.  Thread-safe at the per-user level
    (different users never contend on the same state object).

    ponytail: no cross-user lock needed; dict lookup is GIL-protected enough for this use.
    """

    def __init__(self):
        self._sessions: Dict[str, UserPageState] = {}

    def _state(self, user_id: str) -> UserPageState:
        if user_id not in self._sessions:
            self._sessions[user_id] = UserPageState()
        return self._sessions[user_id]

    def recordQueryTablesForUserSession(self, user_id: str, tables_referenced: List[str]):
        """Call after each query to advance the working set window."""
        self._state(user_id).record_query(tables_referenced)

    def retrieveActiveWorkingSetTablesForUser(self, user_id: str) -> Set[str]:
        """
        Returns the working set: tables the user has touched in the last WINDOW_SIZE queries.
        Empty set = no history (cold start) → caller should include all tables.
        """
        return self._state(user_id).working_set

    def filterSchemaTablesToActiveWorkingSet(self, user_id: str, all_tables: List[str]) -> List[str]:
        """
        Page-in: return tables to include in the LLM prompt.
        Cold start (empty window) → all tables passed through.
        Warm: only working set tables + any newly mentioned table.
        """
        ws = self.retrieveActiveWorkingSetTablesForUser(user_id)
        if not ws:
            return all_tables  # cold start: admit everything
        # always include tables in working set; caller can add query-specific tables on top
        return [t for t in all_tables if t.lower() in ws]

    def retrieveTableReferenceCountsForUser(self, user_id: str) -> Dict[str, int]:
        return self._state(user_id).reference_counts

    def evictUserSessionWorkingSetState(self, user_id: str):
        """Clean up state on user logout / session expiry."""
        self._sessions.pop(user_id, None)

    # Aliases for backward compatibility
    record = recordQueryTablesForUserSession
    active_tables = retrieveActiveWorkingSetTablesForUser
    filter_schema = filterSchemaTablesToActiveWorkingSet
    reference_counts = retrieveTableReferenceCountsForUser
    evict_session = evictUserSessionWorkingSetState



