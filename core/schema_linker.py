"""
core/schema_linker.py — Context Retrieval & Schema Pruning Engine

Implements:
1. True Hybrid Retrieval: BM25 (snake_case/camelCase aware) + Character N-Gram Fuzzy Salience
   fused via Reciprocal Rank Fusion (RRF) parameterized by `rrf_k`.
2. Steiner Minimal Tree / Metric-Closure Graph Join Auto-Injection to ensure unbroken FK join paths.
3. Two-Stage Column Pruning: Preserves PKs, FKs, grounded categorical columns, and high-salience query filter columns.
4. Categorical Cell-Value Grounding via Trie matching with robust punctuation stripping and token boundaries.
"""

from collections import defaultdict
from dataclasses import dataclass, field
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx


STOPWORDS = {
    "a", "about", "all", "an", "and", "any", "are", "as", "at", "be", "been",
    "by", "each", "every", "for", "from", "get", "give", "had", "has", "have",
    "in", "into", "is", "it", "its", "list", "me", "my", "of", "on", "or",
    "our", "please", "query", "return", "show", "so", "some", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "to", "was",
    "were", "what", "which", "who", "whom", "will", "with"
}


@dataclass
class ColumnMeta:
    name: str
    dtype: str
    is_pk: bool = False
    is_fk: bool = False
    fk_target_table: Optional[str] = None
    fk_target_column: Optional[str] = None
    description: str = ""
    categorical_values: List[str] = field(default_factory=list)


@dataclass
class TableMeta:
    name: str
    columns: Dict[str, ColumnMeta]
    description: str = ""


@dataclass
class LinkedSchemaContext:
    selected_tables: List[str]
    selected_columns: Dict[str, List[str]]
    foreign_keys: List[Tuple[str, str, str, str]]  # (src_table, src_col, target_table, target_col)
    grounded_values: Dict[str, str]  # value -> table.column
    prompt_ddl: str


class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.column_ref: Optional[str] = None  # "table.column"


class CategoricalValueTrie:
    """Offline pre-built Trie for sub-millisecond cell value grounding."""

    def __init__(self):
        self.root = TrieNode()

    def insert(self, value: str, column_ref: str):
        node = self.root
        clean_val = value.strip().lower()
        if not clean_val:
            return
        for char in clean_val:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.column_ref = column_ref

    def search_query_matches(self, query: str) -> Dict[str, str]:
        """Finds all categorical cell values present inside the user query with punctuation stripping."""
        clean_text = re.sub(r'[^\w\s]', ' ', query.lower())
        words = [w for w in clean_text.split() if w]
        matches: Dict[str, str] = {}

        for i in range(len(words)):
            for j in range(i + 1, min(i + 6, len(words) + 1)):
                phrase = " ".join(words[i:j])
                node = self.root
                matched = True
                for char in phrase:
                    if char in node.children:
                        node = node.children[char]
                    else:
                        matched = False
                        break
                if matched and node.is_end and node.column_ref:
                    matches[phrase] = node.column_ref

        return matches


class SchemaLinker:
    """
    Retrieves and prunes relevant database schema components for prompt injection.
    """

    def __init__(self, tables: Dict[str, TableMeta], rrf_k: int = 60):
        self.tables = tables
        self.rrf_k = rrf_k
        self.schema_graph = self._build_schema_graph()
        self.value_trie = self._build_value_trie()

    def _build_schema_graph(self) -> nx.Graph:
        """Constructs an undirected graph where V=tables, E=FK relations."""
        G = nx.Graph()
        for t_name in self.tables:
            G.add_node(t_name)

        for t_name, t_meta in self.tables.items():
            for c_name, c_meta in t_meta.columns.items():
                if c_meta.is_fk and c_meta.fk_target_table:
                    if c_meta.fk_target_table in self.tables:
                        G.add_edge(t_name, c_meta.fk_target_table, weight=1.0)
        return G

    def _build_value_trie(self) -> CategoricalValueTrie:
        """Indexes all categorical values for grounding."""
        trie = CategoricalValueTrie()
        for t_name, t_meta in self.tables.items():
            for c_name, c_meta in t_meta.columns.items():
                for val in c_meta.categorical_values:
                    trie.insert(val, f"{t_name}.{c_name}")
        return trie

    def _tokenize(self, text: str, filter_stopwords: bool = True) -> List[str]:
        """Snake_case and camelCase aware tokenizer."""
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', text)
        s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        tokens = [w for w in re.split(r'[^a-z0-9]+', s2) if w]
        if filter_stopwords:
            return [w for w in tokens if w not in STOPWORDS]
        return tokens

    def _bm25_rank_tables(self, query_tokens: List[str]) -> List[str]:
        """Rank tables via BM25 token relevance."""
        scores = []
        for t_name, t_meta in self.tables.items():
            doc_tokens = self._tokenize(t_name, filter_stopwords=False) + self._tokenize(t_meta.description, filter_stopwords=True)
            for c_name, c_meta in t_meta.columns.items():
                doc_tokens += self._tokenize(c_name, filter_stopwords=False) + self._tokenize(c_meta.description, filter_stopwords=True)

            doc_len = max(len(doc_tokens), 1)
            score = 0.0
            for q_tok in query_tokens:
                freq = doc_tokens.count(q_tok)
                if freq > 0:
                    score += (freq * 2.2) / (freq + 1.2 * (0.25 + 0.75 * (doc_len / 40.0)))
            scores.append((t_name, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scores]

    def _fuzzy_rank_tables(self, query: str) -> List[str]:
        """Rank tables via character 3-gram Jaccard similarity for typo tolerance."""
        def get_ngrams(s: str, n: int = 3) -> Set[str]:
            s_clean = re.sub(r'[^a-z0-9]', '', s.lower())
            if len(s_clean) < n:
                return {s_clean} if s_clean else set()
            return {s_clean[i:i+n] for i in range(len(s_clean) - n + 1)}

        q_ngrams = get_ngrams(query)
        if not q_ngrams:
            return list(self.tables.keys())

        scores = []
        for t_name, t_meta in self.tables.items():
            t_text = f"{t_name} {t_meta.description} " + " ".join(t_meta.columns.keys())
            t_ngrams = get_ngrams(t_text)
            intersection = len(q_ngrams.intersection(t_ngrams))
            union = len(q_ngrams.union(t_ngrams))
            jaccard = intersection / max(union, 1)
            scores.append((t_name, jaccard))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scores]

    def _fuse_rrf(self, bm25_ranks: List[str], fuzzy_ranks: List[str], grounded_tables: Set[str]) -> List[str]:
        """Reciprocal Rank Fusion (RRF) combining lexical BM25 + fuzzy n-gram rankings."""
        rrf_scores: Dict[str, float] = defaultdict(float)

        for rank, t_name in enumerate(bm25_ranks):
            rrf_scores[t_name] += 1.0 / (self.rrf_k + rank + 1)

        for rank, t_name in enumerate(fuzzy_ranks):
            rrf_scores[t_name] += 1.0 / (self.rrf_k + rank + 1)

        # Grounded cell values provide a high-confidence direct prior boost
        for t_name in grounded_tables:
            if t_name in rrf_scores:
                rrf_scores[t_name] += 0.05

        sorted_tables = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return [t for t, _ in sorted_tables]

    def link_context(
        self,
        query: str,
        max_tables: int = 5,
        max_columns_per_table: int = 10,
    ) -> LinkedSchemaContext:
        """
        Extracts relevant schema subset, connects tables via Steiner/Shortest paths,
        and generates minimal table DDL.
        """
        if not self.tables:
            return LinkedSchemaContext([], {}, [], {}, "")

        query_tokens = self._tokenize(query, filter_stopwords=True)

        # 1. Cell Value Grounding
        grounded_values = self.value_trie.search_query_matches(query)
        grounded_tables = {ref.split(".")[0] for ref in grounded_values.values() if ref.split(".")[0] in self.tables}

        # 2. Hybrid Retrieval with Reciprocal Rank Fusion
        bm25_ranks = self._bm25_rank_tables(query_tokens)
        fuzzy_ranks = self._fuzzy_rank_tables(query)
        fused_tables = self._fuse_rrf(bm25_ranks, fuzzy_ranks, grounded_tables)

        seed_tables = set(grounded_tables)
        for t_name in fused_tables[:max_tables]:
            seed_tables.add(t_name)

        if not seed_tables:
            seed_tables = {list(self.tables.keys())[0]}

        # 3. Steiner Tree / Shortest Path Bridge Table Auto-Injection
        connected_tables = set(seed_tables)
        seed_list = [t for t in seed_tables if t in self.schema_graph]

        for i in range(len(seed_list)):
            for j in range(i + 1, len(seed_list)):
                u, v = seed_list[i], seed_list[j]
                if nx.has_path(self.schema_graph, u, v):
                    path = nx.shortest_path(self.schema_graph, u, v)
                    for bridge_t in path:
                        connected_tables.add(bridge_t)

        # Preserve relevance ranking order (grounded seeds first, then fused ranks, then bridge tables)
        ordered_final = [t for t in grounded_tables if t in connected_tables]
        for t in fused_tables:
            if t in connected_tables and t not in ordered_final:
                ordered_final.append(t)
        for t in connected_tables:
            if t not in ordered_final:
                ordered_final.append(t)

        final_tables = ordered_final[:max_tables + 2]

        # 4. Column Pruning
        selected_columns: Dict[str, List[str]] = {}
        foreign_keys_set: Set[Tuple[str, str, str, str]] = set()

        for t_name in final_tables:
            t_meta = self.tables.get(t_name)
            if not t_meta:
                continue

            cols_to_keep: Set[str] = set()

            # Always keep PKs and FKs
            for c_name, c_meta in t_meta.columns.items():
                if c_meta.is_pk or c_meta.is_fk:
                    cols_to_keep.add(c_name)
                if c_meta.is_fk and c_meta.fk_target_table in final_tables:
                    foreign_keys_set.add((
                        t_name, c_name, c_meta.fk_target_table, c_meta.fk_target_column or "id"
                    ))

            # Add columns matched by grounded values
            for phrase, ref in grounded_values.items():
                ref_t, ref_c = ref.split(".")
                if ref_t == t_name:
                    cols_to_keep.add(ref_c)

            # Score remaining columns by query token match
            col_scores = []
            for c_name, c_meta in t_meta.columns.items():
                if c_name not in cols_to_keep:
                    c_tokens = self._tokenize(c_name) + self._tokenize(c_meta.description)
                    overlap = sum(1 for q_t in query_tokens if q_t in c_tokens)
                    col_scores.append((c_name, overlap))

            col_scores.sort(key=lambda x: x[1], reverse=True)
            for c_name, score in col_scores:
                if len(cols_to_keep) < max_columns_per_table:
                    cols_to_keep.add(c_name)

            selected_columns[t_name] = sorted(list(cols_to_keep))

        # 5. Format Prompt DDL
        ddl_lines = []
        for t_name in final_tables:
            t_meta = self.tables.get(t_name)
            if not t_meta:
                continue
            col_defs = []
            for c_name in selected_columns[t_name]:
                c_meta = t_meta.columns[c_name]
                pk_str = " PRIMARY KEY" if c_meta.is_pk else ""
                fk_str = f" REFERENCES {c_meta.fk_target_table}({c_meta.fk_target_column})" if c_meta.is_fk and c_meta.fk_target_table else ""
                col_defs.append(f"  {c_name} {c_meta.dtype}{pk_str}{fk_str}")
            ddl_lines.append(f"CREATE TABLE {t_name} (\n" + ",\n".join(col_defs) + "\n);")

        return LinkedSchemaContext(
            selected_tables=final_tables,
            selected_columns=selected_columns,
            foreign_keys=list(foreign_keys_set),
            grounded_values=grounded_values,
            prompt_ddl="\n\n".join(ddl_lines),
        )
