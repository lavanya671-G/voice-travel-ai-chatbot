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
  const cityCache = {};
  let map;
  let routingControl;

  // Initialize map
  function initMap() {
    map = L.map('map').setView([20.5937, 78.9629], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    setTimeout(() => {
      map.invalidateSize();
    }, 500);
  }

  // Initialize Speech Recognition
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

  function appendMessage(type, text, preserveFormat = false) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${type}`;
    
    // Add appropriate icon based on message type
    let icon = '';
    if (type === 'bot') {
      icon = '<i class="fas fa-robot message-icon"></i>';
    } else {
      icon = '<i class="fas fa-user message-icon"></i>';
    }
    
    msgDiv.innerHTML = `
      <div class="message-content">
        ${icon}
        <div class="message-text">${preserveFormat ? `<pre>${text}</pre>` : text}</div>
      </div>
    `;
    
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

    const cleanText = text
      .replace(/[^\x00-\x7F]+/g, " ")
      .replace(/\n/g, ". ")
      .replace(/\s{2,}/g, " ")
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = "en-US";
    utterance.rate = 1;

    micBtn.disabled = true;
    micBtn.classList.add("disabled");

    utterance.onend = () => {
      micBtn.disabled = false;
      micBtn.classList.remove("disabled");
      if (callback) callback();
    };

    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
  }

  function clearDefaultMessages() {
    if (!conversationStarted) {
      chatMessages.innerHTML = "";
      conversationStarted = true;
    }
  }

  function addReminderBox() {
    const reminderText = "You can ask about flights, hotels, weather, attractions or routes. Say 'exit' to quit.";
    appendMessage("bot", reminderText);
    speakText(reminderText);
  }

  function normalizeCityName(city) {
    const corrections = {
      "del": "Delhi",
      "hyd": "Hyderabad",
      "chen": "Chennai",
      "mum": "Mumbai",
      "beng": "Bangalore",
      "bom": "Mumbai",
      "blr": "Bangalore",
      "chn": "Chennai",
      "delhi": "Delhi",
      "hyderabad": "Hyderabad",
      "mumbai": "Mumbai",
      "chennai": "Chennai",
      "bangalore": "Bangalore",
      "kolkata": "Kolkata",
      "pune": "Pune"
    };
    
    const lowerCity = city.toLowerCase().trim();
    return corrections[lowerCity] || city;
  }

  async function getCoordinates(city) {
    if (cityCache[city]) return cityCache[city];

    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(city)}`
      );
      const data = await res.json();
      if (data.length > 0) {
        const coords = [parseFloat(data[0].lat), parseFloat(data[0].lon)];
        cityCache[city] = coords;
        return coords;
      }
    } catch (err) {
      console.error(`Error fetching coordinates for ${city}:`, err);
    }
    return null;
  }

  function showRouteOnMap(originLat, originLng, destLat, destLng) {
    // Clear previous route if exists
    if (routingControl) {
      map.removeControl(routingControl);
      routingControl = null;
    }
    
    // Clear existing markers
    map.eachLayer(layer => {
      if (layer instanceof L.Marker) {
        map.removeLayer(layer);
      }
    });

    // Add markers for origin and destination
    const originMarker = L.marker([originLat, originLng]).addTo(map);
    const destMarker = L.marker([destLat, destLng]).addTo(map);
    
    // Create route
    routingControl = L.Routing.control({
      waypoints: [
        L.latLng(originLat, originLng),
        L.latLng(destLat, destLng)
      ],
      routeWhileDragging: false,
      show: false,
      addWaypoints: false,
      fitSelectedRoutes: true,
      lineOptions: {
        styles: [{ color: '#4B0082', opacity: 0.8, weight: 5 }]
      }
    }).addTo(map);

    routingControl.on('routesfound', function(e) {
      const routes = e.routes;
      if (routes && routes.length) {
        const route = routes[0];
        const summary = `Route distance: ${(route.summary.totalDistance / 1000).toFixed(1)} km, 
                        Estimated time: ${Math.round(route.summary.totalTime / 60)} minutes`;
        appendMessage("bot", summary);
      }
    });

    // Fit map to show both points
    const bounds = new L.LatLngBounds(
      [originLat, originLng],
      [destLat, destLng]
    );
    map.fitBounds(bounds, { padding: [50, 50] });
  }

  async function handleUserQuery(message) {
    const text = message.trim().toLowerCase();

    // Route Query
    const routeRegex = /(?:route|directions|how to go|get to|travel to|travel from)\s+(?:from|between)?\s*([a-zA-Z\s]+?)\s+(?:to|and)\s+([a-zA-Z\s]+)/i;
    const routeMatch = text.match(routeRegex);

    if (routeMatch) {
      const originCity = normalizeCityName(routeMatch[1].trim());
      const destCity = normalizeCityName(routeMatch[2].trim());

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
          const msg = `🗺️ Showing route from ${originCity} to ${destCity}`;
          appendMessage("bot", msg);
          speakText(msg);
        } else {
          const errorMsg = `⚠️ Sorry, I couldn't find route data for ${originCity} to ${destCity}`;
          appendMessage("bot", errorMsg);
          speakText(errorMsg);
        }
      } catch (error) {
        console.error("Route fetch error:", error);
        const errorMsg = "⚠️ Something went wrong while fetching the route";
        appendMessage("bot", errorMsg);
        speakText(errorMsg);
      }
      return;
    }

    // Normal Queries
    clearDefaultMessages();
    const botDiv = appendMessage("bot", "⏳ Fetching the best results, please wait...");

    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      const data = await response.json();
      botDiv.querySelector('.message-text').innerHTML = `<pre>${data.response}</pre>`;
      speakText(data.response, () => {
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
      botDiv.querySelector('.message-text').innerHTML = `<p>⚠️ Sorry, something went wrong. Try again!</p>`;
    }

    scrollToBottom();
  }

  function sendMessage() {
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
    
    // Clear map
    if (routingControl) {
      map.removeControl(routingControl);
      routingControl = null;
    }
    map.eachLayer(layer => {
      if (layer instanceof L.Marker) {
        map.removeLayer(layer);
      }
    });
    map.setView([20.5937, 78.9629], 5);
    
    if (speechSynthesis.speaking) speechSynthesis.cancel();
    speakIntroLines();
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
      <div class="message-content">
        <i class="fas fa-robot message-icon"></i>
        <div class="message-text">
          <p>Hello! I'm your voice travel assistant ✈️. How can I help you today?</p>
        </div>
      </div>
    </div>
    <div class="chat-message bot">
      <div class="message-content">
        <i class="fas fa-robot message-icon"></i>
        <div class="message-text">
          <p>You can ask about flights, hotels, weather, attractions or routes. Say 'exit' to quit or click + icon for new chat.</p>
        </div>
      </div>
    </div>
    <br>
    <div class="chat-message user suggestion" data-text="Help me to book hotel at delhi">
      <div class="message-content">
        <i class="fas fa-user message-icon"></i>
        <div class="message-text">
          <p>🏨 Help me to book hotel at delhi</p>
        </div>
      </div>
    </div>
    <div class="chat-message user suggestion" data-text="What's the weather like in Chennai">
      <div class="message-content">
        <i class="fas fa-user message-icon"></i>
        <div class="message-text">
          <p>🌦️ What's the weather like in Chennai</p>
        </div>
      </div>
    </div>
    <div class="chat-message user suggestion" data-text="Suggest top attractions in delhi">
      <div class="message-content">
        <i class="fas fa-user message-icon"></i>
        <div class="message-text">
          <p>🏝️ Suggest top attractions in delhi</p>
        </div>
      </div>
    </div>
    <div class="chat-message user suggestion" data-text="Book return flight to hyderabad">
      <div class="message-content">
        <i class="fas fa-user message-icon"></i>
        <div class="message-text">
          <p>✈️ Book return flight to hyderabad</p>
        </div>
      </div>
    </div>
    <div class="chat-message user suggestion" data-text="Show route from Mumbai to Delhi">
      <div class="message-content">
        <i class="fas fa-user message-icon"></i>
        <div class="message-text">
          <p>🗺️ Show route from Mumbai to Delhi</p>
        </div>
      </div>
    </div>
  `;
  }

  // Initialize
  initMap();
  chatMessages.innerHTML = defaultIntroMessages();
  speakIntroLines();

  // Event Listeners
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