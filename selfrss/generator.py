from collections.abc import Sequence
from datetime import datetime
import os
from pathlib import Path
import tempfile
from urllib.parse import urljoin

from selfrss.models import Article
from selfrss.rss import render_rss
from selfrss.validation import validate_article_freshness, validate_rss


GAMEWATCH_FILENAME = "gamewatch-pc.xml"
GAMEWITH_FILENAME = "gamewith-pc.xml"
DENFAMI_FILENAME = "denfami-steam.xml"
DEPLOYMENT_FILENAME = "deployment.txt"


def _stage_file(directory: Path, data: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=".selfrss-", dir=directory)
    path = Path(name)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return path


def _replace_all(staged: dict[Path, Path]) -> None:
    backups = {target: target.read_bytes() if target.exists() else None for target in staged}
    replaced: list[Path] = []
    try:
        for target, temporary in staged.items():
            os.replace(temporary, target)
            replaced.append(target)
    except OSError:
        for target in replaced:
            backup = backups[target]
            if backup is None:
                target.unlink(missing_ok=True)
            else:
                rollback = _stage_file(target.parent, backup)
                os.replace(rollback, target)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def write_feed_files(
    gamewatch_articles: Sequence[Article],
    gamewith_articles: Sequence[Article],
    denfami_articles: Sequence[Article],
    output_dir: Path,
    base_url: str | None,
    built_at: datetime,
    minimum: int = 30,
    deployment_id: str | None = None,
) -> dict[str, int]:
    validate_article_freshness(gamewatch_articles, now=built_at)
    validate_article_freshness(gamewith_articles, now=built_at)
    validate_article_freshness(denfami_articles, now=built_at)

    gamewatch_self = urljoin(base_url, GAMEWATCH_FILENAME) if base_url else None
    gamewith_self = urljoin(base_url, GAMEWITH_FILENAME) if base_url else None
    denfami_self = urljoin(base_url, DENFAMI_FILENAME) if base_url else None
    gamewatch_xml = render_rss(
        "GAME Watch - PCゲーム RSS",
        "https://game.watch.impress.co.jp/category/pc/pc/",
        "GAME WatchのPCゲーム関連記事をまとめた非公式RSSフィード",
        gamewatch_articles,
        gamewatch_self,
        built_at,
    )
    gamewith_xml = render_rss(
        "GameWith - PCゲームニュース RSS",
        "https://gamewith.jp/pc/news",
        "GameWithのPCゲームニュースをまとめた非公式RSSフィード",
        gamewith_articles,
        gamewith_self,
        built_at,
    )
    denfami_xml = render_rss(
        "電ファミニコゲーマー - Steam RSS",
        "https://news.denfaminicogamer.jp/tag/steam",
        "電ファミニコゲーマーのSteam関連記事をまとめた非公式RSSフィード",
        denfami_articles,
        denfami_self,
        built_at,
    )
    gamewatch_count = validate_rss(
        gamewatch_xml,
        expected_host="game.watch.impress.co.jp",
        minimum=minimum,
        maximum=minimum,
    )
    gamewith_count = validate_rss(
        gamewith_xml,
        expected_host="gamewith.jp",
        minimum=minimum,
        maximum=minimum,
    )
    denfami_count = validate_rss(
        denfami_xml,
        expected_host="news.denfaminicogamer.jp",
        minimum=minimum,
        maximum=minimum,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        output_dir / GAMEWATCH_FILENAME: _stage_file(output_dir, gamewatch_xml),
        output_dir / GAMEWITH_FILENAME: _stage_file(output_dir, gamewith_xml),
        output_dir / DENFAMI_FILENAME: _stage_file(output_dir, denfami_xml),
    }
    if deployment_id is not None:
        if not deployment_id.strip() or "\n" in deployment_id or "\r" in deployment_id:
            raise ValueError("deployment_id must be a non-empty single line")
        targets[output_dir / DEPLOYMENT_FILENAME] = _stage_file(
            output_dir,
            f"{deployment_id}\n".encode(),
        )
    _replace_all(targets)
    return {
        "GAME Watch": gamewatch_count,
        "GameWith": gamewith_count,
        "Denfami": denfami_count,
    }
