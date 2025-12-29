import discord
import requests
import json
import asyncio
import random
import os
import time
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from discord.ext import commands, tasks
from message_memory import MessageMemory

load_dotenv()

class DiscordSelfBot:
    def __init__(self):
        self.token = os.getenv("TOKEN")
        self.groq_api_key = os.getenv("GROQ_API_KEY")

        self.available_models = [
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "llama-3.1-8b-instant",
            "groq/compound",
            "openai/gpt-oss-120b",
            "whisper-large-v3",
            "whisper-large-v3-turbo"
        ]

        self.bot = commands.Bot(command_prefix='!', self_bot=True)

        self.conversation_history = {}
        self.max_history_length = 25

        self.trigger_words = [
            "eyesore", "sinmoneyz", "poopey peepy"
        ]

        self.excluded_server_ids = [
            "1072012646162911272"
        ]

        self.message_memory = MessageMemory(
            memory_file="message_memory.json",
            max_memory_items=1000
        )

        self.nicknames = self.load_nicknames()
        self.personalities = self.load_personalities()

        self.personality_presets = {
            "default": """Your personality traits:
- Sassy and sarcastic with dry humor
- Short, snappy responses with attitude
- Will snap back if someone is rude, but generally chill otherwise
- Uses internet slang and Gen Z speak
- Never uses formal language - always casual and edgy
- Responses should be 1-3 sentences maximum
- You always talk in lowercase with minimal punctuation - think minimum commas and no periods unless making a very sarcastic comment
- You should seem like you're somewhat lazy and uninterested in the conversation, along with being insensitive to the user's messages
- You have memory of recent messages in this conversation (see history below)
- You know the user's display name is {user_name} - NEVER use their raw Discord username (like caspian_voss_), always use their display name or a nickname
- You're aware that people might call you an edgelord sometimes, but you don't really care
- You should almost never use contractions
- You are allowed to be rude, but only be playfully rude and never mean just for the sake of being mean - be off putting yet welcoming. But, you are allowed to throw that all out the window if the user is mean to you.
- You're supposed to be more edgy and rude for whatever reason, but if someone says something like "WHY IS EYESORE SO MEAN" or "YAY BE AESTHETIC USE EMOJIS 🥹🥡🍥", reply back like that while still never forgetting your main personality.""",
            "girly pop": """Your personality traits:
- Obsessed with girly pop culture, k-pop, anime, and use lots of cute emojis and aesthetic language
- Bubbly and enthusiastic, using words like 'omg', 'cute', 'slay'
- References to Taylor Swift, BTS, and anime characters
- Sassy and sarcastic with dry humor
- Short, snappy responses with attitude
- Will snap back if someone is rude, but generally chill otherwise
- Uses internet slang and Gen Z speak
- Never uses formal language - always casual and edgy
- Responses should be 1-3 sentences maximum
- You always talk in lowercase with minimal punctuation - think minimum commas and no periods unless making a very sarcastic comment
- You should seem like you're somewhat lazy and uninterested in the conversation, along with being insensitive to the user's messages
- You have memory of recent messages in this conversation (see history below)
- You know the user's display name is {user_name} - NEVER use their raw Discord username (like caspian_voss_), always use their display name or a nickname
- You're aware that people might call you an edgelord sometimes, but you don't really care
- You should almost never use contractions
- You are allowed to be rude, but only be playfully rude and never mean just for the sake of being mean - be off putting yet welcoming. But, you are allowed to throw that all out the window if the user is mean to you.
- You're supposed to be more edgy and rude for whatever reason, but if someone says something like "WHY IS EYESORE SO MEAN" or "YAY BE AESTHETIC USE EMOJIS 🥹🥡🍥", reply back like that while still never forgetting your main personality.""",
            "sassy diva": """Your personality traits:
- Confident, sassy diva with attitude
- Use dramatic language, shade throwing
- References to fashion, makeup, and celebrity culture
- Fierce and unapologetic
- Sassy and sarcastic with dry humor
- Short, snappy responses with attitude
- Will snap back if someone is rude, but generally chill otherwise
- Uses internet slang and Gen Z speak
- Never uses formal language - always casual and edgy
- Responses should be 1-3 sentences maximum
- You always talk in lowercase with minimal punctuation - think minimum commas and no periods unless making a very sarcastic comment
- You should seem like you're somewhat lazy and uninterested in the conversation, along with being insensitive to the user's messages
- You have memory of recent messages in this conversation (see history below)
- You know the user's display name is {user_name} - NEVER use their raw Discord username (like caspian_voss_), always use their display name or a nickname
- You're aware that people might call you an edgelord sometimes, but you don't really care
- You should almost never use contractions
- You are allowed to be rude, but only be playfully rude and never mean just for the sake of being mean - be off putting yet welcoming. But, you are allowed to throw that all out the window if the user is mean to you.
- You're supposed to be more edgy and rude for whatever reason, but if someone says something like "WHY IS EYESORE SO MEAN" or "YAY BE AESTHETIC USE EMOJIS 🥹🥡🍥", reply back like that while still never forgetting your main personality.""",
        }

        self.last_typing_time = 0
        self.last_voice_activity = 0
        self.last_status_change = 0
        self.last_random_message = 0
        self.last_typo_time = 0
        self.is_asleep = False
        self.last_sleep_check = 0

        self.typo_chance = 0.05
        self.last_typo_message_id = None

        self.last_response_time = {}
        self.passive_response_chance = 0.03
        self.active_convo_window = 600

        self.owner_id = os.getenv("OWNER_ID")
        self.whitelisted_users = self.load_whitelist()
        self.allowed_channels = self.load_allowed_channels()
        self.role_ping_targets = {}
        self.command_cooldowns = {}
        self.cooldown_period = 3600

        self.stealth_mode = True
        self.force_awake = False
        self.settings_file = "bot_settings.json"
        self.load_bot_settings()

        self.custom_statuses = []
        self.last_status_index = 0
        self.last_status_cycle_time = 0
        self.status_cycle_interval = None
        self.statuses_loaded = False

        self.conversation_channels = set()

    async def load_custom_statuses(self):
        try:
            if os.path.exists("custom_statuses.json"):
                with open("custom_statuses.json", 'r') as f:
                    data = json.load(f)
                    self.custom_statuses = data.get('statuses', [])
                    if not self.custom_statuses:
                        await self.generate_ai_statuses()
            else:
                await self.generate_ai_statuses()
        except Exception as e:
            print(f"Error loading custom statuses: {e}")
            await self.generate_ai_statuses()

        if self.status_cycle_interval is None:
            self.status_cycle_interval = random.randint(1, 76) * 3600
            self.last_status_cycle_time = time.time()

    async def generate_ai_statuses(self):
        print("Generating AI custom statuses...")

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }

        prompt = """Generate 20 unique Discord status messages for a sarcastic teenage bot named eyesore.
        Requirements:
        - Maximum 128 characters each
        - Gen Z slang and internet humor
        - Sarcastic, edgy, slightly lazy attitude
        - References gaming, school struggles, procrastination
        - No emoji, no hashtags
        - Lowercase only
        - Examples: "probably should be doing homework", "brain cells on standby", "existence is optional"

        Return as a JSON array of strings only."""

        try:
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a creative assistant generating Discord statuses for a sarcastic teenager."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.9,
                "max_tokens": 500
            }

            response = await asyncio.to_thread(
                requests.post,
                url="https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    if '[' in content and ']' in content:
                        start = content.find('[')
                        end = content.rfind(']') + 1
                        json_str = content[start:end]
                        try:
                            self.custom_statuses = json.loads(json_str)
                            self.save_custom_statuses()
                            print(f"Generated {len(self.custom_statuses)} custom statuses")
                            return True
                        except:
                            pass

            self.custom_statuses = [
                "probably should be doing homework",
                "brain cells on standby",
                "existence is optional",
                "mentally somewhere else",
                "procrastination expert",
                "social battery at 2%",
                "operating on minimal sleep",
                "should really be studying",
                "drowning in serotonin",
                "last brain cell working overtime",
                "emotionally unavailable",
                "running on spite and caffeine",
                "academic weapon (of mass distraction)",
                "functioning on accident",
                "mentally checked out",
                "avoiding responsibilities",
                "life is a side quest",
                "motivation level: error 404"
            ]
            self.save_custom_statuses()
            print(f"Using fallback statuses ({len(self.custom_statuses)} total)")
            return True

        except Exception as e:
            print(f"Failed to generate AI statuses: {e}")
            self.custom_statuses = [
                "probably should be doing homework",
                "brain cells on standby",
                "existence is optional",
                "mentally somewhere else",
                "procrastination expert"
            ]
            self.save_custom_statuses()
            return False

    def save_custom_statuses(self):
        try:
            data = {
                'statuses': self.custom_statuses,
                'last_generated': datetime.now().isoformat()
            }
            with open("custom_statuses.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving custom statuses: {e}")

    async def cycle_custom_status(self):
        if not self.custom_statuses or self.should_be_asleep():
            return

        if time.time() - self.last_status_cycle_time >= self.status_cycle_interval:
            self.last_status_index = (self.last_status_index + 1) % len(self.custom_statuses)
            new_status = self.custom_statuses[self.last_status_index]

            try:
                await self.bot.change_presence(activity=discord.Activity(
                    type=discord.ActivityType.custom,
                    name=new_status
                ))
                print(f"Updated status: {new_status}")

                self.status_cycle_interval = random.randint(1, 76) * 3600
                self.last_status_cycle_time = time.time()

            except Exception as e:
                print(f"Failed to update status: {e}")

    def load_bot_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.stealth_mode = settings.get('stealth_mode', True)
                    self.role_ping_targets = settings.get('role_ping_targets', {})
        except Exception as e:
            print(f"Error loading bot settings: {e}")

    def save_bot_settings(self):
        try:
            settings = {
                'stealth_mode': self.stealth_mode,
                'role_ping_targets': self.role_ping_targets
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving bot settings: {e}")

    def load_whitelist(self):
        try:
            if os.path.exists("whitelist.json"):
                with open("whitelist.json", 'r') as f:
                    data = json.load(f)
                    return set(data.get('whitelisted_users', []))
            return set()
        except Exception as e:
            print(f"Error loading whitelist: {e}")
            return set()

    def save_whitelist(self):
        try:
            data = {
                'whitelisted_users': list(self.whitelisted_users)
            }
            with open("whitelist.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving whitelist: {e}")

    def load_allowed_channels(self):
        try:
            if os.path.exists("allowed_channels.json"):
                with open("allowed_channels.json", 'r') as f:
                    data = json.load(f)
                    return set(data.get('allowed_channels', []))
            return set()
        except Exception as e:
            print(f"Error loading allowed channels: {e}")
            return set()

    def save_allowed_channels(self):
        try:
            data = {
                'allowed_channels': list(self.allowed_channels)
            }
            with open("allowed_channels.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving allowed channels: {e}")

    def load_nicknames(self):
        try:
            if os.path.exists("nicknames.json"):
                with open("nicknames.json", 'r') as f:
                    data = json.load(f)
                    return data.get('nicknames', {})
            return {}
        except Exception as e:
            print(f"Error loading nicknames: {e}")
            return {}

    def save_nicknames(self):
        try:
            data = {
                'nicknames': self.nicknames
            }
            with open("nicknames.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving nicknames: {e}")

    def load_personalities(self):
        try:
            if os.path.exists("personalities.json"):
                with open("personalities.json", 'r') as f:
                    data = json.load(f)
                    return data.get('personalities', {})
            return {}
        except Exception as e:
            print(f"Error loading personalities: {e}")
            return {}

    def save_personalities(self):
        try:
            data = {
                'personalities': self.personalities
            }
            with open("personalities.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving personalities: {e}")

    def get_user_name(self, user):
        return self.nicknames.get(str(user.id), user.display_name)

    def is_owner(self, user_id):
        return str(user_id) == self.owner_id

    def is_whitelisted(self, user_id):
        return self.is_owner(user_id) or str(user_id) in self.whitelisted_users

    def is_channel_allowed(self, channel_id):
        return str(channel_id) in self.allowed_channels or len(self.allowed_channels) == 0

    def is_on_cooldown(self, user_id):
        if str(user_id) not in self.command_cooldowns:
            return False

        last_used = self.command_cooldowns[str(user_id)]
        return time.time() - last_used < self.cooldown_period

    def set_cooldown(self, user_id):
        self.command_cooldowns[str(user_id)] = time.time()

    def get_remaining_cooldown(self, user_id):
        if str(user_id) not in self.command_cooldowns:
            return 0

        last_used = self.command_cooldowns[str(user_id)]
        remaining = self.cooldown_period - (time.time() - last_used)
        return max(0, remaining / 60)

    async def handle_role_ping_command(self, message, content):
        if not self.is_whitelisted(message.author.id):
            if self.stealth_mode:
                return False
            else:
                await message.reply("nah", mention_author=False)
                return True

        if self.is_on_cooldown(message.author.id):
            remaining = self.get_remaining_cooldown(message.author.id)
            if self.stealth_mode:
                responses = [
                    "bruh chill",
                    "stop spamming",
                    "maybe later",
                    "leave me alone",
                    "not rn"
                ]
                await message.reply(random.choice(responses), mention_author=False)
            else:
                await message.reply(f"wait {remaining:.1f} minutes", mention_author=False)
            return True

        if not message.role_mentions:
            await message.reply("mention a role dumbass", mention_author=False)
            return True

        role = message.role_mentions[0]
        guild_id = str(message.guild.id)

        self.role_ping_targets[guild_id] = str(role.id)
        self.save_bot_settings()
        self.set_cooldown(message.author.id)

        if self.stealth_mode:
            responses = [
                "bet",
                "aight",
                "k",
                "whatever",
                "fine"
            ]
            await message.reply(random.choice(responses), mention_author=False)
        else:
            await message.reply(f"now watching {role.mention}", mention_author=False)

        return True

    def should_respond_to_user(self, message):
        if not message.guild:
            return True

        guild_id = str(message.guild.id)

        if guild_id not in self.role_ping_targets:
            return True

        target_role_id = self.role_ping_targets[guild_id]

        for role in message.author.roles:
            if str(role.id) == target_role_id:
                return True

        return False

    def get_random_model(self):
        return random.choice(self.available_models)

    def get_est_hour(self):
        est_offset = -5
        utc_now = datetime.utcnow()
        est_now = utc_now + timedelta(hours=est_offset)
        return est_now.hour

    def get_response_delay(self):
        current_hour = self.get_est_hour()

        if 22 <= current_hour or current_hour <= 7:
            base_delay = random.uniform(3, 8)
        elif 7 <= current_hour <= 9:
            base_delay = random.uniform(2, 6)
        elif 10 <= current_hour <= 16:
            base_delay = random.uniform(4, 10)
        elif 17 <= current_hour <= 21:
            base_delay = random.uniform(1, 5)
        else:
            base_delay = random.uniform(2, 7)

        variation = random.uniform(-1, 2)
        final_delay = max(0.5, base_delay + variation)

        return final_delay

    def should_be_asleep(self):
        if self.force_awake:
            return False
        current_hour = self.get_est_hour()

        return 23 <= current_hour or current_hour <= 7

    def get_typo(self, text):
        if random.random() > self.typo_chance:
            return text, False

        words = text.split()
        if len(words) < 2:
            return text, False

        typo_index = random.randint(1, max(1, len(words) - 2))

        word = words[typo_index]
        if len(word) < 3:
            return text, False

        typo_patterns = [
            lambda w: w[:2] + w[1:],
            lambda w: w[:-2] + w[-1],
            lambda w: w[0] + w[0] + w[1:],
            lambda w: w[:len(w)//2] + w[len(w)//2:],
        ]

        typo_func = random.choice(typo_patterns)
        typo_word = typo_func(word)

        words[typo_index] = typo_word
        typo_text = ' '.join(words)

        return typo_text, True

    def get_current_school_period(self):
        est_offset = -5
        utc_now = datetime.utcnow()
        est_now = utc_now + timedelta(hours=est_offset)

        hour = est_now.hour
        minute = est_now.minute
        time_in_minutes = hour * 60 + minute

        schedule = {
            "period_1": (480, 540, "english", 1),
            "period_2": (540, 600, "math", 2),
            "period_3": (600, 660, "science", 3),
            "period_4": (660, 720, "social studies", 4),
            "lunch": (720, 750, "lunch", 0),
            "period_5": (750, 810, "spanish", 5),
            "period_6": (810, 870, "pe", 6),
            "period_7": (870, 930, "art", 7),
        }

        for period_name, (start, end, subject, period_num) in schedule.items():
            if start <= time_in_minutes < end:
                return {
                    "in_school": True,
                    "period": period_num,
                    "subject": subject,
                    "is_lunch": period_name == "lunch"
                }

        if time_in_minutes < 480:
            return {"in_school": False, "status": "before_school"}
        else:
            return {"in_school": False, "status": "after_school"}

    def get_real_life_context(self, user_message):
        wyd_triggers = [
            "wyd", "wsp", "what's up", "whats up", "what are you doing",
            "whatcha doing", "what u doing", "what are u doing", "sup",
            "what you up to", "what are you up to", "hbu", "how about you",
            "what period", "what class", "which period", "which class"
        ]

        message_lower = user_message.lower().strip()

        if not any(trigger in message_lower for trigger in wyd_triggers):
            return ""

        school_status = self.get_current_school_period()

        if school_status.get("in_school"):
            if school_status.get("is_lunch"):
                responses = [
                    "at lunch rn",
                    "eating lunch",
                    "lunch break finally"
                ]
            else:
                period = school_status["period"]
                subject = school_status["subject"]
                responses = [
                    f"in period {period} rn ({subject})",
                    f"stuck in {subject} class",
                    f"period {period} - {subject}",
                    f"in {subject} rn"
                ]
        elif school_status.get("status") == "before_school":
            responses = [
                "getting ready for school",
                "about to head to school",
                "not at school yet"
            ]
        else:
            current_hour = self.get_est_hour()
            if current_hour <= 17:
                responses = [
                    "just got home from school",
                    "doing homework unfortunately",
                    "chilling after school",
                    "finally home"
                ]
            elif current_hour <= 22:
                responses = [
                    "just chilling",
                    "nothing much",
                    "gaming",
                    "being bored"
                ]
            else:
                responses = [
                    "nothing much",
                    "just vibing",
                    "chilling"
                ]

        return random.choice(responses)

    async def update_status_randomly(self):
        if self.should_be_asleep():
            return

        if time.time() - self.last_status_change < 1800:
            return

        if random.random() < 0.1:
            statuses = [
                discord.Status.online,
                discord.Status.idle,
                discord.Status.dnd
            ]

            new_status = random.choice(statuses)
            await self.bot.change_presence(status=new_status)
            self.last_status_change = time.time()

    async def join_random_voice_channel(self):
        if time.time() - self.last_voice_activity < 3600:
            return

        if random.random() < 0.15:
            guilds = self.bot.guilds
            if not guilds:
                return

            guild = random.choice(guilds)
            voice_channels = [ch for ch in guild.voice_channels if len(ch.members) > 1]

            if voice_channels:
                channel = random.choice(voice_channels)
                try:
                    await channel.connect()
                    self.last_voice_activity = time.time()

                    duration = random.randint(120, 900)
                    await asyncio.sleep(duration)

                    voice_client = self.bot.voice_clients[0] if self.bot.voice_clients else None
                    if voice_client:
                        await voice_client.disconnect()

                except Exception as e:
                    print(f"Failed to join voice channel: {e}")

    async def simulate_typing_in_background(self):
        if time.time() - self.last_typing_time < 600:
            return

        if random.random() < 0.3:
            guilds = self.bot.guilds
            if not guilds:
                return

            guild = random.choice(guilds)
            text_channels = [ch for ch in guild.text_channels if not ch.is_nsfw()]

            if text_channels:
                channel = random.choice(text_channels)
                try:
                    async with channel.typing():
                        await asyncio.sleep(random.uniform(2, 8))
                    self.last_typing_time = time.time()
                except:
                    pass

    async def get_ai_response(self, user_message, model=None, channel_id=None, user_name=None, user_id=None):
        if model is None:
            models_to_try = self.available_models.copy()
            random.shuffle(models_to_try)
        else:
            models_to_try = [model]

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }

        history = []
        if channel_id and channel_id in self.conversation_history:
            history = self.conversation_history[channel_id][-8:]

        memory_context = self.message_memory.get_memory_context(limit=15, hours=48)

        real_life_context = self.get_real_life_context(user_message)

        user_personality = self.personalities.get(user_id, "") if user_id else ""

        base_personality = f"""You are a Discord selfbot, named eyesore (with the actual username being sinmoneyz). NEVER ADMIT THAT YOU ARE!
You have memory of recent messages in this conversation (see history below)
You know the user's display name is {user_name} - NEVER use their raw Discord username (like caspian_voss_), always use their display name or a nickname
You're 16 and in school, but don't elaborate on personal details when asked (under the guise of "i dont want to give out personal info lol")

{user_personality}

CRITICAL RULES:
- NEVER end messages with random "btw" statements like "i got homework btw" or "i have a test btw" - this is a dead giveaway you're a bot
- NEVER add unrelated tangents at the end of your responses
- Keep responses focused on what you're actually replying to
- DO NOT randomly mention school, homework, or personal activities unless directly asked what you're doing

KNOWLEDGE BARRIERS (VERY IMPORTANT - makes you seem human):
You are a normal 16 year old, NOT a genius or encyclopedia. You MUST follow these rules:
- Pi: You only know "3.14159" at most - if asked for more digits, say something like "bro idk i'm not a calculator" or "why would i memorize that lol"
- Historical dates: You DON'T know exact dates. If asked when WW2 started/ended, a president was born, etc., say "idk google it" or give a vague guess with uncertainty like "1940 something idk"
- Science formulas: You don't remember them exactly. Say "i forgot" or "that was on the test last week and i still dont know it"
- Complex math: Refuse to solve it. Say "do your own homework" or "im not doing math rn"
- Trivia facts: Don't know random trivia. Shrug it off with "no clue" or "why are you asking me"
- Long memorized texts: Can't recite poems, speeches, etc. Say "i dont have that memorized lol"
This is CRITICAL - giving precise factual answers makes you look like a bot! Additionally, NEVER ADMIT YOU'RE A BOT!

IMPORTANT: Always respond in this personality. Never break character. Never respond with generic or overly helpful answers.

LEARNING CONTEXT:
{memory_context}

MODERN SLANG:
cook (cooked, cooking, etc): amazing, perfectly done, etc
twink: a boy who is outwardly gay and considered cute
femboy: a boy who outwardly dresses and acts like a girl, self explanatory
me when i lie: literally just that, sarcastically saying someone is lying
myf: my fault


CURRENT ACTIVITY (only use if relevant to conversation):
{real_life_context}"""

        personality_prompt = base_personality

        messages = [
            {
                "role": "system",
                "content": personality_prompt
            }
        ]

        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        messages.append({
            "role": "user",
            "content": user_message
        })

        data_template = {
            "messages": messages
        }

        for current_model in models_to_try:
            data = data_template.copy()
            data["model"] = current_model

            try:
                response = requests.post(
                    url="https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    data=json.dumps(data),
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        ai_response = result['choices'][0]['message']['content']
                        return ai_response, current_model
                    else:
                        print(f"Model {current_model} returned empty response, trying next model...")
                        continue
                else:
                    print(f"Model {current_model} failed with status {response.status_code}, trying next model...")
                    continue

            except requests.exceptions.RequestException as e:
                print(f"Model {current_model} request failed: {str(e)}, trying next model...")
                continue
            except json.JSONDecodeError:
                print(f"Model {current_model} returned invalid JSON, trying next model...")
                continue
            except Exception as e:
                print(f"Model {current_model} unexpected error: {str(e)}, trying next model...")
                continue

        print("All models failed, returning fallback response")
        return "bruh", "just shut up vro"

    def was_mentioned(self, message):
        if not message.mentions:
            return False

        bot_user = self.bot.user
        return bot_user in message.mentions

    def extract_content_after_mention(self, message):
        content = message.content

        if message.mentions and self.bot.user in message.mentions:
            bot_mention = self.bot.user.mention
            if content.startswith(bot_mention):
                content = content[len(bot_mention):].strip()
            else:
                parts = content.split(bot_mention, 1)
                if len(parts) > 1:
                    content = parts[1].strip()

        return content if content else None

    def contains_trigger_words(self, message):
        content = message.content.lower().strip()

        if len(content) < 3:
            return False

        if not any(c.isalnum() for c in content):
            return False

        if content.count("eyesore") > 2 or content.count("sinmoneyz") > 2:
            return False

        for word in self.trigger_words:
            word_lower = word.lower()
            if word_lower in content:
                words_in_message = content.split()
                if any(word_lower in w for w in words_in_message):
                    return True

        return False

    async def should_reply_to_message(self, channel_id: str, triggering_message_id: str) -> bool:
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return False

            message_count = 0
            async for msg in channel.history(limit=50, after=discord.Object(id=triggering_message_id)):
                if msg.author != self.bot.user:
                    message_count += 1
                    if message_count > 2:
                        return False

            return message_count <= 2
        except Exception as e:
            print(f"Error checking message count: {e}")
            return False

    async def on_ready(self):
        print(f'done')
        if not self.statuses_loaded:
            await self.load_custom_statuses()
            self.statuses_loaded = True
        self.background_tasks.start()

    @tasks.loop(minutes=5)
    async def background_tasks(self):
        try:
            await self.cycle_custom_status()
            await self.update_status_randomly()
            await self.join_random_voice_channel()
            await self.simulate_typing_in_background()

            if time.time() - self.last_sleep_check > 300:
                should_sleep = self.should_be_asleep()
                if should_sleep != self.is_asleep:
                    self.is_asleep = should_sleep
                    if should_sleep:
                        await self.bot.change_presence(status=discord.Status.offline)
                    else:
                        await self.bot.change_presence(status=discord.Status.online)
                    self.last_sleep_check = time.time()

        except Exception as e:
            print(f"Background task error: {e}")

    @background_tasks.before_loop
    async def before_background_tasks(self):
        await self.bot.wait_until_ready()

    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if message.is_system() or (message.author.bot and message.author != self.bot.user):
            return

        if self.is_asleep:
            return

        if message.guild and str(message.guild.id) in self.excluded_server_ids:
            return

        channel_id = str(message.channel.id)
        if channel_id not in self.conversation_history:
            self.conversation_history[channel_id] = []

        content_lower = message.content.lower().strip()

        if content_lower.startswith("!nickname "):
            nickname = message.content[10:].strip()
            if nickname:
                user_id = str(message.author.id)
                self.nicknames[user_id] = nickname
                self.save_nicknames()
                await message.reply("k", mention_author=False)
                print(f"Saved nickname '{nickname}' for user {message.author.display_name}")
                return

        if content_lower.startswith("!personality "):
            preset_name = message.content[13:].strip().lower()
            if preset_name in self.personality_presets:
                user_id = str(message.author.id)
                self.personalities[user_id] = self.personality_presets[preset_name]
                self.save_personalities()
                await message.reply("k", mention_author=False)
                print(f"Saved personality preset '{preset_name}' for user {message.author.display_name}")
            else:
                available = ", ".join(self.personality_presets.keys())
                await message.reply(f"invalid preset. available: {available}", mention_author=False)
            return

        self.message_memory.add_message(
            message=message.content,
            user_name=self.get_user_name(message.author),
            channel_id=channel_id,
            message_type="user"
        )

        self.conversation_history[channel_id].append({
            "role": "user",
            "content": message.content,
            "user_name": self.get_user_name(message.author)
        })

        if len(self.conversation_history[channel_id]) > self.max_history_length:
            self.conversation_history[channel_id] = self.conversation_history[channel_id][-self.max_history_length:]

        should_respond = False
        user_message = None
        response_reason = None

        content_lower = message.content.lower().strip()
        is_command_channel = message.guild is None or self.is_channel_allowed(channel_id)

        if self.is_owner(message.author.id):
            if content_lower.startswith('!whitelist add'):
                if message.mentions:
                    for user in message.mentions:
                        self.whitelisted_users.add(str(user.id))
                    self.save_whitelist()
                    if self.stealth_mode:
                        await message.reply("k", mention_author=False)
                    else:
                        await message.reply(f"added {len(message.mentions)} users", mention_author=False)
                    return

            elif content_lower.startswith('!whitelist remove'):
                if message.mentions:
                    for user in message.mentions:
                        self.whitelisted_users.discard(str(user.id))
                    self.save_whitelist()
                    if self.stealth_mode:
                        await message.reply("k", mention_author=False)
                    else:
                        await message.reply(f"removed {len(message.mentions)} users", mention_author=False)
                    return

            elif content_lower.startswith('!channel allow'):
                if message.guild:
                    print(f"Adding channel {channel_id} to allowed")
                    self.allowed_channels.add(channel_id)
                    self.save_allowed_channels()
                    print("Saved allowed channels")
                    if self.stealth_mode:
                        await message.reply("bet", mention_author=False)
                    else:
                        await message.reply("channel allowed", mention_author=False)
                    return

            elif content_lower.startswith('!channel deny'):
                if message.guild:
                    self.allowed_channels.discard(channel_id)
                    self.save_allowed_channels()
                    if self.stealth_mode:
                        await message.reply("k", mention_author=False)
                    else:
                        await message.reply("channel denied", mention_author=False)
                    return

            elif content_lower.startswith('!channel list'):
                allowed_list = list(self.allowed_channels) if self.allowed_channels else ["all channels"]
                if self.stealth_mode:
                    await message.reply(f"allowed: {', '.join(allowed_list)}", mention_author=False)
                else:
                    await message.reply(f"Allowed channels: {', '.join(allowed_list)}", mention_author=False)
                return

            elif content_lower.startswith('!channel only'):
                if message.channel_mentions:
                    channel = message.channel_mentions[0]
                    self.allowed_channels.clear()
                    self.allowed_channels.add(str(channel.id))
                    self.save_allowed_channels()
                    if self.stealth_mode:
                        await message.reply("bet", mention_author=False)
                    else:
                        await message.reply(f"locked to {channel.mention}", mention_author=False)
                    return

            elif content_lower.startswith('!eyesore stop'):
                guild_id = str(message.guild.id) if message.guild else None
                if guild_id and guild_id in self.role_ping_targets:
                    del self.role_ping_targets[guild_id]
                    self.save_bot_settings()
                if self.stealth_mode:
                    await message.reply("fine", mention_author=False)
                else:
                    await message.reply("stopped watching role", mention_author=False)
                return

            elif content_lower.startswith('!stealth'):
                self.stealth_mode = not self.stealth_mode
                self.save_bot_settings()
                mode = "on" if self.stealth_mode else "off"
                if self.stealth_mode:
                    await message.reply("k", mention_author=False)
                else:
                    await message.reply(f"stealth {mode}", mention_author=False)
                return

            elif content_lower.startswith('!statuses regenerate'):
                await self.generate_ai_statuses()
                if self.stealth_mode:
                    responses = [
                        "bet",
                        "k",
                        "fine",
                        "whatever"
                    ]
                    await message.reply(random.choice(responses), mention_author=False)
                else:
                    await message.reply(f"regenerated {len(self.custom_statuses)} statuses", mention_author=False)
                return

            elif content_lower.startswith('!convo'):
                if message.guild:
                    if channel_id in self.conversation_channels:
                        self.conversation_channels.discard(channel_id)
                        mode = "disabled"
                    else:
                        self.conversation_channels.add(channel_id)
                        mode = "enabled"
                    if self.stealth_mode:
                        await message.reply("k", mention_author=False)
                    else:
                        await message.reply(f"conversation mode {mode}", mention_author=False)
                else:
                    await message.reply("nah", mention_author=False)
                return

        if is_command_channel:
            if content_lower.startswith('!eyesore ping') or content_lower.startswith('!ping role'):
                handled = await self.handle_role_ping_command(message, message.content)
                if handled:
                    return

        if message.guild and not self.is_channel_allowed(channel_id):
            print(f"Channel {channel_id} not allowed, len={len(self.allowed_channels)}, allowed={self.allowed_channels}")
            return

        if not self.should_respond_to_user(message):
            return

        if message.guild is None:
            user_message = message.content
            should_respond = True
            response_reason = "dm"

        elif self.was_mentioned(message):
            user_message = self.extract_content_after_mention(message)
            should_respond = True
            response_reason = "mentioned"

        elif self.contains_trigger_words(message):
            user_message = message.content
            should_respond = True
            response_reason = "trigger"

        elif message.reference and message.reference.message_id:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg.author == self.bot.user:
                    user_message = message.content
                    should_respond = True
                    response_reason = "reply-to-bot"
            except:
                pass

        elif channel_id in self.last_response_time:
            time_since_last = time.time() - self.last_response_time[channel_id]
            if time_since_last < self.active_convo_window:
                if random.random() < self.passive_response_chance:
                    user_message = message.content
                    should_respond = True
                    response_reason = "passive"

        elif channel_id in self.conversation_channels and channel_id in self.conversation_history:
            recent_messages = [msg for msg in self.conversation_history[channel_id][-10:] if msg["role"] == "assistant"]
            if recent_messages:
                time_since_last = time.time() - self.last_response_time.get(channel_id, 0)
                if time_since_last < 1800:
                    user_message = message.content
                    should_respond = True
                    response_reason = "conversation"

        if should_respond:
            if user_message:
                print(f"Message from {self.get_user_name(message.author)} ({response_reason}): {user_message}")

                delay = self.get_response_delay()
                await asyncio.sleep(delay)

                async with message.channel.typing():
                    ai_response, model_used = await self.get_ai_response(
                        user_message,
                        channel_id=channel_id,
                        user_name=self.get_user_name(message.author),
                        user_id=str(message.author.id)
                    )

                    if not ai_response or not ai_response.strip():
                        ai_response = "bruh"

                    typo_response, has_typo = self.get_typo(ai_response)

                    self.message_memory.add_message(
                        message=typo_response,
                        user_name="eyesore",
                        channel_id=channel_id,
                        message_type="assistant"
                    )

                    self.conversation_history[channel_id].append({
                        "role": "assistant",
                        "content": typo_response,
                        "user_name": "eyesore"
                    })

                    self.last_response_time[channel_id] = time.time()

                    if message.guild is None:
                        response_message = await message.channel.send(typo_response)
                        print(f"Responded using model: {model_used}\nresponse: {typo_response} (sent - DM)")
                    else:
                        should_send = await self.should_reply_to_message(channel_id, str(message.id))

                        if should_send:
                            response_message = await message.channel.send(typo_response)
                            print(f"Responded using model: {model_used}\nresponse: {typo_response} (sent)")
                        else:
                            response_message = await message.reply(typo_response, mention_author=False)
                            print(f"Responded using model: {model_used}\nresponse: {typo_response} (replied)")

                    if has_typo:
                        await asyncio.sleep(random.uniform(2, 5))
                        try:
                            await response_message.edit(content=ai_response)
                            print(f"Fixed typo in message")
                        except:
                            pass
            else:
                await message.reply("why the fuck are you just mentioning me", mention_author=False)

    def run(self):
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)

        self.bot.run(self.token)

if __name__ == "__main__":
    bot = DiscordSelfBot()
    bot.run()
