# MCProfileMaker
Minecraftのプロフィール画像を生成するスクリプト

## 言語設定

- `/language` の `language` で日本語（`ja`）または英語（`en`）を選択します。
- 設定はユーザーごとにDBへ保存され、再起動後も保持されます。未設定の場合はDiscordの表示言語を使い、日本語以外は英語になります。
- コマンドの説明・引数の説明・言語の選択肢はDiscordの表示言語に合わせて表示されます。コマンド名は `/mcid`、`/build`、`/language` 共通です。
- コマンドの応答、プロフィール編集画面、生成画像のお気に入りサーバー見出しは選択した言語になります。既存メッセージのボタン表示は、カードを再生成すると更新されます。
- テキストは `langs/ja.json` と `langs/en.json` で管理します。

起動時に `user_language` テーブルを自動作成し、コマンドの翻訳をDiscordへ同期します。既存のプロフィールテーブルの変更は不要です。
依存パッケージは `pip install -r requirements.txt` で導入してください（PostgreSQL接続には `asyncpg` が必要です）。

テスト: `python -m unittest discover -s tests -v`（DB・Discord・外部APIへの接続なし）。
