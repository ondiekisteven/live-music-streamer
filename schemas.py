from pydantic import BaseModel
from typing import List, Optional

# Pydantic models
class SongInfo(BaseModel):
    id: int
    file_path: str
    title: str
    duration_seconds: Optional[int]
    last_played: Optional[str]
    play_count: int
    created_at: str

# Pydantic models
class SongInfoResp(BaseModel):
    id: int
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

class FileUploadResult(BaseModel):
    filename: str
    song_id: int
    status: str
    error: str = None

class MultipleUploadResponse(BaseModel):
    message: str
    total_files: int
    successful_uploads: int
    failed_uploads: int
    results: List[FileUploadResult]

class UserRegister(BaseModel):
    username: str
    password: str

class YouTubeSong(BaseModel):
    url: str
    title: str
    artist: str | None = None
    song_play_time: str | None = None
