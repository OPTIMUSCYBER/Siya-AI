import sqlite3
import os
from datetime import datetime

class Memory:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Conversation history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Long term memory table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def add_conversation_turn(self, role, content):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO conversation_history (role, content) VALUES (?, ?)',
                (role, content)
            )
            conn.commit()

    def get_recent_conversation(self, limit=12):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT role, content, timestamp FROM conversation_history ORDER BY id DESC LIMIT ?',
                (limit,)
            )
            rows = cursor.fetchall()
            # Return in chronological order
            return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]

    def add_long_term_memory(self, category, content):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO long_term_memory (category, content) VALUES (?, ?)',
                (category, content)
            )
            conn.commit()

    def get_all_long_term_memories(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT category, content, timestamp FROM long_term_memory ORDER BY timestamp ASC'
            )
            rows = cursor.fetchall()
            return [{"category": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
            
    def format_long_term_memory_for_prompt(self):
        memories = self.get_all_long_term_memories()
        if not memories:
            return ""
        
        formatted = "Here is what you know about the user:\n"
        # Group by category
        categorized = {}
        for m in memories:
            cat = m['category']
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(m['content'])
            
        for cat, items in categorized.items():
            formatted += f"- {cat.capitalize()}:\n"
            for item in items:
                formatted += f"  * {item}\n"
        return formatted

if __name__ == "__main__":
    # Test memory system
    db_file = "data/siya_memory_test.db"
    
    # Ensure clean state
    if os.path.exists(db_file):
        os.remove(db_file)
        
    mem = Memory(db_file)
    
    # Test conversation history
    mem.add_conversation_turn("user", "Hello Siya!")
    mem.add_conversation_turn("assistant", "Hello Harsh, how can I help you today?")
    
    history = mem.get_recent_conversation()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    print("Conversation history test passed.")
    
    # Test long term memory
    mem.add_long_term_memory("preferences", "Likes dark mode")
    mem.add_long_term_memory("projects", "Working on an AI assistant")
    mem.add_long_term_memory("preferences", "Prefers concise answers")
    
    ltm = mem.get_all_long_term_memories()
    assert len(ltm) == 3
    print("Long term memory test passed.")
    
    formatted = mem.format_long_term_memory_for_prompt()
    print("\nFormatted LTM:")
    print(formatted)
    
    print("\nMemory module fully working!")
