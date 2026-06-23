from __future__ import annotations

from collections import defaultdict

from libs.common.models import RankedTrack


def diversify(
    ranked: list[RankedTrack],
    n: int,
    genres_map: dict[str, list[str]] | None = None,
) -> list[RankedTrack]:
    """Greedy selection of up to n tracks from a sorted ranked list.

    Constraints:
    - No more than 3 tracks from the same artist.
    - No single genre exceeds 40% of the playlist (only checked when genres_map is provided).

    genres_map: optional dict mapping track spotify_id → list of genre strings.
    """
    if n <= 0:
        return []

    max_per_artist = 3
    max_per_genre = max(1, int(n * 0.4))

    artist_counts: dict[str, int] = defaultdict(int)
    genre_counts: dict[str, int] = defaultdict(int)
    selected: list[RankedTrack] = []

    for rt in ranked:
        if len(selected) >= n:
            break

        artist = rt.candidate.track.artist_name
        if artist_counts[artist] >= max_per_artist:
            continue

        track_genres: list[str] = []
        if genres_map is not None:
            track_genres = genres_map.get(rt.candidate.track.spotify_id, [])
            if any(genre_counts[g] >= max_per_genre for g in track_genres):
                continue

        artist_counts[artist] += 1
        for g in track_genres:
            genre_counts[g] += 1
        selected.append(rt)

    return selected
