#!/usr/bin/env python3
"""Collect active AI repositories from GitHub and generate categorized indexes."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CATEGORY_DIR = ROOT / "categories"
TODAY = datetime.now(timezone.utc).date()
MIN_STARS = 50
ACTIVE_DAYS = 180
MAX_PER_CATEGORY = 120
INDEX_TOP_N = 25
CATEGORY_TOP_N = 50

SEARCH_QUERIES = [
    "topic:artificial-intelligence",
    "topic:machine-learning",
    "topic:deep-learning",
    "topic:llm",
    "topic:large-language-models",
    "topic:ai-agents",
    "topic:mcp",
    "topic:generative-ai",
    "topic:ai-tools",
    "topic:rag",
    "topic:diffusion-models",
    "topic:computer-vision",
    "topic:nlp",
    "topic:speech-recognition",
    "topic:reinforcement-learning",
    "topic:prompt-engineering",
    "topic:langchain",
    "topic:llm-inference",
    "topic:awesome-ai",
    "topic:model-context-protocol",
]

CATEGORY_RULES = [
    ("Agents & MCP", (
        "agent", "mcp", "model context protocol", "tool use", "tool-use",
        "computer use", "computer-use", "crewai", "langgraph", "autogen",
        "autonomous agent", "multi-agent", "workflow automation",
    )),
    ("LLM & RAG", (
        "llm", "large language model", "language model", "rag", "retrieval",
        "prompt", "inference", "transformer", "quantization", "embedding",
        "vector database", "chat model", "token", "fine-tuning", "lora",
    )),
    ("Developer Tools", (
        "coding assistant", "code generation", "code review", "cli", "terminal",
        "ide", "extension", "developer tools", "devtool", "copilot", "refactor",
        "programming assistant", "api testing", "productivity tools",
    )),
    ("Frameworks & Infrastructure", (
        "framework", "training", "inference server", "serving", "distributed",
        "kubernetes", "gpu", "compiler", "runtime", "orchestration",
        "vector database", "model deployment", "machine learning operations",
    )),
    ("Research & Papers", (
        "paper", "arxiv", "research", "survey", "reproduction",
        "implementation of", "neurips", "iclr", "icml", "cvpr", "acl", "emnlp",
    )),
    ("Data & Evaluation", (
        "dataset", "benchmark", "evaluation", "eval", "leaderboard",
        "red team", "safety evaluation", "data annotation", "synthetic data",
    )),
    ("Vision, Audio & Creative", (
        "image", "video", "vision", "diffusion", "stable diffusion",
        "segmentation", "object detection", "ocr", "speech", "audio", "voice",
        "tts", "asr", "music", "art generation", "3d generation", "creative",
    )),
    ("Interesting Applications", (
        "chatbot", "assistant", "automation", "workflow", "webui", "web ui",
        "chat ui", "personal assistant", "knowledge base", "note taking",
        "search engine", "game", "application", "app", "dashboard",
    )),
    ("Awesome & Guides", (
        "awesome", "curated list", "resource list", "tutorial", "course",
        "learning path", "guide", "handbook", "best practices", "papers list",
    )),
]

CATEGORY_DESCRIPTIONS = {
    "Agents & MCP": "AI Agent、工具调用、MCP 与自动化工作流",
    "LLM & RAG": "大模型、推理、提示词、RAG 与向量检索",
    "Developer Tools": "编码助手、CLI、IDE 插件与开发效率工具",
    "Frameworks & Infrastructure": "训练、推理、部署与模型基础设施",
    "Research & Papers": "论文实现、研究复现与技术综述",
    "Data & Evaluation": "数据集、Benchmark、评测与安全",
    "Vision, Audio & Creative": "图像、视频、语音、音乐与创意生成",
    "Interesting Applications": "聊天机器人、自动化、WebUI 与有趣应用",
    "Awesome & Guides": "Awesome 列表、教程与学习资源",
    "General AI & Machine Learning": "通用 AI 与机器学习项目",
}


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def github_search(query: str) -> list[dict[str, Any]]:
    cutoff = (TODAY - timedelta(days=ACTIVE_DAYS)).isoformat()
    full_query = f"{query} stars:>={MIN_STARS} pushed:>={cutoff}"
    params = urllib.parse.urlencode({
        "q": full_query,
        "sort": "stars",
        "order": "desc",
        "per_page": "100",
    })
    url = f"https://api.github.com/search/repositories?{params}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "awesome-ai-radar",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
        return payload.get("items", [])
    except urllib.error.HTTPError as exc:
        print(f"GitHub search failed for {full_query!r}: HTTP {exc.code}")
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"GitHub search failed for {full_query!r}: {exc}")
        return []


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def classify(repo: dict[str, Any]) -> str:
    topics = " ".join(repo.get("topics", [])).lower()
    name = (repo.get("name") or "").lower()
    description = (repo.get("description") or "").lower()
    text = f"{topics} {name} {description}"

    for category, keywords in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return "General AI & Machine Learning"


def growth_from_history(history: list[dict[str, Any]], days: int) -> int:
    if not history:
        return 0
    target = TODAY - timedelta(days=days)
    previous = None
    for entry in history:
        try:
            entry_date = date.fromisoformat(entry["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if entry_date <= target:
            previous = int(entry["stars"])
    latest = int(history[-1].get("stars", 0))
    return max(0, latest - previous) if previous is not None else 0


def normalized_repo(
    repo: dict[str, Any],
    old_repo: dict[str, Any] | None,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    pushed = parse_date(repo.get("pushed_at"))
    created = parse_date(repo.get("created_at"))
    stars = int(repo.get("stargazers_count", 0))
    forks = int(repo.get("forks_count", 0))
    growth_7d = growth_from_history(history, 7)
    growth_30d = growth_from_history(history, 30)
    age_days = max(0, (TODAY - created).days) if created else 0
    inactive_days = max(0, (TODAY - pushed).days) if pushed else ACTIVE_DAYS
    recency_bonus = max(0, 120 - inactive_days)
    young_bonus = max(0, 120 - min(age_days, 120)) // 2
    category = classify(repo)
    score = stars + forks * 3 + growth_7d * 12 + growth_30d * 3 + recency_bonus + young_bonus
    if category != "General AI & Machine Learning":
        score += 30

    return {
        "id": repo.get("id"),
        "full_name": repo.get("full_name"),
        "html_url": repo.get("html_url"),
        "description": repo.get("description") or "",
        "category": category,
        "stars": stars,
        "forks": forks,
        "growth_7d": growth_7d,
        "growth_30d": growth_30d,
        "language": repo.get("language") or "",
        "topics": repo.get("topics", []),
        "created_at": repo.get("created_at"),
        "pushed_at": repo.get("pushed_at"),
        "first_seen": (old_repo or {}).get("first_seen", TODAY.isoformat()),
        "last_seen": TODAY.isoformat(),
        "score": score,
    }


def collect_candidates() -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    cutoff = TODAY - timedelta(days=ACTIVE_DAYS)
    for index, query in enumerate(SEARCH_QUERIES):
        if index:
            time.sleep(1.2)
        for repo in github_search(query):
            full_name = repo.get("full_name")
            if not full_name or full_name in candidates:
                continue
            if repo.get("fork") or repo.get("archived") or repo.get("disabled"):
                continue
            if int(repo.get("stargazers_count", 0)) < MIN_STARS:
                continue
            pushed = parse_date(repo.get("pushed_at"))
            if pushed is None or pushed < cutoff:
                continue
            candidates[full_name] = repo
    if not candidates:
        raise RuntimeError("No repositories returned by GitHub Search; refusing to overwrite existing data.")
    print(f"Collected {len(candidates)} unique candidate repositories.")
    return candidates


def select_repositories(
    candidates: dict[str, dict[str, Any]],
    old_repos: dict[str, dict[str, Any]],
    old_history: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    normalized: list[dict[str, Any]] = []
    for full_name, repo in candidates.items():
        history = list(old_history.get(full_name, []))
        history.append({"date": TODAY.isoformat(), "stars": int(repo.get("stargazers_count", 0))})
        normalized.append(normalized_repo(repo, old_repos.get(full_name), history))
        old_history[full_name] = history

    normalized.sort(key=lambda item: (-item["score"], -item["stars"], item["full_name"]))
    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for repo in normalized:
        category = repo["category"]
        if counts.get(category, 0) >= MAX_PER_CATEGORY:
            continue
        counts[category] = counts.get(category, 0) + 1
        selected.append(repo)

    retained_history = {
        repo["full_name"]: old_history[repo["full_name"]][-120:]
        for repo in selected
    }
    return selected, retained_history


def escape_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).replace("|", "\\|").strip()


def anchor(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def repository_table(repos: list[dict[str, Any]]) -> str:
    rows = [
        "| 仓库 | Stars | 7天 | 30天 | 语言 | 简介 |",
        "|---|---:|---:|---:|---|---|",
    ]
    for repo in repos:
        description = escape_cell(repo.get("description") or "—")
        language = escape_cell(repo.get("language") or "—")
        rows.append(
            f"| [{escape_cell(repo['full_name'])}]({repo['html_url']}) "
            f"| {repo['stars']:,} | +{repo['growth_7d']:,} | +{repo['growth_30d']:,} "
            f"| {language} | {description} |"
        )
    return "\n".join(rows)


def write_category_pages(repos: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    CATEGORY_DIR.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in CATEGORY_DESCRIPTIONS}
    for repo in repos:
        grouped.setdefault(repo["category"], []).append(repo)

    for name, items in grouped.items():
        items.sort(key=lambda repo: (-repo["score"], -repo["stars"], repo["full_name"]))
        top = items[:CATEGORY_TOP_N]
        filename = f"{anchor(name)}.md"
        content = [
            f"# {name}",
            "",
            f"> {CATEGORY_DESCRIPTIONS[name]} · 更新时间：{TODAY.isoformat()}",
            "",
            f"共收录 {len(items)} 个项目，以下展示前 {len(top)} 个。",
            "",
            repository_table(top),
            "",
        ]
        (CATEGORY_DIR / filename).write_text("\n".join(content), encoding="utf-8")
    return grouped


def write_index(grouped: dict[str, list[dict[str, Any]]], total: int) -> None:
    summary_rows = [
        "| 分类 | 项目数 | 说明 |",
        "|---|---:|---|",
    ]
    for name in CATEGORY_DESCRIPTIONS:
        count = len(grouped.get(name, []))
        summary_rows.append(
            f"| [{name}](./categories/{anchor(name)}.md) | {count} | {CATEGORY_DESCRIPTIONS[name]} |"
        )

    content = [
        "# Awesome AI Radar Index",
        "",
        f"> 更新日期：**{TODAY.isoformat()}** · 收录项目：**{total}**",
        "",
        "## 分类总览",
        "",
        "\n".join(summary_rows),
        "",
    ]

    for name in CATEGORY_DESCRIPTIONS:
        repos = grouped.get(name, [])[:INDEX_TOP_N]
        content.extend([
            f"## {name}",
            "",
            f"{CATEGORY_DESCRIPTIONS[name]} · 前 {len(repos)} 个项目",
            "",
            repository_table(repos),
            "",
        ])

    (ROOT / "INDEX.md").write_text("\n".join(content), encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    old_data = read_json(DATA_DIR / "repos.json", {"updated_at": None, "repositories": []})
    old_repos = {repo["full_name"]: repo for repo in old_data.get("repositories", [])}
    old_history = read_json(DATA_DIR / "history.json", {})

    candidates = collect_candidates()
    selected, retained_history = select_repositories(candidates, old_repos, old_history)

    write_json(DATA_DIR / "repos.json", {
        "updated_at": TODAY.isoformat(),
        "repositories": selected,
    })
    write_json(DATA_DIR / "history.json", retained_history)
    grouped = write_category_pages(selected)
    write_index(grouped, len(selected))
    print(f"Indexed {len(selected)} repositories across {len(grouped)} categories.")


if __name__ == "__main__":
    main()
