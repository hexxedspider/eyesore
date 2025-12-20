import json
import os
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class MessageMemory:
    
    def __init__(self, memory_file: str = "message_memory.json", max_memory_items: int = 1000):
        self.memory_file = memory_file
        self.max_memory_items = max_memory_items
        self.memory_data = self._load_memory()
    
    def _load_memory(self) -> Dict:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"Warning: Could not load memory from {self.memory_file}, creating new memory")
        
        return {
            "messages": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "total_messages": 0
            }
        }
    
    def _save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving memory to {self.memory_file}: {e}")
    
    def add_message(self, message: str, user_name: str, channel_id: str, 
                   message_type: str = "user", timestamp: Optional[float] = None):
        if not message or not message.strip():
            return
        
        if timestamp is None:
            timestamp = time.time()
        
        message_entry = {
            "id": f"{timestamp}_{user_name}_{len(self.memory_data['messages'])}",
            "message": message.strip(),
            "user_name": user_name,
            "channel_id": channel_id,
            "type": message_type,
            "timestamp": timestamp,
            "date": datetime.fromtimestamp(timestamp).isoformat()
        }
        
        self.memory_data["messages"].append(message_entry)
        self.memory_data["metadata"]["total_messages"] = len(self.memory_data["messages"])
        
        if len(self.memory_data["messages"]) > self.max_memory_items:
            excess = len(self.memory_data["messages"]) - self.max_memory_items
            self.memory_data["messages"] = self.memory_data["messages"][excess:]
        
        self._save_memory()
    
    def get_recent_messages(self, limit: int = 10, hours: int = 24, 
                          user_name: Optional[str] = None) -> List[Dict]:
        cutoff_time = time.time() - (hours * 3600)
        
        filtered_messages = [
            msg for msg in self.memory_data["messages"]
            if msg["timestamp"] >= cutoff_time and 
            (user_name is None or msg["user_name"] == user_name)
        ]
        
        filtered_messages.sort(key=lambda x: x["timestamp"], reverse=True)
        return filtered_messages[:limit]
    
    def get_memory_context(self, limit: int = 15, hours: int = 48) -> str:
        recent_messages = self.get_recent_messages(limit=limit, hours=hours)
        
        if not recent_messages:
            return ""
        
        context_lines = ["\n=== LEARNED MESSAGES FOR CONTEXT ==="]
        
        for msg in reversed(recent_messages):
            timestamp_str = datetime.fromtimestamp(msg["timestamp"]).strftime("%Y-%m-%d %H:%M")
            context_lines.append(
                f"[{timestamp_str}] {msg['user_name']}: {msg['message']}"
            )
        
        context_lines.append("=== END CONTEXT ===\n")
        
        return "\n".join(context_lines)
    
    def search_messages(self, query: str, user_name: Optional[str] = None) -> List[Dict]:
        query_lower = query.lower()
        matches = []
        
        for msg in self.memory_data["messages"]:
            if query_lower in msg["message"].lower():
                if user_name is None or msg["user_name"] == user_name:
                    matches.append(msg)
        
        return matches
    
    def get_user_stats(self, user_name: str) -> Dict:
        user_messages = [
            msg for msg in self.memory_data["messages"]
            if msg["user_name"] == user_name
        ]
        
        if not user_messages:
            return {
                "user_name": user_name,
                "total_messages": 0,
                "first_message": None,
                "last_message": None
            }
        
        user_messages.sort(key=lambda x: x["timestamp"])
        
        return {
            "user_name": user_name,
            "total_messages": len(user_messages),
            "first_message": user_messages[0]["date"],
            "last_message": user_messages[-1]["date"]
        }
        
        if not user_messages:
            return {
                "user_name": user_name,
                "total_messages": 0,
                "first_message": None,
                "last_message": None
            }
        
        user_messages.sort(key=lambda x: x["timestamp"])
        
        return {
            "user_name": user_name,
            "total_messages": len(user_messages),
            "first_message": user_messages[0]["date"],
            "last_message": user_messages[-1]["date"]
        }
    
    def clear_memory(self):
        self.memory_data = {
            "messages": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "total_messages": 0
            }
        }
        self._save_memory()
    
    def get_memory_size(self) -> int:
        return len(self.memory_data["messages"])
