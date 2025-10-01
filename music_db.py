import sqlite3
import logging
import os
import threading
from datetime import datetime
from typing import List, Optional, Tuple
from auth import hash_password
from config import Config
from schemas import YouTubeSong
import mysql.connector
from mysql.connector import Error


logger = logging.getLogger(__name__)


class MusicDatabaseMysql:

    def __init__(self, db_path: str = os.path.join(Config.BASE_DIR, "data/music_stream.db")):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.connection_config = {
            'host': Config.MYSQL_HOST,
            'database': Config.MYSQL_DB,
            'user': Config.MYSQL_USER,
            'password': Config.MYSQL_PASS,
            'port': Config.MYSQL_PORT,
            'autocommit': False,
            'charset': 'utf8mb4'
        }
    
    def get_connection(self):
        """Get a MySQL connection with error handling"""
        try:
            return mysql.connector.connect(**self.connection_config)
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise
    
    def add_song(self, file_path: str, title: Optional[str] = None, duration: Optional[int] = None) -> int:
        """Add a song to the database, return song ID"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Extract title from filename if not provided
            if not title:
                title = os.path.splitext(os.path.basename(file_path))[0]
            
            cursor.execute('''
                INSERT INTO songs (file_path, title, duration_seconds, source_type)
                VALUES (%s, %s, %s, 'file')
                ON DUPLICATE KEY UPDATE 
                    title = VALUES(title), 
                    duration_seconds = VALUES(duration_seconds),
                    source_type = VALUES(source_type)
            ''', (file_path, title, duration))
            
            song_id = cursor.lastrowid
            conn.commit()
            return song_id
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error adding song: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_song(self, song_id: int) -> Optional[Tuple]:
        """Get song by ID: (id, file_path, title, duration_seconds, last_played, play_count, created_at)"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM songs WHERE id = %s', (song_id,))
            result = cursor.fetchone()
            
            return result
            
        except Error as e:
            logger.exception(f"Error getting song: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_song_by_path(self, file_path: str) -> Optional[Tuple]:
        """Get song by file path"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM songs WHERE file_path = %s', (file_path,))
            result = cursor.fetchone()
            
            return result
            
        except Error as e:
            logger.exception(f"Error getting song by path: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def update_song_played(self, song_id: int):
        """Mark song as played and increment play count"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE songs 
                SET last_played = CURRENT_TIMESTAMP, play_count = play_count + 1
                WHERE id = %s
            ''', (song_id,))
            
            conn.commit()
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error updating song played: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_all_songs(self) -> List[Tuple]:
        """Get all songs ordered by creation date"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM songs where song_play_time = %s ORDER BY created_at', (Config.get_play_time(),))
            results = cursor.fetchall()
            
            return results
            
        except Error as e:
            logger.exception(f"Error getting all songs: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def set_current_song(self, song_id: int, next_song_id: Optional[int] = None, position: int = 0, application_id: int = 1):
        """Set currently playing song and optionally next song"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE playback_state 
                SET current_song_id = %s, next_song_id = %s, playlist_position = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (song_id, next_song_id, position, application_id))
            
            conn.commit()
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error setting current song: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_current_song(self, application_id: int = 1) -> Optional[Tuple]:
        """Get currently playing song info"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.* FROM songs s
                JOIN playback_state p ON s.id = p.current_song_id
                WHERE p.id = %s
            ''', (application_id,))
            result = cursor.fetchone()
            
            return result
            
        except Error as e:
            logger.exception(f"Error getting current song: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_next_song(self, application_id: int = 1) -> Optional[Tuple]:
        """Get next song to be played"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.* FROM songs s
                JOIN playback_state p ON s.id = p.next_song_id
                WHERE p.id = %s
            ''', (application_id,))
            result = cursor.fetchone()
            
            return result
            
        except Error as e:
            logger.exception(f"Error getting next song: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_playback_state(self, application_id: int = 1) -> Optional[Tuple]:
        """Get current playback state: (current_song_id, next_song_id, playlist_position, is_streaming, updated_at)"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT current_song_id, next_song_id, playlist_position, is_streaming, updated_at
                FROM playback_state WHERE id = %s
            ''', (application_id,))
            result = cursor.fetchone()
            
            return result
            
        except Error as e:
            logger.exception(f"Error getting playback state: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def start_streaming(self, application_id: int = 1):
        """Create playback state record when streaming starts"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update existing playback state
            cursor.execute('''
                UPDATE playback_state 
                SET is_streaming = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (application_id,))
            
            conn.commit()
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error starting streaming: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def stop_streaming(self, application_id: int = 1):
        """Remove playback state record when streaming stops"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update the playback state record
            cursor.execute('''
                UPDATE playback_state 
                SET is_streaming = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (application_id,))
            
            conn.commit()
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error stopping streaming: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def is_streaming(self, application_id: int = 1) -> bool:
        """Check if streaming is active"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT is_streaming FROM playback_state WHERE id = %s', (application_id,))
            result = cursor.fetchone()
            
            return bool(result[0]) if result else False
            
        except Error as e:
            logger.exception(f"Error checking streaming status: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def remove_song(self, song_id: int) -> bool:
        """Remove song from database"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM songs WHERE id = %s', (song_id,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            return deleted
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error removing song: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def advance_playback(self, increment_play_count=False, application_id: int = 1):
        """
        Promote next -> current, optionally increment play_count for new current,
        select a new random next (excluding current), and return (current, next).

        Returns:
        (current_row, next_row) where each is a dict: {'id','file_path','title'}
        Either may be None if no song is available.
        """
        conn = None
        try:
            conn = self.get_connection()
            conn.start_transaction(isolation_level='REPEATABLE READ')
            cursor = conn.cursor(dictionary=True)
            
            # Ensure playback_state exists
            cursor.execute(
                "INSERT IGNORE INTO playback_state (id, is_streaming) VALUES (%s, 0)", (application_id,)
            )

            cursor.execute(
                "SELECT current_song_id, next_song_id FROM playback_state WHERE id = %s", (application_id,)
            )
            ps = cursor.fetchone()
            current_id = ps["current_song_id"] if ps else None
            next_id = ps["next_song_id"] if ps else None

            # Case A: first-run, both NULL -> choose two random songs (or one if only one)
            if not current_id and not next_id:
                cursor.execute(
                    "SELECT id, file_path, title, source_type FROM songs WHERE song_play_time = %s and application_id = %s ORDER BY RAND() LIMIT 2",
                    (Config.get_play_time(), application_id)
                )
                rows = cursor.fetchall()
                if not rows:
                    conn.commit()
                    return None, None  # no songs at all

                if len(rows) == 1:
                    cur_row = rows[0]
                    next_row = rows[0]
                else:
                    cur_row = rows[0]
                    next_row = rows[1]

                cursor.execute(
                    "UPDATE playback_state SET current_song_id = %s, next_song_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (cur_row["id"], next_row["id"], application_id),
                )

                cursor.execute(
                    "UPDATE songs SET play_count = play_count + 1, last_played = CURRENT_TIMESTAMP WHERE id = %s",
                    (cur_row["id"],),
                )

            else:
                # Case B: normal promotion
                # If there is no next_id (weird case), pick a random next that isn't current
                if next_id is None:
                    cursor.execute(
                        "SELECT id FROM songs WHERE id != %s AND song_play_time = %s and application_id = %s ORDER BY RAND() LIMIT 1", 
                        (current_id, Config.get_play_time(), application_id)
                    )
                    row = cursor.fetchone()
                    if row:
                        next_id = row["id"]
                        cursor.execute(
                            "UPDATE playback_state SET next_song_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                            (next_id, application_id),
                        )
                    else: 
                        cursor.execute(
                            "UPDATE playback_state SET next_song_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                            (current_id, application_id),
                        )
                        next_id = current_id

                # Promote next -> current
                cursor.execute(
                    "UPDATE playback_state SET current_song_id = next_song_id, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (application_id,)
                )

                # Get the newly promoted current ID
                cursor.execute(
                    "SELECT current_song_id FROM playback_state WHERE id = %s", (application_id,)
                )
                new_current_id = cursor.fetchone()["current_song_id"]

                if increment_play_count:
                    cursor.execute(
                        "UPDATE songs SET play_count = play_count + 1, last_played = CURRENT_TIMESTAMP WHERE id = %s",
                        (new_current_id,),
                    )

                # Pick a new random next (exclude the new current)
                if Config.ONLY_FILES:
                    cursor.execute(
                    "SELECT id FROM songs WHERE id != %s AND source_type = 'file' and application_id = %s ORDER BY RAND() LIMIT 1", (new_current_id,application_id)
                    )
                else:
                    cursor.execute(
                        "SELECT id FROM songs WHERE id != %s AND song_play_time = %s and application_id = %s ORDER BY RAND() LIMIT 1", 
                        (new_current_id, Config.get_play_time(),application_id)
                    )
                row = cursor.fetchone()
                if row:
                    cursor.execute(
                        "UPDATE playback_state SET next_song_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (row["id"], application_id),
                    )
                else:
                    # no other songs, keep next_song_id = new_current_id (or NULL)
                    cursor.execute(
                        "UPDATE playback_state SET next_song_id = current_song_id, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (application_id,)
                    )

            conn.commit()

            # Fetch and return the full current and next rows (file_path/title)
            cursor.execute(
                "SELECT s.id, s.file_path, s.title, s.source_type FROM playback_state ps JOIN songs s ON ps.current_song_id = s.id WHERE ps.id = %s", (application_id,)
            )
            current = cursor.fetchone()
            cursor.execute(
                "SELECT s.id, s.file_path, s.title, s.source_type FROM playback_state ps JOIN songs s ON ps.next_song_id = s.id WHERE ps.id = %s", (application_id,)
            )
            nxt = cursor.fetchone()

            def row_to_dict(r):
                res = {"id": r["id"], "file_path": r["file_path"], "title": r["title"], "source_type": r["source_type"]} if r else None
                print(f"ROW: {res}")
                return res
            
            return row_to_dict(current), row_to_dict(nxt)

        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()

    def cleanup_missing_files(self) -> int:
        """Remove songs from database where files no longer exist"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get all songs
            cursor.execute('SELECT id, file_path FROM songs WHERE source_type = "file"')
            songs = cursor.fetchall()
            
            deleted_count = 0
            for song_id, file_path in songs:
                if not os.path.exists(file_path):
                    cursor.execute('DELETE FROM songs WHERE id = %s', (song_id,))
                    deleted_count += 1
            
            conn.commit()
            return deleted_count
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error cleaning up missing files: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        conn = None
        try:
            conn = self.get_connection()
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
            cursor.execute('SELECT COALESCE(SUM(play_count), 0) FROM songs')
            total_plays = cursor.fetchone()[0]
            
            return {
                'total_songs': total_songs,
                'total_plays': total_plays,
                'most_played': most_played[0] if most_played else None,
                'most_played_count': most_played[1] if most_played else 0
            }
            
        except Error as e:
            logger.exception(f"Error getting stats: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()

    def register_user(self, username, password) -> dict: 
        """Register a new user, return user info"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                        (username, hash_password(password)))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            return {"id": user_id, "username": username}
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error registering user: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_user(self, username):
        """Get user by username"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            return user
            
        except Error as e:
            logger.exception(f"Error getting user: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def save_youtube_link(self, song: YouTubeSong):
        """Save YouTube song link to database"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO songs (file_path, title, source_type, artist, song_play_time)
                VALUES (%s, %s, 'youtube', %s, %s)
            """, (song.url, song.title, song.artist, song.song_play_time))
            conn.commit()
            
            return True
            
        except Error as e:
            if conn:
                conn.rollback()
            logger.exception(f"Error saving YouTube link: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()