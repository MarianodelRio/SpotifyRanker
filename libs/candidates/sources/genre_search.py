from __future__ import annotations

from libs.common.enums import CandidateSource
from libs.common.models import Candidate, Track, UserProfile
from libs.spotify.fetcher import SpotifyFetcher

_PER_SOURCE_CAP = 150
_TOP_GENRES_N = 5
_RESULTS_PER_GENRE = 30


async def fetch_genre_search_candidates(
    profile: UserProfile,
    fetcher: SpotifyFetcher,
) -> list[Candidate]:
    if not profile.genre_weights:
        return []

    top_genres = sorted(profile.genre_weights.items(), key=lambda kv: kv[1], reverse=True)[
        :_TOP_GENRES_N
    ]

    candidates: list[Candidate] = []

    for genre, _weight in top_genres:
        if len(candidates) >= _PER_SOURCE_CAP:
            break

        results = await fetcher.search(
            q=f'genre:"{genre}"',
            type="track",
            limit=_RESULTS_PER_GENRE,
        )
        tracks: list[Track] = results  # type: ignore[assignment]

        for track in tracks:
            if len(candidates) >= _PER_SOURCE_CAP:
                break
            if track.spotify_id in profile.known_track_ids:
                continue
            candidates.append(
                Candidate(
                    track=track,
                    source=CandidateSource.genre_search,
                    artist_affinity_score=0.0,
                )
            )

    return candidates
