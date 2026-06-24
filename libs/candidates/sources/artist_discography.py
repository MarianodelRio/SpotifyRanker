from __future__ import annotations

from libs.common.enums import CandidateSource
from libs.common.models import Candidate, UserProfile
from libs.spotify.fetcher import SpotifyFetcher

_PER_SOURCE_CAP = 150
_TOP_ARTISTS_N = 10
_SEARCH_LIMIT = 10


async def fetch_artist_discography_candidates(
    profile: UserProfile,
    fetcher: SpotifyFetcher,
    artist_names: dict[str, str],
) -> list[Candidate]:
    if not profile.artist_affinities:
        return []

    top_artists = sorted(profile.artist_affinities.items(), key=lambda kv: kv[1], reverse=True)[
        :_TOP_ARTISTS_N
    ]

    candidates: list[Candidate] = []

    for artist_id, affinity in top_artists:
        if len(candidates) >= _PER_SOURCE_CAP:
            break

        name = artist_names.get(artist_id)
        if not name:
            continue

        tracks = await fetcher.search(q=name, type="track", limit=_SEARCH_LIMIT)
        for track in tracks:
            if len(candidates) >= _PER_SOURCE_CAP:
                break
            if track.spotify_id in profile.known_track_ids:
                continue
            candidates.append(
                Candidate(
                    track=track,
                    source=CandidateSource.artist_discography,
                    artist_affinity_score=affinity,
                )
            )

    return candidates
