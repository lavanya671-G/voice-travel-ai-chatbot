document.addEventListener("DOMContentLoaded", () => {
  const sendBtn = document.getElementById("sendBtn");
  const micBtn = document.getElementById("micBtn");
  const userInput = document.getElementById("userInput");
  const chatMessages = document.getElementById("chatMessages");
  const clearChatBtn = document.getElementById("clear-chat");
  const popupMessage = document.getElementById("popupMessage");
  const popupClose = document.getElementById("popupClose");

  let popupClosed = false;
  let conversationStarted = false;
  let recognition;

  // ✅ Cache to speed up repeated city lookups (faster routes)
  const cityCache = {};

  // ✅ Initialize Speech Recognition
  function initSpeechRecognition() {
    if (!("webkitSpeechRecognition" in window)) {
      alert("Your browser doesn't support speech recognition.");
      return null;
    }
    const rec = new webkitSpeechRecognition();
    rec.lang = "en-US";
    rec.continuous = false;
    rec.interimResults = false;
    return rec;
  }

  function startListening() {
    if (!recognition) recognition = initSpeechRecognition();
    if (!recognition) return;

    micBtn.classList.add("listening");
    recognition.start();

    recognition.onresult = (event) => {
      micBtn.classList.remove("listening");
      const transcript = event.results[0][0].transcript.trim();
      clearDefaultMessages();
      appendMessage("user", transcript);
      handleUserQuery(transcript);
    };

    recognition.onend = () => micBtn.classList.remove("listening");

    recognition.onerror = (event) => {
      micBtn.classList.remove("listening");
      console.error("Speech recognition error:", event.error);
      const msg = "⚠️ Couldn't understand you. Try again!";
      appendMessage("bot", msg);
      speakText(msg);
      userInput.focus();
    };
  }

  // ✅ Append message
  function appendMessage(type, text, preserveFormat = false) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${type}`;
    msgDiv.innerHTML = preserveFormat ? `<pre>${text}</pre>` : `<p>${text}</p>`;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
  }

  function scrollToBottom() {
    chatMessages.scrollTo({
      top: chatMessages.scrollHeight,
      behavior: "smooth",
    });
  }

  function speakText(text, callback = null) {
  if (!("speechSynthesis" in window)) return;

  // ✅ Clean the text for speech
  const cleanText = text
    .replace(/[^\x00-\x7F]+/g, " ")
    .replace(/\n/g, ". ")
    .replace(/\s{2,}/g, " ")
    .trim();

  if (!cleanText) return;

  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.lang = "en-US";
  utterance.rate = 1;

  // ✅ Disable mic while speaking
  micBtn.disabled = true;
  micBtn.classList.add("disabled");

  utterance.onend = () => {
    micBtn.disabled = false;
    micBtn.classList.remove("disabled");
    if (callback) callback();
  };

  speechSynthesis.cancel(); // stop any previous speech
  speechSynthesis.speak(utterance);
}


  function clearDefaultMessages() {
    if (!conversationStarted) {
      chatMessages.innerHTML = "";
      conversationStarted = true;
    }
  }

  function addReminderBox() {
    const reminderText =
      "You can ask about flights, hotels, weather, attractions or routes. Say 'exit' to quit.";
    appendMessage("bot", reminderText);
    speakText(reminderText);
  }

  // ✅ Auto-correct common city misspellings
function normalizeCityName(city) {
  const corrections = {
    "benglore": "Bangalore",
    "bengaluru": "Bangalore",
    "mumabi": "Mumbai",
    "hyd": "Hyderabad",
    "madras": "Chennai", // old names mapping
    "calcutta": "Kolkata",
    "delhi": "Delhi" // example redundant but useful
  };

  const lowerCity = city.toLowerCase();
  for (let wrong in corrections) {
    if (lowerCity.includes(wrong)) {
      return corrections[wrong];
    }
  }
  return city; // return same if no correction
}

  // ✅ Fetch lat/lon dynamically (cached for speed)
  async function getCoordinates(city) {
    if (cityCache[city]) return cityCache[city]; // ✅ Use cache

    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(city)}`
      );
      const data = await res.json();
      if (data.length > 0) {
        const coords = [parseFloat(data[0].lat), parseFloat(data[0].lon)];
        cityCache[city] = coords; // ✅ Save to cache
        return coords;
      }
    } catch (err) {
      console.error(`Error fetching coordinates for ${city}:`, err);
    }
    return null;
  }

  // ✅ Handle All User Queries (Main Logic)
  async function handleUserQuery(message) {
    const text = message.trim().toLowerCase();

    // ✅ Route Query
    const routeRegex = /route\s+from\s+([a-zA-Z\s]+)\s+to\s+([a-zA-Z\s]+)/i;
    const routeMatch = text.match(routeRegex);

    if (routeMatch) {
      const originCity = routeMatch[1].trim();
      const destCity = routeMatch[2].trim();

      try {
        const originCoords = await getCoordinates(originCity);
        const destCoords = await getCoordinates(destCity);

        if (originCoords && destCoords) {
          showRouteOnMap(
            originCoords[0],
            originCoords[1],
            destCoords[0],
            destCoords[1]
          );
          const msg = `Here is the best route from ${originCity} to ${destCity}.`;
          appendMessage("bot", msg);
          speakText(msg);

          setTimeout(addReminderBox, 2500);
        } else {
          const errorMsg = `⚠️ Sorry, I couldn't find route data for ${originCity} to ${destCity}.`;
          appendMessage("bot", errorMsg);
          speakText(errorMsg);
        }
      } catch (error) {
        console.error("Route fetch error:", error);
        const errorMsg = "⚠️ Something went wrong while fetching the route.";
        appendMessage("bot", errorMsg);
        speakText(errorMsg);
      }
      return;
    }

    // ✅ Normal Queries (Flask)
    // ✅ 3. Handle Normal Queries (Call Flask Backend)
  clearDefaultMessages();

  // ✅ Show loading instantly
  const botDiv = appendMessage("bot", "⏳ Fetching the best results, please wait...");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

      // Inside handleUserQuery after receiving response
const data = await response.json();
botDiv.innerHTML = `<pre>${data.response}</pre>`;
speakText(data.response, () => {
  // ✅ Speak reminder ONLY after finishing main response
  if (
    data.response.includes("Booking confirmed") ||
    data.response.includes("Booking cancelled") ||  
    data.response.includes("The weather in") ||
    data.response.includes("Top attractions in") ||
    data.response.includes("Here are the hotel options") ||
    data.response.includes("Here are the flight options")
  ) {
    setTimeout(addReminderBox, 1200);
  }
});

    } catch (error) {
      console.error("Error fetching bot response:", error);
      botDiv.innerHTML = `<p>⚠️ Sorry, something went wrong. Try again!</p>`;
    }

    scrollToBottom();
  }

  async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    clearDefaultMessages();
    appendMessage("user", message);
    userInput.value = "";
    handleUserQuery(message);
  }

  function resetChat() {
    chatMessages.innerHTML = defaultIntroMessages();
    conversationStarted = false;
    if (speechSynthesis.speaking) speechSynthesis.cancel();
    scrollToBottom();
  }

  function speakIntroLines() {
  const intro1 = "Hello! I'm your voice travel assistant. How can I help you today?";
  const intro2 = "You can ask about flights, hotels, weather, attractions or routes. Say exit to quit, or click the plus icon for a new chat.";

  micBtn.disabled = true;
  micBtn.classList.add("disabled");

  const utter1 = new SpeechSynthesisUtterance(intro1.replace(/[^\x00-\x7F]+/g, " "));
  utter1.lang = "en-US";
  utter1.rate = 1;

  utter1.onend = () => {
    const utter2 = new SpeechSynthesisUtterance(intro2.replace(/[^\x00-\x7F]+/g, " "));
    utter2.lang = "en-US";
    utter2.rate = 1;
    utter2.onend = () => {
      micBtn.disabled = false;
      micBtn.classList.remove("disabled");
    };
    speechSynthesis.speak(utter2);
  };

  speechSynthesis.cancel();
  speechSynthesis.speak(utter1);
}



  function defaultIntroMessages() {
    return `
    <div class="chat-message bot">
      <p>Hello! I'm your voice travel assistant ✈️. How can I help you today?</p>
    </div>
    <div class="chat-message bot">
      <p>You can ask about flights, hotels, weather, attractions or routes. Say 'exit' to quit or click + icon for new chat.</p>
    </div>
    <br>
    <div class="chat-message user suggestion" style="margin-left:200px" data-text="Help me to book hotel at delhi">
      <p>🧳 Help me to book hotel at delhi</p>
    </div>
    <div class="chat-message user suggestion" style="margin-left:200px" data-text="What’s the weather like in Chennai">
      <p>🌦️ What’s the weather like in Chennai</p>
    </div>
    <div class="chat-message user suggestion" style="margin-left:200px" data-text="Suggest top attractions in delhi">
      <p>🏝️ Suggest top attractions in delhi</p>
    </div>
    <div class="chat-message user suggestion" style="margin-left:200px" data-text="Book return flight to hyderabad">
      <p>🗓️ Book return flight to hyderabad</p>
    </div>
  `;
  }

  chatMessages.innerHTML = defaultIntroMessages();
  speakIntroLines();

  chatMessages.addEventListener("click", (e) => {
    const suggestion = e.target.closest(".suggestion");
    if (suggestion) {
      const text = suggestion.dataset.text;
      userInput.value = text;
      sendMessage();
    }
  });

  chatMessages.addEventListener("scroll", () => {
    if (popupClosed) return;
    const totalMessages = chatMessages.querySelectorAll(".chat-message").length;
    if (totalMessages > 20) {
      popupMessage.style.display = "block";
    }
  });

  popupClose.addEventListener("click", () => {
    popupMessage.style.display = "none";
    popupClosed = true;
  });

  sendBtn.addEventListener("click", sendMessage);
  micBtn.addEventListener("click", startListening);
  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  clearChatBtn.addEventListener("click", resetChat);
});

// ✅ Map Initialization (Only once)
var map = L.map("map").setView([21.1466, 79.0889], 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

var routingControl;
function showRouteOnMap(originLat, originLng, destLat, destLng) {
  if (routingControl) {
    map.removeControl(routingControl);
  }

  routingControl = L.Routing.control({
    waypoints: [
      L.latLng(originLat, originLng),
      L.latLng(destLat, destLng),
    ],
    routeWhileDragging: false,
    showAlternatives: false,
    addWaypoints: false,
    fitSelectedRoutes: true,
    draggableWaypoints: false,
    lineOptions: {
      addWaypoints: false,
      styles: [{ color: "blue", opacity: 0.8, weight: 5 }],
    },
  }).addTo(map);

  map.fitBounds([
    [originLat, originLng],
    [destLat, destLng],
  ]);
}
