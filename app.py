"""
MUSIC RECOMMENDATION SYSTEM
"""

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import random
import urllib.parse

app = Flask(__name__)

# ================= LOAD DATA =================
df = pd.read_csv("ClassicHit.csv")
print(df.columns)
df = df.drop_duplicates(subset=["Track", "Artist"])

print("Jumlah data setelah preprocessing:", len(df))

# ================= FILTER GENRE SESUAI PILIHAN =================
allowed_genres = [
    "Alt. Rock", "Blues", "Country", "Disco", "Folk",
    "Funk", "Gospel", "Jazz", "Metal", "Pop",
    "Punk", "R&B", "Rap", "Reggae", "Rock",
    "Ska", "Today", "World"
]

df = df[df["Genre"].isin(allowed_genres)]

# ================= MOOD ENGINEERING =================
def categorize_mood(row):

    energy = row["Energy"]
    valence = row["Valence"]
    tempo = row["Tempo"]
    acoustic = row["Acousticness"]
    loudness = row.get("Loudness", -10)

    # =========================
    # MARAH (ANGRY)
    # =========================
    if energy > 0.85 and tempo > 130 and loudness > -6:
        return "Marah"

    # =========================
    # STRESS - RELEASE
    # =========================
    if energy > 0.8 and tempo > 125 and valence < 0.5:
        return "Stres (Melampiaskan)"

    # =========================
    # STRESS - RELIEF
    # =========================
    if energy < 0.45 and tempo < 100 and acoustic > 0.3:
        return "Stres (Meredakan)"

    # =========================
    # JATUH CINTA
    # =========================
    if valence > 0.7 and 0.4 < energy < 0.75:
        return "Jatuh Cinta"

    # =========================
    # TENANG
    # =========================
    if energy < 0.5 and valence > 0.5:
        return "Tenang"

    # =========================
    # HAPPY
    # =========================
    if valence > 0.75 and energy > 0.6:
        return "Bahagia"

    # =========================
    # SAD
    # =========================
    if valence < 0.4:
        return "Sedih"

    return "Santai"


df["Mood"] = df.apply(categorize_mood, axis=1)

df = df.reset_index(drop=True)


# ================= TEXT FEATURES (TF-IDF) =================
df["text_features"] = df["Genre"] + " " + df["Mood"]
tfidf = TfidfVectorizer()
tfidf_matrix = tfidf.fit_transform(df["text_features"])

# Tampilkan dimensi matriks
print("Dimensi matriks TF-IDF:", tfidf_matrix.shape)

# Tampilkan jumlah fitur unik
print("Jumlah fitur unik (vocabulary):", len(tfidf.get_feature_names_out()))

# ================= AUDIO FEATURES =================
audio_features = [
    "Danceability",
    "Energy",
    "Valence",
    "Tempo",
    "Acousticness",
    "Popularity"
]

# ================= FITUR UNTUK MATCHING MOOD-GENRE =================
matching_features = [
    "Danceability",
    "Energy",
    "Valence",
    "Tempo",
    "Acousticness",
    "Loudness",
    "Speechiness",
    "Instrumentalness",
    "Liveness"
]

def get_genres_for_mood(selected_mood, top_k=5):

    mood_df = df[df["Mood"] == selected_mood]

    if mood_df.empty:
        return []

    # Profil rata-rata atribut untuk mood
    mood_vector = mood_df[matching_features].mean().values.reshape(1, -1)

    genre_scores = {}

    for genre in df["Genre"].unique():

        genre_df = df[df["Genre"] == genre]

        if genre_df.empty:
            continue

        # Profil rata-rata atribut untuk genre
        genre_vector = genre_df[matching_features].mean().values.reshape(1, -1)

        similarity = cosine_similarity(mood_vector, genre_vector)[0][0]

        genre_scores[genre] = similarity

    # Urutkan berdasarkan similarity
    sorted_genres = sorted(
        genre_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [g[0] for g in sorted_genres[:top_k]]


scaler = StandardScaler()
audio_matrix = scaler.fit_transform(df[audio_features])

# ================= HYBRID RECOMMENDATION FUNCTION =================
def get_recommendations(user_mood, user_genre, top_n=10, alpha=0.5):

    filtered_df = df[
        (df["Mood"] == user_mood) &
        (df["Genre"] == user_genre)
    ]

    if filtered_df.empty:
        return []

    if len(filtered_df) < top_n:
        filtered_df = df[df["Mood"] == user_mood]

    if len(filtered_df) < top_n:
        filtered_df = df.copy()
    
    if filtered_df.empty:
        return []

    filtered_indices = filtered_df.index.tolist()
    if len(filtered_indices) == 0:
        return []


    # ===== TF-IDF Similarity =====
    query_text = f"{user_genre} {user_mood}"
    query_vector = tfidf.transform([query_text])

    tfidf_scores = cosine_similarity(
        query_vector,
        tfidf_matrix[filtered_indices]
    ).flatten()

    # ===== Audio Similarity =====
    filtered_audio = audio_matrix[filtered_indices]
    if filtered_audio.shape[0] == 0:
        return []

    user_audio_vector = np.mean(filtered_audio, axis=0).reshape(1, -1)

    audio_scores = cosine_similarity(
        user_audio_vector,
        filtered_audio
    ).flatten()

    # ===== Hybrid Score =====
    hybrid_scores = alpha * tfidf_scores + (1 - alpha) * audio_scores
    sorted_idx = hybrid_scores.argsort()[::-1]

    print("\n===== DETAIL PERHITUNGAN SIMILARITY =====")
    print("Input Mood:", user_mood)
    print("Input Genre:", user_genre)

    for i in sorted_idx[:10]:
        print(
            "Lagu:", filtered_df.iloc[i]["Track"],
            "| TF-IDF:", round(tfidf_scores[i], 4),
            "| Audio:", round(audio_scores[i], 4),
            "| Hybrid:", round(hybrid_scores[i], 4)
        )

    results = []

    for i in sorted_idx[:top_n]:
        song = filtered_df.iloc[i]

        query = f"{song['Track']} {song['Artist']}"
        spotify_url = "https://open.spotify.com/search/" + urllib.parse.quote(query)

        results.append({
            "song_name": song["Track"],
            "artist": song["Artist"],
            "genre": song["Genre"],
            "mood": song["Mood"],
            "tempo": int(song["Tempo"]),
            "spotify_url": spotify_url
        })

    return results


# ================= ROUTES =================
@app.route("/")
def index():

    moods = sorted(df["Mood"].unique())
    genres = sorted(df["Genre"].unique())

    mood_genre_map = {}
    
    for mood in moods:
        mood_genre_map[mood] = get_genres_for_mood(mood)

    return render_template(
        "index.html",
        moods=moods,
        genres=genres,
        mood_genre_map=mood_genre_map
    )


@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.json
    user_mood = data.get("mood")
    user_genre = data.get("genre")

    if not user_mood or not user_genre:
        return jsonify({"error": "Mood dan Genre wajib dipilih"}), 400

    recommendations = get_recommendations(user_mood, user_genre)

    return jsonify({
        "message": f"Ditemukan {len(recommendations)} lagu rekomendasi",
        "recommendations": recommendations
    })


import os

if __name__ == "__main__":
    print("🎵 Hybrid Music Recommendation System Running...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
