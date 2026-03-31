from __future__ import annotations

import asyncio
import html
import os
import queue
import re
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from shutil import copy2
from tkinter import BOTH, END, LEFT, RIGHT, X, messagebox, StringVar, Tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import browser_cookie3
import cv2
import requests
from playwright.async_api import async_playwright

from instagram_vivaldi_scroller_downloader import (
    DownloadedPost,
    analyze_download_folder,
    build_output_dir,
    extract_username_from_profile_url,
    safe_slug,
    write_manifest,
)


APP_TITLE = "Instagram Loja - Solucao Unica"
DESKTOP_DIR = Path.home() / "Desktop"
MEDIA_SESSION = requests.Session()
MEDIA_SESSION.headers.update({"User-Agent": "Mozilla/5.0"})


def _playwright_cookies() -> list[dict[str, object]]:
    cookies: list[dict[str, object]] = []
    for cookie in browser_cookie3.vivaldi(domain_name="instagram.com"):
        same_site = "Lax"
        raw = ""
        if hasattr(cookie, "_rest"):
            raw = str(cookie._rest.get("SameSite", "") or "").lower()
        if raw == "strict":
            same_site = "Strict"
        elif raw == "none":
            same_site = "None"

        cookies.append(
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path or "/",
                "expires": float(cookie.expires) if cookie.expires else -1,
                "httpOnly": bool(getattr(cookie, "_rest", {}).get("HttpOnly", False)),
                "secure": bool(cookie.secure),
                "sameSite": same_site,
            }
        )
    return cookies


def _canonical_post_url(raw_url: str) -> str:
    match = re.search(r"/(p|reel|tv)/([A-Za-z0-9_-]+)/", raw_url)
    if not match:
        return raw_url
    kind, shortcode = match.groups()
    return f"https://www.instagram.com/{kind}/{shortcode}/"


async def _collect_profile_targets_async(profile_url: str, max_posts: int, status_callback) -> dict[str, object]:
    cookies = _playwright_cookies()
    urls: list[str] = []
    seen: set[str] = set()
    highlight_urls: list[str] = []
    username = extract_username_from_profile_url(profile_url)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 2200},
            locale="pt-BR",
        )
        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()
        status_callback("Abrindo perfil no Instagram...")
        await page.goto(profile_url, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(3500)

        if "login" in page.url.lower():
            raise RuntimeError("O Instagram redirecionou para login. Verifique se a sessao do Vivaldi ainda esta ativa.")

        stable_rounds = 0
        last_count = 0
        rounds = 0

        while stable_rounds < 8 and rounds < 140:
            hrefs = await page.eval_on_selector_all(
                "a[href*='/p/'], a[href*='/reel/'], a[href*='/tv/']",
                "els => els.map(a => a.href)",
            )
            for href in hrefs:
                canonical = _canonical_post_url(href)
                if canonical not in seen:
                    seen.add(canonical)
                    urls.append(canonical)

            count = len(urls)
            rounds += 1
            status_callback(f"Scroll {rounds}: {count} posts coletados")

            if max_posts > 0 and count >= max_posts:
                urls = urls[:max_posts]
                break

            if count == last_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
            last_count = count

            await page.mouse.wheel(0, 7000)
            await page.wait_for_timeout(1400)

        highlight_urls = await page.eval_on_selector_all(
            "a[href*='/stories/highlights/']",
            "els => Array.from(new Set(els.map(a => a.href)))",
        )
        await browser.close()

    return {
        "posts": urls,
        "highlights": highlight_urls,
        "story": f"https://www.instagram.com/stories/{username}/" if username else "",
    }


def collect_profile_targets(profile_url: str, max_posts: int, status_callback) -> dict[str, object]:
    return asyncio.run(_collect_profile_targets_async(profile_url, max_posts, status_callback))


async def _extract_page_meta(page) -> dict[str, str]:
    return await page.evaluate(
        """() => {
        const pick = (selector) => {
          const el = document.querySelector(selector);
          return el ? (el.getAttribute('content') || '').trim() : '';
        };
        return {
          title: document.title || '',
          ogTitle: pick('meta[property="og:title"]'),
          ogDescription: pick('meta[property="og:description"]'),
          description: pick('meta[name="description"]'),
        };
    }"""
    )


async def _pick_main_media_candidate(page, prefer_video: bool = False) -> dict[str, object] | None:
    return await page.evaluate(
        """(preferVideo) => {
        const viewportH = window.innerHeight || 1200;
        const nodes = Array.from(document.querySelectorAll('video, img'));
        const items = nodes.map((el, idx) => {
          const rect = el.getBoundingClientRect();
          const src = el.currentSrc || el.src || '';
          const alt = (el.alt || '').trim();
          const area = Math.max(0, rect.width) * Math.max(0, rect.height);
          return {
            idx,
            tag: el.tagName.toLowerCase(),
            src,
            alt,
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
            area,
          };
        }).filter(item => item.src && item.area > 120000 && item.y < viewportH * 1.1 && item.y + item.height > 40)
          .filter(item => !/foto do perfil|profile picture|avatar do usuário|avatar do usuario|imagem do áudio|imagem do audio/i.test(item.alt))
          .sort((a, b) => {
            if (preferVideo && a.tag !== b.tag) {
              if (a.tag === 'video') return -1;
              if (b.tag === 'video') return 1;
            }
            if (b.area !== a.area) return b.area - a.area;
            return Math.abs(a.y) - Math.abs(b.y);
          });
        return items[0] || null;
      }""",
        prefer_video,
    )


async def _click_next_carousel(page) -> bool:
    selectors = [
        "button[aria-label='Avançar']",
        "button[aria-label='Advance']",
        "button:has(svg[aria-label='Avançar'])",
        "button:has(svg[aria-label='Next'])",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        if await locator.count():
            try:
                await locator.first.click(timeout=1500)
                await page.wait_for_timeout(1200)
                return True
            except Exception:
                continue
    return False


def _download_to_path(url: str, target: Path) -> Path:
    response = MEDIA_SESSION.get(url, timeout=90, stream=True)
    response.raise_for_status()
    with target.open("wb") as handle:
        for chunk in response.iter_content(65536):
            if chunk:
                handle.write(chunk)
    return target


def _save_image_candidate(
    image_url: str,
    output_dir: Path,
    basename: str,
    source_url: str,
    media_kind: str,
    title: str,
    description: str,
    username: str,
    caption_excerpt: str,
) -> list[DownloadedPost]:
    image_path = output_dir / "images" / f"{basename}.jpg"
    _download_to_path(image_url, image_path)
    return [
        DownloadedPost(
            post_url=source_url,
            shortcode=basename,
            media_url=image_url,
            local_path=str(image_path),
            media_kind=media_kind,
            title=title,
            description=description,
            username=username,
            caption_excerpt=caption_excerpt,
            downloaded_at=datetime.now().isoformat(timespec="seconds"),
        )
    ]


def _extract_video_frames(
    video_url: str,
    output_dir: Path,
    basename: str,
    source_url: str,
    title: str,
    description: str,
    username: str,
    caption_excerpt: str,
    frame_interval_s: int,
    max_frames: int,
) -> list[DownloadedPost]:
    fd, temp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    temp_video = Path(temp_path)
    try:
        _download_to_path(video_url, temp_video)
        cap = cv2.VideoCapture(str(temp_video))
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = frame_count / fps if fps > 0 and frame_count > 0 else 0

        sample_times = [0.0]
        if duration > 0:
            step = max(1, frame_interval_s)
            current = float(step)
            while current < duration and len(sample_times) < max_frames:
                sample_times.append(current)
                current += step
            tail = max(0.0, duration - 0.3)
            if tail not in sample_times and len(sample_times) < max_frames:
                sample_times.append(tail)

        rows: list[DownloadedPost] = []
        for index, second in enumerate(sample_times[:max_frames], start=1):
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, second) * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            frame_path = output_dir / "images" / f"{basename}_frame_{index:02d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            rows.append(
                DownloadedPost(
                    post_url=source_url,
                    shortcode=f"{basename}_f{index:02d}",
                    media_url=video_url,
                    local_path=str(frame_path),
                    media_kind="video_frame",
                    title=title,
                    description=description,
                    username=username,
                    caption_excerpt=f"{caption_excerpt} frame_at={second:.1f}s".strip(),
                    downloaded_at=datetime.now().isoformat(timespec="seconds"),
                )
            )
        cap.release()
        return rows
    finally:
        try:
            temp_video.unlink(missing_ok=True)
        except Exception:
            pass


async def _extract_target_rows(page, source_url: str, output_dir: Path, username: str, frame_interval_s: int, status_callback) -> list[DownloadedPost]:
    await page.goto(source_url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(3000)
    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(700)

    meta = await _extract_page_meta(page)
    title = html.unescape(meta.get("ogTitle") or meta.get("title") or "")
    description = html.unescape(meta.get("ogDescription") or "")
    caption_excerpt = html.unescape(meta.get("description") or "")

    rows: list[DownloadedPost] = []
    seen_sources: set[str] = set()
    slide = 0

    while slide < 10:
        prefer_video = "/reel/" in source_url or "/tv/" in source_url
        candidate = await _pick_main_media_candidate(page, prefer_video=prefer_video)
        if not candidate or not candidate.get("src"):
            break

        src = str(candidate["src"])
        alt_text = html.unescape(str(candidate.get("alt") or ""))
        if src not in seen_sources:
            seen_sources.add(src)
            basename_root = safe_slug(re.sub(r"[^A-Za-z0-9_-]+", "_", source_url.rstrip("/").split("/")[-1]), "media")
            basename = f"{basename_root}_{slide + 1:02d}"
            if candidate["tag"] == "video":
                status_callback(f"Extraindo frames de video: {source_url}")
                rows.extend(
                    _extract_video_frames(
                        src,
                        output_dir,
                        basename,
                        source_url,
                        title,
                        f"{description} {alt_text}".strip(),
                        username,
                        caption_excerpt,
                        frame_interval_s=frame_interval_s,
                        max_frames=8,
                    )
                )
            else:
                rows.extend(
                    _save_image_candidate(
                        src,
                        output_dir,
                        basename,
                        source_url,
                        "image",
                        title,
                        f"{description} {alt_text}".strip(),
                        username,
                        caption_excerpt,
                    )
                )

        slide += 1
        advanced = await _click_next_carousel(page)
        if not advanced:
            break

    return rows


async def _extract_story_sequence(page, story_url: str, output_dir: Path, username: str, frame_interval_s: int, status_callback) -> list[DownloadedPost]:
    await page.goto(story_url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(3500)
    if "login" in page.url.lower():
        return []

    rows: list[DownloadedPost] = []
    seen_sources: set[str] = set()
    repeated = 0
    title = ""
    description = ""

    for index in range(20):
        candidate = await _pick_main_media_candidate(page, prefer_video=True)
        if not candidate or not candidate.get("src"):
            break

        src = str(candidate["src"])
        alt_text = html.unescape(str(candidate.get("alt") or ""))
        if src in seen_sources:
            repeated += 1
        else:
            repeated = 0
            seen_sources.add(src)
            basename_root = safe_slug(re.sub(r"[^A-Za-z0-9_-]+", "_", story_url.rstrip("/").split("/")[-1]), "story")
            basename = f"{basename_root}_{index + 1:02d}"
            if candidate["tag"] == "video":
                status_callback(f"Extraindo frames de story/destaque: {story_url}")
                rows.extend(
                    _extract_video_frames(
                        src,
                        output_dir,
                        basename,
                        story_url,
                        title,
                        alt_text or description,
                        username,
                        "story_or_highlight",
                        frame_interval_s=frame_interval_s,
                        max_frames=6,
                    )
                )
            else:
                rows.extend(
                    _save_image_candidate(
                        src,
                        output_dir,
                        basename,
                        story_url,
                        "story_image",
                        title,
                        alt_text or description,
                        username,
                        "story_or_highlight",
                    )
                )

        if repeated >= 2:
            break

        try:
            await page.keyboard.press("ArrowRight")
        except Exception:
            try:
                await page.mouse.click(1200, 500)
            except Exception:
                break
        await page.wait_for_timeout(1200)

    return rows


async def _extract_all_media_rows_async(
    profile_url: str,
    targets: dict[str, object],
    output_dir: Path,
    username: str,
    frame_interval_s: int,
    status_callback,
) -> list[DownloadedPost]:
    cookies = _playwright_cookies()
    rows: list[DownloadedPost] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1800},
            locale="pt-BR",
        )
        if cookies:
            await context.add_cookies(cookies)
        page = await context.new_page()

        for url in targets.get("posts", []):
            status_callback(f"Abrindo post/reel: {url}")
            rows.extend(await _extract_target_rows(page, str(url), output_dir, username, frame_interval_s, status_callback))

        story_url = str(targets.get("story") or "")
        if story_url:
            status_callback("Varrendo stories atuais...")
            rows.extend(await _extract_story_sequence(page, story_url, output_dir, username, frame_interval_s, status_callback))

        for url in targets.get("highlights", []):
            status_callback(f"Varrendo destaque: {url}")
            rows.extend(await _extract_story_sequence(page, str(url), output_dir, username, frame_interval_s, status_callback))

        await browser.close()

    return rows


def extract_all_media_rows(
    profile_url: str,
    targets: dict[str, object],
    output_dir: Path,
    username: str,
    frame_interval_s: int,
    status_callback,
) -> list[DownloadedPost]:
    return asyncio.run(
        _extract_all_media_rows_async(
            profile_url,
            targets,
            output_dir,
            username,
            frame_interval_s,
            status_callback,
        )
    )


def export_results_to_desktop(output_dir: Path, review_outputs: dict[str, str], profile_hint: str) -> dict[str, str]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = safe_slug(profile_hint, "instagram_loja")
    exported: dict[str, str] = {}

    for label in ("facade", "interior"):
        source = review_outputs.get(f"{label}_final", "")
        if not source:
            continue
        source_path = Path(source)
        if not source_path.exists():
            continue
        target = DESKTOP_DIR / f"{slug}_{label}_{stamp}{source_path.suffix.lower()}"
        copy2(source_path, target)
        exported[label] = str(target)

    summary_path = DESKTOP_DIR / f"{slug}_resultado_{stamp}.txt"
    lines = [
        f"perfil={profile_hint}",
        f"pasta_lote={output_dir}",
        f"fachada={exported.get('facade', '')}",
        f"interior={exported.get('interior', '')}",
        f"resumo={review_outputs.get('summary', '')}",
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    exported["summary"] = str(summary_path)
    return exported


class App(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("860x620")
        self.minsize(760, 560)
        self.queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.status_var = StringVar(value="Pronto.")
        self.profile_url_var = StringVar(value="")
        self.max_posts_var = StringVar(value="80")
        self.frame_interval_var = StringVar(value="2")
        self.last_output_dir: Path | None = None
        self._build_ui()
        self.after(200, self._drain_queue)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill=BOTH, expand=True)

        ttk.Label(root, text=APP_TITLE, font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Cole o link do perfil. O app faz o scroll, baixa as imagens e entrega 1 fachada e 1 interior no Desktop.",
        ).pack(anchor="w", pady=(4, 12))

        profile_row = ttk.Frame(root)
        profile_row.pack(fill=X, pady=(0, 8))
        ttk.Label(profile_row, text="Perfil Instagram:").pack(side=LEFT)
        ttk.Entry(profile_row, textvariable=self.profile_url_var).pack(side=LEFT, fill=X, expand=True, padx=(8, 0))

        options_row = ttk.Frame(root)
        options_row.pack(fill=X, pady=(0, 10))
        ttk.Label(options_row, text="Max posts:").pack(side=LEFT)
        ttk.Entry(options_row, textvariable=self.max_posts_var, width=8).pack(side=LEFT, padx=(8, 12))
        ttk.Label(options_row, text="Frame a cada(s):").pack(side=LEFT)
        ttk.Entry(options_row, textvariable=self.frame_interval_var, width=8).pack(side=LEFT, padx=(8, 12))
        ttk.Button(options_row, text="Executar Tudo", command=self.start_pipeline).pack(side=LEFT)
        ttk.Button(options_row, text="Abrir Pasta do Lote", command=self.open_last_output_dir).pack(side=LEFT, padx=(8, 0))
        ttk.Button(options_row, text="Abrir Desktop", command=self.open_desktop).pack(side=RIGHT)

        self.log = ScrolledText(root, wrap="word", height=28)
        self.log.pack(fill=BOTH, expand=True)

        ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill=X, pady=(12, 0))

    def append_log(self, message: str) -> None:
        self.log.insert(END, message + "\n")
        self.log.see(END)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def open_desktop(self) -> None:
        os.startfile(str(DESKTOP_DIR))

    def open_last_output_dir(self) -> None:
        if not self.last_output_dir or not self.last_output_dir.exists():
            messagebox.showwarning(APP_TITLE, "Nenhuma pasta de lote foi criada ainda.")
            return
        os.startfile(str(self.last_output_dir))

    def start_pipeline(self) -> None:
        profile_url = self.profile_url_var.get().strip()
        username = extract_username_from_profile_url(profile_url)
        if not username:
            messagebox.showwarning(APP_TITLE, "Informe um link valido de perfil do Instagram.")
            return

        try:
            max_posts = int(self.max_posts_var.get().strip() or "0")
        except ValueError:
            messagebox.showwarning(APP_TITLE, "Max posts precisa ser um numero inteiro.")
            return
        try:
            frame_interval_s = int(self.frame_interval_var.get().strip() or "2")
        except ValueError:
            messagebox.showwarning(APP_TITLE, "Frame a cada(s) precisa ser um numero inteiro.")
            return

        self.log.delete("1.0", END)
        self.set_status("Processando...")
        worker = threading.Thread(
            target=self._pipeline_worker,
            args=(profile_url, username, max_posts, max(1, frame_interval_s)),
            daemon=True,
        )
        worker.start()

    def _pipeline_worker(self, profile_url: str, username: str, max_posts: int, frame_interval_s: int) -> None:
        def emit(message: str) -> None:
            self.queue.put(("log", message))

        try:
            output_dir = build_output_dir(username)
            self.last_output_dir = output_dir
            self.queue.put(("log", f"Pasta do lote: {output_dir}"))

            targets = collect_profile_targets(profile_url, max_posts, emit)
            urls = list(targets.get("posts", []))
            if not urls and not targets.get("highlights") and not targets.get("story"):
                raise RuntimeError("Nenhuma midia foi encontrada durante o auto scroll.")

            post_file = output_dir / "post_urls.txt"
            post_file.write_text("\n".join(urls), encoding="utf-8")
            self.queue.put(("log", f"Posts coletados: {len(urls)}"))
            self.queue.put(("log", f"Lista salva em: {post_file}"))
            self.queue.put(("log", f"Destaques encontrados: {len(targets.get('highlights', []))}"))

            rows = extract_all_media_rows(profile_url, targets, output_dir, username, frame_interval_s, emit)
            if not rows:
                raise RuntimeError("A extração terminou sem imagens/frames utilizáveis.")
            write_manifest(rows, output_dir)
            self.queue.put(("log", f"Imagens/frames gerados: {len(rows)}"))

            review_outputs = analyze_download_folder(output_dir)
            exported = export_results_to_desktop(output_dir, review_outputs, username)

            if exported.get("facade"):
                self.queue.put(("log", f"Fachada final no Desktop: {exported['facade']}"))
            if exported.get("interior"):
                self.queue.put(("log", f"Interior final no Desktop: {exported['interior']}"))
            self.queue.put(("log", f"Resumo no Desktop: {exported['summary']}"))
            self.queue.put(("status", "Concluido. Resultado final salvo no Desktop."))
        except Exception as error:
            self.queue.put(("log", f"Erro: {error}"))
            self.queue.put(("status", f"Falha: {error}"))

    def _drain_queue(self) -> None:
        while True:
            try:
                kind, payload = self.queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self.append_log(payload)
            elif kind == "status":
                self.set_status(payload)

        self.after(200, self._drain_queue)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
