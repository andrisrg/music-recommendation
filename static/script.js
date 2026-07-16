document.addEventListener("DOMContentLoaded", function () {

  console.log("🎵 Music Recommendation System loaded!");

  const moodSelect = document.getElementById("mood");
  const genreSelect = document.getElementById("genre");

  const moodGenreMap = JSON.parse(
    document.getElementById("mood-data").textContent
  );

  // =========================
  // UPDATE GENRE SAAT MOOD BERUBAH
  // =========================
  moodSelect.addEventListener("change", function () {

    const selectedMood = this.value;

    // Reset dropdown genre
    genreSelect.innerHTML =
      '<option value="">Pilih Genre Favorit Kamu</option>';

    if (!selectedMood || !moodGenreMap[selectedMood]) {
      return;
    }

    moodGenreMap[selectedMood].forEach(function (genre) {
      const option = document.createElement("option");
      option.value = genre;
      option.textContent = genre;
      genreSelect.appendChild(option);
    });

  });


  // =========================
  // HANDLE FORM SUBMIT
  // =========================
  document
    .getElementById("recommendationForm")
    .addEventListener("submit", async function (e) {

      e.preventDefault();

      const mood = moodSelect.value;
      const genre = genreSelect.value;

      if (!mood) {
        alert("Mohon pilih mood Kamu!");
        return;
      }

      if (!genre) {
        alert("Mohon pilih genre favorit Kamu!");
        return;
      }

      document.getElementById("loading").style.display = "block";
      document.getElementById("results").style.display = "none";

      try {

        const response = await fetch("/recommend", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mood: mood, genre: genre })
        });

        const data = await response.json();

        document.getElementById("loading").style.display = "none";

        if (response.ok) {
          displayRecommendations(data);
        } else {
          alert("Error: " + (data.error || "Something went wrong"));
        }

      } catch (error) {
        document.getElementById("loading").style.display = "none";
        alert("Error: " + error.message);
        console.error("Error:", error);
      }

    });

});


// =========================
// DISPLAY RECOMMENDATIONS
// =========================
function displayRecommendations(data) {

  const resultsDiv = document.getElementById("results");
  const messageDiv = document.getElementById("resultMessage");
  const listDiv = document.getElementById("recommendationsList");

  resultsDiv.style.display = "block";
  messageDiv.textContent = data.message;
  listDiv.innerHTML = "";

  if (!data.recommendations || data.recommendations.length === 0) {
    listDiv.innerHTML =
      '<p style="text-align:center;padding:20px;">Tidak ada lagu ditemukan.</p>';
    return;
  }

  data.recommendations.forEach((song, index) => {

    const songCard = document.createElement("div");
    songCard.className = "song-card";

    songCard.innerHTML = `
        <div class="song-number">${index + 1}</div>

        <div class="song-title">
            🎵 ${song.song_name}
        </div>

        <div class="song-artist">
           🎤 ${song.artist}
        </div>

        <div class="song-details">
            <span class="detail-badge">🎸 ${song.genre}</span>
            <span class="detail-badge">😊 ${song.mood}</span>
            <span class="detail-badge">🎼 ${song.tempo} BPM</span>
        </div>

        <div style="margin-top:15px;">
            <a href="${song.spotify_url}"
              target="_blank"
              class="spotify-btn">
              🎧 Dengarkan di Spotify
            </a>
        </div>
    `;

    listDiv.appendChild(songCard);

  });

  resultsDiv.scrollIntoView({ behavior: "smooth" });

}
