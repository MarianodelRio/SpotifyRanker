# Idea 2: TasteRanker — Personal Music Discovery Engine

## 1. Introduction

**TasteRanker** is a project idea focused on building a personal music recommendation system connected to Spotify. The goal is not to replicate Spotify's algorithm exactly, but to create a custom engine that learns from the user's musical taste, generates new candidates from different sources, and produces personalized playlists tailored to different listening modes.

The idea stems from a very concrete situation: the user already has a large library of liked songs, personal playlists, frequent artists, and a listening history. All of that represents a rich musical profile. The system should be able to read as much available information as possible, transform it into a taste profile, and use it to recommend new songs that are likely to fit the user.

The project would start with classical recommendation and ranking techniques, without requiring deep learning at the beginning, but leaving an architecture ready to incorporate more advanced models in the future.

---

## 2. Motivation

Recommendation systems are a central part of many digital products: music, film, shopping, news, social networks, education, and content. A music recommendation project allows learning very relevant concepts such as:

- user profiles;
- explicit and implicit feedback;
- candidate generation;
- ranking;
- diversity and novelty;
- filtering out already-known items;
- contextual recommendation;
- recommendation evaluation;
- integration with external APIs;
- automatic playlist creation;
- feedback loop.

Although the idea of recommending music may seem classical, the value of the project lies in building a realistic system under real platform constraints. Spotify should not be seen as a magic recommendations endpoint, but as a source of personal data and a destination for creating playlists. The recommendation engine should be built within the project itself.

The main motivation is to build a tool that answers questions like:

- What new songs might I enjoy based on my listening history?
- What music could I discover without straying too far from what I already listen to?
- What songs fit what I am listening to right now?
- How can I generate a new playlist balancing taste, novelty, and diversity?
- How does my musical profile change in the short, medium, and long term?

---

## 3. General Vision

The vision is to build a **personal music discovery engine**.

The system should:

1. Connect to Spotify.
2. Read the user's available musical data.
3. Build a personal musical profile.
4. Generate a broad set of candidate tracks.
5. Enrich those tracks with available metadata.
6. Rank the tracks according to different criteria.
7. Generate personalized playlists.
8. Collect user feedback.
9. Improve future recommendations.

The central idea is not to have access to all of Spotify's music. That would be unrealistic. The idea is to generate a sufficiently large and relevant universe of candidates from the user's library, artists, albums, playlists, searches, external tags, and complementary sources.

---

## 4. Two Main Recommendation Modes

### 4.1. Global Profile-Based Recommendation

This mode uses everything that can be learned about the user:

- saved songs;
- recently played songs;
- top tracks;
- top artists;
- own playlists;
- frequent artists;
- repeated albums;
- inferred genres or tags;
- previously accepted/rejected songs;
- short, medium, and long-term listening patterns.

The goal is to build a general taste profile and generate new music that fits that profile.

Example:

> The user has a lot of indie rock, melodic electronic, alternative pop, and Spanish urban music. The system generates a discovery playlist with new songs balancing precision, novelty, and diversity.

This mode would be ideal for playlists such as:

- weekly discovery;
- songs similar to my general taste;
- new but safe music;
- artists I will probably enjoy;
- songs from albums/artists I already listen to but haven't saved.

### 4.2. Contextual or Session-Based Recommendation

This second mode is more dynamic. It does not recommend based solely on the full historical profile, but based on what the user is currently listening to or has listened to in a recent session.

Example:

> If the user has just listened to three electronic music songs, the system should recommend more songs in that direction, even if their global profile also includes rock, pop, or rap.

This mode can use:

- last songs listened to;
- a specific playlist as a seed;
- a specific song;
- a specific artist;
- a recent listening sequence;
- a mode selected by the user.

Possible playlists:

- continue this vibe;
- more like this session;
- electronic continuation;
- similar to this playlist;
- same mood, new artists;
- same genre, more exploratory.

This second system is especially interesting because it allows distinguishing between **historical taste** and **current context**.

---

## 5. Data That Could Be Retrieved

### 5.1. From Spotify

Spotify could be used to obtain personal information and basic metadata:

- user's saved songs;
- recently played songs;
- user's top tracks;
- user's top artists;
- own playlists;
- tracks within playlists;
- basic track information;
- basic artist information;
- albums;
- song duration;
- popularity;
- Spotify identifiers;
- album/artist images;
- market availability;
- creation of new playlists.

One important limitation must be kept in mind: Spotify has restricted for new apps several endpoints related to recommendations, audio features, audio analysis, and related artists. That is why the project should be designed not to depend on those endpoints.

### 5.2. From External Sources

To enrich the system, external sources could be used:

- Last.fm: tags, similar artists, top tracks, scrobbles, social/community information.
- MusicBrainz: open metadata about artists, recordings, releases, and musical relationships.
- ListenBrainz: listening histories, statistics, recommendations, and open data from the MetaBrainz ecosystem.
- Public music datasets: for experimenting with collaborative filtering or offline models.

These sources would complement what Spotify does not offer or does not allow to be queried directly.

### 5.3. Data Generated by the System Itself

The system would also generate its own data:

- recommendations shown;
- accepted songs;
- rejected songs;
- songs marked as already known;
- songs added to playlist;
- ranking weights used;
- selected recommendation mode;
- history of generated playlists;
- recommendation explanations;
- diversity/novelty metrics.

This information is very valuable because it would allow creating a custom feedback loop.

---

## 6. Candidate Generation

The system should not attempt to rank the entire global music catalog. Instead, it should generate candidates from different strategies.

Possible candidate sources:

1. **Favorite artists**
   Look for songs by artists the user listens to a lot but has not saved.

2. **Partially known albums**
   If the user has several songs from an album, recommend other songs from the same album.

3. **Similar artists**
   Use Last.fm, MusicBrainz/ListenBrainz, or other sources to find related artists.

4. **Public playlists**
   Search for playlists related to the user's tastes and extract candidate songs.

5. **Inferred tags or genres**
   If the user's profile is associated with tags like `indie rock`, `electronic`, `latin alternative`, or `garage rock`, search for songs/artists related to those tags.

6. **Current session**
   If the user is listening to electronic music, generate candidates closer to electronic even if their global profile is broader.

7. **Historical feedback**
   If the user tends to reject a type of music or accept another, adjust future candidates accordingly.

8. **Controlled exploration**
   Introduce songs further from the profile to increase discovery, but with a limit.

---

## 7. Song Ranking

Once a set of candidates is generated, the system should rank them.

The score could combine many signals:

- similarity to global profile;
- similarity to current session;
- affinity with favorite artists;
- tag/genre overlap;
- popularity;
- novelty;
- diversity;
- duration;
- presence in related playlists;
- relationship with known albums;
- distance from rejected songs;
- whether the song is already saved;
- whether the song was recently listened to;
- whether the artist appears too many times.

Conceptual example:

```text
score =
  taste_similarity
+ session_similarity
+ artist_affinity
+ tag_overlap
+ playlist_signal
+ novelty
+ diversity
- already_known_penalty
- repetition_penalty
```

The goal is not only to recommend the most similar songs. It is also necessary to balance:

- precision: likely to be enjoyed;
- discovery: not too obvious;
- diversity: not all from the same artist/genre;
- context: fitting what the user wants to listen to now;
- user control: being able to adjust the type of playlist.

---

## 8. Metadata and Musical Information

The available information for each song can vary greatly depending on the source. Some possible variables:

- title;
- artist;
- album;
- duration;
- popularity;
- release date;
- artist genres;
- external tags;
- playlists where it appears;
- relationship with other artists;
- frequency in listening histories;
- whether it is saved by the user;
- whether it was recently listened to;
- previous user feedback.

Song-level audio information could also be explored, but this is more complex. Spotify no longer provides audio features/audio analysis for new apps in many cases. Possible future alternatives could be:

- using previews if available from some source;
- analyzing local audio if the user has files;
- using audio embeddings from external models;
- using textual metadata as a proxy;
- using community tags;
- using lyrics or descriptions if legal and available sources exist.

For a first version, the most realistic approach would be to work with metadata, tags, listening histories, and relationships between songs/artists.

---

## 9. Possible Models

### 9.1. First Version: Classical Models

There is no need to start with deep learning. Possible initial approaches:

- scoring rules;
- TF-IDF over tags/artists/albums;
- cosine similarity;
- popularity baseline;
- content-based filtering;
- item-item similarity;
- heuristic ranking;
- feedback-based reweighting.

This allows building a functional and explainable system.

### 9.2. Intermediate Version

Once enough internal data is available:

- simple learning-to-rank;
- logistic regression to predict like/dislike;
- gradient boosting;
- matrix factorization with external datasets;
- text embeddings with sentence-transformers;
- taste clustering;
- diversification using maximal marginal relevance.

### 9.3. Advanced Version

Later on, deep learning could be explored:

- music embeddings;
- sequential models for sessions;
- two-tower recommenders;
- neural collaborative filtering;
- models based on listening histories;
- learned reranking;
- multimodal representations if audio/text/metadata is available.

The architecture should allow incorporating these models without rebuilding the entire system.

---

## 10. Playlist Modes

The user could generate playlists with different objectives:

- **Safe Discovery**: songs very close to historical taste.
- **Balanced Discovery**: mix of precision and novelty.
- **Adventurous Discovery**: more exploration and new artists.
- **Continue This Vibe**: continue the current session.
- **More Like This Playlist**: generate songs similar to a specific playlist.
- **Same Artists, New Tracks**: unsaved songs from favorite artists.
- **New Artists, Same Taste**: new artists but with similar tags.
- **Short Songs / Long Songs**: control duration.
- **Less Mainstream**: reduce average popularity.
- **High Diversity**: limit repetition of artists/genres.

These modes would make the system more of a product and less of a script.

---

## 11. Feedback Loop

User feedback would be a central part.

Types of feedback:

- I like it;
- I don't like it;
- I already knew this one;
- add to playlist;
- don't recommend this artist;
- recommend more of this style;
- too mainstream;
- too obscure;
- doesn't fit this playlist;
- good recommendation for this context.

This feedback could modify:

- ranking weights;
- tag preferences;
- artist affinity;
- exploration level;
- repetition filters;
- future penalties.

Over time, the system could learn a more personal profile than the one obtained from Spotify alone.

---

## 12. Possible Interfaces

### 12.1. Frontend

A web app could include:

- Spotify login;
- musical profile dashboard;
- view of dominant artists/songs/tags;
- playlist generator;
- novelty/diversity controls;
- recommendation preview;
- per-song feedback;
- button to create playlist in Spotify;
- history of generated playlists.

### 12.2. API

The system could also expose endpoints:

- import data from Spotify;
- query musical profile;
- generate candidates;
- rank songs;
- create playlist;
- record feedback;
- query previous recommendations.

### 12.3. Code Usage

It could also have a small SDK or Python layer:

```python
from tasteranker import TasteRanker

engine = TasteRanker.from_spotify_user(user_id="me")
playlist = engine.generate_playlist(mode="balanced_discovery", size=30)
```

---

## 13. Candidate Tools

### Backend and Data

- Python
- FastAPI
- SQLite or PostgreSQL
- SQLAlchemy
- Pydantic
- Pandas / Polars
- Docker
- pytest

### APIs and External Sources

- Spotify Web API
- Last.fm API
- MusicBrainz API
- ListenBrainz API

### Recommendation and ML

- scikit-learn
- scipy
- implicit / LightFM, in later phases
- sentence-transformers, if text embeddings are used
- MLflow, optional for experiments

### Frontend

- React
- Vite
- TypeScript
- Tailwind or similar

---

## 14. Possible Challenges

### Spotify Restrictions

Some endpoints that were previously very useful for recommendation and music analysis are no longer available for new apps. The project must be designed to not depend on them.

### No Full Catalog Access

One should not attempt to rank all of Spotify's music. The realistic approach is to generate relevant candidates from multiple sources.

### Metadata Quality

Tags, genres, and relationships between artists can be noisy. The system should tolerate incomplete information.

### Evaluation

Evaluating music recommendations is difficult. Proxies can be used:

- saved songs as positives;
- unsaved songs as unknowns;
- explicit user feedback;
- hit rate on hidden songs;
- diversity;
- novelty;
- coverage;
- rate of songs added to playlist.

### Privacy

Musical taste can reveal personal information. The system should store tokens and data carefully, minimize data sent to external services, and allow deleting listening histories.

---

## 15. Possible Evolution

### Conceptual MVP

- Spotify login.
- Import saved tracks, top tracks, top artists, and playlists.
- Build a basic profile.
- Generate candidates from artists/albums/playlists.
- Rank by simple scoring.
- Create playlist in Spotify.

### Good Version

- Enrichment with Last.fm.
- Tags and similar artists.
- Playlist modes.
- Feedback loop.
- Dashboard.
- Recommendation explanations.

### Advanced Version

- Model learned from feedback.
- Contextual/session-based recommendation.
- Text embeddings.
- Advanced diversification.
- Integration with ListenBrainz/MusicBrainz.
- Optional deep learning.
- Optional LLM curator.

---

## 16. Possible Project Tagline

> TasteRanker is a personal music discovery engine that learns from a user's Spotify library, listening behavior and playlists to generate explainable discovery playlists through hybrid candidate generation, contextual ranking and feedback-driven personalization.

---

## 17. Differentiating Idea

The differentiating idea is not simply to recommend songs. It is to build a system that combines:

- historical musical profile;
- current listening context;
- multi-source candidate generation;
- explainable ranking;
- novelty/diversity control;
- feedback loop;
- real playlist creation.

The project should demonstrate that a recommendation system is not just a model, but a complete pipeline: data, candidates, ranking, product, feedback, and continuous improvement.

---

## 18. References to Research

- Spotify Web API: user data, saved tracks, recently played, top tracks/artists, playlists, and search.
- Recent Spotify API changes: restrictions on recommendations, audio features, audio analysis, and related artists.
- Last.fm API: tags, similar artists, top tracks, and listening data.
- MusicBrainz API: open music metadata.
- ListenBrainz API: histories, statistics, and open recommendations.
- Hybrid recommendation systems.
- Session-based recommendation.
- Learning-to-rank.
- Recommendation diversification.
