"""武蔵野大学トップから同一ホストのHTMLを幅優先で巡回する。"""
import csv
import json
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

START_URL = "https://www.musashino-u.ac.jp/"
HOST = urlsplit(START_URL).hostname
USER_AGENT = "UniversitySitemapAssignment/1.0"
DELAY = 1.0
STATE = Path("crawl_state.json")
# titleのない画像・文書などはHTMLページの巡回対象から除く。
ASSETS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
          ".css", ".js", ".zip", ".xlsx", ".xls", ".doc", ".docx", ".ppt",
          ".pptx", ".mp4", ".mp3", ".wav", ".woff", ".woff2"}


def normalize(href, base):
    """相対URLを解決し、外部ホストとフラグメントを除く。クエリは保持する。"""
    try:
        parts = urlsplit(urljoin(base, href.strip()))
        if parts.scheme not in ("http", "https") or parts.hostname != HOST:
            return None
        if parts.username or parts.password or parts.port not in (None, 80, 443):
            return None
        if Path(parts.path.lower()).suffix in ASSETS:
            return None
        return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", parts.query, ""))
    except ValueError:
        return None


def save_csv(pages):
    """辞書のkeyとvalueをCSVの2列にする。"""
    with open("sitemap.csv", "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["URL", "title"])
        writer.writerows(sorted(pages.items()))


def crawl():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    def get(url):
        # リダイレクトを含むすべてのHTTPリクエストの前に待機する。
        time.sleep(DELAY)
        return session.get(url, timeout=(10, 30), allow_redirects=False)

    robots_url = urljoin(START_URL, "robots.txt")
    response = get(robots_url)
    robots = RobotFileParser()
    if response.status_code in (404, 410):
        robots.parse([])
    elif response.status_code == 200:
        robots.parse(response.text.splitlines())
    else:
        raise RuntimeError(f"robots.txtの確認に失敗: {response.status_code}")
    delay = max(DELAY, robots.crawl_delay(USER_AGENT) or robots.crawl_delay("*") or 0)

    if STATE.exists():
        state = json.loads(STATE.read_text(encoding="utf-8"))
        queue = deque(state["pending"])
        visited = set(state["visited"])
        pages = state["pages"]  # URL: title の辞書型変数
        errors = state["errors"]
    else:
        queue, visited, pages, errors = deque([START_URL]), set(), {}, []
    queued = set(queue) | visited

    def checkpoint():
        STATE.write_text(json.dumps({"pending": list(queue), "visited": sorted(visited),
                                    "pages": pages, "errors": errors}, ensure_ascii=False), encoding="utf-8")
        save_csv(pages)
        Path("crawl_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        while queue:
            url = queue[0]
            if url in visited:
                queue.popleft()
                continue
            if not robots.can_fetch(USER_AGENT, url):
                errors.append({"url": url, "reason": "robots.txtで巡回禁止"})
                visited.add(url)
                queue.popleft()
                continue
            try:
                if delay > DELAY:
                    time.sleep(delay - DELAY)
                res = get(url)
                if res.status_code in (429, 503):
                    raise RuntimeError(f"サーバーから{res.status_code}。中断して後で再開してください。")
                if res.is_redirect:
                    target = normalize(res.headers.get("Location", ""), url)
                    if target and target not in queued:
                        queue.append(target)
                        queued.add(target)
                else:
                    res.raise_for_status()
                    if "html" in res.headers.get("Content-Type", "").lower():
                        soup = BeautifulSoup(res.content, "html.parser")
                        pages[url] = soup.title.get_text().strip() if soup.title else ""
                        base_tag = soup.find("base", href=True)
                        base = urljoin(url, base_tag["href"]) if base_tag else url
                        for link in soup.find_all("a", href=True):
                            target = normalize(link["href"], base)
                            if target and target not in queued:
                                queue.append(target)
                                queued.add(target)
            except requests.RequestException as exc:
                errors.append({"url": url, "reason": str(exc)})
            visited.add(url)
            queue.popleft()
            if len(visited) % 10 == 0:
                checkpoint()
                print(f"訪問 {len(visited)}, HTML {len(pages)}, 未訪問 {len(queue)}", flush=True)
    finally:
        checkpoint()
        session.close()
    print(f"完了: {len(pages)}ページ、エラー等 {len(errors)}件", flush=True)
    return pages


if __name__ == "__main__":
    crawl()
