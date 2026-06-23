from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import AuthRepository, PlaylistRepository
from db.session import get_db
from libs.candidates.generator import CandidateGenerator
from libs.common.enums import PlaylistMode
from libs.common.models import GeneratedPlaylist
from libs.common.models import Track as TrackModel
from libs.ml.inference import ModelNotTrainedError, load_model
from libs.playlist.assembler import assemble
from libs.profile.builder import build_profile
from libs.ranker.ranker import rank
from libs.spotify.client import SpotifyClient
from libs.spotify.fetcher import SpotifyFetcher

router = APIRouter(prefix="/playlist", tags=["playlist"])


class GenerateRequest(BaseModel):
    mode: PlaylistMode
    size: int = 20


class PlaylistSummary(BaseModel):
    id: str
    name: str
    mode: PlaylistMode
    size: int
    created_at: datetime
    spotify_url: str | None = None


class PlaylistTrackDetail(BaseModel):
    track: TrackModel
    rank: int
    final_score: float
    score_breakdown: dict[str, float]


class PlaylistDetail(BaseModel):
    id: str
    name: str
    mode: PlaylistMode
    size: int
    created_at: datetime
    spotify_url: str | None = None
    tracks: list[PlaylistTrackDetail]


class ExportResponse(BaseModel):
    spotify_url: str


@router.post("/generate", response_model=GeneratedPlaylist)
async def generate_playlist(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> GeneratedPlaylist:
    try:
        towers = load_model()
    except ModelNotTrainedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    profile = await build_profile(db)

    auth_repo = AuthRepository(db)
    auth = await auth_repo.get_auth()
    if auth is None or auth.access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client = SpotifyClient(auth.access_token)
    fetcher = SpotifyFetcher(client)

    candidates = await CandidateGenerator().generate(profile, fetcher, db)
    if not candidates:
        raise HTTPException(
            status_code=422,
            detail="No candidates could be generated. Import your library first.",
        )

    ranked = rank(candidates, profile, body.mode, towers, n=body.size)
    return await assemble(ranked, body.mode, body.size, db)


@router.get("/history", response_model=list[PlaylistSummary])
async def get_playlist_history(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PlaylistSummary]:
    repo = PlaylistRepository(db)
    playlists = await repo.get_history()
    return [
        PlaylistSummary(
            id=p.id,
            name=p.name,
            mode=PlaylistMode(p.mode),
            size=p.size,
            created_at=p.created_at,
            spotify_url=p.spotify_url,
        )
        for p in playlists
    ]


@router.get("/{playlist_id}", response_model=PlaylistDetail)
async def get_playlist(
    playlist_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PlaylistDetail:
    repo = PlaylistRepository(db)
    playlist = await repo.get_by_id_with_tracks(playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    tracks = [
        PlaylistTrackDetail(
            track=TrackModel(
                spotify_id=pt.track.spotify_id,
                title=pt.track.title,
                artist_name=pt.track.artist_name or "",
                album_title=pt.track.album_title or "",
                duration_ms=pt.track.duration_ms or 0,
                popularity=pt.track.popularity or 0,
                image_url=pt.track.image_url,
            ),
            rank=pt.rank,
            final_score=pt.final_score or 0.0,
            score_breakdown=pt.score_breakdown or {},
        )
        for pt in sorted(playlist.tracks, key=lambda t: t.rank)
    ]

    return PlaylistDetail(
        id=playlist.id,
        name=playlist.name,
        mode=PlaylistMode(playlist.mode),
        size=playlist.size,
        created_at=playlist.created_at,
        spotify_url=playlist.spotify_url,
        tracks=tracks,
    )


@router.post("/{playlist_id}/export", response_model=ExportResponse)
async def export_playlist(
    playlist_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ExportResponse:
    repo = PlaylistRepository(db)
    playlist = await repo.get_by_id_with_tracks(playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    auth_repo = AuthRepository(db)
    auth = await auth_repo.get_auth()
    if auth is None or auth.access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client = SpotifyClient(auth.access_token)
    fetcher = SpotifyFetcher(client)

    user_id = await fetcher.get_current_user_id()
    spotify_playlist_id = await fetcher.create_playlist(user_id, playlist.name)

    sorted_tracks = sorted(playlist.tracks, key=lambda t: t.rank)
    track_uris = [f"spotify:track:{pt.track.spotify_id}" for pt in sorted_tracks]
    await fetcher.add_tracks_to_playlist(spotify_playlist_id, track_uris)

    spotify_url = f"https://open.spotify.com/playlist/{spotify_playlist_id}"
    await repo.update_export(
        playlist_id,
        spotify_playlist_id=spotify_playlist_id,
        spotify_url=spotify_url,
    )

    return ExportResponse(spotify_url=spotify_url)
