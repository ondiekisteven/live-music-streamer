from pydantic import BaseModel
from typing import Optional

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

class UserRegister(BaseModel):
    username: str
    password: str

