# Google 検索ステータス 履歴ビューア

[Google 検索ステータス ダッシュボード](https://status.search.google.com/?hl=ja) の履歴（ランキング更新・クロール/インデックス/表示の障害）を自動で集めて可視化するツールです。

## 仕組み

- `fetch_status.py` … `incidents.json` を取得（失敗時は Atom フィード）し、`data/` に保存。既存データとマージするので古い履歴も残ります。
- `.github/workflows/search-status.yml` … 6時間ごとに上記を実行し、変化があればコミット。
- `index.html` … 年表・日ごとのカレンダー・一覧に加え、検索の仕組み（クロール／インデックス登録／表示／ランキング）の解説と、順位が落ちたときの切り分け表を載せています。カテゴリ・期間・キーワードで絞り込めます。

## 使い方

1. このブランチを main（デフォルトブランチ）にマージする（スケジュール実行はデフォルトブランチでのみ動きます）。
2. GitHub の Actions タブ →「Update Google Search Status data」→ **Run workflow** で初回取得。
3. 閲覧: リポジトリの Settings → Pages で main ブランチを公開し `…/search-status/` を開く。またはファイルを落として `index.html` をブラウザで直接開いてもOK。

URL に `?product=Ranking` を付けると、そのカテゴリだけを表示した状態で開きます。
