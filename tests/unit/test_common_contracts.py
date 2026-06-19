import pytest

from libs.common.enums import (
    CandidateSource,
    FeedbackType,
    ImportStatus,
    PlaylistMode,
    PlaySource,
    TimeRange,
)
from libs.common.models import (
    Artist,
    Candidate,
    FeedbackEntry,
    GeneratedPlaylist,
    RankedTrack,
    Track,
    UserProfile,
)


# --- Enum value tests ---


def test_playlist_mode_values() -> None:
    assert set(PlaylistMode) == {PlaylistMode.safe, PlaylistMode.balanced, PlaylistMode.adventurous}


def test_feedback_type_values() -> None:
    assert set(FeedbackType) == {FeedbackType.like, FeedbackType.dislike}


def test_import_status_values() -> None:
    assert set(ImportStatus) == {
        ImportStatus.idle,
        ImportStatus.running,
        ImportStatus.completed,
        ImportStatus.failed,
    }


def test_candidate_source_values() -> None:
    assert set(CandidateSource) == {
        CandidateSource.artist_discography,
        CandidateSource.genre_search,
    }


def test_play_source_values() -> None:
    assert set(PlaySource) == {PlaySource.my_music, PlaySource.search, PlaySource.discover}


def test_time_range_values() -> None:
    assert set(TimeRange) == {TimeRange.short_term, TimeRange.medium_term, TimeRange.long_term}


# --- Model instantiation tests ---


@pytest.fixture()
def sample_track() -> Track:
    return Track(
        spotify_id="spotify:track:abc",
        title="Song",
        artist_name="Artist",
        album_title="Album",
        duration_ms=200000,
        popularity=70,
        image_url=None,
    )


def test_track_instantiation(sample_track: Track) -> None:
    assert sample_track.spotify_id == "spotify:track:abc"
    assert sample_track.image_url is None


def test_artist_instantiation() -> None:
    artist = Artist(spotify_id="s:artist:x", name="Band", popularity=80, genres=["rock"])
    assert artist.genres == ["rock"]
    assert artist.image_url is None


def test_user_profile_defaults() -> None:
    profile = UserProfile()
    assert profile.genre_weights == {}
    assert profile.artist_affinities == {}
    assert profile.known_track_ids == set()
    assert profile.global_like_ratio == 0.0
    assert profile.diversity_score == 0.0


def test_candidate_instantiation(sample_track: Track) -> None:
    candidate = Candidate(
        track=sample_track,
        source=CandidateSource.artist_discography,
        artist_affinity_score=0.9,
    )
    assert candidate.source == CandidateSource.artist_discography


def test_ranked_track_instantiation(sample_track: Track) -> None:
    candidate = Candidate(
        track=sample_track,
        source=CandidateSource.genre_search,
        artist_affinity_score=0.5,
    )
    ranked = RankedTrack(
        candidate=candidate,
        final_score=0.85,
        score_breakdown={"affinity": 0.5, "popularity": 0.35},
    )
    assert ranked.final_score == pytest.approx(0.85)
    assert ranked.score_breakdown["affinity"] == pytest.approx(0.5)


def test_generated_playlist_has_id(sample_track: Track) -> None:
    playlist = GeneratedPlaylist(name="Discovery Mix", mode=PlaylistMode.balanced, tracks=[])
    assert playlist.id != ""
    assert playlist.spotify_url is None


def test_feedback_entry_optional_playlist_id() -> None:
    entry = FeedbackEntry(
        track_id="spotify:track:xyz",
        feedback_type=FeedbackType.like,
        source=PlaySource.discover,
    )
    assert entry.playlist_id is None


# --- DAG: no cross-module imports inside libs/common ---


def test_no_libs_imports_in_common() -> None:
    import importlib
    import inspect

    import libs.common.enums as enums_mod
    import libs.common.models as models_mod

    for mod in (enums_mod, models_mod):
        source = inspect.getsource(mod)
        assert "from libs.spotify" not in source
        assert "from libs.profile" not in source
        assert "from libs.candidates" not in source
        assert "from libs.ranker" not in source
        assert "from libs.ml" not in source
        assert "from libs.playlist" not in source
        assert "from libs.feedback" not in source
