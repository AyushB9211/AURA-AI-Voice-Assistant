"""
AURA 0.4 — Pro Edition (voice + text hybrid)
personal hybrid AI assistant.
Features:
    - Voice + text hybrid input (tries mic first, falls back to typing)
    - Smart YouTube playback, Google search, Weather, News, Wikipedia
    - Offline fallbacks, friendly tone variations, and simple app/music control
    - No wake word required — always ready in the loop
"""
from dotenv import load_dotenv
import os
import datetime
import random
import re
import webbrowser
import requests
import time
import sys


# Load API keys from .env file
load_dotenv()

OPENWEATHER_API = os.getenv("OPENWEATHER_API")
NEWS_API = os.getenv("NEWS_API")


# ----------------- USER CONFIG -----------------
USER_NAME = "User"        # change your name here
DEFAULT_CITY = "Mumbai,IN"  # change your city here
MUSIC_FOLDER = "Music"      # optional
# ------------------------------------------------


# ----------------- Required modules -----------------
MISSING = []
try:
    import pyttsx3
except Exception:
    MISSING.append("pyttsx3")

try:
    import pywhatkit
except Exception:
    MISSING.append("pywhatkit")

try:
    import wikipedia
except Exception:
    MISSING.append("wikipedia")

# Optional niceties
try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import pyjokes
except Exception:
    pyjokes = None

if MISSING:
    print("Missing modules:", ", ".join(MISSING))
    print("Install with: pip install " + " ".join(MISSING))
    # We'll still let the user run if they want to only use text features
    # but some features will fail if required modules are missing.


# ----------------- TTS SETUP -----------------
engine = None
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    # friendly default voice selection with fallback
    engine.setProperty('voice', voices[1].id if len(voices) > 1 else voices[0].id)
    engine.setProperty('rate', 170)
except Exception as e:
    print("Warning: TTS (pyttsx3) not available:", e)
    engine = None

# small set of emotional responses to vary tone
_POSITIVE = ["Sure thing!", "On it!", "Got you!", "Right away!", "Absolutely!"]
_NEUTRAL = ["Okay.", "Alright.", "Done."]
_NEGATIVE = ["Oops, can't do that right now.", "Sorry, I couldn't complete that."]

def speak(text, tone="neutral"):
    """Speak + print. tone in ['positive','neutral','negative'] for variation."""
    if tone == "positive":
        prefix = random.choice(_POSITIVE) + " "
    elif tone == "negative":
        prefix = random.choice(_NEGATIVE) + " "
    else:
        prefix = ""
    out = prefix + str(text)
    print("AURA:", out)
    if engine:
        try:
            engine.say(out)
            engine.runAndWait()
        except Exception as e:
            print("TTS error:", e)

# ----------------- INPUT (voice + text hybrid) -----------------
def take_command(timeout=6):
    """
    Try to use microphone (SpeechRecognition) first.
    If unavailable, or recognition fails, fallback to text input.
    Returns lowercase string.
    """
    # Try speech recognition if available
    if sr is not None:
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                print("Listening (say something) ...")
                recognizer.pause_threshold = 1
                audio = recognizer.listen(source, timeout=timeout)
            try:
                text = recognizer.recognize_google(audio, language='en-in')
                print("You said:", text)
                return text.lower()
            except sr.UnknownValueError:
                speak("I didn't catch that. Please type it or try again.", "neutral")
            except sr.RequestError:
                speak("Speech recognition service unavailable — please type your command.", "negative")
        except Exception as e:
            # mic problems — likely no mic or permission/driver issue
            print("Microphone not available or failed:", e)
    # Text fallback
    try:
        return input("Type your command: ").lower()
    except KeyboardInterrupt:
        speak("Interrupted. Exiting.", "neutral")
        sys.exit(0)

# ----------------- INTERNET HELPERS -----------------
def internet_available():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except Exception:
        return False
def smart_google_search(query):
    q = re.sub(r"(search|google|find|look up|for|about)", "", query, flags=re.IGNORECASE).strip()
    if not q:
        q = input("What should I search for? ")
    speak(f"Searching Google for {q}", "neutral")
    webbrowser.open(f"https://www.google.com/search?q={q}")

def play_on_youtube(query):
    # Clean query and add context
    q = query.lower().strip()
    q = re.sub(r"\b(play|on youtube|search|video|song|music|for|the|a|an)\b", "", q).strip()
    if "song" in query or "music" in query:
        q = (q + " song").strip()
    elif "news" in query:
        q = (q + " news").strip()
    elif "movie" in query or "trailer" in query:
        q = (q + " movie trailer").strip()
    if not q:
        q = input("What should I play on YouTube? ")
    speak(f"Searching and playing {q} on YouTube...", "positive")
    try:
        pywhatkit.playonyt(q)
        time.sleep(2)
        speak(f"Now playing {q} on YouTube.", "neutral")
    except Exception as e:
        print("pywhatkit error:", e)
        search_url = f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}"
        webbrowser.open(search_url)
        speak("I opened YouTube search results instead.", "neutral")

def wiki_search(query):
    q = re.sub(r"(who is|what is|tell me about|explain|define|wiki|wikipedia)", "", query, flags=re.IGNORECASE).strip()
    if not q:
        q = input("What should I look up on Wikipedia? ")
    speak(f"Searching Wikipedia for {q}", "neutral")
    try:
        result = wikipedia.summary(q, sentences=2)
        speak(result, "neutral")
    except wikipedia.exceptions.DisambiguationError:
        speak("There are multiple possible entries. Please be more specific.", "neutral")
    except Exception:
        speak("I couldn't find anything on that topic.", "negative")

def get_weather(query):
    city = DEFAULT_CITY.split(",")[0]

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API}&units=metric"

    try:
        response = requests.get(url).json()
        temp = response["main"]["temp"]
        desc = response["weather"][0]["description"]
        speak(f"The temperature in {city} is {temp} degree Celsius with {desc}.", "neutral")
    except:
        speak("Unable to fetch weather. Please check your API key.", "negative")

def get_news(query):
    url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API}"

    try:
        response = requests.get(url).json()
        articles = response["articles"][:5]

        speak("Here are top news headlines.", "positive")
        for i, article in enumerate(articles, 1):
            speak(f"News {i}: {article['title']}", "neutral")
    except:
        speak("Unable to fetch news. Please check your API key.", "negative")

# ----------------- OFFLINE FEATURES -----------------

def tell_time():
    time_now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The current time is {time_now}")

def tell_date():
    today = datetime.date.today().strftime("%d %B %Y")
    speak(f"Today's date is {today}")

def tell_joke():
    if pyjokes:
        speak(pyjokes.get_joke(), "positive")
    else:
        speak("Joke feature not available. Install pyjokes module.")


# ----------------- GREETING -----------------
def greet_user():
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12:
        speak(f"Good morning {USER_NAME}! I am AURA, your AI assistant.", "positive")
    elif 12 <= hour < 18:
        speak(f"Good afternoon {USER_NAME}! I am AURA, your AI assistant.", "positive")
    else:
        speak(f"Good evening {USER_NAME}! I am AURA, your AI assistant.", "positive")

    speak("I am ready. How may I help you?", "neutral")

# ----------------- MAIN LOOP -----------------
def run_aura():
    greet_user()
    while True:
        query = take_command()
        if not query or query.strip() == "":
            continue
        q = query.lower()
    
        # ---- Online features ----
        if any(word in q for word in ["weather", "temperature", "forecast"]):
            if internet_available():
                get_weather(q)
            else:
                speak("No internet connection—can't fetch weather.", "negative")
        elif "news" in q:
            if internet_available():
                get_news(q)
            else:
                speak("No internet connection—can't fetch news.", "negative")
        elif "youtube" in q or ("play" in q and "on youtube" in q) or ("play" in q and "music" in q and "youtube" in q):
            if internet_available():
                play_on_youtube(q)
            else:
                speak("No internet connection—can't play YouTube.", "negative")
        elif any(word in q for word in ["search", "google", "find", "look up"]):
            if internet_available():
                smart_google_search(q)
            else:
                speak("No internet connection—can't perform web searches.", "negative")
        elif any(word in q for word in ["who is", "what is", "tell me about", "define", "wikipedia", "wiki"]):
            if internet_available():
                wiki_search(q)
            else:
                speak("No internet connection—Wikipedia requires internet.", "negative")
        elif any(word in q for word in ["exit", "quit", "shutdown", "goodbye", "bye"]):
            speak(f"Goodbye {USER_NAME}! Shutting down AURA. See you soon.", "positive")

        elif "time" in q:
            tell_time()

        elif "date" in q:
            tell_date()

        elif "joke" in q:
            tell_joke()

            break
        else:
            # Fallback help suggestion
            speak("Sorry, I don't know that yet. Try asking about weather, YouTube, Wikipedia, or a Google search.", "neutral")

def show_banner():
    print("\n==============================")
    print("   AURA AI Assistant v1.0")
    print("==============================\n")
if __name__ == "__main__":
    show_banner()
    run_aura()



