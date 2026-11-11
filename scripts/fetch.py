"""Fetch all feeds listed in feeds.json and write site/news.json.

Runs on GitHub Actions. A feed that fails is skipped and reported in
the "status" block so the app can show which sources are down.
"""
import calendar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "scripts" / "feeds.json"
OUT = ROOT / "site" / "news.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def norm_title(t):
    return re.sub(r"[^\w]+", " ", t.lower()).strip()[:90]


def entry_time(e):
    for key in ("published_parsed", "updated_parsed"):
        v = e.get(key)
        if v:
            return int(calendar.timegm(v))
    return None


def parse_source(src, now, max_age, keywords):
    raw = http_get(src["url"])
    feed = feedparser.parse(raw)
    if feed.bozo and not feed.entries:
        raise ValueError("unreadable feed")
    items = []
    is_gnews = "news.google.com" in src["url"]
    for e in feed.entries:
        title = clean(e.get("title"))
        link = e.get("link")
        if not title or not link:
            continue
        publisher = src["name"]
        if is_gnews:
            # Google News titles look like "Headline - Publisher"
            s = e.get("source") or {}
            pub = s.get("title") if isinstance(s, dict) else None
            if pub:
                publisher = pub
                if title.endswith(" - " + pub):
                    title = title[: -len(pub) - 3].strip()
        ts = entry_time(e)
        if ts and now - ts > max_age * 3600:
            continue
        summary = "" if is_gnews else clean(e.get("summary"))[:220]
        if keywords:
            hay = (title + " " + summary).lower()
            if not any(k in hay for k in keywords):
                continue
        item = {"t": title, "u": link, "s": publisher, "ts": ts}
        if summary:
            item["d"] = summary
        if src.get("tag"):
            item["tag"] = src["tag"]
        items.append(item)
    return items


def fetch_quote(q):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(q["symbol"]) + "?range=1d&interval=1d")
    data = json.loads(http_get(url))
    meta = data["chart"]["result"][0]["meta"]
    price = meta.get("regularMarketPrice")
    prev = meta.get("previousClose") or meta.get("chartPreviousClose")
    if price is None or not prev:
        raise ValueError("no price")
    return {
        "name": q["name"],
        "price": round(price, 2),
        "chg": round((price - prev) / prev * 100, 2),
        "ts": meta.get("regularMarketTime"),
    }


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    now = int(time.time())
    out = {"generated": now, "tabs": [], "status": []}
    for tab in cfg["tabs"]:
        keywords = [k.lower() for k in tab.get("keywords", [])]
        collected = []
        for src in tab["sources"]:
            try:
                items = parse_source(src, now, tab.get("max_age_hours", 36), keywords)
                items.sort(key=lambda x: x["ts"] or 0, reverse=True)
                collected.extend(items[: cfg["max_items_per_source"]])
                out["status"].append({"tab": tab["name"], "src": src["name"], "ok": True, "n": len(items)})
            except Exception as ex:  # keep going if one feed is down
                out["status"].append({"tab": tab["name"], "src": src["name"], "ok": False, "err": str(ex)[:120]})
                print(f"[WARN] {tab['name']} / {src['name']}: {ex}", file=sys.stderr)
        seen, unique = set(), []
        for it in sorted(collected, key=lambda x: x["ts"] or 0, reverse=True):
            key = norm_title(it["t"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(it)
        tab_out = {"id": tab["id"], "name": tab["name"], "items": unique[: cfg["max_items_per_tab"]]}
        if tab.get("quotes"):
            tab_out["quotes"] = []
            for q in tab["quotes"]:
                try:
                    tab_out["quotes"].append(fetch_quote(q))
                except Exception as ex:
                    print(f"[WARN] quote {q['symbol']}: {ex}", file=sys.stderr)
        out["tabs"].append(tab_out)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ok = sum(1 for s in out["status"] if s["ok"])
    print(f"Done: {ok}/{len(out['status'])} feeds ok, written {OUT}")


if __name__ == "__main__":
    main()
