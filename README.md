# JJikEoVoCa Backend Server
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![OpenSSL](https://img.shields.io/badge/OpenSSL-721412?style=for-the-badge&logo=openssl&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Google Cloud](https://img.shields.io/badge/GoogleCloud-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white)

This repository provides Python-based TCP/IP socket server architecture designed for a comprehensive English vocabulary learning application. The backend manages user wordbooks, integrates a Retrieval-Augmented Generation (RAG) AI chatbot for personalized coaching, processes image-to-text OCR for scanning vocabulary, and evaluates pronunciation via Speech-to-Text (STT) APIs.

---

## Repository Structure
```
.
├── handlers/               # Client API request (Intention) routers
│   ├── authentication_handler.py
│   ├── chatbot_handler.py  # RAG-based AI conversation & stat analysis
│   ├── dictionary_handler.py
│   └── ...                 
├── lib/                    # Core business logic and external API clients
│   ├── ai_client.py        # Gemini API wrapper for generation & embedding
│   ├── db_manager.py       # Thread-safe SQLite Connection Pool manager
│   ├── hybridToText.py     # Hybrid OCR combining Vision API + Gemini
│   ├── similarity_checker.py # CMU & Double Metaphone pronunciation scoring
│   └── vector_store.py     # ChromaDB vector storage for RAG memory
├── res/                    # Static resources, DBs, and Logs (Auto-generated)
│   ├── cert/               # TLS certificates (`server.crt`, `server.key`)
│   ├── database/           # SQLite (`app.db`) & ChromaDB storage
│   └── logs/               
├── tests/                  # Test scripts and fixtures (Audio/Images)
├── utils/                  # Utility modules (Data transmission, Hashing, etc.)
│   ├── audio_converter.py  # In-memory FFmpeg audio codec conversion
│   └── data_transmitter.py # Custom TCP socket buffer & JSON transmission
├── config.py               # Global configuration and environment variables
├── main.py                 # Multithreaded TLS socket server entry point
└── requirements.txt        # Python package dependencies
```
---
## Prerequisites
>**IMPORTANT** : This server relies on specific audio conversion tools and cloud credentials.

1. **Python 3.10+**
2. **FFmpeg**: Must be installed and added to the system `PATH` to handle dynamic 
audio codec conversions (e.g., converting client audio to `pcm_s16le` 16kHz wav).
3. **Google Cloud Credentials**: Requires a valid `my-service-account-key.json`
for Cloud Vision and Google Speech-to-Text APIs.
4. **Gemini API Key**: Required for the Generative AI and Text Embedding models.

---

## **Installation & Setup**
1. **Install Python dependencies**:\
   ```bash
    pip install -r requirements.txt
    ```
   
2. **Environment Varaiables (.env)**:\
    Create a `.env` file in the root directory and add your Gemini API key.
    ```python
     GEMINI_API_KEY=your_actual_api_key_here
    ```
   
3. **Service Account Key**:\
    Place your Google Cloud credentials file (`my-service-account-key.json`) in the project root.

4. **TLS Certificates**:\
    Place your SSL certificates (`server.crt` and `server.key`) inside 
    the res/cert/ directory to enable encrypted socket communication.

---

## **Usage**
Start the main server:
```bash
    python main.py
```
By default, the server binds to `0.0.0.0:2121` and spawns a thread pool 
for incoming connections.

- **Graceful Shutdown**:
Inside the interactive terminal running the server, simply type shutdown and 
press Enter. The server will safely close active TLS connections and database 
pools before exiting

---

## **Custom Communication Protocol (JSON over TCP)**
Unlike standard HTTP interfaces, this server communicates using a **custom TCP Socket payload** wrapped in TLS.

- **Payload Structure**\
    Every transmission must be prefixed with a 4-byte unsigned integer (Big-Endian) representing the exact 
byte length of the following JSON string.

    `[4-Byte Length Header] + [JSON String]`

- **Standard JSON Format**\
The JSON payload **must** contain an `intention` (acting as the routing endpoint) and a `payload` (the actual data).

- **Client Request Example (Authentication)**:
```json
{
  "intention": "Authentication",
  "payload": {
    "email": "user@example.com",
    "nickname": "Student1",
    "image": "profile_url",
    "oneline": "Hello!"
  }
}
```

- **Server Response Example**:
```json
{
  "status": "ACCEPT",
  "code": "EXISTING_USER",
  "payload": {
    "uid": "1234",
    "nickname": "Student1",
    "email": "user@example.com",
    "image": "profile_url",
    "oneline": "Hello!"
  }
}
```
***Note**: The server handles errors by returning a `status: "REJECT"` or `"ERROR"` with corresponding error messages.*

---

## Troubleshooting
- **"Codec Mismatch" Warning in Logs**:\
The client sent an audio format that Google STT cannot natively process. The server will automatically invoke FFmpeg (`audio_converter.py`) to convert it to a 16kHz mono WAV in memory. Ensure FFmpeg is installed if this step fails.

- **"FileNotFoundError: [Errno 2] No such file or directoryres/cert/server.crt"**:\
You are missing the TLS certificates. You must generate self-signed certificates or obtain valid ones and place them in the correct path.

- **Database Concurrency Errors**: \
The SQLite database (`app.db`) uses `PRAGMA journal_mode=WAL` and a custom
connection pool. If you encounter locking issues during local testing,
ensure you are not opening the .db file exclusively with external DB 
viewers while the server is running.

---
## License & Acknowledgments

This source code is tailored specifically for the Team Soncoding.

**Acknowledgements
- AI service architecture and `STT_google.py`, `T2T.py`, `ai_client.py`, `hybridToText.py`, `imageToText.py`, `service.py`, `vector_store.py` are written by **Yongwoo Lee**.
- Other codes are written by **Wooyong Eom**.

---
_Last Updated: March 13, 2026_ 
