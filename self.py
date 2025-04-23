from telethon import TelegramClient, events, functions, types
import asyncio
import pytz
from datetime import datetime
import logging
import random
import os
from PIL import Image, ImageDraw, ImageFont
import time
import jdatetime
from gtts import gTTS
import textwrap
from io import BytesIO
import requests
import json
import aiohttp
from telethon.tl.types import MessageEntityMention, MessageEntityTextUrl
import sys
import sqlite3
from pathlib import Path

# Configuration
CONFIG = {
    'api_id': 29042268,
    'api_hash': '54a7b377dd4a04a58108639febe2f443',
    'session_name': 'anon',
    'auto_reconnect': True,
    'retry_delay': 30,
    'connection_retries': -1,
    'flood_sleep_threshold': 60,
    'database_path': 'selfbot.db',
    'logs_path': 'logs',
    'media_path': 'media'
}

# Create necessary directories
for path in [CONFIG['logs_path'], CONFIG['media_path']]:
    Path(path).mkdir(exist_ok=True)

# Enhanced Logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{CONFIG['logs_path']}/selfbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database Setup
class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS enemies
                        (user_id TEXT PRIMARY KEY, name TEXT, date_added TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS settings
                        (key TEXT PRIMARY KEY, value TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS saved_messages
                        (id INTEGER PRIMARY KEY, message TEXT, date TEXT)''')
            conn.commit()

    def add_enemy(self, user_id, name):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO enemies VALUES (?, ?, ?)',
                     (str(user_id), name, datetime.now().isoformat()))
            conn.commit()

    def remove_enemy(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM enemies WHERE user_id = ?', (str(user_id),))
            conn.commit()

    def get_enemies(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            return c.execute('SELECT * FROM enemies').fetchall()

    def save_setting(self, key, value):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO settings VALUES (?, ?)',
                     (key, json.dumps(value)))
            conn.commit()

    def get_setting(self, key, default=None):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            result = c.execute('SELECT value FROM settings WHERE key = ?',
                             (key,)).fetchone()
            return json.loads(result[0]) if result else default

# Original insults list
insults = [
    "کیرم تو کص ننت", "مادرجنده", "کص ننت", "کونی", "جنده", "کیری", "بی ناموس", "حرومزاده", "مادر قحبه", "جاکش",
    "کص ننه", "ننه جنده", "مادر کصده", "خارکصه", "کون گشاد", "ننه کیردزد", "مادر به خطا", "توله سگ", "پدر سگ", "حروم لقمه",
    "ننه الکسیس", "کص ننت میجوشه", "کیرم تو کص مادرت", "مادر جنده ی حرومی", "زنا زاده", "مادر خراب", "کصکش", "ننه سگ پرست",
    "مادرتو گاییدم", "خواهرتو گاییدم", "کیر سگ تو کص ننت", "کص مادرت", "کیر خر تو کص ننت", "کص خواهرت", "کون گشاد",
    "سیکتیر کص ننه", "ننه کیر خور", "خارکصده", "مادر جنده", "ننه خیابونی", "کیرم تو دهنت", "کص لیس", "ساک زن",
    "کیرم تو قبر ننت", "بی غیرت", "کص ننه پولی", "کیرم تو کص زنده و مردت", "مادر به خطا", "لاشی", "عوضی", "آشغال",
    "ننه کص طلا", "کیرم تو کص ننت بالا پایین", "کیر قاطر تو کص ننت", "کص ننت خونه خالی", "کیرم تو کص ننت یه دور", 
    "مادر خراب گشاد", "کیرم تو نسل اولت", "کیرم تو کص ننت محکم", "کیر خر تو کص مادرت", "کیرم تو روح مادر جندت",
    "کص ننت سفید برفی", "کیرم تو کص خارت", "کیر سگ تو کص مادرت", "کص ننه کیر خور", "کیرم تو کص زیر خواب",
    "مادر جنده ولگرد", "کیرم تو دهن مادرت", "کص مادرت گشاد", "کیرم تو لای پای مادرت", "کص ننت خیس",
    "کیرم تو کص مادرت بگردش", "کص ننه پاره", "مادر جنده حرفه ای", "کیرم تو کص و کون ننت", "کص ننه تنگ",
    "کیرم تو حلق مادرت", "ننه جنده مفت خور", "کیرم از پهنا تو کص ننت", "کص مادرت بد بو", "کیرم تو همه کس و کارت",
    "مادر کصده سیاه", "کیرم تو کص گشاد مادرت", "کص ننه ساک زن", "کیرم تو کص خاندانت", "مادر جنده خیابونی",
    "کیرم تو کص ننت یه عمر", "ننه جنده کص خور", "کیرم تو نسل و نژادت", "کص مادرت پاره", "کیرم تو شرف مادرت",
    "مادر جنده فراری", "کیرم تو روح مادرت", "کص ننه جندت", "کیرم تو غیرتت", "کص مادر بدکاره",
    "کیرم تو ننه جندت", "مادر کصده لاشی", "کیرم تو وجود مادرت", "کص ننه بی آبرو", "کیرم تو شعور ننت"
]

class EnemySystem:
    def __init__(self, db):
        self.db = db
        self.enemies = set(x[0] for x in db.get_enemies())
        self.enemy_responses = {
            'normal': insults,
            'custom': set(),
            'auto_delete': True,
            'response_count': 3,
            'response_delay': 0.5
        }

    async def add_enemy(self, user_id, client, event):
        try:
            user = await client.get_entity(user_id)
            name = user.first_name or "Unknown"
            self.enemies.add(str(user_id))
            self.db.add_enemy(user_id, name)
            
            response = (
                f"✅ کاربر {name} به لیست دشمن اضافه شد\n"
                f"⚡️ تعداد پاسخ: {self.enemy_responses['response_count']}\n"
                f"🕒 تاخیر: {self.enemy_responses['response_delay']} ثانیه"
            )
            await event.edit(response)
            
        except Exception as e:
            logger.error(f"Error adding enemy: {e}")
            await event.edit("❌ خطا در افزودن دشمن")

    async def remove_enemy(self, user_id, event):
        try:
            self.enemies.discard(str(user_id))
            self.db.remove_enemy(user_id)
            await event.edit("✅ کاربر از لیست دشمن حذف شد")
        except Exception as e:
            logger.error(f"Error removing enemy: {e}")
            await event.edit("❌ خطا در حذف دشمن")

    async def handle_enemy_message(self, event, client):
        if str(event.from_id.user_id) in self.enemies:
            try:
                # Send multiple responses
                used_responses = set()
                for _ in range(self.enemy_responses['response_count']):
                    available_responses = [r for r in self.enemy_responses['normal'] 
                                        if r not in used_responses]
                    if not available_responses:
                        break
                        
                    response = random.choice(available_responses)
                    used_responses.add(response)
                    await event.reply(response)
                    await asyncio.sleep(self.enemy_responses['response_delay'])
                
                # Auto delete if enabled
                if self.enemy_responses['auto_delete']:
                    await event.delete()
                    
            except Exception as e:
                logger.error(f"Error handling enemy message: {e}")

class OptionsSystem:
    def __init__(self, db):
        self.db = db
        self.load_settings()

    def load_settings(self):
        self.options = {
            'auto_delete': self.db.get_setting('auto_delete', True),
            'auto_block': self.db.get_setting('auto_block', False),
            'smart_responses': self.db.get_setting('smart_responses', True),
            'log_messages': self.db.get_setting('log_messages', True),
            'notify_admin': self.db.get_setting('notify_admin', False),
            'safe_mode': self.db.get_setting('safe_mode', True),
            'custom_delay': self.db.get_setting('custom_delay', 0.5),
            'max_responses': self.db.get_setting('max_responses', 3),
            'backup_enabled': self.db.get_setting('backup_enabled', True)
        }
        
        self.fonts = {
            'bold': self.db.get_setting('font_bold', True),
            'italic': self.db.get_setting('font_italic', True),
            'script': self.db.get_setting('font_script', True),
            'double': self.db.get_setting('font_double', True),
            'bubble': self.db.get_setting('font_bubble', True),
            'square': self.db.get_setting('font_square', True)
        }
        
        self.security = {
            'anti_flood': self.db.get_setting('security_flood', True),
            'anti_spam': self.db.get_setting('security_spam', True),
            'anti_forward': self.db.get_setting('security_forward', True),
            'anti_screenshot': self.db.get_setting('security_screenshot', True),
            'anti_copy': self.db.get_setting('security_copy', True)
        }

    def save_settings(self):
        for key, value in self.options.items():
            self.db.save_setting(key, value)
        for key, value in self.fonts.items():
            self.db.save_setting(f'font_{key}', value)
        for key, value in self.security.items():
            self.db.save_setting(f'security_{key}', value)

class MediaProcessor:
    def __init__(self, media_path):
        self.media_path = media_path
        Path(media_path).mkdir(exist_ok=True)

    async def text_to_voice(self, text, lang='fa'):
        try:
            filename = f"{self.media_path}/voice_{int(time.time())}.mp3"
            tts = gTTS(text=text, lang=lang)
            tts.save(filename)
            return filename
        except Exception as e:
            logger.error(f"Voice conversion error: {e}")
            return None

    async def text_to_image(self, text, width=800, height=400):
        try:
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Enhanced font handling
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()

            # Enhanced text wrapping with RTL support
            margin = 20
            offset = 40
            lines = textwrap.wrap(text, width=30)
            
            for line in lines:
                # RTL support
                if any(ord(c) >= 0x590 and ord(c) <= 0x6FF for c in line):
                    line = line[::-1]
                    
                draw.text((margin, offset), line, font=font, fill='black')
                offset += font.getsize(line)[1] + 10

            filename = f"{self.media_path}/image_{int(time.time())}.png"
            img.save(filename, quality=95)
            return filename
        except Exception as e:
            logger.error(f"Image conversion error: {e}")
            return None

    async def text_to_gif(self, text):
        try:
            width = 800
            height = 400
            frames = []
            colors = ['red', 'blue', 'green', 'purple', 'orange']
            
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()

            for color in colors:
                img = Image.new('RGB', (width, height), color='white')
                draw = ImageDraw.Draw(img)
                
                # Center text
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                x = (width - text_width) // 2
                y = (height - text_height) // 2
                
                draw.text((x, y), text, font=font, fill=color)
                frames.append(img)

            filename = f"{self.media_path}/gif_{int(time.time())}.gif"
            frames[0].save(
                filename,
                save_all=True,
                append_images=frames[1:],
                duration=500,
                loop=0
            )
            return filename
        except Exception as e:
            logger.error(f"GIF conversion error: {e}")
            return None

class MessageHandler:
    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.enemy_system = EnemySystem(db)
        self.options = OptionsSystem(db)
        self.media_processor = MediaProcessor(CONFIG['media_path'])
        self.message_queue = asyncio.Queue()
        self.active_tasks = set()

    async def process_message_queue(self):
        while True:
            try:
                message = await self.message_queue.get()
                await self.handle_message(message)
                self.message_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
            await asyncio.sleep(0.1)

    async def handle_message(self, event):
        try:
            # Handle enemy messages
            if event.from_id and str(event.from_id.user_id) in self.enemy_system.enemies:
                await self.enemy_system.handle_enemy_message(event, self.client)
                return

            # Handle commands
            if event.raw_text:
                await self.handle_command(event)

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def handle_command(self, event):
        try:
            command = event.raw_text.lower().split()[0]
            
            if command == "تنظیم_دشمن" and event.is_reply:
                replied = await event.get_reply_message()
                if replied and replied.from_id:
                    await self.enemy_system.add_enemy(replied.from_id.user_id, self.client, event)
                    
            elif command == "حذف_دشمن" and event.is_reply:
                replied = await event.get_reply_message()
                if replied and replied.from_id:
                    await self.enemy_system.remove_enemy(replied.from_id.user_id, event)
                    
            elif command == "تنظیمات_دشمن":
                await self.show_enemy_settings(event)
                
            elif command == "تنظیمات":
                await self.show_settings(event)
                
            # Add more command handlers here
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")

class TimeManager:
    def __init__(self, client):
        self.client = client
        self.time_enabled = True
        self.last_update = 0
        self.update_interval = 60  # seconds

    def to_superscript(self, num):
        superscripts = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
        }
        return ''.join(superscripts.get(n, n) for n in str(num))

    async def update_time(self):
        while True:
            try:
                if self.time_enabled:
                    now = datetime.now(pytz.timezone('Asia/Tehran'))
                    if time.time() - self.last_update >= self.update_interval:
                        hours = self.to_superscript(now.strftime('%H'))
                        minutes = self.to_superscript(now.strftime('%M'))
                        time_string = f"{hours}:{minutes}"
                        await self.client(functions.account.UpdateProfileRequest(last_name=time_string))
                        self.last_update = time.time()
            except Exception as e:
                logger.error(f"Error updating time: {e}")
            await asyncio.sleep(1)

class ActionManager:
    def __init__(self, client):
        self.client = client
        self.actions = {
            'typing': False,
            'online': False,
            'reaction': False
        }

    async def auto_online(self):
        while self.actions['online']:
            try:
                await self.client(functions.account.UpdateStatusRequest(offline=False))
            except Exception as e:
                logger.error(f"Error updating online status: {e}")
            await asyncio.sleep(30)

    async def auto_typing(self, chat):
        while self.actions['typing']:
            try:
                async with self.client.action(chat, 'typing'):
                    await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Error in typing action: {e}")

    async def auto_reaction(self, event):
        if self.actions['reaction']:
            try:
                await event.message.react('👍')
            except Exception as e:
                logger.error(f"Error in reaction: {e}")

class EnhancedTelegramClient(TelegramClient):
    def __init__(self):
        super().__init__(
            CONFIG['session_name'],
            CONFIG['api_id'],
            CONFIG['api_hash'],
            connection_retries=CONFIG['connection_retries'],
            auto_reconnect=CONFIG['auto_reconnect']
        )
        self.db = Database(CONFIG['database_path'])
        self.message_handler = MessageHandler(self, self.db)
        self.time_manager = TimeManager(self)
        self.action_manager = ActionManager(self)
        self.media_processor = MediaProcessor(CONFIG['media_path'])

    async def start(self):
        await super().start()
        
        # Start background tasks
        asyncio.create_task(self.time_manager.update_time())
        asyncio.create_task(self.message_handler.process_message_queue())
        
        # Initialize handlers
        await self.initialize_handlers()

    async def initialize_handlers(self):
        @self.on(events.NewMessage)
        async def on_new_message(event):
            try:
                if not event.message:
                    return

                # Add message to queue for processing
                await self.message_handler.message_queue.put(event)

                # Handle enemy messages immediately
                if event.from_id and str(event.from_id.user_id) in self.message_handler.enemy_system.enemies:
                    await self.message_handler.enemy_system.handle_enemy_message(event, self)

            except Exception as e:
                logger.error(f"Error in message handler: {e}")

        @self.on(events.MessageEdited)
        async def on_edit(event):
            try:
                if event.from_id and str(event.from_id.user_id) in self.message_handler.enemy_system.enemies:
                    await self.message_handler.enemy_system.handle_enemy_message(event, self)
            except Exception as e:
                logger.error(f"Error in edit handler: {e}")

        @self.on(events.MessageDeleted)
        async def on_delete(event):
            try:
                # Handle deleted messages if needed
                pass
            except Exception as e:
                logger.error(f"Error in delete handler: {e}")

        @self.on(events.MessageRead)
        async def on_read(event):
            try:
                # Handle read messages if needed
                pass
            except Exception as e:
                logger.error(f"Error in read handler: {e}")

        @self.on(events.ChatAction)
        async def on_chat_action(event):
            try:
                # Handle chat actions (join, leave, etc.)
                pass
            except Exception as e:
                logger.error(f"Error in chat action handler: {e}")

    async def send_formatted_message(self, event, text, style=None):
        try:
            if style == 'bold':
                text = f"**{text}**"
            elif style == 'italic':
                text = f"_{text}_"
            elif style == 'code':
                text = f"`{text}`"
            elif style == 'strike':
                text = f"~~{text}~~"
            
            await event.respond(text, parse_mode='md')
        except Exception as e:
            logger.error(f"Error sending formatted message: {e}")
            await event.respond(text)  # Fallback to plain text

    async def backup_data(self):
        try:
            # Backup database
            backup_path = f"{CONFIG['logs_path']}/backup_{int(time.time())}.db"
            with open(CONFIG['database_path'], 'rb') as source, open(backup_path, 'wb') as target:
                target.write(source.read())
            
            # Backup settings
            settings_backup = {
                'enemies': list(self.message_handler.enemy_system.enemies),
                'options': self.message_handler.options.options,
                'fonts': self.message_handler.options.fonts,
                'security': self.message_handler.options.security
            }
            
            with open(f"{CONFIG['logs_path']}/settings_backup.json", 'w') as f:
                json.dump(settings_backup, f, indent=4)
                
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False

async def show_help():
    return '''📱 راهنمای ربات:

⚙️ تنظیمات دشمن:
• تنظیم دشمن (ریپلای) - اضافه کردن به لیست دشمن
• حذف دشمن (ریپلای) - حذف از لیست دشمن  
• لیست دشمن - نمایش لیست دشمنان
• تنظیمات دشمن - تنظیمات سیستم دشمن
• تنظیم پاسخ [تعداد] - تعداد پاسخ به دشمن
• تنظیم تاخیر [عدد] - تاخیر بین پاسخ ها

⚡️ اکشن های خودکار:
• typing on/off - تایپینگ دائم
• online on/off - آنلاین دائم 
• reaction on/off - ری‌اکشن خودکار
• time on/off - نمایش ساعت در نام

🔒 قفل‌ها:
• lock screenshot on/off - قفل اسکرین‌شات
• lock forward on/off - قفل فوروارد
• lock copy on/off - قفل کپی

🎨 تبدیل‌ها:
• متن به ویس [متن] - تبدیل متن به ویس
• متن به عکس [متن] - تبدیل متن به عکس
• متن به گیف [متن] - تبدیل متن به گیف
• ذخیره عکس - ذخیره عکس (ریپلای)

⚙️ تنظیمات عمومی:
• تنظیمات - نمایش تنظیمات ربات
• پشتیبان‌گیری - تهیه نسخه پشتیبان
• بازیابی - بازیابی نسخه پشتیبان
• وضعیت - نمایش وضعیت ربات

📝 دستورات متنی:
• bold on/off - فونت ضخیم
• italic on/off - فونت کج
• script on/off - فونت دست‌نویس
• double on/off - فونت دوتایی
• bubble on/off - فونت حبابی
• square on/off - فونت مربعی'''

async def main():
    try:
        print("\n=== Self Bot Starting ===\n")
        
        client = EnhancedTelegramClient()
        await client.start()
        
        if not await client.is_user_authorized():
            print("لطفا شماره تلفن خود را وارد کنید (مثال: +989123456789):")
            phone = input("> ")
            
            try:
                await client.send_code_request(phone)
                print("\nکد تایید ارسال شد. لطفا کد را وارد کنید:")
                code = input("> ")
                await client.sign_in(phone, code)
                
            except Exception as e:
                if "two-steps verification" in str(e).lower():
                    print("\nرمز دو مرحله‌ای فعال است. لطفا رمز را وارد کنید:")
                    password = input("> ")
                    await client.sign_in(password=password)
                else:
                    print(f"\nخطا در ورود: {str(e)}")
                    return

        print("\n✅ با موفقیت وارد شدید!")
        print("💡 برای نمایش راهنما، کلمه 'پنل' را ارسال کنید\n")

        @client.on(events.NewMessage(pattern='پنل'))
        async def help_handler(event):
            if event.from_id.user_id == (await client.get_me()).id:
                help_text = await show_help()
                await event.reply(help_text)

        @client.on(events.NewMessage(pattern=r'^تنظیم پاسخ (\d+)$'))
        async def set_response_count(event):
            if event.from_id.user_id == (await client.get_me()).id:
                count = int(event.pattern_match.group(1))
                client.message_handler.enemy_system.enemy_responses['response_count'] = count
                await event.edit(f"✅ تعداد پاسخ به {count} تغییر کرد")

        @client.on(events.NewMessage(pattern=r'^تنظیم تاخیر (\d+\.?\d*)$'))
        async def set_response_delay(event):
            if event.from_id.user_id == (await client.get_me()).id:
                delay = float(event.pattern_match.group(1))
                client.message_handler.enemy_system.enemy_responses['response_delay'] = delay
                await event.edit(f"✅ تاخیر به {delay} ثانیه تغییر کرد")

        @client.on(events.NewMessage(pattern='پشتیبان‌گیری'))
        async def backup_handler(event):
            if event.from_id.user_id == (await client.get_me()).id:
                if await client.backup_data():
                    await event.edit("✅ پشتیبان‌گیری با موفقیت انجام شد")
                else:
                    await event.edit("❌ خطا در پشتیبان‌گیری")

        @client.on(events.NewMessage(pattern='وضعیت'))
        async def status_handler(event):
            if event.from_id.user_id == (await client.get_me()).id:
                try:
                    start_time = time.time()
                    await client(functions.PingRequest(ping_id=0))
                    ping = round((time.time() - start_time) * 1000, 2)

                    tehran_tz = pytz.timezone('Asia/Tehran')
                    now = datetime.now(tehran_tz)
                    j_date = jdatetime.datetime.fromgregorian(datetime=now)
                    
                    status = f"""
⚡️ پینگ ربات: {ping} ms

📅 تاریخ: {j_date.strftime('%Y/%m/%d')}
⏰ ساعت: {now.strftime('%H:%M:%S')}

💡 وضعیت قابلیت‌ها:
• تایپینگ: {'✅' if client.action_manager.actions['typing'] else '❌'}
• آنلاین: {'✅' if client.action_manager.actions['online'] else '❌'}
• ری‌اکشن: {'✅' if client.action_manager.actions['reaction'] else '❌'}
• ساعت: {'✅' if client.time_manager.time_enabled else '❌'}

📊 آمار:
• تعداد دشمنان: {len(client.message_handler.enemy_system.enemies)}
• تعداد پاسخ: {client.message_handler.enemy_system.enemy_responses['response_count']}
• تاخیر پاسخ: {client.message_handler.enemy_system.enemy_responses['response_delay']} ثانیه
"""
                    await event.edit(status)
                except Exception as e:
                    logger.error(f"Error in status handler: {e}")
                    await event.edit("❌ خطا در نمایش وضعیت")

        await client.run_until_disconnected()

    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        print(f"\nخطای بحرانی: {e}")
    finally:
        print("\nخروج از برنامه...")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nخروج با دستور کاربر...")
    except Exception as e:
        print(f"\nخطای نهایی: {e}")
