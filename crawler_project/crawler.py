#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_cookie_string(cookie_string: str) -> Dict[str, str]:
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    return {key: morsel.value for key, morsel in cookie.items()}


def setup_session(cookie_string: str | None) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
    if cookie_string:
        session.cookies.update(parse_cookie_string(cookie_string))
    return session


def login(session: requests.Session, config: Dict[str, Any]) -> None:
    login_url = config.get("login_url")
    if not login_url:
        raise ValueError("未配置 login_url，无法执行账号密码登录。")

    username = config.get("username")
    password = config.get("password")
    if not username or not password:
        raise ValueError("未配置 username/password，无法执行账号密码登录。")

    payload = {
        config.get("username_field", "username"): username,
        config.get("password_field", "password"): password,
    }
    extra_fields = config.get("extra_fields", {})
    if isinstance(extra_fields, dict):
        payload.update(extra_fields)

    response = session.post(login_url, data=payload, timeout=30)
    response.raise_for_status()


def extract_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    tables = []
    for table in soup.find_all("table"):
        headers = []
        header_row = table.find("tr")
        if header_row:
            headers = [cell.get_text(strip=True) for cell in header_row.find_all(["th", "td"])]
        rows = []
        for row in table.find_all("tr")[1:]:
            cells = [cell.get_text(strip=True) for cell in row.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if headers or rows:
            tables.append({"headers": headers, "rows": rows})
    return tables


def extract_summary(soup: BeautifulSoup, limit: int = 500) -> str:
    text = " ".join(soup.get_text(" ", strip=True).split())
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def fetch_pages(session: requests.Session, base_url: str, pages: List[str]) -> List[Dict[str, Any]]:
    results = []
    for path in pages:
        page_url = urljoin(base_url, path)
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        page_title = soup.title.string.strip() if soup.title and soup.title.string else page_url
        tables = extract_tables(soup)
        summary = ""
        if not tables:
            summary = extract_summary(soup)

        results.append(
            {
                "url": page_url,
                "title": page_title,
                "tables": tables,
                "summary": summary,
            }
        )
    return results


def render_html(pages: List[Dict[str, Any]]) -> str:
    sections = []
    for page in pages:
        section = [f"<h2><a href=\"{page['url']}\">{page['title']}</a></h2>"]
        if page["tables"]:
            for table in page["tables"]:
                section.append("<table>")
                if table["headers"]:
                    header_html = "".join(f"<th>{header}</th>" for header in table["headers"])
                    section.append(f"<tr>{header_html}</tr>")
                for row in table["rows"]:
                    row_html = "".join(f"<td>{cell}</td>" for cell in row)
                    section.append(f"<tr>{row_html}</tr>")
                section.append("</table>")
        else:
            section.append(f"<p class=\"summary\">{page['summary']}</p>")
        sections.append("\n".join(section))

    content = "\n".join(sections) if sections else "<p>未抓取到页面数据。</p>"
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\">
  <title>站点数据快照</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; }}
    h1 {{ margin-bottom: 0.5rem; }}
    h2 {{ margin-top: 2rem; }}
    table {{ border-collapse: collapse; margin: 1rem 0; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f6f6f6; }}
    .summary {{ color: #555; }}
  </style>
</head>
<body>
  <h1>站点数据快照</h1>
  <p>生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
  {content}
</body>
</html>"""


def ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="登录后抓取站点并生成静态页面")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--cookie", help="直接提供 Cookie 字符串")
    parser.add_argument("--cookie-file", help="从文件读取 Cookie")
    parser.add_argument("--output", default="output", help="输出目录")
    args = parser.parse_args()

    config = load_config(args.config)
    cookie_string = args.cookie
    if not cookie_string and args.cookie_file:
        with open(args.cookie_file, "r", encoding="utf-8") as handle:
            cookie_string = handle.read().strip()

    session = setup_session(cookie_string)

    if not cookie_string:
        login(session, config)

    base_url = config.get("base_url")
    if not base_url:
        raise ValueError("未配置 base_url。")

    pages = config.get("pages", [])
    if not pages:
        raise ValueError("未配置 pages 列表。")

    data = {
        "base_url": base_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pages": fetch_pages(session, base_url, pages),
    }

    ensure_output_dir(args.output)
    data_path = os.path.join(args.output, "data.json")
    html_path = os.path.join(args.output, "index.html")

    with open(data_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)

    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(render_html(data["pages"]))

    print(f"输出完成：{data_path}")
    print(f"输出完成：{html_path}")


if __name__ == "__main__":
    main()
