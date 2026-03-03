import os
import re
import hashlib
import html
import feedparser

def safe_slug(text: str, max_len: int = 60) -> str:
    """
    파일명에 안전하게 쓸 수 있도록 정리:
    - / \ : * ? " < > | 같은 금지 문자 제거
    - 공백은 - 로 치환
    - 너무 길면 잘라냄
    """
    text = text.strip()
    text = re.sub(r'[\\/:*?"<>|]', "", text)   # Windows 금지 문자 제거
    text = re.sub(r"\s+", "-", text)           # 공백 -> -
    text = re.sub(r"-{2,}", "-", text)         # 연속 - 정리
    return text[:max_len].strip("-") or "untitled"

def pick_feed(urls):
    """여러 RSS 주소 후보 중 엔트리가 실제로 나오는 URL을 선택"""
    for u in urls:
        feed = feedparser.parse(u)
        if getattr(feed, "entries", None):
            return u, feed
    return urls[0], feedparser.parse(urls[0])

def main():
    RSS_URL='https://api.velog.io/rss/@inhlee'
    rss_url = os.getenv("RSS_URL", "").strip()

    # 기본 후보들 (api / v2 둘 다 시도)
    if rss_url:
        candidates = [rss_url]
    else:
        # TODO: 여기 아이디를 네 벨로그 아이디로 바꾸거나, RSS_URL 환경변수를 설정해줘
        velog_id = "여기에_벨로그아이디"
        candidates = [
            f"https://api.velog.io/rss/@{velog_id}",
            f"https://v2.velog.io/rss/@{velog_id}",
        ]

    chosen_url, feed = pick_feed(candidates)

    if getattr(feed, "bozo", 0):
        # RSS 파싱 실패 시 bozo_exception에 정보가 들어있을 때가 많음
        print("RSS parse warning:", getattr(feed, "bozo_exception", "unknown"))

    entries = getattr(feed, "entries", [])
    print(f"Using RSS: {chosen_url}")
    print(f"Entries: {len(entries)}")

    # 2) 저장 폴더
    posts_dir = os.path.join(".", "velog-posts")
    os.makedirs(posts_dir, exist_ok=True)

    # 3) 글 저장/갱신
    created, updated, skipped = 0, 0, 0

    for entry in entries:
        title = (getattr(entry, "title", "") or "").strip()
        link = (getattr(entry, "link", "") or "").strip()
        desc = getattr(entry, "description", "") or ""

        # 제목이 비어있으면 스킵
        if not title:
            skipped += 1
            continue

        # 파일명 충돌 방지: 링크(또는 id) 기반 해시 8자리 붙이기
        unique_src = (getattr(entry, "id", "") or link or title).encode("utf-8")
        h = hashlib.sha1(unique_src).hexdigest()[:8]

        slug = safe_slug(title)
        file_name = f"{slug}-{h}.md"
        file_path = os.path.join(posts_dir, file_name)

        # 내용(HTML이 섞여 있을 수 있어 unescape만)
        body = html.unescape(desc).strip()

        md = f"""---
title: "{title.replace('"', '\\"')}"
source: "{link}"
---

{body}
"""

        # 기존 파일이 없으면 생성, 있으면 내용 비교 후 갱신
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md)
            created += 1
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                old = f.read()
            if old != md:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md)
                updated += 1
            else:
                skipped += 1

    print(f"Created: {created}, Updated: {updated}, Skipped: {skipped}")

if __name__ == "__main__":
    main()
