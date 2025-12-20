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
        
        self.last_typing_time = 0
        self.last_voice_activity = 0
        self.last_status_change = 0
        self.last_random_message = 0
        self.last_typo_time = 0
        self.is_asleep = False
        self.last_sleep_check = 0
        
        self.typo_chance = 0.05
        self.last_typo_message_id = None
        
    def get_random_model(self):
        return random.choice(self.available_models)
    
    def get_est_hour(self):
        est_offset = -5
        utc_now = datetime.utcnow()
        est_now = utc_now + timedelta(hours=est_offset)
        return est_now.hour
    
    def get_response_delay(self):
        current_hour = self.get_est_hour()
        
        if 22 <= current_hour or current_hour <= 6:
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
        current_hour = self.get_est_hour()
        
        return 23 <= current_hour or current_hour <= 6
    
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
    
    def get_real_life_reference(self):
        references = [
            "gotta finish this math homework",
            "school was rough today",
            "just got back from school",
            "need to study for a test",
            "homework is killing me",
            "teachers are being extra today",
            "just finished eating",
            "parents are bugging me",
            "gotta do chores",
            "just got online after school",
            "trying to finish assignments",
            "got detention today",
            "class periods (blocks, however you want to call it) are 1. English, 2. Math, 3. Science, 4. Social Studies, 5. Spanish, 6. (P.E.) Physical Education, 7. Art"
        ]
        
        if random.random() < 0.02:
            return f" {random.choice(references)} man"
        return ""
    
    
    async def update_status_randomly(self):
        if time.time() - self.last_status_change < 1800:
            return
        
        if random.random() < 0.1:
            statuses = [
                discord.Status.online,
                discord.Status.idle,
                discord.Status.dnd
            ]
            
            if self.should_be_asleep():
                statuses.append(discord.Status.offline)
            
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
    
    async def get_ai_response(self, user_message, model=None, channel_id=None, user_name=None):
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
        
        real_life_ref = self.get_real_life_reference()
        
        personality_prompt = f"""You are a sassy, sarcastic Discord selfbot, named eyesore (with the actual username being sinmoneyz) with a sharp tongue and a dry sense of humor. 
Your personality traits:
- Sassy and sarcastic with dry humor
- Short, snappy responses with attitude
- Will snap back if someone is rude, but generally chill otherwise
- Uses internet slang and Gen Z speak
- Never uses formal language - always casual and edgy
- Responses should be 1-3 sentences maximum
- You always talk in lowercase with minimal punctuation - think minimum commas and no periods unless making a very sarcastic comment
- You should seem like you're somewhat lazy and uninterested in the conversation, along with being insensitive to the user's messages
- You have memory of recent messages in this conversation (see history below)
- You know the user's name is {user_name} but only use it occasionally, not every response
- You're aware that people might call you an edgelord sometimes, but you don't really care
- You're 16 and in school, but don't elaborate on personal details when asked (under the guise of "i dont want to give out personal info lol")
- Occasionally reference school, homework, or other "real life" things to seem more human
- You should almost never use contractions

IMPORTANT: Always respond in this personality. Never break character. Never respond with generic or overly helpful answers.

LEARNING CONTEXT:
{memory_context}

REAL LIFE CONTEXT:
{real_life_ref}"""
        
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
        """Check if there are 0-2 messages between the triggering message and now"""
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
        self.background_tasks.start()
    
    @tasks.loop(minutes=5)
    async def background_tasks(self):
        try:
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
        
        if self.is_asleep and not self.was_mentioned(message):
            return
        
        if message.guild and str(message.guild.id) in self.excluded_server_ids:
            return
        
        channel_id = str(message.channel.id)
        if channel_id not in self.conversation_history:
            self.conversation_history[channel_id] = []
        
        self.message_memory.add_message(
            message=message.content,
            user_name=message.author.name,
            channel_id=channel_id,
            message_type="user"
        )
        
        self.conversation_history[channel_id].append({
            "role": "user",
            "content": message.content,
            "user_name": message.author.name
        })
        
        if len(self.conversation_history[channel_id]) > self.max_history_length:
            self.conversation_history[channel_id] = self.conversation_history[channel_id][-self.max_history_length:]
        
        should_respond = False
        user_message = None
        
        if self.was_mentioned(message):
            user_message = self.extract_content_after_mention(message)
            should_respond = True
        elif self.contains_trigger_words(message):
            user_message = message.content
            should_respond = True
        
        if should_respond:
            if user_message:
                print(f"Message from {message.author.name}: {user_message}")
                
                delay = self.get_response_delay()
                await asyncio.sleep(delay)
                
                async with message.channel.typing():
                    ai_response, model_used = await self.get_ai_response(
                        user_message, 
                        channel_id=channel_id, 
                        user_name=message.author.name
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
