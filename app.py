from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import sys
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

# Add the ffmpeg directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent / "ffmpeg"))

from music_db import MusicDatabase
from config import Config

app = FastAPI(title="Music Streamer API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = MusicDatabase(Config.DATABASE_PATH)

# Pydantic models
class SongInfo(BaseModel):
    id: int
    file_path: str
    title: str
    duration_seconds: Optional[int]
    last_played: Optional[str]
    play_count: int
    created_at: str

class CurrentStatus(BaseModel):
    current_song: Optional[SongInfo]
    next_song: Optional[SongInfo]
    playlist_position: int
    total_songs: int
    is_streaming: bool

class Stats(BaseModel):
    total_songs: int
    total_plays: int
    most_played: Optional[str]
    most_played_count: int

class UploadResponse(BaseModel):
    message: str
    filename: str
    song_id: int

@app.get("/")
async def root():
    return {"message": "Music Streamer API", "version": "1.0.0"}

@app.get("/api/status", response_model=CurrentStatus)
async def get_status():
    """Get current streaming status"""
    try:
        # Get current and next song
        current_song_data = db.get_current_song()
        next_song_data = db.get_next_song()
        playback_state = db.get_playback_state()
        stats = db.get_stats()
        
        # Convert to SongInfo models
        current_song = None
        if current_song_data:
            current_song = SongInfo(
                id=current_song_data[0],
                file_path=current_song_data[1],
                title=current_song_data[2],
                duration_seconds=current_song_data[3],
                last_played=current_song_data[4],
                play_count=current_song_data[5],
                created_at=current_song_data[6]
            )
        
        next_song = None
        if next_song_data:
            next_song = SongInfo(
                id=next_song_data[0],
                file_path=next_song_data[1],
                title=next_song_data[2],
                duration_seconds=next_song_data[3],
                last_played=next_song_data[4],
                play_count=next_song_data[5],
                created_at=next_song_data[6]
            )
        
        return CurrentStatus(
            current_song=current_song,
            next_song=next_song,
            playlist_position=playback_state[2] if playback_state else 0,
            total_songs=stats['total_songs'],
            is_streaming=bool(playback_state)  # True if record exists, False if no record
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

@app.get("/api/songs", response_model=List[SongInfo])
async def get_all_songs():
    """Get all songs in the database"""
    try:
        songs_data = db.get_all_songs()
        songs = []
        for song_data in songs_data:
            songs.append(SongInfo(
                id=song_data[0],
                file_path=song_data[1],
                title=song_data[2],
                duration_seconds=song_data[3],
                last_played=song_data[4],
                play_count=song_data[5],
                created_at=song_data[6]
            ))
        return songs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting songs: {str(e)}")

@app.get("/api/stats", response_model=Stats)
async def get_stats():
    """Get database statistics"""
    try:
        stats = db.get_stats()
        return Stats(
            total_songs=stats['total_songs'],
            total_plays=stats['total_plays'],
            most_played=stats['most_played'],
            most_played_count=stats['most_played_count']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@app.post("/api/upload", response_model=UploadResponse)
async def upload_music(file: UploadFile = File(...)):
    """Upload a new music file"""
    try:
        # Validate file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in Config.SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported extensions: {Config.SUPPORTED_EXTENSIONS}"
            )
        
        # Create music directory if it doesn't exist
        os.makedirs(Config.MUSIC_DIR, exist_ok=True)
        
        # Generate safe filename
        safe_filename = file.filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
        file_path = os.path.join(Config.MUSIC_DIR, safe_filename)
        
        # Check if file already exists
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            name, ext = os.path.splitext(original_path)
            file_path = f"{name}_{counter}{ext}"
            counter += 1
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Add to database
        song_id = db.add_song(file_path)
        
        return UploadResponse(
            message="File uploaded successfully",
            filename=os.path.basename(file_path),
            song_id=song_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.delete("/api/songs/{song_id}")
async def delete_song(song_id: int):
    """Delete a song from database and filesystem"""
    try:
        # Get song info first
        song_data = db.get_song(song_id)
        if not song_data:
            raise HTTPException(status_code=404, detail="Song not found")
        
        file_path = song_data[1]
        
        # Remove from database
        success = db.remove_song(song_id)
        if not success:
            raise HTTPException(status_code=404, detail="Song not found in database")
        
        # Remove file from filesystem
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return {"message": "Song deleted successfully", "song_id": song_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting song: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
