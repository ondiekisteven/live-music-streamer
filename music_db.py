import sqlite3
import os
import threading
from datetime import datetime
from typing import List, Optional, Tuple

class MusicDatabase:
    """SQLite database helper for music streaming application"""
    
    def __init__(self, db_path: str = "data/music_stream.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Songs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    title TEXT,
                    duration_seconds INTEGER,
                    last_played TIMESTAMP,
                    play_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Playback state table (singleton)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS playback_state (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    current_song_id INTEGER,
                    next_song_id INTEGER,
                    playlist_position INTEGER DEFAULT 0,
                    is_streaming BOOLEAN DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (current_song_id) REFERENCES songs (id),
                    FOREIGN KEY (next_song_id) REFERENCES songs (id),
                    CHECK (id = 1)
                )
            ''')
            
            # Add is_streaming column if it doesn't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE playback_state ADD COLUMN is_streaming BOOLEAN DEFAULT 0')
            except sqlite3.OperationalError:
                # Column already exists, ignore
                pass
            
            # Don't create default playback_state record - it will be created when streaming starts
            
            conn.commit()
            conn.close()
    
    def add_song(self, file_path: str, title: Optional[str] = None, duration: Optional[int] = None) -> int:
        """Add a song to the database, return song ID"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract title from filename if not provided
            if not title:
                title = os.path.splitext(os.path.basename(file_path))[0]
            
            cursor.execute('''
                INSERT OR REPLACE INTO songs (file_path, title, duration_seconds)
                VALUES (?, ?, ?)
            ''', (file_path, title, duration))
            
            song_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return song_id
    
    def get_song(self, song_id: int) -> Optional[Tuple]:
        """Get song by ID: (id, file_path, title, duration_seconds, last_played, play_count, created_at)"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM songs WHERE id = ?', (song_id,))
            result = cursor.fetchone()
            
            conn.close()
            return result
    
    def get_song_by_path(self, file_path: str) -> Optional[Tuple]:
        """Get song by file path"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM songs WHERE file_path = ?', (file_path,))
            result = cursor.fetchone()
            
            conn.close()
            return result
    
    def update_song_played(self, song_id: int):
        """Mark song as played and increment play count"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE songs 
                SET last_played = CURRENT_TIMESTAMP, play_count = play_count + 1
                WHERE id = ?
            ''', (song_id,))
            
            conn.commit()
            conn.close()
    
    def get_all_songs(self) -> List[Tuple]:
        """Get all songs ordered by creation date"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM songs ORDER BY created_at')
            results = cursor.fetchall()
            
            conn.close()
            return results
    
    def set_current_song(self, song_id: int, next_song_id: Optional[int] = None, position: int = 0):
        """Set currently playing song and optionally next song"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE playback_state 
                SET current_song_id = ?, next_song_id = ?, playlist_position = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (song_id, next_song_id, position))
            
            conn.commit()
            conn.close()
    
    def get_current_song(self) -> Optional[Tuple]:
        """Get currently playing song info"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.* FROM songs s
                JOIN playback_state p ON s.id = p.current_song_id
                WHERE p.id = 1
            ''')
            result = cursor.fetchone()
            
            conn.close()
            return result
    
    def get_next_song(self) -> Optional[Tuple]:
        """Get next song to be played"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.* FROM songs s
                JOIN playback_state p ON s.id = p.next_song_id
                WHERE p.id = 1
            ''')
            result = cursor.fetchone()
            
            conn.close()
            return result
    
    def get_playback_state(self) -> Optional[Tuple]:
        """Get current playback state: (current_song_id, next_song_id, playlist_position, is_streaming, updated_at)"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT current_song_id, next_song_id, playlist_position, is_streaming, updated_at
                FROM playback_state WHERE id = 1
            ''')
            result = cursor.fetchone()
            
            conn.close()
            return result
    
    def start_streaming(self):
        """Create playback state record when streaming starts"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Remove any existing playback state
            cursor.execute('DELETE FROM playback_state')
            
            # Create new playback state record
            cursor.execute('''
                INSERT INTO playback_state (is_streaming, updated_at)
                VALUES (1, CURRENT_TIMESTAMP)
            ''')
            
            conn.commit()
            conn.close()
    
    def stop_streaming(self):
        """Remove playback state record when streaming stops"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Remove the playback state record completely
            cursor.execute('DELETE FROM playback_state')
            
            conn.commit()
            conn.close()
    
    def is_streaming(self) -> bool:
        """Check if streaming is active by checking if playback_state record exists"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM playback_state')
            result = cursor.fetchone()
            
            conn.close()
            return bool(result[0]) if result else False
    
    def remove_song(self, song_id: int) -> bool:
        """Remove song from database"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM songs WHERE id = ?', (song_id,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            return deleted
    
    def cleanup_missing_files(self) -> int:
        """Remove songs from database where files no longer exist"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all songs
            cursor.execute('SELECT id, file_path FROM songs')
            songs = cursor.fetchall()
            
            deleted_count = 0
            for song_id, file_path in songs:
                if not os.path.exists(file_path):
                    cursor.execute('DELETE FROM songs WHERE id = ?', (song_id,))
                    deleted_count += 1
            
            conn.commit()
            conn.close()
            return deleted_count
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total songs
            cursor.execute('SELECT COUNT(*) FROM songs')
            total_songs = cursor.fetchone()[0]
            
            # Most played song
            cursor.execute('''
                SELECT title, play_count FROM songs 
                ORDER BY play_count DESC LIMIT 1
            ''')
            most_played = cursor.fetchone()
            
            # Total play count
            cursor.execute('SELECT SUM(play_count) FROM songs')
            total_plays = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_songs': total_songs,
                'total_plays': total_plays,
                'most_played': most_played[0] if most_played else None,
                'most_played_count': most_played[1] if most_played else 0
            }
