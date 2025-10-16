import os
import sys
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from tl_fetcher import TelegramMessageExtractor
from discord_bot import TelegramToDiscord

# ========================================
# ログ設定
# ========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
log = logging.getLogger("main")

# ========================================
# 環境変数読み込み
# ========================================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
api_id = int(os.getenv("TG_API_ID", "0"))
api_hash = os.getenv("TG_API_HASH", "")
# session = os.getenv("TG_SESSION", "tg_session")
if os.path.exists("/app/sessions"):
    session = "/app/sessions/let1008_session"   # Docker環境
else:
    # ローカル環境：フォルダを確実に作る
    Path("sessions").mkdir(parents=True, exist_ok=True)
    session = "sessions/let1008_session"
target = os.getenv("target2")
limit = int(os.getenv("TG_LIMIT", "200"))

# ========================================
# グローバル変数
# ========================================
last_processed_id = None  # 最後に処理したメッセージID
is_first_run = True       # 初回実行フラグ

if not (api_id and api_hash and target and DISCORD_TOKEN and CHANNEL_ID):
    raise RuntimeError("TG_API_ID / TG_API_HASH / TELEGRAM_TARGET / DISCORD_TOKEN / CHANNEL_ID を .env に設定してください")


# ========================================
# Telegram メッセージ取得関数
# ========================================
async def get_tg_results(min_id=None):
    """
    Telegramからメッセージを取得
    
    Args:
        min_id: このID以降のメッセージを取得 (Noneの場合は全件取得)
    
    Returns:
        URLを含むメッセージのリスト (古い順にソート済み)
    """
    info_bot = TelegramMessageExtractor(api_id, api_hash, session)
    await info_bot.connect()
    client = info_bot.client
    
    try:
        chat = await client.get_entity(target)
        
        # min_idが指定されている場合: そのID「より後」のメッセージを取得
        if min_id:
            messages = await client.get_messages(chat, limit=limit, min_id=min_id)
        else:
            # min_idがない場合(初回): 全件取得
            messages = await client.get_messages(chat, limit=limit)
        
        log.info(f"🔍 取得したメッセージ総数: {len(messages)}")
        
        results = []
        
        for m in messages:
            log.info(f"🔍 チェック中 Message ID: {m.id}")
            
            text = info_bot._get_text(m)
            # URL抽出 (4つのソースから)
            urls = info_bot.extract_all_urls(m)
            
            log.info(f"🔍 Message ID:{m.id} のURL数: {len(urls)}")
            
            if urls:
                sender = await m.get_sender()
                sender_name = (getattr(sender, "first_name", None) or 
                             getattr(sender, "username", None) or 
                             str(getattr(sender, "id", "不明")))
                
                # 前後のコンテキストメッセージを取得
                context = await info_bot.get_context_messages(
                    chat, 
                    m.id, 
                    before=2,
                    after=5
                )
                
                message_dict = {
                    "id": m.id,
                    "date": m.date,
                    "sender_name": sender_name,
                    "text": text,
                    "url_count": len(urls),
                    "urls": [],
                    "context_before": context['before'],
                    "context_after": context['after']
                }
                
                for url_info in urls:
                    url_dict = {
                        "source_type": url_info.source_type,
                        "url": url_info.url,
                        "text": url_info.text if url_info.text else None,
                        "position": url_info.position if url_info.position else None
                    }
                    message_dict["urls"].append(url_dict)
                
                results.append(message_dict)
        
        # 古い順にソート
        results.sort(key=lambda x: x['date'])
        
        log.info(f"🔍 URLつきメッセージ数: {len(results)}")
        
        return results
        
    except Exception as e:
        log.error(f"❌ Telegram取得エラー: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        await client.disconnect()


# ========================================
# メイン処理
# ========================================
if __name__ == "__main__":
    if not DISCORD_TOKEN or not CHANNEL_ID:
        log.error("❌ DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID not found!")
        sys.exit(1)
    
    # Discord Botインスタンス作成
    discord_bot = TelegramToDiscord(DISCORD_TOKEN, CHANNEL_ID)
    
    # on_readyイベントを上書き
    @discord_bot.bot.event
    async def on_ready():
        global last_processed_id, is_first_run
        
        log.info(f"✅ Ready: {discord_bot.bot.user}")
        
        # 初回のみ実行
        if is_first_run:
            is_first_run = False
            
            channel = discord_bot.bot.get_channel(CHANNEL_ID)
            if channel:
                await channel.send("🤖 Bot is now online! (1分毎に自動チェック)")
            
            # ========== 初回実行 ==========
            log.info("📥 初回: Telegramから過去メッセージを取得中...")
            results = await get_tg_results(min_id=None)
            
            if results:
                log.info(f"✅ {len(results)}件のメッセージを送信します")
                await discord_bot.send_telegram_embeds(results)
                # 最新のIDを記録
                last_processed_id = max(msg['id'] for msg in results)
                log.info(f"📌 最後に処理したID: {last_processed_id}")
            else:
                log.info("ℹ️ URLを含むメッセージが見つかりませんでした")
            
            # ========== 1分毎のチェックループ ==========
            while True:
                await asyncio.sleep(60)  # 60秒待機
                log.info("🔄 1分毎チェック: 新しいメッセージを確認中...")
                
                # 最後に処理したID以降を取得
                results = await get_tg_results(min_id=last_processed_id)
                
                if results:
                    log.info(f"✅ {len(results)}件の新しいメッセージを送信します")
                    await discord_bot.send_telegram_embeds(results)
                    # 最新のIDを更新
                    last_processed_id = max(msg['id'] for msg in results)
                    log.info(f"📌 最後に処理したID更新: {last_processed_id}")
                else:
                    log.info("ℹ️ 新しいURLつきメッセージはありません")
        else:
            # Discord再接続時はスキップ
            log.info("🔄 Discord再接続されました (初回処理はスキップ)")
    
    try:
        discord_bot.run()
    except KeyboardInterrupt:
        log.info("🛑 Bot stopped by user")