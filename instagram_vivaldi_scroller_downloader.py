from __future__ import annotations

import csv
import html
import mimetypes
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from shutil import copy2
from tkinter import BOTH, END, LEFT, X, filedialog, messagebox, StringVar, Tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from urllib.parse import urlparse

import browser_cookie3
import cv2
import requests
import torch
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageOps


APP_TITLE = "Instagram Scroller e Downloader"
BASE_DIR = Path(__file__).resolve().parent
DESKTOP_DIR = Path.home() / "Desktop"
OUTPUT_ROOT = DESKTOP_DIR / "INSTAGRAM_LOJAS_BAIXADAS"
AUTOSCROLL_SCRIPT_PATH = BASE_DIR / "instagram_profile_autoscroll_export.js"
MANIFEST_NAME = "manifest.tsv"
UA = "Mozilla/5.0"
_CLIP_PIPELINE = None
_CLIP_CACHE: dict[str, tuple[float, float]] = {}
_CLIP_EMBED_MODELS = None
_REFERENCE_PATTERN_CACHE: dict[str, object] | None = None
REFERENCE_SOURCE_DIR = Path(r"\\192.168.0.10\Fotos")
REFERENCE_CACHE_DIR = BASE_DIR / "reference_patterns_cache"
REFERENCE_MAX_SOURCE_IMAGES = 120
FACADE_TERMS = [
    "fachada",
    "faixada",
    "frente",
    "vitrine",
    "entrada",
    "externa",
    "externo",
    "rua",
    "porta",
    "letreiro",
    "placa",
    "loja fisica",
    "loja física",
]
INTERIOR_TERMS = [
    "interior",
    "dentro",
    "ambiente",
    "araras",
    "cabideiro",
    "balcao",
    "balcão",
    "prateleira",
    "prateleiras",
    "gondola",
    "gôndola",
    "gondolas",
    "gôndolas",
    "expositor",
    "expositores",
    "corredor",
    "corredores",
    "estante",
    "estantes",
    "produtos",
    "mercadorias",
    "itens",
    "venda",
    "mostruario",
    "mostruário",
    "estoque",
    "salão",
    "salao",
]
INTERIOR_NEGATIVE_TERMS = [
    "look do dia",
    "look",
    "modelo",
    "modelando",
    "selfie",
    "provador",
    "close",
    "detalhe",
    "ensaio",
    "catálogo",
    "catalogo",
]
GENERIC_STORE_TERMS = [
    "loja",
    "store",
    "boutique",
]


@dataclass(slots=True)
class DownloadedPost:
    post_url: str
    shortcode: str
    media_url: str
    local_path: str
    media_kind: str
    title: str
    description: str
    username: str
    caption_excerpt: str
    downloaded_at: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def normalize_post_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("URL vazia.")
    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    parsed = urlparse(value)
    if "instagram.com" not in parsed.netloc.lower():
        raise ValueError(f"Link fora do Instagram: {raw}")

    match = re.search(r"/(p|reel|tv)/([A-Za-z0-9_-]+)/?", parsed.path)
    if not match:
        raise ValueError(f"Link nao parece ser de post/reel: {raw}")

    kind, shortcode = match.groups()
    return f"https://www.instagram.com/{kind}/{shortcode}/"


def extract_username_from_profile_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    parsed = urlparse(value)
    if "instagram.com" not in parsed.netloc.lower():
        return ""

    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return ""
    first = parts[0].strip()
    if first.lower() in {"p", "reel", "tv", "stories", "explore"}:
        return ""
    return first


def extract_shortcode(url: str) -> str:
    match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)/", url)
    if not match:
        raise ValueError(f"Sem shortcode: {url}")
    return match.group(1)


def parse_urls_from_text(raw: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            normalized = normalize_post_url(stripped)
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)
    return urls


def load_vivaldi_cookies() -> requests.cookies.RequestsCookieJar:
    cookiejar = browser_cookie3.vivaldi(domain_name="instagram.com")
    jar = requests.cookies.RequestsCookieJar()
    for cookie in cookiejar:
        jar.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
    return jar


def build_session(include_cookies: bool = False) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    if include_cookies:
        try:
            session.cookies.update(load_vivaldi_cookies())
        except Exception:
            pass
    return session


def meta_content(soup: BeautifulSoup, *, prop: str | None = None, name: str | None = None) -> str:
    attrs = {}
    if prop:
        attrs["property"] = prop
    if name:
        attrs["name"] = name
    node = soup.find("meta", attrs=attrs)
    if not node:
        return ""
    return clean_text(node.get("content", ""))


def infer_username(title: str, description: str) -> str:
    for source in (title, description):
        match = re.search(r"@([A-Za-z0-9._]+)", source or "")
        if match:
            return match.group(1)
    return ""


def fetch_post_metadata(session: requests.Session, post_url: str) -> dict[str, str]:
    response = session.get(post_url, timeout=35)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = meta_content(soup, prop="og:title")
    description = meta_content(soup, prop="og:description")
    caption_excerpt = meta_content(soup, name="description")
    media_url = meta_content(soup, prop="og:image")
    video_url = meta_content(soup, prop="og:video")
    media_kind = "video_preview" if video_url else "image"
    username = infer_username(title, description) or infer_username(caption_excerpt, "")

    return {
        "title": title,
        "description": description,
        "caption_excerpt": caption_excerpt,
        "media_url": media_url,
        "media_kind": media_kind,
        "username": username,
    }


def extension_from_response(response: requests.Response, url: str) -> str:
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
    if content_type:
        guessed = mimetypes.guess_extension(content_type)
        if guessed:
            return guessed.replace(".jpe", ".jpg")
    parsed = urlparse(url)
    return Path(parsed.path).suffix.lower() or ".jpg"


def download_media(session: requests.Session, media_url: str, target: Path) -> Path:
    response = session.get(media_url, timeout=45, stream=True)
    response.raise_for_status()
    extension = extension_from_response(response, media_url)
    final_target = target.with_suffix(extension)

    with final_target.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                handle.write(chunk)
    return final_target


def safe_slug(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("._")
    return cleaned or fallback


def write_manifest(rows: list[DownloadedPost], output_dir: Path) -> Path:
    manifest_path = output_dir / MANIFEST_NAME
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(DownloadedPost.__dataclass_fields__.keys())
        for row in rows:
            writer.writerow(
                [
                    row.post_url,
                    row.shortcode,
                    row.media_url,
                    row.local_path,
                    row.media_kind,
                    row.title,
                    row.description,
                    row.username,
                    row.caption_excerpt,
                    row.downloaded_at,
                ]
            )
    return manifest_path


def read_manifest(path: Path) -> list[DownloadedPost]:
    rows: list[DownloadedPost] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for item in reader:
            rows.append(
                DownloadedPost(
                    post_url=item["post_url"],
                    shortcode=item["shortcode"],
                    media_url=item["media_url"],
                    local_path=item["local_path"],
                    media_kind=item["media_kind"],
                    title=item["title"],
                    description=item["description"],
                    username=item["username"],
                    caption_excerpt=item["caption_excerpt"],
                    downloaded_at=item["downloaded_at"],
                )
            )
    return rows


def build_output_dir(profile_hint: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUT_ROOT / f"{safe_slug(profile_hint, 'instagram')}_{timestamp}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "images").mkdir(exist_ok=True)
    (folder / "best_facade").mkdir(exist_ok=True)
    (folder / "best_interior").mkdir(exist_ok=True)
    return folder


def score_terms(text_blob: str, terms: list[str], generic_weight: float = 0.0) -> float:
    score = 0.0
    for term in terms:
        if term in text_blob:
            score += 2.0
    for term in GENERIC_STORE_TERMS:
        if term in text_blob:
            score += generic_weight
    return score


def image_shape_bonus(image_path: Path, target: str) -> float:
    try:
        with Image.open(image_path) as image:
            width, height = image.size
    except Exception:
        return 0.0

    if width <= 0 or height <= 0:
        return 0.0

    ratio = width / max(height, 1)
    if target == "facade":
        if ratio >= 1.1:
            return 0.8
        if ratio <= 0.85:
            return -0.1
        return 0.2
    if ratio <= 0.95:
        return 0.6
    if ratio >= 1.25:
        return -0.1
    return 0.2


def _get_clip_pipeline():
    global _CLIP_PIPELINE
    if _CLIP_PIPELINE is not None:
        return _CLIP_PIPELINE
    try:
        from transformers import pipeline

        _CLIP_PIPELINE = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
    except Exception:
        _CLIP_PIPELINE = False
    return _CLIP_PIPELINE


def clip_visual_scores(image_path: Path) -> tuple[float, float]:
    cache_key = str(image_path)
    if cache_key in _CLIP_CACHE:
        return _CLIP_CACHE[cache_key]

    classifier = _get_clip_pipeline()
    if not classifier:
        _CLIP_CACHE[cache_key] = (0.0, 0.0)
        return (0.0, 0.0)

    labels = [
        "storefront facade of a shop",
        "store entrance with signboard",
        "outside of a clothing store",
        "inside a store with shelves full of products",
        "store aisle with products on shelves",
        "store interior with merchandise displays",
        "clothing racks inside a store",
        "store counter with products behind it",
        "fashion model portrait",
        "catalog photo of clothes",
        "product promotion poster",
        "single person posing for a store photo",
        "close-up product photo",
    ]

    try:
        with Image.open(image_path) as image:
            results = classifier(image.convert("RGB"), candidate_labels=labels)
    except Exception:
        _CLIP_CACHE[cache_key] = (0.0, 0.0)
        return (0.0, 0.0)

    score_map = {item["label"]: float(item["score"]) for item in results}
    facade_positive = max(
        score_map.get("storefront facade of a shop", 0.0),
        score_map.get("store entrance with signboard", 0.0),
        score_map.get("outside of a clothing store", 0.0),
    )
    interior_positive = max(
        score_map.get("inside a store with shelves full of products", 0.0),
        score_map.get("store aisle with products on shelves", 0.0),
        score_map.get("store interior with merchandise displays", 0.0),
        score_map.get("clothing racks inside a store", 0.0),
        score_map.get("store counter with products behind it", 0.0),
    )
    portrait_negative = max(
        score_map.get("fashion model portrait", 0.0),
        score_map.get("catalog photo of clothes", 0.0),
        score_map.get("product promotion poster", 0.0),
        score_map.get("single person posing for a store photo", 0.0),
        score_map.get("close-up product photo", 0.0),
    )

    facade_score = facade_positive - (portrait_negative * 0.95) - (interior_positive * 0.15)
    interior_score = interior_positive - (portrait_negative * 1.1)
    _CLIP_CACHE[cache_key] = (facade_score, interior_score)
    return (facade_score, interior_score)


def _get_clip_embedder():
    global _CLIP_EMBED_MODELS
    if _CLIP_EMBED_MODELS is not None:
        return _CLIP_EMBED_MODELS
    try:
        from transformers import CLIPModel, CLIPProcessor

        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        model.eval()
        _CLIP_EMBED_MODELS = (processor, model)
    except Exception:
        _CLIP_EMBED_MODELS = False
    return _CLIP_EMBED_MODELS


def _image_embedding(image_path: Path) -> torch.Tensor | None:
    bundle = _get_clip_embedder()
    if not bundle:
        return None
    processor, model = bundle
    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
        return features[0]
    except Exception:
        return None


def _extract_reference_panels(image_path: Path) -> list[Path]:
    REFERENCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        image = cv2.imread(str(image_path))
        if image is None:
            return []
    except Exception:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    root_name = safe_slug(image_path.stem, "ref")
    output_dir = REFERENCE_CACHE_DIR / "panels" / root_name
    output_dir.mkdir(parents=True, exist_ok=True)

    panels: list[Path] = []
    area_limit = image.shape[0] * image.shape[1]
    index = 0
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < 0.05 * area_limit:
            continue
        crop = image[y : y + h, x : x + w]
        panel_path = output_dir / f"{index:02d}.jpg"
        cv2.imwrite(str(panel_path), crop)
        panels.append(panel_path)
        index += 1

    if not panels:
        single = output_dir / "00.jpg"
        cv2.imwrite(str(single), image)
        panels.append(single)
    return panels


def build_reference_patterns() -> dict[str, object]:
    global _REFERENCE_PATTERN_CACHE
    if _REFERENCE_PATTERN_CACHE is not None:
        return _REFERENCE_PATTERN_CACHE

    result: dict[str, object] = {
        "facade_paths": [],
        "interior_paths": [],
        "facade_embeddings": [],
        "interior_embeddings": [],
    }
    if not REFERENCE_SOURCE_DIR.exists():
        _REFERENCE_PATTERN_CACHE = result
        return result

    image_paths: list[Path] = []
    for path in REFERENCE_SOURCE_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            image_paths.append(path)
        if len(image_paths) >= REFERENCE_MAX_SOURCE_IMAGES:
            break

    scored_facade: list[tuple[float, Path]] = []
    scored_interior: list[tuple[float, Path]] = []
    for source in image_paths:
        for panel in _extract_reference_panels(source):
            facade_score, interior_score = clip_visual_scores(panel)
            if facade_score > 0.15:
                scored_facade.append((facade_score, panel))
            if interior_score > 0.15:
                scored_interior.append((interior_score, panel))

    scored_facade.sort(key=lambda item: item[0], reverse=True)
    scored_interior.sort(key=lambda item: item[0], reverse=True)
    facade_paths = [path for _, path in scored_facade[:20]]
    interior_paths = [path for _, path in scored_interior[:20]]

    result["facade_paths"] = facade_paths
    result["interior_paths"] = interior_paths
    result["facade_embeddings"] = [emb for path in facade_paths if (emb := _image_embedding(path)) is not None]
    result["interior_embeddings"] = [emb for path in interior_paths if (emb := _image_embedding(path)) is not None]
    _REFERENCE_PATTERN_CACHE = result
    return result


def reference_similarity_scores(image_path: Path) -> tuple[float, float]:
    refs = build_reference_patterns()
    embedding = _image_embedding(image_path)
    if embedding is None:
        return (0.0, 0.0)

    def best_similarity(pool: list[torch.Tensor]) -> float:
        if not pool:
            return 0.0
        sims = [float(torch.dot(embedding, ref).item()) for ref in pool]
        return max(sims) if sims else 0.0

    facade_sim = best_similarity(refs["facade_embeddings"])
    interior_sim = best_similarity(refs["interior_embeddings"])
    return facade_sim, interior_sim


def rank_records(rows: list[DownloadedPost]) -> tuple[list[tuple[float, DownloadedPost]], list[tuple[float, DownloadedPost]]]:
    facade_ranked: list[tuple[float, DownloadedPost]] = []
    interior_ranked: list[tuple[float, DownloadedPost]] = []

    for row in rows:
        blob = " ".join([row.title, row.description, row.caption_excerpt]).lower()
        image_path = Path(row.local_path)
        facade_score = score_terms(blob, FACADE_TERMS, generic_weight=0.35) + image_shape_bonus(image_path, "facade")
        interior_score = score_terms(blob, INTERIOR_TERMS, generic_weight=0.15) + image_shape_bonus(image_path, "interior")
        clip_facade, clip_interior = clip_visual_scores(image_path)
        ref_facade, ref_interior = reference_similarity_scores(image_path)
        facade_score += clip_facade * 3.0
        interior_score += clip_interior * 4.2
        facade_score += ref_facade * 1.8
        interior_score += ref_interior * 2.4

        if row.media_kind == "video_preview":
            facade_score += 0.15
            interior_score += 0.15
        if row.media_kind == "video_frame":
            interior_score += 0.2

        if "vitrine" in blob or "frente" in blob:
            interior_score -= 0.2
        if "provador" in blob or "araras" in blob:
            facade_score -= 0.2
        for term in INTERIOR_NEGATIVE_TERMS:
            if term in blob:
                interior_score -= 1.3

        # Interior valido aqui significa ambiente interno com mercadoria visivel:
        # prateleiras, araras, expositores, corredor ou produtos vendidos aparecendo.
        if not any(
            term in blob
            for term in (
                "prateleira",
                "prateleiras",
                "araras",
                "cabideiro",
                "gondola",
                "gôndola",
                "expositor",
                "corredor",
                "produtos",
                "mercadorias",
                "estante",
            )
        ):
            interior_score -= 0.35

        facade_ranked.append((facade_score, row))
        interior_ranked.append((interior_score, row))

    facade_ranked.sort(key=lambda item: item[0], reverse=True)
    interior_ranked.sort(key=lambda item: item[0], reverse=True)
    return facade_ranked, interior_ranked


def copy_top_candidates(
    ranked: list[tuple[float, DownloadedPost]],
    destination_dir: Path,
    prefix: str,
    limit: int = 6,
) -> list[tuple[float, Path, DownloadedPost]]:
    saved: list[tuple[float, Path, DownloadedPost]] = []
    seen: set[str] = set()
    for index, (score, row) in enumerate(ranked, start=1):
        source = Path(row.local_path)
        if not source.exists():
            continue
        if source.name in seen:
            continue
        seen.add(source.name)
        target = destination_dir / f"{index:02d}_{prefix}_{score:.2f}_{source.name}"
        target.write_bytes(source.read_bytes())
        saved.append((score, target, row))
        if len(saved) >= limit:
            break
    return saved


def promote_best_pick(
    entries: list[tuple[float, Path, DownloadedPost]],
    output_dir: Path,
    label: str,
) -> str:
    if not entries:
        return ""
    best_score, best_path, row = entries[0]
    destination = output_dir / f"FINAL_{label}_{best_score:.2f}_{best_path.name}"
    copy2(best_path, destination)
    marker = output_dir / f"FINAL_{label}.txt"
    marker.write_text(
        "\n".join(
            [
                f"label={label}",
                f"score={best_score:.2f}",
                f"file={destination.name}",
                f"post_url={row.post_url}",
                f"shortcode={row.shortcode}",
                f"username={row.username}",
            ]
        ),
        encoding="utf-8",
    )
    return str(destination)


def create_contact_sheet(
    entries: list[tuple[float, Path, DownloadedPost]],
    target: Path,
    title: str,
    cols: int = 3,
    thumb_size: tuple[int, int] = (320, 320),
) -> None:
    if not entries:
        return

    rows = (len(entries) + cols - 1) // cols
    margin = 18
    label_height = 56
    width = cols * thumb_size[0] + (cols + 1) * margin
    height = rows * (thumb_size[1] + label_height) + (rows + 1) * margin + 40
    sheet = Image.new("RGB", (width, height), "#f3efe7")
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, 10), title, fill="#1f2937")

    for index, (score, image_path, row) in enumerate(entries):
        col = index % cols
        row_index = index // cols
        x = margin + col * (thumb_size[0] + margin)
        y = 40 + margin + row_index * (thumb_size[1] + label_height + margin)
        try:
            with Image.open(image_path) as image:
                thumb = ImageOps.contain(image.convert("RGB"), thumb_size)
        except Exception:
            thumb = Image.new("RGB", thumb_size, "#d1d5db")

        frame = Image.new("RGB", thumb_size, "white")
        offset = ((thumb_size[0] - thumb.width) // 2, (thumb_size[1] - thumb.height) // 2)
        frame.paste(thumb, offset)
        sheet.paste(frame, (x, y))

        caption = f"{index + 1}. score {score:.2f}\n{row.shortcode}  @{row.username or 'sem_user'}"
        draw.text((x, y + thumb_size[1] + 8), caption, fill="#111827")

    sheet.save(target, quality=92)


def build_review_summary(
    facade_saved: list[tuple[float, Path, DownloadedPost]],
    interior_saved: list[tuple[float, Path, DownloadedPost]],
    output_dir: Path,
) -> Path:
    summary_path = output_dir / "review_summary.txt"
    lines = [
        "Melhores candidatos para revisao",
        "",
        "Fachada:",
    ]
    if facade_saved:
        for score, path, row in facade_saved:
            lines.append(f"- {path.name} | score={score:.2f} | {row.post_url}")
    else:
        lines.append("- nenhum candidato salvo")

    lines.extend(["", "Interior:"])
    if interior_saved:
        for score, path, row in interior_saved:
            lines.append(f"- {path.name} | score={score:.2f} | {row.post_url}")
    else:
        lines.append("- nenhum candidato salvo")

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def analyze_download_folder(output_dir: Path) -> dict[str, str]:
    manifest_path = output_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest nao encontrado em {output_dir}")

    rows = read_manifest(manifest_path)
    if not rows:
        raise ValueError("Nenhum item no manifest.")

    facade_ranked, interior_ranked = rank_records(rows)
    facade_saved = copy_top_candidates(facade_ranked, output_dir / "best_facade", "facade")
    interior_saved = copy_top_candidates(interior_ranked, output_dir / "best_interior", "interior")

    facade_sheet = output_dir / "best_facade_contact_sheet.jpg"
    interior_sheet = output_dir / "best_interior_contact_sheet.jpg"
    create_contact_sheet(facade_saved, facade_sheet, "Top candidatos de Fachada")
    create_contact_sheet(interior_saved, interior_sheet, "Top candidatos de Interior")
    summary = build_review_summary(facade_saved, interior_saved, output_dir)
    facade_final = promote_best_pick(facade_saved, output_dir, "facade")
    interior_final = promote_best_pick(interior_saved, output_dir, "interior")

    return {
        "manifest": str(manifest_path),
        "facade_sheet": str(facade_sheet),
        "interior_sheet": str(interior_sheet),
        "summary": str(summary),
        "facade_final": facade_final,
        "interior_final": interior_final,
    }


def download_posts(
    urls: list[str],
    output_dir: Path,
    status_callback,
) -> tuple[list[DownloadedPost], list[str]]:
    public_session = build_session(include_cookies=False)
    cookie_session = build_session(include_cookies=True)
    rows: list[DownloadedPost] = []
    errors: list[str] = []
    images_dir = output_dir / "images"

    for index, url in enumerate(urls, start=1):
        shortcode = extract_shortcode(url)
        status_callback(f"[{index}/{len(urls)}] Lendo {shortcode}...")
        try:
            metadata = fetch_post_metadata(public_session, url)
            if not metadata["media_url"]:
                metadata = fetch_post_metadata(cookie_session, url)
            media_url = metadata["media_url"]
            if not media_url:
                raise ValueError("Sem og:image na pagina.")

            username = metadata["username"] or "instagram"
            base_name = f"{index:03d}_{shortcode}_{safe_slug(username, 'user')}"
            temp_target = images_dir / f"{base_name}.jpg"
            try:
                final_target = download_media(public_session, media_url, temp_target)
            except Exception:
                final_target = download_media(cookie_session, media_url, temp_target)

            rows.append(
                DownloadedPost(
                    post_url=url,
                    shortcode=shortcode,
                    media_url=media_url,
                    local_path=str(final_target),
                    media_kind=metadata["media_kind"],
                    title=metadata["title"],
                    description=metadata["description"],
                    username=username,
                    caption_excerpt=metadata["caption_excerpt"],
                    downloaded_at=datetime.now().isoformat(timespec="seconds"),
                )
            )
        except Exception as error:
            errors.append(f"{url} -> {error}")
        time.sleep(0.6)

    write_manifest(rows, output_dir)
    return rows, errors


class App(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1080x760")
        self.minsize(920, 680)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

        self.queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.status_var = StringVar(value="Pronto.")
        self.folder_to_review_var = StringVar(value="")
        self.profile_url_var = StringVar(value="")

        self._build_ui()
        self.after(200, self._drain_queue)

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self, padding=14)
        root_frame.pack(fill=BOTH, expand=True)

        title = ttk.Label(root_frame, text=APP_TITLE, font=("Segoe UI", 15, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            root_frame,
            text=(
                "Fluxo: 1) auto-scroll no Vivaldi para exportar links dos posts, "
                "2) download dos stills/imagens, 3) triagem dos melhores candidatos."
            ),
        )
        subtitle.pack(anchor="w", pady=(4, 12))

        notebook = ttk.Notebook(root_frame)
        notebook.pack(fill=BOTH, expand=True)

        self._build_scroll_tab(notebook)
        self._build_download_tab(notebook)
        self._build_analysis_tab(notebook)

        status_bar = ttk.Label(root_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(fill=X, pady=(12, 0))

    def _build_scroll_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="1. Auto Scroll")

        instructions = (
            "1. Abra o perfil da loja no Vivaldi ja na grade de posts.\n"
            "2. Pressione F12 e abra a aba Console.\n"
            "3. Clique em 'Copiar Script'.\n"
            "4. Cole no console e pressione Enter.\n"
            "5. Espere ate o script parar sozinho e baixar um .txt com todos os links.\n"
            "6. Na aba seguinte, carregue esse .txt ou cole os links."
        )
        ttk.Label(frame, text=instructions, justify=LEFT).pack(anchor="w", fill=X)

        button_row = ttk.Frame(frame)
        button_row.pack(fill=X, pady=(12, 10))
        ttk.Button(button_row, text="Copiar Script", command=self.copy_autoscroll_script).pack(side=LEFT)
        ttk.Button(button_row, text="Salvar Script no Desktop", command=self.save_autoscroll_script_to_desktop).pack(
            side=LEFT, padx=(8, 0)
        )
        ttk.Button(button_row, text="Abrir Pasta de Saida", command=self.open_output_root).pack(side=LEFT, padx=(8, 0))

        self.script_preview = ScrolledText(frame, wrap="word", height=24)
        self.script_preview.pack(fill=BOTH, expand=True)
        self.script_preview.insert("1.0", read_text(AUTOSCROLL_SCRIPT_PATH))
        self.script_preview.configure(state="disabled")

    def _build_download_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="2. Downloader")

        info = (
            "Cole aqui os links dos posts exportados pelo auto-scroll. O downloader vai baixar a imagem do post "
            "ou o still de reels/videos e guardar tudo no Desktop."
        )
        ttk.Label(frame, text=info, justify=LEFT).pack(anchor="w", fill=X)

        profile_row = ttk.Frame(frame)
        profile_row.pack(fill=X, pady=(12, 4))
        ttk.Label(profile_row, text="Perfil Instagram:").pack(side=LEFT)
        ttk.Entry(profile_row, textvariable=self.profile_url_var).pack(side=LEFT, fill=X, expand=True, padx=(8, 8))
        ttk.Button(profile_row, text="Usar Username", command=self.use_username_from_profile_url).pack(side=LEFT)

        entry_row = ttk.Frame(frame)
        entry_row.pack(fill=X, pady=(8, 8))
        ttk.Label(entry_row, text="Nome da loja/pasta:").pack(side=LEFT)
        self.profile_hint_entry = ttk.Entry(entry_row)
        self.profile_hint_entry.pack(side=LEFT, fill=X, expand=True, padx=(8, 12))
        self.profile_hint_entry.insert(0, "instagram_loja")

        button_row = ttk.Frame(frame)
        button_row.pack(fill=X, pady=(0, 8))
        ttk.Button(button_row, text="Carregar TXT", command=self.load_urls_from_file).pack(side=LEFT)
        ttk.Button(button_row, text="Colar da Area de Transferencia", command=self.paste_clipboard_urls).pack(
            side=LEFT, padx=(8, 0)
        )
        ttk.Button(button_row, text="Baixar Imagens", command=self.start_download).pack(side=LEFT, padx=(8, 0))
        ttk.Button(button_row, text="Limpar", command=self.clear_urls).pack(side=LEFT, padx=(8, 0))

        self.urls_text = ScrolledText(frame, wrap="word", height=17)
        self.urls_text.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="Log da execucao:").pack(anchor="w", pady=(12, 6))
        self.download_log = ScrolledText(frame, wrap="word", height=11)
        self.download_log.pack(fill=BOTH, expand=True)

    def _build_analysis_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="3. Analise")

        ttk.Label(
            frame,
            text=(
                "A analise monta uma triagem automatica, separando os melhores candidatos de fachada e interior "
                "em subpastas e gerando contact sheets para revisao rapida."
            ),
            justify=LEFT,
        ).pack(anchor="w", fill=X)

        pick_row = ttk.Frame(frame)
        pick_row.pack(fill=X, pady=(12, 12))
        ttk.Entry(pick_row, textvariable=self.folder_to_review_var).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(pick_row, text="Escolher Pasta", command=self.choose_review_folder).pack(side=LEFT, padx=(8, 0))
        ttk.Button(pick_row, text="Analisar Pasta", command=self.start_analysis).pack(side=LEFT, padx=(8, 0))
        ttk.Button(pick_row, text="Abrir Pasta", command=self.open_review_folder).pack(side=LEFT, padx=(8, 0))

        self.analysis_log = ScrolledText(frame, wrap="word", height=24)
        self.analysis_log.pack(fill=BOTH, expand=True)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def append_download_log(self, message: str) -> None:
        self.download_log.insert(END, message + "\n")
        self.download_log.see(END)

    def append_analysis_log(self, message: str) -> None:
        self.analysis_log.insert(END, message + "\n")
        self.analysis_log.see(END)

    def copy_autoscroll_script(self) -> None:
        script = read_text(AUTOSCROLL_SCRIPT_PATH)
        self.clipboard_clear()
        self.clipboard_append(script)
        self.set_status("Script copiado para a area de transferencia.")

    def save_autoscroll_script_to_desktop(self) -> None:
        target = DESKTOP_DIR / "instagram_profile_autoscroll_export.js"
        target.write_text(read_text(AUTOSCROLL_SCRIPT_PATH), encoding="utf-8")
        self.set_status(f"Script salvo em {target}")
        messagebox.showinfo(APP_TITLE, f"Script salvo em:\n{target}")

    def open_output_root(self) -> None:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            import os

            os.startfile(str(OUTPUT_ROOT))
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Nao foi possivel abrir a pasta.\n{error}")

    def load_urls_from_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione o TXT exportado do Vivaldi",
            filetypes=[("Arquivos TXT", "*.txt"), ("Todos", "*.*")],
        )
        if not path:
            return
        content = Path(path).read_text(encoding="utf-8", errors="replace")
        self.urls_text.delete("1.0", END)
        self.urls_text.insert("1.0", content)
        self.set_status(f"TXT carregado: {path}")

    def paste_clipboard_urls(self) -> None:
        try:
            content = self.clipboard_get()
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Nao foi possivel ler a area de transferencia.\n{error}")
            return
        self.urls_text.delete("1.0", END)
        self.urls_text.insert("1.0", content)
        self.set_status("Links colados na area de download.")

    def clear_urls(self) -> None:
        self.urls_text.delete("1.0", END)
        self.set_status("Lista de links limpa.")

    def use_username_from_profile_url(self) -> None:
        username = extract_username_from_profile_url(self.profile_url_var.get())
        if not username:
            messagebox.showwarning(APP_TITLE, "Informe um link valido de perfil do Instagram.")
            return
        self.profile_hint_entry.delete(0, END)
        self.profile_hint_entry.insert(0, username)
        self.set_status(f"Username aplicado: {username}")

    def choose_review_folder(self) -> None:
        path = filedialog.askdirectory(
            title="Selecione a pasta baixada",
            initialdir=str(OUTPUT_ROOT),
        )
        if path:
            self.folder_to_review_var.set(path)
            self.set_status(f"Pasta selecionada: {path}")

    def open_review_folder(self) -> None:
        folder = self.folder_to_review_var.get().strip()
        if not folder:
            messagebox.showwarning(APP_TITLE, "Escolha uma pasta primeiro.")
            return
        if not Path(folder).exists():
            messagebox.showwarning(APP_TITLE, "A pasta selecionada nao existe mais.")
            return
        os.startfile(folder)

    def start_download(self) -> None:
        raw = self.urls_text.get("1.0", END)
        urls = parse_urls_from_text(raw)
        if not urls:
            messagebox.showwarning(APP_TITLE, "Cole ou carregue links validos de posts do Instagram.")
            return

        profile_hint = self.profile_hint_entry.get().strip() or "instagram_loja"
        output_dir = build_output_dir(profile_hint)
        self.download_log.delete("1.0", END)
        self.analysis_log.delete("1.0", END)
        self.folder_to_review_var.set(str(output_dir))
        self.append_download_log(f"Baixando {len(urls)} posts para:")
        self.append_download_log(str(output_dir))
        self.set_status("Download em andamento...")

        worker = threading.Thread(target=self._download_worker, args=(urls, output_dir), daemon=True)
        worker.start()

    def _download_worker(self, urls: list[str], output_dir: Path) -> None:
        def emit(message: str) -> None:
            self.queue.put(("download_log", message))

        try:
            rows, errors = download_posts(urls, output_dir, emit)
            self.queue.put(("download_log", f"Download concluido. Arquivos salvos: {len(rows)}"))
            if errors:
                self.queue.put(("download_log", "Ocorreram falhas:"))
                for error in errors:
                    self.queue.put(("download_log", error))

            review_outputs = analyze_download_folder(output_dir)
            self.queue.put(("analysis_log", f"Analise criada em {output_dir}"))
            self.queue.put(("analysis_log", f"Resumo: {review_outputs['summary']}"))
            self.queue.put(("analysis_log", f"Contact sheet fachada: {review_outputs['facade_sheet']}"))
            self.queue.put(("analysis_log", f"Contact sheet interior: {review_outputs['interior_sheet']}"))
            if review_outputs["facade_final"]:
                self.queue.put(("analysis_log", f"Escolha final fachada: {review_outputs['facade_final']}"))
            if review_outputs["interior_final"]:
                self.queue.put(("analysis_log", f"Escolha final interior: {review_outputs['interior_final']}"))
            self.queue.put(("status", f"Concluido. Pasta pronta: {output_dir}"))
        except Exception as error:
            self.queue.put(("status", f"Falha: {error}"))
            self.queue.put(("download_log", f"Falha no downloader: {error}"))

    def start_analysis(self) -> None:
        folder = self.folder_to_review_var.get().strip()
        if not folder:
            messagebox.showwarning(APP_TITLE, "Escolha uma pasta ja baixada.")
            return

        output_dir = Path(folder)
        self.analysis_log.delete("1.0", END)
        self.append_analysis_log(f"Analisando pasta: {output_dir}")
        self.set_status("Analise em andamento...")
        worker = threading.Thread(target=self._analysis_worker, args=(output_dir,), daemon=True)
        worker.start()

    def _analysis_worker(self, output_dir: Path) -> None:
        try:
            review_outputs = analyze_download_folder(output_dir)
            self.queue.put(("analysis_log", f"Resumo: {review_outputs['summary']}"))
            self.queue.put(("analysis_log", f"Contact sheet fachada: {review_outputs['facade_sheet']}"))
            self.queue.put(("analysis_log", f"Contact sheet interior: {review_outputs['interior_sheet']}"))
            if review_outputs["facade_final"]:
                self.queue.put(("analysis_log", f"Escolha final fachada: {review_outputs['facade_final']}"))
            if review_outputs["interior_final"]:
                self.queue.put(("analysis_log", f"Escolha final interior: {review_outputs['interior_final']}"))
            self.queue.put(("status", f"Analise concluida em {output_dir}"))
        except Exception as error:
            self.queue.put(("analysis_log", f"Falha na analise: {error}"))
            self.queue.put(("status", f"Falha na analise: {error}"))

    def _drain_queue(self) -> None:
        while True:
            try:
                event, payload = self.queue.get_nowait()
            except queue.Empty:
                break

            if event == "download_log":
                self.append_download_log(payload)
            elif event == "analysis_log":
                self.append_analysis_log(payload)
            elif event == "status":
                self.set_status(payload)

        self.after(200, self._drain_queue)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
