document.addEventListener("DOMContentLoaded", updateTalks);

function updateTalks() {
    const upcoming = document.getElementById("upcoming-talks");
    const upcomingEmpty = document.getElementById("no-upcoming-talks");
    const past = document.getElementById("past-talks");
    const allTalks = document.getElementById("all-talks");
    
    // Compare dates at the day level.
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const upcomingTalks = [];
    const pastTalks = [];
    
    allTalks.querySelectorAll(".talk-card").forEach(function (card) {
        const [year, month, day] = card.querySelector(".talk-date").dataset.date.split("-").map(Number);
        const date = new Date(year, month - 1, day);
        
        if (date >= today) {
            upcomingTalks.push(card);
        } else {
            pastTalks.push(card);
        }
    });
    
    // Sort upcoming talks with oldest first.
    upcomingTalks.forEach(function (card) {
        upcoming.appendChild(card);
    });
    
    // Sort past talks with newest first.
    pastTalks.reverse().forEach(function (card) {
        past.appendChild(card);
    });
    
    if (upcomingTalks.length === 0) {
        upcoming.style.display = "none";
        upcomingEmpty.style.display = "";
    } else {
        upcoming.style.display = "";
        upcomingEmpty.style.display = "none";
    }
}
