
````markdown
# 🤖 Telegram to Discord Bot

Telegram チャンネルから URL を含むメッセージを自動検知し、Discord に転送する Bot

![Bot Demo](https://pbs.twimg.com/media/Gj0GF9IaEAAInel?format=jpg&name=large)

---

## 📋 できること

- 🔍 Telegram チャンネルを定期監視
- 🔗 URL を含むメッセージを自動検出（4 つの方法で抽出）
- 💬 前後の会話も一緒に転送
- 📢 Discord に見やすく整形して投稿

**デモ・詳細**: [https://x.com/leidream1/status/1978234085639385336](https://x.com/leidream1/status/1978234085639385336)

---

## 🚀 セットアップ

### 1. 環境構築

```bash
conda env create -f environment.yml
conda activate linkbot
```
````

### 2. Telegram API 取得

1. [https://my.telegram.org/apps](https://my.telegram.org/apps) にアクセス
2. 新しいアプリケーションを作成
3. `API ID` と `API Hash` をメモ

### 3. Discord Bot 作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」→ Bot 作成
3. 「Bot」→「Reset Token」で Token 取得
4. **MESSAGE CONTENT INTENT** を ON
5. 「OAuth2」→「URL Generator」
   - Scopes: `bot`
   - Permissions: `Send Messages`, `Embed Links`, `Read Message History`
6. 生成された URL で Bot をサーバーに招待

### 4. チャンネル ID 取得

Discord 設定で「開発者モード」ON → チャンネルを右クリック → 「ID をコピー」

### 5. 環境変数設定

プロジェクトルートに `.env` ファイル作成:

```env
# Telegram
TG_API_ID=12345678
TG_API_HASH=your_api_hash_here
TG_SESSION=tg_session
target2=@channelname
TG_LIMIT=100

# Discord
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=1234567890123456789
```

### 6. .gitignore 作成

```gitignore
.env
*.session
*.session-journal
__pycache__/
```

---

## ▶️ 使い方

```bash
python main.py
```

**初回のみ**: 電話番号と認証コード入力  
**2 回目以降**: 自動起動

**停止**: `Ctrl + C`

---

## ⚙️ カスタマイズ

### チェック間隔変更

`main.py` の 120 行目付近:

```python
await asyncio.sleep(60)  # 秒数を変更
```

**推奨設定:**

- `60` = 1 分（リアルタイム）
- `600` = 10 分（バランス）
- `3600` = 1 時間（可読性重視 ⭐ 推奨）

### 前後の会話数変更

`main.py` の 75 行目付近:

```python
context = await info_bot.get_context_messages(
    chat, m.id,
    before=2,  # 前のメッセージ数
    after=5    # 後のメッセージ数
)
```

---

## ⚠️ 重要な注意

### 「後の会話」が取れない問題

**チェック間隔が短すぎると、URL の後にまだ投稿がない可能性大**

| 間隔      | リアルタイム性 | 後の会話取得率 | おすすめ用途   |
| --------- | -------------- | -------------- | -------------- |
| 1 分      | ★★★★★          | 10%            | 緊急通知       |
| 10 分     | ★★★★☆          | 50%            | 一般利用       |
| 1 時間 ⭐ | ★★☆☆☆          | 90%            | **可読性重視** |

**推奨: 1 時間間隔**

- URL の後に他のユーザーが反応する時間がある
- 会話の流れ全体が把握できる

---

## 🐛 トラブルシューティング

| エラー                           | 解決方法                                               |
| -------------------------------- | ------------------------------------------------------ |
| `DISCORD_BOT_TOKEN not found`    | `.env` ファイルがあるか確認                            |
| `Channel not found`              | Bot がサーバーにいるかチェック ID を再確認             |
| `Telegram authentication failed` | `.session` ファイル削除 → 再実行                       |
| URL が検出されない               | ログで `URL数: 0` 確認 → メッセージに URL があるか確認 |

---

## 🔒 セキュリティ

**絶対に公開しないファイル:**

- `.env`（認証情報）
- `*.session`（Telegram セッション）
- `DISCORD_BOT_TOKEN`（漏洩時は即再発行）

**`.gitignore` に必ず追加してください**

---

## 📤 投稿例

![Discord投稿例](https://pbs.twimg.com/media/Gj0GF9IaEAAInel?format=jpg&name=large)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 前の会話:
[10:30] ユーザーA: これ見た？
[10:31] ユーザーB: まだ

## 🐾ーーー10-15 10:32頃の会話ーーーーーーーー
**ユーザーC**: 面白い記事！

https://example.com/article

📝 後の会話:
[10:33] ユーザーD: ありがとう
[10:34] ユーザーE: 見てみる
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

````markdown
---
## 🐳 Dockerでの利用方法

ローカル実行よりも安定し、依存関係を自動で管理できます。
以下のコマンドを **そのままコピー＆ペーストでOK** です。
---

### 🧩 1️⃣ ビルドと起動

```bash
docker compose up -d --build
```
````

> 🔹 初回のみイメージを自動ビルド
> 🔹 `-d` はバックグラウンド起動（常駐モード）

---

### 🧩 2️⃣ 初回ログイン（Telegram 認証）

```bash
docker compose run --rm -it tg_to_dc_bot python main.py
```

> 電話番号・認証コードを入力してログイン（1 回だけ必要）
> 成功すると `sessions/let1008_session.session` がローカルに保存されます。

---

### 🧩 3️⃣ 常駐起動とログ確認

```bash
docker compose up -d
docker compose logs -f
```

> Bot が自動で起動し、`restart: always` 設定により
> PC 再起動後も自動復帰します。

---

### 🧩 4️⃣ 停止・再起動・削除

```bash
docker compose stop        # 一時停止
docker compose restart     # 再起動
docker compose down        # 停止＋削除（再ビルド時）
```

---

### 📁 必要ファイル構成

```
telegram-_chat_to_discord/
├── main.py
├── tl_fetcher.py
├── discord_bot.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env
└── sessions/   ← Telegramセッションが自動保存される
```

---

### 🔒 注意事項

- `/sessions` フォルダはローカルとコンテナで共有されるため、
  **再ログイン不要・再ビルドしてもセッション維持**

---

> 💡 **まとめ**
>
> - 手軽に試したい → `python main.py`
> - 安定稼働・再起動自動化したい → **Docker Compose で実行**

---



---

## 🔗 参考リンク

- **デモ動画・詳細**: [Twitter/X](https://x.com/leidream1/status/1978234085639385336)
- **Telegram API**: [https://my.telegram.org/apps](https://my.telegram.org/apps)
- **Discord Developer Portal**: [https://discord.com/developers/applications](https://discord.com/developers/applications)

---
