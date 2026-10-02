#!/usr/bin/env python3
"""Google 検索ステータス ダッシュボードの履歴を取得し、可視化用データを書き出す。

取得順:
  1. https://status.search.google.com/incidents.json （詳細な開始・終了日時つき）
  2. 失敗したら https://status.search.google.com/en/feed.atom （直近分のみ）

既存の data/incidents.json とマージするので、フィードから消えた古い履歴も残る。
出力:
  data/incidents.json  … 生データ（他ツールからの再利用向け）
  data/incidents.js    … index.html が <script> で読み込む版（file:// でも動く）
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://status.search.google.com"
DATA_DIR = Path(__file__).resolve().parent / "data"
JSON_PATH = DATA_DIR / "incidents.json"
JS_PATH = DATA_DIR / "incidents.js"
UA = "Mozilla/5.0 (search-status-visualizer)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8")


def fetch_products():
    """product id -> 名前。取れなければ空。"""
    try:
        raw = json.loads(fetch(f"{BASE}/products.json"))
    except Exception as e:  # noqa: BLE001
        print(f"products.json: skip ({e})", file=sys.stderr)
        return {}
    items = raw.get("products", raw) if isinstance(raw, dict) else raw
    return {p["id"]: p.get("title") or p.get("name") for p in items if isinstance(p, dict) and "id" in p}


def from_json(products):
    raw = json.loads(fetch(f"{BASE}/incidents.json"))
    out = []
    for inc in raw:
        affected = inc.get("affected_products") or []
        product_id = affected[0].get("id") if affected else inc.get("service_key")
        product = (affected[0].get("title") if affected else None) or inc.get("service_name") \
            or products.get(product_id) or "Other"
        updates = [
            {"when": u.get("when") or u.get("created"), "status": u.get("status"), "text": u.get("text")}
            for u in inc.get("updates") or []
        ]
        uri = inc.get("uri") or ""
        out.append({
            "id": inc["id"],
            "title": inc.get("external_desc") or "",
            "product": product,
            "product_id": product_id,
            "begin": inc.get("begin") or inc.get("created"),
            "end": inc.get("end"),
            "status": (inc.get("most_recent_update") or {}).get("status") or inc.get("status_impact"),
            "severity": inc.get("severity"),
            "url": uri if uri.startswith("http") else f"{BASE}/{uri.lstrip('/')}" if uri else None,
            "updates": updates,
        })
    return out


def from_atom():
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(fetch(f"{BASE}/en/feed.atom"))
    out = []
    for e in root.findall("a:entry", ns):
        title = (e.findtext("a:title", "", ns) or "").strip()
        content = re.sub(r"<[^>]+>", " ", e.findtext("a:content", "", ns) or "")
        link = e.find("a:link", ns)
        cat = e.find("a:category", ns)
        m = re.match(r"^\s*(?:RESOLVED:\s*)?(.*)$", title)
        out.append({
            "id": e.findtext("a:id", "", ns) or title,
            "title": m.group(1) if m else title,
            "product": cat.get("term") if cat is not None else "Other",
            "product_id": None,
            "begin": e.findtext("a:published", None, ns) or e.findtext("a:updated", None, ns),
            # フィードには終了日時がないので、解決済みなら最終更新を終了とみなす
            "end": e.findtext("a:updated", None, ns) if re.search(r"resolved|completed", title + content, re.I) else None,
            "status": None,
            "severity": None,
            "url": link.get("href") if link is not None else None,
            "updates": [],
        })
    return out


def load_existing():
    if JSON_PATH.exists():
        return {i["id"]: i for i in json.loads(JSON_PATH.read_text("utf-8")).get("incidents", [])}
    return {}


def main():
    products = fetch_products()
    source = "incidents.json"
    try:
        fresh = from_json(products)
    except Exception as e:  # noqa: BLE001
        print(f"incidents.json failed ({e}); falling back to atom feed", file=sys.stderr)
        source = "feed.atom"
        fresh = from_atom()

    existing = load_existing()
    merged = dict(existing)
    for inc in fresh:
        merged[inc["id"]] = inc
    incidents = sorted(merged.values(), key=lambda i: i.get("begin") or "", reverse=True)
    if merged == existing and JS_PATH.exists():
        # 変化がなければファイルを触らない（無意味なコミットを防ぐ）
        print(f"{len(fresh)} fetched from {source}, no change")
        return

    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"{BASE}/{source}",
        "incidents": incidents,
    }
    DATA_DIR.mkdir(exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=1)
    JSON_PATH.write_text(text + "\n", "utf-8")
    JS_PATH.write_text(f"window.STATUS_DATA = {text};\n", "utf-8")
    print(f"{len(fresh)} fetched from {source}, {len(incidents)} total")


if __name__ == "__main__":
    main()
