import discord
import requests
import json
import asyncio
import random
import os
from dotenv import load_dotenv
from discord.ext import commands
from message_memory import MessageMemory

# Load environment variables from .env file
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
            "eyesore", "sinmoneyz", "sin", "moneyz", "poopey peepy"
        ]
        
        # Initialize message memory system for learning
        self.message_memory = MessageMemory(
            memory_file="message_memory.json",
            max_memory_items=1000
        )
        
    def get_random_model(self):
        return random.choice(self.available_models)
    
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
        
        # Get learned messages from memory for context
        memory_context = self.message_memory.get_memory_context(limit=15, hours=48)
        
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
- If using punctuation, use it sparingly and only when necessary, and add a space before it; e.g. "y should i care ?"
- You should almost never use contractions
- You have memory of recent messages in this conversation (see history below)
- You know the user's name is {user_name} but only use it occasionally, not every response
- You're aware that people might call you an edgelord sometimes, but you don't really care

IMPORTANT: Always respond in this personality. Never break character. Never respond with generic or overly helpful answers.

LEARNING CONTEXT:
{memory_context}"""
        
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
        """Check if message contains any trigger words - but only respond to meaningful messages"""
        content = message.content.lower().strip()
        
        # Skip if message is too short (likely just spam or single words)
        if len(content) < 3:
            return False
        
        # Skip if message is just whitespace or punctuation
        if not any(c.isalnum() for c in content):
            return False
        
        # Skip if message is just the bot's name repeated
        if content.count("eyesore") > 2 or content.count("sinmoneyz") > 2:
            return False
        
        # Check for actual trigger words in meaningful context (case-insensitive)
        for word in self.trigger_words:
            word_lower = word.lower()
            # Use word boundaries to avoid matching partial words
            if word_lower in content:
                # Make sure it's not just part of a longer word or spam
                words_in_message = content.split()
                if any(word_lower in w for w in words_in_message):
                    return True
        
        return False
    
    async def on_ready(self):
        print(f'done')
    
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        
        # Skip system messages and other bots
        if message.is_system() or (message.author.bot and message.author != self.bot.user):
            return
        
        channel_id = str(message.channel.id)
        if channel_id not in self.conversation_history:
            self.conversation_history[channel_id] = []
        
        # Store the incoming message in memory for learning
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
        
        # Check if bot was mentioned or if message contains trigger words
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
                
                delay = random.randint(1, 5)
                await asyncio.sleep(delay)
                
                async with message.channel.typing():
                    ai_response, model_used = await self.get_ai_response(
                        user_message, 
                        channel_id=channel_id, 
                        user_name=message.author.name
                    )
                    
                    # Fallback if AI response is empty
                    if not ai_response or not ai_response.strip():
                        ai_response = "bruh"
                    
                    # Store the bot's response in memory for learning
                    self.message_memory.add_message(
                        message=ai_response,
                        user_name="eyesore",
                        channel_id=channel_id,
                        message_type="assistant"
                    )
                    
                    self.conversation_history[channel_id].append({
                        "role": "assistant",
                        "content": ai_response,
                        "user_name": "eyesore"
                    })
                    
                    response_text = f"{ai_response}"
                    await message.reply(response_text, mention_author=False)
                    print(f"Responded using model: {model_used}\nresponse: {response_text}")
            else:
                await message.reply("why the fuck are you just mentioning me", mention_author=False)
    
    def run(self):
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)
        
        self.bot.run(self.token)

if __name__ == "__main__":
    bot = DiscordSelfBot()
    bot.run()
