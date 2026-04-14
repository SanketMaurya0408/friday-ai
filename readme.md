# 🤖 Friday AI Assistant

**Friday AI** is an advanced AI-powered desktop assistant built using Python. It can perform intelligent automation tasks, control your system, interact via voice, and execute real-world actions like searching the web, opening applications, and managing tasks.

---

## 🚀 Key Features

### 🎤 Intelligent Assistant

* Voice-enabled interaction system
* Wake word detection system (`wake_manager.py`)
* Smart command processing

### 🧠 AI Agent System

* Task planning & execution (`planner.py`, `executor.py`)
* Error handling system
* Queue-based task management

### ⚙️ System Automation

* Open applications (`open_app.py`)
* Control system settings (`computer_settings.py`)
* Execute command line operations (`cmd_control.py`)
* Desktop control & automation

### 🌐 Web & Internet Features

* Web search automation (`web_search.py`)
* YouTube control & autoplay (`youtube_video.py`)
* Browser automation (`browser_control.py`)

### 📩 Communication & Utilities

* Send messages (`send_message.py`)
* Weather reporting (`weather_report.py`)
* Flight information finder (`flight_finder.py`)
* Reminder system (`reminder.py`)

### 🧠 Memory System

* Long-term memory storage (`memory_manager.py`)
* Config & memory handling system
* Stores user interactions and preferences

### 🖥️ UI & Interaction

* Custom UI interface (`ui.py`)
* Screen processing capabilities

---

## 🛠️ Tech Stack

* **Python 3**
* Speech Recognition & TTS
* Automation Libraries (OS, subprocess, etc.)
* AI APIs (OpenRouter / Gemini)
* JSON-based memory system

---

## 📂 Project Structure

```bash
Friday AI/
│── actions/
│   ├── browser_control.py
│   ├── cmd_control.py
│   ├── code_helper.py
│   ├── computer_control.py
│   ├── computer_settings.py
│   ├── desktop.py
│   ├── dev_agent.py
│   ├── file_controller.py
│   ├── flight_finder.py
│   ├── game_updater.py
│   ├── news_action.py
│   ├── open_app.py
│   ├── reminder.py
│   ├── screen_processor.py
│   ├── send_message.py
│   ├── weather_report.py
│   ├── web_search.py
│   └── youtube_video.py
│
│── agent/
│   ├── planner.py
│   ├── executor.py
│   ├── task_queue.py
│   └── error_handler.py
│
│── memory/
│   ├── memory_manager.py
│   ├── config_manager.py
│   └── long_term.json
│
│── config/
│   └── api_keys.json  ⚠️ (Do not upload publicly)
│
│── core/
│   └── prompt.txt
│
│── main.py
│── ui.py
│── wake_manager.py
│── requirements.txt
│── setup.py
│── README.md
```

---

## ▶️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/SanketMaurya0408/friday-ai.git
cd friday-ai
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Run the Assistant

```bash
python main.py
```

---
## 🔑 API Key Setup

If your API key is missing or exposed, you can generate a new one:

👉 Free Gemini API key: https://aistudio.google.com/apikey

Then open the file:

```bash
config/api_keys.json
```

Update it like this:

```json
{
    "gemini_api_key": "your_existing_key_here",
    "newsdata_api_key": "pub_xxxxxxxxxxxxxxxxxxxxxxxx"
}
```

⚠️ Important:

* Never share your API keys publicly
* If exposed, regenerate immediately
* Always keep `api_keys.json` in `.gitignore`

## ⚠️ Security Note

* Do NOT upload `api_keys.json` publicly
* Use environment variables or `.env` file instead

---

## 📸 Demo

*Add screenshots or GIF of your UI here*

---

## 🔮 Future Enhancements

* Emotion detection system
* Always-on voice listening
* Advanced GUI dashboard
* Self-learning AI capabilities
* Multi-language support

---

## 👨‍💻 Author

**Sanket Maurya**
Machine Learning Engineer 🚀

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!
