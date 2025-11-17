import sqlite3
import psycopg2
import os
import logging
from typing import List, Optional

class BotDatabase:
    def __init__(self, use_postgres: bool = True):
        self.use_postgres = use_postgres and os.getenv('DATABASE_URL')
        if self.use_postgres:
            self.db_url = os.getenv('DATABASE_URL')
        else:
            self.db_path = "bot_database.db"
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            if self.use_postgres:
                conn = psycopg2.connect(self.db_url)
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_verified INTEGER DEFAULT 1,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create user conversations table for Venice AI context
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        role TEXT,
                        content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Create enhanced context memory table for better chat continuity
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS context_memory (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        context_type TEXT,
                        context_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                conn.commit()
                conn.close()
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_verified INTEGER DEFAULT 1,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create user conversations table for Venice AI context
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        role TEXT,
                        content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Create enhanced context memory table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS context_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        context_type TEXT,
                        context_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                conn.commit()
                conn.close()
                
            logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
    
    def add_user(self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None):
        """Add or update user in database"""
        try:
            if self.use_postgres:
                conn = psycopg2.connect(self.db_url)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, is_verified)
                    VALUES (%s, %s, %s, %s, 1)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET username = %s, first_name = %s, last_name = %s, is_verified = 1
                ''', (user_id, username, first_name, last_name, username, first_name, last_name))
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, is_verified)
                    VALUES (?, ?, ?, ?, 1)
                ''', (user_id, username, first_name, last_name))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error adding user: {e}")
            return False
    
    def verify_user(self, user_id: int):
        """Mark user as verified (kept for compatibility)"""
        return True
    
    def is_user_verified(self, user_id: int) -> bool:
        """Check if user is verified - now always returns True"""
        return True
    
    def get_all_users(self) -> List[int]:
        """Get all user IDs for broadcasting"""
        try:
            if self.use_postgres:
                conn = psycopg2.connect(self.db_url)
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users')
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users')
            
            users = [row[0] for row in cursor.fetchall()]
            conn.close()
            return users
        except Exception as e:
            logging.error(f"Error getting users: {e}")
            return []
    
    def add_conversation(self, user_id: int, role: str, content: str):
        """Add conversation entry for Venice AI context"""
        try:
            if self.use_postgres:
                conn = psycopg2.connect(self.db_url)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversations (user_id, role, content)
                    VALUES (%s, %s, %s)
                ''', (user_id, role, content))
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversations (user_id, role, content)
                    VALUES (?, ?, ?)
                ''', (user_id, role, content))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error adding conversation: {e}")
            return False
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[dict]:
        """Get recent conversation history for context"""
        try:
            if self.use_postgres:
                conn = psycopg2.connect(self.db_url)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT role, content FROM conversations 
                    WHERE user_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                ''', (user_id, limit))
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT role, content FROM conversations 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            # Return in correct order (oldest first)
            return [{"role": row[0], "content": row[1]} for row in reversed(results)]
        except Exception as e:
            logging.error(f"Error getting conversation history: {e}")
            return []
    
    def clear_conversation(self, user_id: int):
        """Clear conversation history for a user"""
        try:
            if self.use_postgres:
                conn = psycopg2.connect(self.db_url)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM conversations WHERE user_id = %s', (user_id,))
                cursor.execute('DELETE FROM context_memory WHERE user_id = %s', (user_id,))
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM context_memory WHERE user_id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error clearing conversation: {e}")
            return False
    
    def store_context_memory(self, user_id: int, context_type: str, context_data: str):
        """Store specific context information for better memory"""
        try:
            if self.use_postgres:
                conn = psycopg2.connect(self.db_url)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO context_memory (user_id, context_type, context_data)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, context_type) 
                    DO UPDATE SET context_data = %s, updated_at = CURRENT_TIMESTAMP
                ''', (user_id, context_type, context_data, context_data))
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO context_memory (user_id, context_type, context_data)
                    VALUES (?, ?, ?)
                ''', (user_id, context_type, context_data))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error storing context memory: {e}")
            return False
    
    def get_context_memory(self, user_id: int, context_type: Optional[str] = None) -> List[dict]:
        """Get context memory for better conversation continuity"""
        try:
            if self.use_postgres:
                conn = psycopg2.connect(self.db_url)
                cursor = conn.cursor()
                if context_type:
                    cursor.execute('''
                        SELECT context_type, context_data, updated_at 
                        FROM context_memory 
                        WHERE user_id = %s AND context_type = %s
                        ORDER BY updated_at DESC
                    ''', (user_id, context_type))
                else:
                    cursor.execute('''
                        SELECT context_type, context_data, updated_at 
                        FROM context_memory 
                        WHERE user_id = %s
                        ORDER BY updated_at DESC
                    ''', (user_id,))
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                if context_type:
                    cursor.execute('''
                        SELECT context_type, context_data, updated_at 
                        FROM context_memory 
                        WHERE user_id = ? AND context_type = ?
                        ORDER BY updated_at DESC
                    ''', (user_id, context_type))
                else:
                    cursor.execute('''
                        SELECT context_type, context_data, updated_at 
                        FROM context_memory 
                        WHERE user_id = ?
                        ORDER BY updated_at DESC
                    ''', (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [{"type": row[0], "data": row[1], "updated": row[2]} for row in results]
        except Exception as e:
            logging.error(f"Error getting context memory: {e}")
            return []
    
    def get_enhanced_conversation_context(self, user_id: int) -> dict:
        """Get comprehensive conversation context for AI"""
        conversation_history = self.get_conversation_history(user_id, limit=15)
        context_memory = self.get_context_memory(user_id)
        
        return {
            "conversation_history": conversation_history,
            "context_memory": context_memory,
            "has_context": len(conversation_history) > 0 or len(context_memory) > 0
        }