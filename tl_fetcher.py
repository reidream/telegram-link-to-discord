import os
import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import (
    Message,
    MessageEntityUrl,
    MessageEntityTextUrl,
    ReplyInlineMarkup,
    KeyboardButtonUrl,
    KeyboardButtonUrlAuth,
    MessageMediaWebPage,
)

# ========================================
# データクラス定義
# ========================================

@dataclass
class URLInfo:
    """
    URL情報を格納するデータクラス
    
    Attributes:
        source_type: URL抽出元 (TEXT, ENTITY, BUTTON, PREVIEW)
        url: 抽出されたURL
        text: URLに関連するテキスト (任意)
        position: ボタンの位置情報 (任意)
    """
    source_type: str
    url: str
    text: Optional[str] = None
    position: Optional[Dict[str, int]] = None


@dataclass
class SenderInfo:
    """
    送信者情報
    
    Attributes:
        id: ユーザーID
        username: ユーザー名
        first_name: 名前
    """
    id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None


@dataclass
class MessageMetadata:
    """
    メッセージのメタデータ
    
    Attributes:
        message_id: メッセージID
        date: 送信日時
        chat_id: チャットID
        sender: 送信者情報
        text_preview: テキストプレビュー
        entities: エンティティリスト
        buttons: ボタンリスト
        media: メディア情報
        extracted_urls: 抽出されたURLリスト
    """
    message_id: int
    date: datetime
    chat_id: Optional[int]
    sender: Optional[SenderInfo]
    text_preview: str
    entities: List[Dict[str, Any]]
    buttons: List[Dict[str, Any]]
    media: Optional[Dict[str, Any]]
    extracted_urls: List[URLInfo]


# ========================================
# メインクラス
# ========================================

class TelegramMessageExtractor:
    """
    Telegramメッセージからメタデータとリンク抽出を行うクラス
    
    機能:
    - Telegramへの接続・切断
    - メッセージからのURL抽出 (4つのソースから)
    - コンテキストメッセージ取得 (前後のメッセージ)
    """

    # URL抽出用の正規表現パターン
    url_pattern = re.compile(r'''(?ix)
            \b(
                (?:https?://|www\.|t\.me/|telegram\.me/)?              # 先頭プレフィックス（任意）
                [a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])                  # 第1ラベル
                (?:\.[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9]))+           # .tld(.sub)...
                (?:\:\d+)?                                            # :port（任意）
                (?:/[^\s<>()\[\]{}"'、。】』」>)]*)?                   # パス（空白や括弧・引用は除外）
            )
            ''')

    def __init__(self, api_id: int, api_hash: str, session: str):
        """
        初期化
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            session: セッション名
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session = session
        self.client: Optional[TelegramClient] = None

    # ========================================
    # 接続管理
    # ========================================

    async def connect(self):
        """Telegramクライアントに接続"""
        if not self.client:
            self.client = TelegramClient(self.session, self.api_id, self.api_hash)
        await self.client.start()
        
    async def disconnect(self):
        """Telegramクライアントから切断"""
        if self.client:
            await self.client.disconnect()

    # ========================================
    # ユーティリティメソッド
    # ========================================

    @staticmethod
    def _get_text(message: Message) -> str:
        """
        メッセージからテキストを取得
        
        Args:
            message: Telegramメッセージ
            
        Returns:
            メッセージテキスト (空の場合は空文字列)
        """
        return (getattr(message, "raw_text", None) or 
                getattr(message, "text", None) or "") or ""
        
    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        URLを正規化
        
        処理:
        - 前後の空白を削除
        - 末尾の句読点を削除
        - www.で始まる場合はhttps://を追加
        
        Args:
            url: 正規化するURL
            
        Returns:
            正規化されたURL
        """
        if not url:
            return url
        url = url.strip().rstrip(".,、。)］】>」」」")
        if url.startswith("www."):
            url = "https://" + url
        return url

    # ========================================
    # URL抽出メソッド (4つのソース)
    # ========================================

    def _extract_text_urls(self, text: str) -> List[URLInfo]:
        """
        【ソース1】テキストから正規表現でURLを抽出
        
        Args:
            text: 検索対象のテキスト
            
        Returns:
            抽出されたURLのリスト
        """
        urls = []
        for match in self.url_pattern.findall(text):
            urls.append(URLInfo(source_type="TEXT", url=self._normalize_url(match)))
        return urls
    
    def _extract_entity_urls(self, message: Message) -> List[URLInfo]:
        """
        【ソース2】エンティティからURLを抽出
        
        TelegramのMessageEntityTextUrlとMessageEntityUrlから抽出
        
        Args:
            message: Telegramメッセージ
            
        Returns:
            抽出されたURLのリスト
        """
        urls = []
        text = self._get_text(message)
        
        for entity in (getattr(message, "entities", None) or []):
            if isinstance(entity, MessageEntityTextUrl) and getattr(entity, "url", None):
                fragment = text[entity.offset:entity.offset + entity.length]
                urls.append(URLInfo(
                    source_type="ENTITY",
                    url=self._normalize_url(entity.url),
                    text=fragment
                ))
            elif isinstance(entity, MessageEntityUrl):
                fragment = text[entity.offset:entity.offset + entity.length]
                urls.append(URLInfo(
                    source_type="ENTITY",
                    url=self._normalize_url(fragment),
                    text=fragment
                ))
        return urls
    
    def _extract_button_urls(self, message: Message) -> List[URLInfo]:
        """
        【ソース3】ボタンからURLを抽出
        
        インラインキーボードボタンからURL抽出
        
        Args:
            message: Telegramメッセージ
            
        Returns:
            抽出されたURLのリスト
        """
        urls = []
        reply_markup = getattr(message, "reply_markup", None)
        
        if isinstance(reply_markup, ReplyInlineMarkup):
            for row_idx, row in enumerate(reply_markup.rows or []):
                for col_idx, button in enumerate(getattr(row, "buttons", None) or []):
                    if isinstance(button, (KeyboardButtonUrl, KeyboardButtonUrlAuth)):
                        if url := getattr(button, "url", None):
                            urls.append(URLInfo(
                                source_type="BUTTON",
                                url=self._normalize_url(url),
                                text=getattr(button, "text", ""),
                                position={"row": row_idx, "col": col_idx}
                            ))
        return urls
    
    def _extract_preview_urls(self, message: Message) -> List[URLInfo]:
        """
        【ソース4】プレビューからURLを抽出
        
        リンクプレビュー(WebPage)からURL抽出
        
        Args:
            message: Telegramメッセージ
            
        Returns:
            抽出されたURLのリスト
        """
        urls = []
        media = getattr(message, "media", None)
        
        if isinstance(media, MessageMediaWebPage):
            webpage = getattr(media, "webpage", None)
            if webpage and (url := getattr(webpage, "url", None)):
                urls.append(URLInfo(
                    source_type="PREVIEW",
                    url=self._normalize_url(url),
                    text=getattr(webpage, "title", None)
                ))
        return urls
    
    def extract_all_urls(self, message: Message) -> List[URLInfo]:
        """
        メッセージから全てのURLを抽出（重複排除付き）
        
        4つのソースから抽出:
        1. テキスト (正規表現)
        2. エンティティ (MessageEntityTextUrl, MessageEntityUrl)
        3. ボタン (InlineKeyboard)
        4. プレビュー (WebPage)
        
        Args:
            message: Telegramメッセージ
            
        Returns:
            重複排除されたURLInfoのリスト
        """
        all_urls = []
        all_urls.extend(self._extract_text_urls(self._get_text(message)))
        all_urls.extend(self._extract_entity_urls(message))
        all_urls.extend(self._extract_button_urls(message))
        all_urls.extend(self._extract_preview_urls(message))
        
        # 重複排除
        seen = set()
        unique_urls = []
        for url_info in all_urls:
            if url_info.url not in seen:
                seen.add(url_info.url)
                unique_urls.append(url_info)
        
        return unique_urls

    # ========================================
    # コンテキストメッセージ取得
    # ========================================

    async def get_context_messages(self, chat, message_id: int, before: int = 2, after: int = 5) -> Dict[str, List[Dict]]:
        """
        指定メッセージの前後のコンテキストメッセージを取得
        
        Args:
            chat: チャットエンティティ
            message_id: 基準となるメッセージID
            before: 前に取得するメッセージ数 (デフォルト2)
            after: 後に取得するメッセージ数 (デフォルト5)
            
        Returns:
            {'before': [...], 'after': [...]} 形式の辞書
            各メッセージは {id, date, sender_name, text} を含む
        """
        context = {
            'before': [],
            'after': []
        }
        
        # ========== 前のメッセージを取得 ==========
        before_messages = await self.client.get_messages(
            chat, 
            limit=before * 2,
            offset_id=message_id,
            reverse=False
        )
        
        for m in before_messages:
            if m.id != message_id and len(context['before']) < before:
                text = self._get_text(m)
                if text and len(text) > 6:  # 6文字以上のメッセージのみ
                    sender = await m.get_sender()
                    sender_name = (getattr(sender, "first_name", None) or 
                                 getattr(sender, "username", None) or 
                                 str(getattr(sender, "id", "不明")))
                    context['before'].append({
                        'id': m.id,
                        'date': m.date,
                        'sender_name': sender_name,
                        'text': text
                    })
        
        # 古い順に並び替え
        context['before'].reverse()
        
        # ========== 後のメッセージを取得 ==========
        after_messages = await self.client.get_messages(
            chat,
            limit=(after * 2) + 1,
            min_id=message_id - 1,
            reverse=True
        )
        
        for m in after_messages:
            if m.id != message_id and len(context['after']) < after:
                text = self._get_text(m)
                if text and len(text) > 6:  # 6文字以上のメッセージのみ
                    sender = await m.get_sender()
                    sender_name = (getattr(sender, "first_name", None) or 
                                 getattr(sender, "username", None) or 
                                 str(getattr(sender, "id", "不明")))
                    context['after'].append({
                        'id': m.id,
                        'date': m.date,
                        'sender_name': sender_name,
                        'text': text
                    })
        
        return context


# ========================================
# テスト用main関数
# ========================================

async def main():
    """
    単体テスト用のmain関数
    
    環境変数から設定を読み込み、URLつきメッセージを抽出して表示
    """
    load_dotenv()
    api_id = int(os.getenv("TG_API_ID", "0"))
    api_hash = os.getenv("TG_API_HASH", "")
    session = os.getenv("TG_SESSION", "tg_session")
    target = os.getenv("leidream123")
    limit = int(os.getenv("TG_LIMIT", "20"))

    if not (api_id and api_hash and target):
        raise RuntimeError("TG_API_ID / TG_API_HASH / TELEGRAM_TARGET を .env に設定してください")

    info_bot = TelegramMessageExtractor(api_id, api_hash, session)
    await info_bot.connect()
    client = info_bot.client
    
    try:
        chat = await client.get_entity(target)
        messages = await client.get_messages(chat, limit=limit)
        results = []

        for m in messages:
            text = info_bot._get_text(m)
            
            # URL抽出
            urls = info_bot.extract_all_urls(m)
            if urls:
                sender = await m.get_sender()
                sender_name = (getattr(sender, "first_name", None) or 
                             getattr(sender, "username", None) or 
                             str(getattr(sender, "id", "不明")))
                
                message_dict = {
                    "id": m.id,
                    "date": m.date,
                    "sender_name": sender_name,
                    "text": text,
                    "url_count": len(urls),
                    "urls": []
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
        
        return results
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        await client.disconnect()
        print("\n✓ 完了しました")


if __name__ == "__main__":
    a = asyncio.run(main())
    print(a)