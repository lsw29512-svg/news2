#!/usr/bin/env python3
"""매시간 60개 기업의 구글 뉴스를 모아 '최근 이슈 3가지'를 정리해 briefs.json에 저장한다. (AI·API 키 불필요)

- 기사 제목에서 자주 겹치는 단어로 기사를 묶고, 묶음마다 가장 최신 기사 제목을 대표 이슈로 쓴다.
- 지난 정리 때보다 새 기사가 MIN_NEW개 미만이면 이전 내용을 그대로 유지한다.
- 바뀐 내용이 하나도 없으면 briefs.json을 건드리지 않는다(불필요한 커밋 방지).
- 표준 라이브러리만 사용한다(설치할 패키지 없음).
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))

MIN_NEW = int(os.environ.get("MIN_NEW", "2"))   # 새 기사가 이 개수 이상일 때만 다시 정리
WINDOW = os.environ.get("WINDOW", "3d")          # 뉴스 검색 기간
TOP_N = int(os.environ.get("TOP_N", "20"))       # 기업당 분석할 기사 수
WORKERS = int(os.environ.get("WORKERS", "4"))
MAX_LEN = 80                                     # 이슈 한 줄 최대 글자 수

STOP = set("""단독 속보 종합 오늘 내일 올해 관련 대한 위해 통해 이후 전망 분석 논란 발표 기자 영상 포토 사진
결국 이번 지난 최근 우리 이제 있다 한다 했다 된다 에서 으로 까지 부터 것으로 위한 대해 따라 하는 하고 했다고
오전 오후 현재 내년 올해는 사업 회사 기업 그룹 업계 시장 확대 추진 검토 강화 개최 진행 협력 계획""".split())

PARTICLE = re.compile(r"(에서|으로|까지|부터|에게|은|는|이|가|을|를|의|에|도|와|과|만|로)$")


def now_str():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def http(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_news(query):
    q = urllib.parse.quote(f"{query} when:{WINDOW}")
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    root = ET.fromstring(http(url))
    items = []
    for it in root.iter("item"):
        title = re.sub(r"\s+-\s+[^-]+$", "", (it.findtext("title") or "").strip())
        source = (it.findtext("source") or "").strip()
        link = (it.findtext("link") or "").strip()
        try:
            ts = parsedate_to_datetime(it.findtext("pubDate") or "").timestamp()
        except Exception:
            ts = 0
        if title and link:
            items.append({"title": title, "source": source, "link": link, "ts": ts})
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:TOP_N]


def tokens(title, skip):
    out = set()
    for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", title):
        if len(w) > 2:
            w = PARTICLE.sub("", w)
        if len(w) < 2 or w in STOP or w in skip:
            continue
        if not re.search(r"[가-힣A-Za-z]", w):
            continue
        out.add(w)
    return out


def shorten(text):
    text = text.strip()
    return text if len(text) <= MAX_LEN else text[: MAX_LEN - 1].rstrip() + "…"


def make_issues(name_query, items):
    """기사 제목을 키워드로 묶어 이슈 최대 3개를 만든다. items는 최신순."""
    skip = {w for w in re.split(r"\s+OR\s+|\s+", name_query) if w}
    pool = [(a, tokens(a["title"], skip)) for a in items]
    issues = []
    while len(issues) < 3:
        df = {}
        for _, t in pool:
            for w in t:
                df[w] = df.get(w, 0) + 1
        cands = [(w, n) for w, n in df.items() if n >= 2]
        if not cands:
            break
        word, _ = sorted(cands, key=lambda x: (-x[1], -len(x[0])))[0]
        group = [a for a, t in pool if word in t]
        pool = [(a, t) for a, t in pool if word not in t]
        line = shorten(group[0]["title"])  # items가 최신순이라 첫 기사가 가장 최신
        if len(group) > 1:
            line += f" (관련 기사 {len(group)}건)"
        issues.append(line)
    # 묶이지 않은 기사로 3개를 채운다
    for a, _ in pool:
        if len(issues) >= 3:
            break
        issues.append(shorten(a["title"]))
    return issues


def main():
    with open(os.path.join(HERE, "companies.json"), encoding="utf-8") as f:
        conf = json.load(f)
    aliases = conf.get("aliases", {})
    names = [n for group in conf["groups"].values() for n in group]

    path = os.path.join(HERE, "briefs.json")
    try:
        with open(path, encoding="utf-8") as f:
            prev = json.load(f)
    except Exception:
        prev = {}
    prev_briefs = prev.get("briefs", {})
    prev_meta = prev.get("meta", {})

    def work(name):
        old_issues = prev_briefs.get(name)
        old_meta = prev_meta.get(name, {})
        query = aliases.get(name, name)
        try:
            items = fetch_news(query)
        except Exception as e:  # noqa: BLE001
            return name, old_issues, old_meta, f"뉴스 실패({e})"
        if not items:
            return name, old_issues, old_meta, "기사 없음"
        links = [i["link"] for i in items]
        old_links = set(old_meta.get("links", []))
        new_count = len([l for l in links if l not in old_links])
        if old_issues and old_links and new_count < MIN_NEW:
            return name, old_issues, old_meta, f"유지(새 기사 {new_count})"
        issues = make_issues(query, items)
        if not issues:
            return name, old_issues, old_meta, "정리할 내용 없음"
        meta = {"links": links, "summarized_at": now_str()}
        return name, issues, meta, f"갱신(새 기사 {new_count})"

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = list(ex.map(work, names))

    briefs, meta, changed = {}, {}, 0
    for name, issues, m, status in results:
        print(f"{name}: {status}")
        if issues:
            briefs[name] = issues
            meta[name] = m
        if status.startswith("갱신"):
            changed += 1

    if changed == 0:
        print("바뀐 내용이 없어 briefs.json을 그대로 둡니다.")
        return 0

    out = {"updated": now_str(), "briefs": briefs, "meta": meta}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{changed}개 기업을 갱신했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
