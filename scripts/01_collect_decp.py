import argparse
import csv
import json
import os
import time
from typing import Dict, Iterable, List, Optional

import requests


def load_config(path: str) -> Dict:
    # Accept BOM if file was created with UTF-8 BOM on Windows
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_url(base_url: str, resource_id: str) -> str:
    return base_url.format(resource_id=resource_id)


def fetch_page(url: str, params: Dict, timeout: int = 60, max_retries: int = 5) -> Dict:
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Request failed after {max_retries} retries: {last_err}")


def iter_pages(
    url: str,
    filters: Dict,
    page_size: int,
    columns: Optional[List[str]],
    max_pages: Optional[int],
    sleep_seconds: float,
    start_page: int,
) -> Iterable[Dict]:
    page = start_page
    while True:
        params = dict(filters)
        params["page"] = page
        params["page_size"] = page_size
        if columns:
            params["columns"] = ",".join(columns)

        payload = fetch_page(url, params=params)
        data = payload.get("data", [])
        if not data:
            break

        yield payload

        if max_pages and page >= (start_page - 1 + max_pages):
            break

        page += 1
        if sleep_seconds:
            time.sleep(sleep_seconds)


def infer_columns_from_payload(payload: Dict) -> List[str]:
    data = payload.get("data", [])
    if not data:
        return []
    keys = set()
    for row in data:
        keys.update(row.keys())
    return sorted(keys)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect DECP data from the tabular API")
    parser.add_argument("--config", default="configs/collect_decp.json", help="Path to config JSON")
    parser.add_argument("--inspect", action="store_true", help="Print inferred columns and exit")
    parser.add_argument("--start-page", type=int, default=None, help="Override start page")
    parser.add_argument("--max-pages", type=int, default=None, help="Override max pages")
    parser.add_argument("--append", action="store_true", help="Append to existing CSV")
    parser.add_argument("--page-size", type=int, default=None, help="Override page size")
    parser.add_argument("--sleep", type=float, default=None, help="Override sleep seconds")
    args = parser.parse_args()

    cfg = load_config(args.config)
    url = build_url(cfg["base_url"], cfg["resource_id"])
    filters = cfg.get("filters", {})
    columns = cfg.get("columns") or []
    page_size = int(cfg.get("page_size", 200))
    max_pages = cfg.get("max_pages")
    sleep_seconds = float(cfg.get("sleep_seconds", 0))
    start_page = int(cfg.get("start_page", 1))
    append = bool(cfg.get("append", False))
    output_csv = cfg.get("output_csv", "data/raw/decp.csv")

    if args.page_size is not None:
        page_size = args.page_size
    if args.max_pages is not None:
        max_pages = args.max_pages
    if args.sleep is not None:
        sleep_seconds = args.sleep
    if args.start_page is not None:
        start_page = args.start_page
    if args.append:
        append = True

    if args.inspect:
        payload = fetch_page(url, params={"page": 1, "page_size": 1, **filters})
        inferred = infer_columns_from_payload(payload)
        print("\n".join(inferred))
        return 0

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    writer = None
    fieldnames: List[str] = []
    rows_written = 0

    existing_header: Optional[List[str]] = None
    if append and os.path.exists(output_csv):
        with open(output_csv, "r", newline="", encoding="utf-8") as rf:
            reader = csv.reader(rf)
            existing_header = next(reader, None)
        if existing_header:
            fieldnames = existing_header

    mode = "a" if append else "w"
    with open(output_csv, mode, newline="", encoding="utf-8") as f:
        for payload in iter_pages(
            url, filters, page_size, columns, max_pages, sleep_seconds, start_page
        ):
            data = payload.get("data", [])
            if writer is None:
                if not fieldnames:
                    if columns:
                        fieldnames = columns
                    else:
                        fieldnames = infer_columns_from_payload(payload)
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not append or not existing_header:
                    writer.writeheader()

            for row in data:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
                rows_written += 1

    print(f"Wrote {rows_written} rows to {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
