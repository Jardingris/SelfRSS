# SelfRSS

GAME WatchとGameWithのPCゲームカテゴリ、電ファミニコゲーマーのSteamタグから、個人利用向けの非公式RSS 3本を生成してGitHub Pagesで配信する。

- GAME Watch: タイトル、記事URL、公式RSSで対応できる公開日時
- GameWith: タイトル、記事URL、公開日時
- 電ファミニコゲーマー: タイトル、記事URL（日付は並び順と鮮度検証だけに使用）
- 各フィードは新しい順に40件、同一URLを除外
- 記事の概要、本文、画像は複製しない

## 公開フィード

- `https://jardingris.github.io/SelfRSS/gamewatch-pc.xml`
- `https://jardingris.github.io/SelfRSS/gamewith-pc.xml`
- `https://jardingris.github.io/SelfRSS/denfami-steam.xml`

公開ページ: `https://jardingris.github.io/SelfRSS/`

このリポジトリは各配信元の公式サービスではない。記事とサイトの権利は各配信元に帰属する。

## ローカル実行

Python 3.12以上を使う。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.txt
.venv/bin/python make_rss.py --output-dir site --limit 40
```

公開URLをRSSの自己参照URLに入れる場合:

```bash
.venv/bin/python make_rss.py \
  --output-dir site \
  --base-url https://jardingris.github.io/SelfRSS/ \
  --limit 40
```

生成前にrobots.txtを確認し、HTTPエラー、HTML構造の変化、件数不足、重複URL、古すぎる記事、壊れたXMLを検出した場合は失敗する。3本とも検証を通るまで既存XMLは置き換えない。

## テスト

通常のテストは外部サイトへ接続しない。

```bash
.venv/bin/python -m unittest discover -s tests -v
```

実サイトから各40件を取得し、生成XMLの先頭記事まで比較するlive test:

```bash
SELFRSS_LIVE=1 .venv/bin/python -m unittest tests.test_live -v
```

公開後のHTTPレスポンス、Content-Type、XML、40件ちょうど、記事URLホストを確認する:

```bash
.venv/bin/python verify_public.py \
  --base-url https://jardingris.github.io/SelfRSS/ \
  --minimum 40
```

## GitHub ActionsとPages

`.github/workflows/update-rss.yml` は日本時間の毎時15分・45分（30分間隔）と手動実行で動く。

1. unit test
2. 実サイトから40件ずつ取得し、RSSを生成・検証
3. `site/` をGitHub Pagesへデプロイ
4. 公開URLを再取得し、40件とrun固有のdeployment markerを検証

生成XMLはコミットせず、ActionsのPages artifactとして配信する。パスワード、API token、Feedly認証情報は使わない。

公開リポジトリで60日間活動がない場合、GitHubはscheduled workflowを自動停止することがある。その場合はActions画面からworkflowを有効化し、`Run workflow` で手動実行する。

## FeedlyとNetNewsWire

Feedlyの `Follow Sources` に上記XML URLを1本ずつ入力してフォローする。NetNewsWire側で同じFeedlyアカウントを追加すると購読が同期される。FeedlyやNetNewsWireの認証情報はこのリポジトリへ保存しない。

## 構成

- `make_rss.py`: 生成CLI
- `verify_public.py`: デプロイ後の公開検証CLI
- `selfrss/gamewatch.py`: GAME Watch抽出・ページ送り・公式RSS日時の統合
- `selfrss/gamewith.py`: GameWith抽出・ページ送り
- `selfrss/denfami.py`: 電ファミニコゲーマーSteamタグ抽出・ページ送り
- `selfrss/http.py`: timeout、retry、User-Agent、robots.txt確認
- `selfrss/rss.py`: RSS 2.0生成
- `selfrss/validation.py`: 記事とXMLの安全検証
- `site/index.html`: Pagesの案内ページ
- `tests/`: unit testと明示実行のlive test

## トラブルシュート

- `card is missing` / `container count`: 配信元のHTML構造が変わった可能性がある。抽出条件を確認する。
- `below minimum`: 取得件数が40件未満。ページ送り、配信元の掲載数、アクセス状況を確認する。
- `robots.txt disallows`: 自動取得を続行せず、配信元の方針を確認する。
- `latest article is older`: URLや日時抽出が現在のページと合っているか確認する。
- 公開検証の404: Pagesの反映待ちか、repositoryのPages設定とworkflow runを確認する。

## 取得元

- [GAME Watch PCゲーム](https://game.watch.impress.co.jp/category/pcgame/)
- [GameWith PCゲーム](https://gamewith.jp/pc/)
- [電ファミニコゲーマー Steam](https://news.denfaminicogamer.jp/tag/steam)
