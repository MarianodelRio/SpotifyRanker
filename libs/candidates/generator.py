from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.artist import ArtistRepository
from libs.candidates.deduplicator import deduplicate_and_upsert
from libs.candidates.sources.artist_discography import fetch_artist_discography_candidates
from libs.candidates.sources.genre_search import fetch_genre_search_candidates
from libs.common.models import Candidate, UserProfile
from libs.spotify.fetcher import SpotifyFetcher

_TOTAL_CAP = 500


class CandidateGenerator:
    async def generate(
        self,
        profile: UserProfile,
        fetcher: SpotifyFetcher,
        session: AsyncSession,
    ) -> list[Candidate]:
        if not profile.artist_affinities and not profile.genre_weights:
            return []

        artist_names = await ArtistRepository(session).get_names_by_spotify_ids(
            list(profile.artist_affinities.keys())
        )
        discography = await fetch_artist_discography_candidates(profile, fetcher, artist_names)
        genre = await fetch_genre_search_candidates(profile, fetcher)

        # Merge: artist_discography takes priority when trimming to cap
        combined = discography + genre
        if len(combined) > _TOTAL_CAP:
            combined = combined[:_TOTAL_CAP]

        return await deduplicate_and_upsert(combined, session)
