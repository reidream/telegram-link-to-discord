import os, sys, logging
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
from typing import List, Dict

# ========================================
# ログ設定
# ========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
log = logging.getLogger("bot")

# ========================================
# Bot設定 (環境変数から読み込み)
# ========================================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))


class TelegramToDiscord:
    """
    TelegramメッセージをDiscordに転送するBotクラス
    """
    
    def __init__(self, token, channel_id):
        """
        初期化
        
        Args:
            token: Discord Bot Token
            channel_id: 送信先チャンネルID
        """
        self.TOKEN = token
        self.CHANNEL_ID = channel_id
        
        # Discord Bot設定
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Bot起動時のイベント
        @self.bot.event
        async def on_ready():
            log.info(f"✅ Ready: {self.bot.user}")
            channel = self.bot.get_channel(self.CHANNEL_ID)
            if channel:
                await channel.send("Bot is now online!")
    
    async def send_to_discord(self, text: str):
        """
        Discordにテキストメッセージを送信
        
        Args:
            text: 送信するテキスト
        """
        channel = self.bot.get_channel(self.CHANNEL_ID)
        if channel:
            await channel.send(text)
            log.info(f"✅ Sent: {text[:50]}...")
        else:
            log.error(f"❌ Channel not found")
    
    async def send_telegram_embeds(self, results: List[Dict]):
        """
        TelegramメッセージをDiscordに整形して送信
        
        フォーマット:
        - 区切り線
        - 前のコンテキスト (2件)
        - メインメッセージ (送信者名、テキスト)
        - URL (個別送信でプレビュー表示)
        - 後のコンテキスト (5件)
        - 区切り線
        
        Args:
            results: Telegramメッセージのリスト
        """
        for msg in results:
            try:
                # ========== 日時フォーマット ==========
                date_str = msg['date'].strftime('%m-%d %H:%M')
                
                # ========== チャンネル取得 ==========
                channel = self.bot.get_channel(self.CHANNEL_ID)
                if not channel:
                    continue
                
                # ========== 区切り線(開始) ==========
                await channel.send("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                # ========== 前のコンテキスト ==========
                if msg.get('context_before'):
                    context_msg = "```\n📜 前の会話:\n"
                    for ctx in msg['context_before']:
                        ctx_date = ctx['date'].strftime('%H:%M')
                        context_msg += f"[{ctx_date}] {ctx['sender_name']}: {ctx['text'][:100]}\n"
                    context_msg += "```"
                    await channel.send(context_msg)
                
                # ========== テキストとURLを分離 ==========
                text_without_urls = msg['text']
                for url_info in msg['urls']:
                    text_without_urls = text_without_urls.replace(url_info['url'], '').strip()
                
                # ========== メインメッセージ ==========
                message = f"## 🐾ーーー{date_str}頃の会話ーーーーーーーー\n"
                message += f"**{msg['sender_name']}**: {text_without_urls}" if text_without_urls else f"**{msg['sender_name']}**"
                
                await channel.send(message)
                
                # ========== URLを個別送信 (プレビュー表示) ==========
                for url_info in msg['urls']:
                    await channel.send(url_info['url'])
                    await asyncio.sleep(0.3)  # レート制限対策
                
                # ========== 後のコンテキスト ==========
                if msg.get('context_after'):
                    context_msg = "```\n📝 後の会話:\n"
                    for ctx in msg['context_after']:
                        ctx_date = ctx['date'].strftime('%H:%M')
                        context_msg += f"[{ctx_date}] {ctx['sender_name']}: {ctx['text'][:100]}\n"
                    context_msg += "```"
                    await channel.send(context_msg)
                
                # ========== 区切り線(終了) ==========
                await channel.send("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
                
                log.info(f"✅ 送信完了: Message ID {msg['id']}")
                
                await asyncio.sleep(0.5)  # メッセージ間の待機
                
            except Exception as e:
                log.error(f"❌ 送信エラー: {e}")
    
    def run(self):
        """
        Discord Botを起動
        """
        self.bot.run(self.TOKEN)


# ========================================
# 単体テスト用
# ========================================
if __name__ == "__main__":
    if not TOKEN or not CHANNEL_ID:
        log.error("❌ TOKEN or CHANNEL_ID not found!")
        sys.exit(1)
    
    bot = TelegramToDiscord(TOKEN, CHANNEL_ID)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("🛑 Bot stopped by user")