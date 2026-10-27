# 武蔵野大学 Webサイトのサイトマップ抽出

DS Programming（2026年10月21日）の個別課題。学籍番号：2622006。

このリポジトリでは収集コードと実行手順を提供する。CSVと取得ログは`python scrape.py`を実行すると生成される。

## 課題の処理

1. `https://www.musashino-u.ac.jp/` にアクセスする。
2. Beautiful SoupでHTMLを解析し、`a`タグの`href`からリンクを取り出す。
3. 未訪問URLをキューに入れ、同一ホストのページを幅優先探索する。
4. 辞書型変数`pages`に`{URL: titleの文字列}`として保存する。
5. 辞書の内容を`csv.writer`で`sitemap.csv`に書き出す。

各HTTPリクエストの前に必ず`time.sleep(1.0)`を実行する。並列アクセスは行わない。
`robots.txt`を確認し、巡回禁止のURLは訪問しない。指定の待機時間が1秒より長い場合はそちらを優先する。

## 実行方法

Python 3.10以降とuvを使用する。リポジトリのディレクトリで実行する。

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python scrape.py
```

途中経過は10件ごとに表示・保存される。ページ数によっては長時間かかる。
Ctrl+Cで中断しても保存され、同じコマンドで再開できる。
最初から取り直す場合は`crawl_state.json`を削除してから実行する。
429または503の場合は巡回を中断するため、時間を置いて再開する。

## 収集範囲とCSV

- 「同一ドメイン」はトップページと同じホスト`www.musashino-u.ac.jp`とする。別サブドメインは含めない。
- トップページからHTML中のリンクを辿って到達できるページが対象。JavaScriptのみで生成されるリンクや未リンクのページは対象外。
- 相対URLは絶対URLへ変換する。`#`以降のフラグメントは除き、クエリ文字列は保持する。
- 画像、PDFなどの既知のファイル形式は除外する。その他はContent-TypeがHTMLの場合のみ保存する。
- 外部ホストへのリダイレクトは辿らない。同一ホストのリダイレクト先はキューへ追加する。
- タイトルがないHTMLは空文字列で保存する。
- `sitemap.csv`は`URL,title`の2列。日本語をExcelでも開きやすいUTF-8 BOM付きで保存する。
- 取得失敗、robots.txtによる除外は`crawl_errors.json`で確認できる。失敗したURLを成功したページとしてCSVへ混ぜない。
- 出力は取得時点の状態。全サイトの存在するURLを保証するものではない。

## ファイル

| ファイル | 内容 |
| --- | --- |
| `scrape.py` | 巡回・辞書への格納・CSV保存 |
| `sitemap.csv` | 実行時に生成される取得結果 |
| `crawl_errors.json` | 実行時に生成される取得失敗・除外の記録 |
| `requirements.txt` | 依存ライブラリ |
| `abe.py` | 元からあった授業用ファイル |

## GitHub Flow

`main`から`feature/sitemap-crawler`を作成し、作業ブランチでコードと説明をコミットする。
作業ブランチをPushし、Pull Requestで変更を確認してから`main`へマージする。
提出時はこのPublicリポジトリのURLをGoogle Classroomに登録する。
