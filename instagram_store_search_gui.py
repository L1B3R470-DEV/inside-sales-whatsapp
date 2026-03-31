from __future__ import annotations

import html
import json
import mimetypes
import queue
import re
import threading
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, VERTICAL, X, Y, filedialog, messagebox, StringVar, Tk
from tkinter import ttk
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen


APP_TITLE = "Busca Publica de Fotos de Loja"
BASE_DIR = Path(__file__).resolve().parent
DESKTOP_DIR = Path.home() / "Desktop"
OUTPUT_DIR = DESKTOP_DIR / "RESULTADOS_FOTOS_LOJA"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)


@dataclass(slots=True)
class SearchResult:
    source: str
    label: str
    url: str
    note: str = ""


@dataclass(slots=True)
class ImageCandidate:
    image_type: str
    query: str
    image_url: str
    source_page: str
    confidence: float
    note: str = ""


def normalize_instagram_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("Cole um link do Instagram.")
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    parsed = urlparse(value)
    if "instagram.com" not in parsed.netloc.lower():
        raise ValueError("Informe um link valido do Instagram.")
    return value


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": UA})
    with urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")


def compact(value: str, max_len: int = 220) -> str:
    return re.sub(r"\s+", " ", value or "").strip()[:max_len]


def infer_store_aliases(username: str, store_name: str) -> list[str]:
    raw_candidates = [username.strip(), store_name.strip()]
    aliases: list[str] = []

    for raw in raw_candidates:
        value = normalize_for_alias(raw)
        if not value:
            continue

        cleaned = re.sub(r"^(lojas?|shop|store)", "", value).strip()
        split = split_compound_name(cleaned or value)

        if split:
            aliases.append(split)
        if cleaned:
            aliases.append(cleaned)
        aliases.append(value)

    unique: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        alias = alias.strip()
        if not alias or alias in seen:
            continue
        seen.add(alias)
        unique.append(alias)
    return unique


def normalize_for_alias(value: str) -> str:
    cleaned = re.sub(r"[@_./-]+", " ", value.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def split_compound_name(value: str) -> str:
    preferred_tokens = [
        "vip",
        "vest",
        "moda",
        "fashion",
        "calcados",
        "calçados",
        "store",
        "shop",
    ]
    for token in preferred_tokens:
        if token in value and value != token:
            pieces = value.replace(token, f"{token} ").strip()
            pieces = re.sub(r"\s+", " ", pieces).strip()
            if pieces != value:
                return pieces
    return ""


def extract_meta(html_text: str, attr_name: str, attr_value: str) -> str:
    pattern = (
        rf'<meta[^>]+{attr_name}="{re.escape(attr_value)}"[^>]+content="([^"]+)"'
        rf'|<meta[^>]+content="([^"]+)"[^>]+{attr_name}="{re.escape(attr_value)}"'
    )
    match = re.search(pattern, html_text, flags=re.IGNORECASE)
    if not match:
        return ""
    return html.unescape(match.group(1) or match.group(2) or "")


def extract_profile_summary(html_text: str, instagram_url: str) -> dict[str, object]:
    canonical = extract_meta(html_text, "property", "og:url") or instagram_url
    og_title = extract_meta(html_text, "property", "og:title")
    og_description = extract_meta(html_text, "property", "og:description")
    meta_description = extract_meta(html_text, "name", "description")

    username = ""
    match_username = re.search(r"instagram\.com/([^/?#]+)/?", canonical, flags=re.IGNORECASE)
    if match_username:
        username = match_username.group(1)

    store_name = og_title
    if "(@" in store_name:
        store_name = store_name.split("(@", 1)[0].strip()
    if "•" in store_name:
        store_name = store_name.split("•", 1)[0].strip()
    if not store_name and username:
        aliases = infer_store_aliases(username, "")
        if aliases:
            store_name = aliases[-1]

    bio = ""
    bio_match = re.search(r'on Instagram: &quot;(.+?)&quot;', html_text, flags=re.IGNORECASE | re.DOTALL)
    if bio_match:
        bio = html.unescape(bio_match.group(1))
    elif "on Instagram:" in meta_description:
        bio = meta_description.split("on Instagram:", 1)[-1].strip().strip('"')

    bio = bio.replace("\\n", "\n").strip()
    bio_lines = [line.strip(" •-") for line in bio.splitlines() if line.strip()]

    locations: list[str] = []
    for line in bio_lines:
        lower = line.lower()
        if any(token in lower for token in ("loja fisica", "física", "lajeado", "sitio novo", "sítio novo", "ma")):
            cleaned = compact(line, 120)
            if cleaned and cleaned not in locations:
                locations.append(cleaned)

    return {
        "instagram_url": canonical,
        "username": username,
        "store_name": store_name or username,
        "bio": bio,
        "bio_lines": bio_lines,
        "locations": locations,
        "meta_description": meta_description,
        "og_description": og_description,
    }


def build_queries(summary: dict[str, object]) -> list[tuple[str, str]]:
    store_name = compact(str(summary.get("store_name", "")).strip(), 80)
    username = compact(str(summary.get("username", "")).strip(), 80)
    aliases = infer_store_aliases(username, store_name)
    locations = [compact(str(item), 80) for item in summary.get("locations", [])]

    queries: list[tuple[str, str]] = []
    for alias in aliases[:3]:
        queries.append(("google_web", f'"{alias}" loja'))
        queries.append(("google_web", f'"{alias}" instagram'))
        queries.append(("google_images", f'"{alias}" fachada loja'))
        queries.append(("google_images", f'"{alias}" interior loja'))
        queries.append(("google_maps", f'"{alias}"'))
        queries.append(("bing_web", f'"{alias}" loja'))
        queries.append(("bing_web", f'"{alias}" instagram'))

    if username:
        queries.append(("bing_web", f'"{username}" instagram'))
        queries.append(("google_web", f'"{username}" instagram loja'))
        queries.append(("google_web", username))

    for location in locations:
        for alias in aliases[:3]:
            queries.append(("google_web", f'"{alias}" "{location}"'))
            queries.append(("google_images", f'"{alias}" "{location}" fachada'))
            queries.append(("google_images", f'"{alias}" "{location}" interior'))
            queries.append(("google_maps", f'"{alias}" "{location}"'))
            queries.append(("bing_web", f'"{alias}" "{location}"'))
            queries.append(("google_web", f'site:facebook.com "{alias}" "{location}"'))

    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in queries:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def build_image_queries(summary: dict[str, object]) -> list[tuple[str, str]]:
    username = compact(str(summary.get("username", "")).strip(), 80)
    store_name = compact(str(summary.get("store_name", "")).strip(), 80)
    aliases = infer_store_aliases(username, store_name)[:3]
    locations = [compact(str(item), 80) for item in summary.get("locations", [])][:3]

    queries: list[tuple[str, str]] = []
    for alias in aliases:
        if locations:
            for location in locations:
                queries.extend(
                    [
                        ("facade", f'"{alias}" "{location}" fachada loja'),
                        ("facade", f'"{alias}" "{location}" frente da loja'),
                        ("facade", f'"{alias}" "{location}" vitrine'),
                        ("interior", f'"{alias}" "{location}" interior loja'),
                        ("interior", f'"{alias}" "{location}" dentro da loja'),
                        ("interior", f'"{alias}" "{location}" provador loja'),
                    ]
                )
        else:
            queries.extend(
                [
                    ("facade", f'"{alias}" fachada loja'),
                    ("facade", f'"{alias}" frente da loja'),
                    ("interior", f'"{alias}" interior loja'),
                    ("interior", f'"{alias}" dentro da loja'),
                ]
            )

    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in queries:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def search_url(engine: str, query: str) -> str:
    encoded = quote_plus(query)
    if engine == "google_web":
        return f"https://www.google.com/search?q={encoded}"
    if engine == "google_images":
        return f"https://www.google.com/search?tbm=isch&q={encoded}"
    if engine == "google_maps":
        return f"https://www.google.com/maps/search/{encoded}"
    if engine == "bing_web":
        return f"https://www.bing.com/search?q={encoded}"
    return f"https://www.google.com/search?q={encoded}"


def parse_bing_results(html_text: str) -> list[SearchResult]:
    results: list[SearchResult] = []
    pattern = re.compile(
        r'<li class="b_algo".*?<h2><a[^>]+href="([^"]+)"[^>]*>(.*?)</a></h2>(.*?)(?:</li>|<div class="b_pag")',
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html_text):
        href = html.unescape(match.group(1))
        title = compact(re.sub(r"<.*?>", "", html.unescape(match.group(2))), 120)
        snippet = compact(re.sub(r"<.*?>", "", html.unescape(match.group(3))), 180)
        if not href.startswith("http"):
            continue
        results.append(SearchResult(source="bing_result", label=title or href, url=href, note=snippet))
    return results


def parse_bing_image_results(html_text: str, image_type: str, query: str) -> list[ImageCandidate]:
    image_urls = [html.unescape(item) for item in re.findall(r'murl&quot;:&quot;(.*?)&quot;', html_text)]
    page_urls = [html.unescape(item) for item in re.findall(r'purl&quot;:&quot;(.*?)&quot;', html_text)]
    candidates: list[ImageCandidate] = []
    for image_url, source_page in zip(image_urls, page_urls, strict=False):
        if not image_url.startswith("http"):
            continue
        if not source_page.startswith("http"):
            continue
        candidates.append(
            ImageCandidate(
                image_type=image_type,
                query=query,
                image_url=image_url,
                source_page=source_page,
                confidence=0.0,
            )
        )
    return candidates


def rank_image_candidate(candidate: ImageCandidate, summary: dict[str, object]) -> float:
    aliases = infer_store_aliases(
        compact(str(summary.get("username", "")), 80),
        compact(str(summary.get("store_name", "")), 80),
    )
    locations = [normalize_for_alias(str(item)) for item in summary.get("locations", [])]

    score = 0.25
    text = normalize_for_alias(" ".join([candidate.source_page, candidate.image_url]))

    preferred_domains = (
        "instagram.com",
        "cdninstagram.com",
        "fbcdn.net",
        "facebook.com",
        "googleusercontent.com",
        "google.com",
    )
    blocked_domains = (
        "pinterest.",
        "pinimg.com",
        "mercadolivre.",
        "shopee.",
        "aliexpress.",
        "amazon.",
        "scribd.",
        "zhihu.",
        "havan.",
        "youtube.com",
        "youtu.be",
        "tiktok.com",
    )

    if any(domain in candidate.source_page.lower() for domain in preferred_domains):
        score += 0.18
    if any(domain in candidate.image_url.lower() for domain in preferred_domains):
        score += 0.16
    if any(domain in candidate.source_page.lower() for domain in blocked_domains):
        score -= 0.35
    if any(domain in candidate.image_url.lower() for domain in blocked_domains):
        score -= 0.25

    alias_hits = 0
    for alias in aliases:
        if alias and alias in text:
            score += 0.18
            alias_hits += 1
    for location in locations:
        if location and location in text:
            score += 0.12

    if candidate.image_type == "facade":
        if any(token in text for token in ("fachada", "frente", "vitrine", "entrada", "outside", "storefront")):
            score += 0.20
    if candidate.image_type == "interior":
        if any(token in text for token in ("interior", "inside", "provador", "arara", "balcao", "prateleira")):
            score += 0.20

    if alias_hits == 0 and not any(domain in candidate.source_page.lower() for domain in preferred_domains):
        score = min(score, 0.44)

    return round(max(0.0, min(score, 0.99)), 2)


def choose_best_images(summary: dict[str, object], progress: queue.Queue[tuple[str, object]]) -> dict[str, ImageCandidate]:
    best: dict[str, ImageCandidate] = {}
    image_queries = build_image_queries(summary)
    seen_image_urls: set[str] = set()

    for image_type, query in image_queries:
        progress.put(("log", f"Buscando imagem publica: {query}"))
        try:
            bing_html = fetch_text("https://www.bing.com/images/search?q=" + quote_plus(query))
        except Exception as exc:
            progress.put(("log", f"Falha na busca de imagens '{query}': {exc}"))
            continue

        candidates = parse_bing_image_results(bing_html, image_type, query)
        for candidate in candidates[:15]:
            if candidate.image_url in seen_image_urls:
                continue
            seen_image_urls.add(candidate.image_url)
            candidate.confidence = rank_image_candidate(candidate, summary)
            candidate.note = f"query={query}"
            current = best.get(image_type)
            if current is None or candidate.confidence > current.confidence:
                best[image_type] = candidate

    return best


def resolve_image_url(image_url: str) -> str:
    if "lookaside.instagram.com/seo/google_widget/crawler/" not in image_url:
        return image_url
    try:
        html_text = fetch_text(image_url)
        resolved = extract_meta(html_text, "property", "og:image")
        if resolved:
            return resolved
    except Exception:
        return image_url
    return image_url


def capture_bing_image_search_screenshot(query: str, image_type: str) -> Path | None:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except Exception:
        return None

    options = Options()
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1800")
    options.add_argument("--lang=pt-BR")

    target_dir = OUTPUT_DIR / f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{'01' if image_type == 'facade' else '02'}_{image_type}_fallback.png"

    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://www.bing.com/images/search?q=" + quote_plus(query))
        driver.save_screenshot(str(path))
        return path
    finally:
        driver.quit()


def guess_extension(image_url: str, content_type: str | None = None) -> str:
    path = urlparse(image_url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    return ".jpg"


def slugify(value: str) -> str:
    value = normalize_for_alias(value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "loja"


def download_best_images(summary: dict[str, object], best_images: dict[str, ImageCandidate]) -> list[Path]:
    store_slug = slugify(str(summary.get("store_name") or summary.get("username") or "loja"))
    target_dir = OUTPUT_DIR / f"{store_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[Path] = []
    for image_type in ("facade", "interior"):
        candidate = best_images.get(image_type)
        if not candidate:
            fallback = capture_bing_image_search_screenshot(
                f'"{summary.get("store_name") or summary.get("username")}" {image_type} loja',
                image_type,
            )
            if fallback:
                saved_files.append(fallback)
            continue
        final_image_url = resolve_image_url(candidate.image_url)
        request = Request(final_image_url, headers={"User-Agent": UA})
        try:
            with urlopen(request, timeout=30) as response:
                content_type = response.headers.get("Content-Type", "")
                data = response.read()
                if "text/html" in content_type.lower():
                    raise ValueError("resolved to html, not image")
                ext = guess_extension(final_image_url, content_type)
            file_path = target_dir / f"{'01' if image_type == 'facade' else '02'}_{image_type}{ext}"
            file_path.write_bytes(data)
            saved_files.append(file_path)
        except Exception:
            fallback = capture_bing_image_search_screenshot(candidate.query, image_type)
            if fallback:
                saved_files.append(fallback)
    return saved_files


def run_public_search(instagram_url: str, progress: queue.Queue[tuple[str, object]]) -> dict[str, object]:
    progress.put(("log", "Lendo perfil publico do Instagram..."))
    profile_html = fetch_text(instagram_url)
    summary = extract_profile_summary(profile_html, instagram_url)

    progress.put(("summary", summary))
    progress.put(("log", "Montando caminhos de busca publica..."))

    queries = build_queries(summary)
    search_links: list[SearchResult] = [
        SearchResult("instagram_profile", "Perfil publico do Instagram", summary["instagram_url"], ""),
    ]

    for engine, query in queries:
        label = f"{engine}: {query}"
        search_links.append(SearchResult(engine, label, search_url(engine, query)))

    progress.put(("log", "Consultando Bing para resultados publicos iniciais..."))
    found_urls: dict[str, SearchResult] = {}
    for engine, query in queries:
        if engine != "bing_web":
            continue
        url = search_url(engine, query)
        progress.put(("log", f"Buscando: {query}"))
        try:
            bing_html = fetch_text(url)
        except Exception as exc:
            progress.put(("log", f"Falha no Bing para '{query}': {exc}"))
            continue
        for result in parse_bing_results(bing_html)[:8]:
            if result.url not in found_urls:
                found_urls[result.url] = result

    best_images = choose_best_images(summary, progress)
    saved_files = download_best_images(summary, best_images)

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_instagram_url": instagram_url,
        "summary": summary,
        "search_links": [asdict(item) for item in search_links],
        "public_results": [asdict(item) for item in found_urls.values()],
        "best_images": {key: asdict(value) for key, value in best_images.items()},
        "saved_files": [str(path) for path in saved_files],
    }
    return report


class App:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("1180x760")
        self.root.minsize(1000, 680)

        self.url_var = StringVar()
        self.status_var = StringVar(value="Cole o link do Instagram da loja e clique em Buscar.")
        self.result_rows: list[SearchResult] = []
        self.search_rows: list[SearchResult] = []
        self.report: dict[str, object] | None = None
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_layout()
        self.root.after(150, self._poll_worker_queue)

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=BOTH, expand=True)

        top = ttk.Frame(outer)
        top.pack(fill=X)

        ttk.Label(top, text="Link do Instagram da loja/cliente").pack(anchor="w")
        entry_row = ttk.Frame(top)
        entry_row.pack(fill=X, pady=(6, 4))

        entry = ttk.Entry(entry_row, textvariable=self.url_var)
        entry.pack(side=LEFT, fill=X, expand=True)
        entry.focus_set()

        self.search_button = ttk.Button(entry_row, text="Buscar", command=self.start_search)
        self.search_button.pack(side=LEFT, padx=(8, 0))

        self.open_button = ttk.Button(entry_row, text="Abrir Buscas Principais", command=self.open_key_links)
        self.open_button.pack(side=LEFT, padx=(8, 0))

        status = ttk.Label(top, textvariable=self.status_var)
        status.pack(anchor="w", pady=(2, 10))

        summary_box = ttk.LabelFrame(outer, text="Resumo do Perfil", padding=10)
        summary_box.pack(fill=X)
        self.summary_text = ttk.Label(summary_box, text="Nenhum perfil carregado ainda.", justify=LEFT)
        self.summary_text.pack(anchor="w")

        middle = ttk.PanedWindow(outer, orient="horizontal")
        middle.pack(fill=BOTH, expand=True, pady=(12, 0))

        left = ttk.LabelFrame(middle, text="Caminhos de Busca", padding=8)
        right = ttk.LabelFrame(middle, text="Resultados Publicos Encontrados", padding=8)
        middle.add(left, weight=1)
        middle.add(right, weight=1)

        self.search_tree = self._build_tree(
            parent=left,
            columns=("source", "label", "url"),
            headings=("Fonte", "Busca", "URL"),
            widths=(120, 280, 420),
        )
        self.search_tree.bind("<Double-1>", self._open_selected_search_link)

        self.result_tree = self._build_tree(
            parent=right,
            columns=("source", "label", "url"),
            headings=("Fonte", "Titulo", "URL"),
            widths=(120, 280, 420),
        )
        self.result_tree.bind("<Double-1>", self._open_selected_result_link)

        bottom = ttk.LabelFrame(outer, text="Log", padding=8)
        bottom.pack(fill=BOTH, expand=False, pady=(12, 0))

        self.log = ttk.Treeview(bottom, columns=("message",), show="headings", height=8)
        self.log.heading("message", text="Mensagem")
        self.log.column("message", width=1120, anchor="w")
        self.log.pack(fill=BOTH, expand=True)

    def _build_tree(
        self,
        parent: ttk.Widget,
        columns: tuple[str, ...],
        headings: tuple[str, ...],
        widths: tuple[int, ...],
    ) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill=BOTH, expand=True)

        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column, heading, width in zip(columns, headings, widths, strict=True):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="w")
        yscroll = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.pack(side=RIGHT, fill=Y)
        return tree

    def start_search(self) -> None:
        raw_url = self.url_var.get()
        try:
            instagram_url = normalize_instagram_url(raw_url)
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        self.search_button.configure(state="disabled")
        self.status_var.set("Buscando e salvando 1 fachada + 1 interior no Desktop...")
        self._clear_tree(self.search_tree)
        self._clear_tree(self.result_tree)
        self._clear_tree(self.log)
        self.summary_text.configure(text="Carregando...")
        self.result_rows = []
        self.search_rows = []
        self.report = None

        worker = threading.Thread(
            target=self._worker_run,
            args=(instagram_url,),
            daemon=True,
        )
        worker.start()

    def _worker_run(self, instagram_url: str) -> None:
        try:
            report = run_public_search(instagram_url, self.worker_queue)
            self.worker_queue.put(("done", report))
        except Exception as exc:
            self.worker_queue.put(("error", str(exc)))

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                event, payload = self.worker_queue.get_nowait()
                if event == "log":
                    self.log.insert("", END, values=(str(payload),))
                elif event == "summary":
                    self._render_summary(payload)
                elif event == "done":
                    self._finish(payload)
                elif event == "error":
                    self._fail(str(payload))
        except queue.Empty:
            pass
        self.root.after(150, self._poll_worker_queue)

    def _render_summary(self, summary: dict[str, object]) -> None:
        lines = [
            f"Loja: {summary.get('store_name') or '-'}",
            f"Usuario: @{summary.get('username') or '-'}",
        ]
        locations = summary.get("locations") or []
        if locations:
            lines.append("Localidades inferidas: " + " | ".join(str(item) for item in locations))
        bio = compact(str(summary.get("bio") or ""), 400)
        if bio:
            lines.append("Bio: " + bio)
        self.summary_text.configure(text="\n".join(lines))

    def _finish(self, report: dict[str, object]) -> None:
        self.report = report
        self.search_button.configure(state="normal")
        saved_files = report.get("saved_files", [])
        if saved_files:
            self.status_var.set("Busca concluida e imagens salvas no Desktop.")
        else:
            self.status_var.set("Busca concluida, mas nenhuma imagem foi salva.")

        self.search_rows = [SearchResult(**item) for item in report.get("search_links", [])]
        self.result_rows = [SearchResult(**item) for item in report.get("public_results", [])]

        for row in self.search_rows:
            self.search_tree.insert("", END, values=(row.source, row.label, row.url))
        for row in self.result_rows:
            self.result_tree.insert("", END, values=(row.source, row.label, row.url))

        best_images = report.get("best_images", {})
        for image_type in ("facade", "interior"):
            item = best_images.get(image_type)
            if item:
                self.log.insert(
                    "",
                    END,
                    values=(
                        f"{image_type}: confidence={item['confidence']} | origem={item['source_page']} | imagem={item['image_url']}",
                    ),
                )
        if saved_files:
            for path in saved_files:
                self.log.insert("", END, values=(f"Imagem salva: {path}",))
        else:
            self.log.insert("", END, values=("Nenhuma imagem forte o suficiente foi salva.",))

    def _fail(self, message: str) -> None:
        self.search_button.configure(state="normal")
        self.status_var.set("Falha na busca.")
        self.log.insert("", END, values=(f"Erro: {message}",))
        messagebox.showerror(APP_TITLE, message)

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    def _open_selected_search_link(self, _event: object) -> None:
        self._open_from_tree(self.search_tree, self.search_rows)

    def _open_selected_result_link(self, _event: object) -> None:
        self._open_from_tree(self.result_tree, self.result_rows)

    def _open_from_tree(self, tree: ttk.Treeview, rows: list[SearchResult]) -> None:
        selected = tree.selection()
        if not selected:
            return
        item = selected[0]
        index = tree.index(item)
        if index < len(rows):
            webbrowser.open(rows[index].url)

    def open_key_links(self) -> None:
        if not self.search_rows:
            messagebox.showinfo(APP_TITLE, "Nenhuma busca pronta ainda.")
            return
        opened = 0
        preferred = {"instagram_profile", "google_web", "google_images", "google_maps"}
        for row in self.search_rows:
            if row.source in preferred:
                webbrowser.open(row.url)
                opened += 1
                if opened >= 6:
                    break

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
