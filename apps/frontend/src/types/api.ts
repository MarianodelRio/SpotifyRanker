// Enums

export type PlaylistMode = "safe" | "balanced" | "adventurous";

export type FeedbackType = "like" | "dislike";

export type ImportStatus = "idle" | "running" | "completed" | "partial" | "failed";

export type CandidateSource = "artist_discography" | "genre_search";

export type PlaySource = "my_music" | "search" | "discover";

export type SaveSource = "spotify" | "app";

export type TimeRange = "short_term" | "medium_term" | "long_term";

// Models

export interface Track {
  spotify_id: string;
  title: string;
  artist_name: string;
  album_title: string;
  duration_ms: number;
  popularity: number;
  image_url: string | null;
}

export interface Artist {
  spotify_id: string;
  name: string;
  popularity: number;
  genres: string[];
  image_url: string | null;
}

export interface UserProfile {
  genre_weights: Record<string, number>;
  artist_affinities: Record<string, number>;
  known_track_ids: string[];
  global_like_ratio: number;
  diversity_score: number;
}

export interface Candidate {
  track: Track;
  source: CandidateSource;
  artist_affinity_score: number;
}

export interface RankedTrack {
  candidate: Candidate;
  final_score: number;
  score_breakdown: Record<string, number>;
}

export interface GeneratedPlaylist {
  id: string;
  name: string;
  mode: PlaylistMode;
  tracks: RankedTrack[];
  created_at: string;
  spotify_url: string | null;
}

export interface FeedbackEntry {
  track_id: string;
  feedback_type: FeedbackType;
  source: PlaySource;
  playlist_id: string | null;
}

// Response shapes (used by the API client modules)

export interface AuthStatus {
  is_authenticated: boolean;
  display_name: string | null;
}

export interface TokenResponse {
  access_token: string;
}

export interface ImportProgress {
  status: ImportStatus;
  tracks_imported: number;
  artists_imported: number;
}

export interface LibraryPage {
  tracks: Track[];
  total: number;
  page: number;
  per_page: number;
}

export interface SearchResult {
  tracks: Track[];
}

export interface ModelStatus {
  trained_at: string | null;
  examples_count: number;
  training_in_progress: boolean;
  last_loss: number | null;
}

export interface DeclaredArtist {
  spotify_id: string;
  name: string;
  image_url: string | null;
  track_count: number;
  created_at: string;
}

export interface DeclaredPlaylist {
  spotify_id: string;
  name: string;
  track_count: number;
  created_at: string;
}

export interface DeclaredResponse {
  artists: DeclaredArtist[];
  playlists: DeclaredPlaylist[];
}

export interface ProfileResponse {
  genre_weights: Record<string, number>;
  top_artists: Record<string, number>;
  stats: {
    total_tracks: number;
    global_like_ratio: number;
    diversity_score: number;
    declared_artists: number;
    declared_playlists: number;
  };
}

// Request shapes

export interface PlayerEventRequest {
  track_id: string;
  ms_played: number;
  source: PlaySource;
  playlist_id: string | null;
}

export interface PlaylistGenerateRequest {
  mode: PlaylistMode;
  size: number;
}
