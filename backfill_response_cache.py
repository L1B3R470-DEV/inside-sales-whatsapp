import argparse
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


SAFE_CACHE_INTENTS = {
    "saudacao",
    "agradecimento",
    "institucional_empresa",
    "produto_catalogo",
    "prazo_entrega",
    "pagamento",
    "preco_orcamento",
}

AMBIGUOUS_SHORTCUTS = {"sim", "nao", "não", "ok", "obrigado", "obrigada", "oi", "ola", "olá"}

FALLBACK_PATTERNS = [
    "peco um instante",
    "peço um instante",
    "assumo seu atendimento pessoalmente",
    "nao consegui responder agora",
    "não consegui responder agora",
    "atendimento automatico ativo",
    "atendimento automático ativo",
    "alto volume no momento",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_ascii(value: str) -> str:
    text = str(value or "").lower()
    text = (
        text.replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill inicial do response_cache a partir do conversation_history")
    p.add_argument(
        "--db-path",
        default=r"C:\AUTOMACAO\dados\router_runtime.sqlite",
        help="Caminho do sqlite usado pelo router",
    )
    p.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Minimo de ocorrencias de uma mesma pergunta para virar cache",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Somente simula, sem gravar",
    )
    p.add_argument(
        "--bootstrap-if-empty",
        action="store_true",
        help="Se nao houver candidatos no historico, semeia cache inicial com perguntas recorrentes",
    )
    return p.parse_args()


def load_pairs(conn: sqlite3.Connection) -> List[Tuple[str, str, str]]:
    """
    Retorna pares (inbound_text, outbound_text, intent_inbound)
    usando sequencia da conversation_history por contato.
    """
    rows = conn.execute(
        """
        SELECT contact_key, direction, message_text, intent, created_at
        FROM conversation_history
        ORDER BY contact_key, created_at
        """
    ).fetchall()

    by_contact: Dict[str, List[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        by_contact[str(r["contact_key"] or "")].append(r)

    pairs: List[Tuple[str, str, str]] = []
    for _, seq in by_contact.items():
        for i in range(len(seq) - 1):
            cur = seq[i]
            nxt = seq[i + 1]
            if str(cur["direction"]) != "inbound":
                continue
            if str(nxt["direction"]) != "outbound":
                continue
            inbound = str(cur["message_text"] or "").strip()
            outbound = str(nxt["message_text"] or "").strip()
            intent = str(cur["intent"] or "").strip()
            if inbound and outbound:
                pairs.append((inbound, outbound, intent))
    return pairs


def is_safe_pair(inbound: str, outbound: str, intent: str) -> Tuple[bool, str]:
    norm_in = normalize_ascii(inbound)
    norm_out = normalize_ascii(outbound)
    if len(norm_in) < 8:
        return False, "too_short_inbound"
    if len(norm_out) < 16:
        return False, "too_short_outbound"
    if norm_in in AMBIGUOUS_SHORTCUTS:
        return False, "ambiguous_shortcut"
    if intent not in SAFE_CACHE_INTENTS:
        return False, "unsafe_intent"
    for p in FALLBACK_PATTERNS:
        if p in norm_out:
            return False, "fallback_reply"
    return True, "ok"


def build_candidates(
    pairs: List[Tuple[str, str, str]],
    min_count: int,
) -> Dict[str, Dict]:
    """
    Agrupa por normalized inbound e escolhe resposta mais frequente.
    """
    grouped: Dict[str, Dict] = {}
    for inbound, outbound, intent in pairs:
        ok, _ = is_safe_pair(inbound, outbound, intent)
        if not ok:
            continue
        norm_in = normalize_ascii(inbound)
        item = grouped.setdefault(
            norm_in,
            {"intent": intent, "reply_counter": Counter(), "samples": 0},
        )
        if intent in SAFE_CACHE_INTENTS:
            item["intent"] = intent
        item["reply_counter"][outbound] += 1
        item["samples"] += 1

    final: Dict[str, Dict] = {}
    for norm_in, item in grouped.items():
        total = int(item["samples"])
        if total < min_count:
            continue
        reply, freq = item["reply_counter"].most_common(1)[0]
        # confianca simples baseada em consenso da resposta dominante
        consensus = freq / max(1, total)
        confidence = round(min(0.98, 0.62 + consensus * 0.36), 3)
        final[norm_in] = {
            "reply_text": reply,
            "intent": item["intent"] if item["intent"] in SAFE_CACHE_INTENTS else "geral",
            "confidence": confidence,
            "samples": total,
            "dominant_freq": freq,
        }
    return final


def upsert_cache(conn: sqlite3.Connection, candidates: Dict[str, Dict], dry_run: bool) -> Dict[str, int]:
    now = utc_now()
    inserted = 0
    updated = 0
    skipped_existing_better = 0

    for norm_in, data in candidates.items():
        row = conn.execute(
            """
            SELECT normalized_message, confidence, hit_count, source
            FROM response_cache
            WHERE normalized_message = ?
            """,
            (norm_in,),
        ).fetchone()
        if row:
            existing_conf = float(row["confidence"] or 0)
            existing_hits = int(row["hit_count"] or 0)
            new_conf = float(data["confidence"])
            # atualiza se nova confianca for melhor ou registro pouco usado
            if new_conf < existing_conf and existing_hits >= 3:
                skipped_existing_better += 1
                continue
            if not dry_run:
                conn.execute(
                    """
                    UPDATE response_cache
                    SET reply_text = ?, intent = ?, confidence = ?, source = ?, active = 1, updated_at = ?
                    WHERE normalized_message = ?
                    """,
                    (
                        data["reply_text"][:520],
                        data["intent"],
                        new_conf,
                        "backfill_history",
                        now,
                        norm_in,
                    ),
                )
            updated += 1
        else:
            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO response_cache
                    (normalized_message, reply_text, intent, confidence, source, active, hit_count, created_at, updated_at, last_hit_at)
                    VALUES (?, ?, ?, ?, 'backfill_history', 1, 0, ?, ?, NULL)
                    """,
                    (
                        norm_in,
                        data["reply_text"][:520],
                        data["intent"],
                        float(data["confidence"]),
                        now,
                        now,
                    ),
                )
            inserted += 1

    if not dry_run:
        conn.commit()
    return {
        "inserted": inserted,
        "updated": updated,
        "skipped_existing_better": skipped_existing_better,
    }


def bootstrap_candidates() -> Dict[str, Dict]:
    seeds = [
        ("quais formas de pagamento voces aceitam", "Trabalhamos com condicoes comerciais conforme o perfil do pedido. Se quiser, eu te explico a melhor opcao para o seu caso.", "pagamento"),
        ("como funciona o pagamento", "As condicoes de pagamento variam conforme o volume e perfil do pedido. Me diga sua necessidade que te oriento com objetividade.", "pagamento"),
        ("qual o prazo de entrega", "O prazo depende da sua regiao e itens escolhidos. Me informa sua cidade que te passo a previsao mais assertiva.", "prazo_entrega"),
        ("vocês entregam para todo o brasil", "Atendemos diversas regioes do Brasil. Me informa sua cidade e estado para eu confirmar a melhor condicao de atendimento.", "prazo_entrega"),
        ("me fale sobre a classe", "A Classe atua no B2B de acessorios em couro, com foco em revenda e giro comercial. Se quiser, te mostro as linhas mais aderentes ao seu perfil.", "institucional_empresa"),
        ("como funciona a revenda", "Eu te explico o processo de revenda passo a passo e ja iniciamos seu pre-cadastro para analise comercial. Posso te fazer as perguntas rapidas de triagem?", "preco_orcamento"),
        ("quero revender", "Perfeito. Vamos iniciar seu pre-cadastro de revenda para direcionar seu atendimento comercial com prioridade. Podemos comecar agora?", "preco_orcamento"),
        ("voces vendem no atacado", "Sim, atuamos no canal de revenda. Para te orientar na melhor condicao comercial, me conta qual categoria voce quer priorizar.", "preco_orcamento"),
        ("quais produtos voces tem", "Temos linhas com bom giro em carteiras, cintos, bolsas e mochilas. Qual categoria voce quer priorizar agora?", "produto_catalogo"),
        ("tem bolsas", "Temos sim opcoes de bolsas com bom giro para revenda. Voce prefere linha feminina, masculina ou uma selecao mista?", "produto_catalogo"),
        ("tem carteiras", "Temos carteiras com boa saida comercial. Voce quer focar em linha masculina, feminina ou mista?", "produto_catalogo"),
        ("tem cintos", "Temos opcoes de cintos com bom desempenho em revenda. Voce prefere linha masculina, feminina ou mista?", "produto_catalogo"),
        ("bom dia", "Bom dia. Que bom falar com voce. Me conta em uma linha como posso te ajudar agora para eu te orientar com objetividade.", "saudacao"),
        ("boa tarde", "Boa tarde. Que bom falar com voce. Me conta em uma linha sua necessidade para eu te orientar de forma objetiva.", "saudacao"),
        ("boa noite", "Boa noite. Estou a disposicao para te ajudar. Me conta sua necessidade para eu te orientar no melhor caminho.", "saudacao"),
        ("obrigado", "Perfeito. Fico a disposicao para te apoiar no proximo passo do seu atendimento comercial.", "agradecimento"),
        ("obrigada", "Perfeito. Fico a disposicao para te apoiar no proximo passo do seu atendimento comercial.", "agradecimento"),
    ]
    out: Dict[str, Dict] = {}
    for inbound, reply, intent in seeds:
        norm_in = normalize_ascii(inbound)
        out[norm_in] = {
            "reply_text": reply,
            "intent": intent,
            "confidence": 0.88,
            "samples": 1,
            "dominant_freq": 1,
        }
    return out


def main() -> None:
    args = parse_args()
    db_path = Path(args.db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"DB nao encontrada: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    pairs = load_pairs(conn)
    candidates = build_candidates(pairs, min_count=max(1, int(args.min_count)))
    used_bootstrap = False
    if not candidates and args.bootstrap_if_empty:
        candidates = bootstrap_candidates()
        used_bootstrap = True
    stats = upsert_cache(conn, candidates, dry_run=bool(args.dry_run))

    total_cache = conn.execute("SELECT COUNT(*) AS c FROM response_cache WHERE active = 1").fetchone()["c"]
    conn.close()

    print("backfill_done=true")
    print(f"db_path={db_path}")
    print(f"dry_run={bool(args.dry_run)}")
    print(f"pairs_scanned={len(pairs)}")
    print(f"candidates={len(candidates)}")
    print(f"used_bootstrap={used_bootstrap}")
    print(f"inserted={stats['inserted']}")
    print(f"updated={stats['updated']}")
    print(f"skipped_existing_better={stats['skipped_existing_better']}")
    print(f"cache_total_active={total_cache}")


if __name__ == "__main__":
    main()
