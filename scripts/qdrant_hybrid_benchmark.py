import argparse
import json
import re
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

from rank_bm25 import BM25Okapi


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTER_DB = Path(r"C:\AUTOMACAO\dados\router_runtime.sqlite")
DEFAULT_OUT = ROOT / "ANALISES" / "QDRANT_HYBRID_BENCHMARK.md"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def tokenize(text: str):
    return re.findall(r"[a-z0-9áéíóúâêôãõç]+", norm(text))


def load_chunks(db_path: Path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT chunk_id, file_path, file_name, chunk_text, token_count, updated_at
        FROM rag_chunks
        WHERE COALESCE(chunk_text, '') <> ''
        ORDER BY updated_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_queries(db_path: Path, limit: int):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT normalized_message, COUNT(*) AS c
        FROM route_logs
        WHERE COALESCE(normalized_message, '') <> ''
        GROUP BY normalized_message
        ORDER BY c DESC, MAX(created_at) DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    queries = [r["normalized_message"] for r in rows]
    fallback = [
        "como acessar o portal b2b",
        "quero montar pedido",
        "qual valor minimo para comprar",
        "tem book ou catalogo",
        "prazo de entrega",
    ]
    for item in fallback:
        if item not in queries:
            queries.append(item)
    return queries[:limit]


def rrf_merge(rankings, k=60):
    scores = defaultdict(float)
    refs = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            chunk_id = item["chunk_id"]
            scores[chunk_id] += 1.0 / (k + rank)
            refs[chunk_id] = item
    merged = []
    for chunk_id, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
        item = dict(refs[chunk_id])
        item["hybrid_score"] = score
        merged.append(item)
    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_ROUTER_DB))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--queries", type=int, default=12)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = load_chunks(db_path)
    if not chunks:
        raise SystemExit(f"Sem rag_chunks em {db_path}")

    tokenized = [tokenize(c["chunk_text"]) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    queries = load_queries(db_path, args.queries)

    results = []
    started = time.perf_counter()
    for query in queries:
        q_started = time.perf_counter()
        scores = bm25.get_scores(tokenize(query))
        ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: args.top_k]
        bm25_hits = []
        for idx in ranked_idx:
            chunk = chunks[idx]
            bm25_hits.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "file_name": chunk.get("file_name") or Path(chunk.get("file_path") or "").name,
                    "score": float(scores[idx]),
                    "snippet": re.sub(r"\s+", " ", chunk["chunk_text"])[:220],
                }
            )
        hybrid_hits = rrf_merge([bm25_hits])[: args.top_k]
        results.append(
            {
                "query": query,
                "latency_ms": round((time.perf_counter() - q_started) * 1000, 2),
                "bm25_hits": bm25_hits,
                "hybrid_preview": hybrid_hits,
            }
        )

    elapsed = round((time.perf_counter() - started) * 1000, 2)
    payload = {
        "db": str(db_path),
        "chunks": len(chunks),
        "queries": len(queries),
        "elapsed_ms": elapsed,
        "mode": "bm25_rrf_scaffold",
        "note": "Scaffold pronto para adicionar dense Qdrant quando uma colecao paralela for criada.",
        "results": results,
    }

    lines = [
        "# Qdrant Hybrid Benchmark - Laboratorio",
        "",
        f"- DB: `{db_path}`",
        f"- Chunks avaliados: `{len(chunks)}`",
        f"- Queries: `{len(queries)}`",
        f"- Tempo total: `{elapsed} ms`",
        "- Modo atual: `bm25_rrf_scaffold`.",
        "- Proxima etapa: criar colecao Qdrant paralela com vetores dense+sparse e comparar contra este baseline.",
        "",
        "## Amostras",
    ]
    for item in results:
        lines.append(f"### {item['query']}")
        lines.append(f"- Latencia BM25: `{item['latency_ms']} ms`")
        for hit in item["bm25_hits"][:3]:
            lines.append(f"- `{hit['file_name']}` score `{hit['score']:.4f}`: {hit['snippet']}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "json": str(json_path), "chunks": len(chunks), "queries": len(queries)}))


if __name__ == "__main__":
    main()
