# 🧠 Backend Wizards — Stage 1: String Analyzer Service

Welcome to my **Stage 1** submission for the **HNG 13 Backend Internship**.  
This project implements a **RESTful API service** that analyzes strings, stores their computed properties, and allows rich filtering — including **natural-language queries**.

I built this in **FastAPI** to sharpen my Python backend skills (instead of my usual Spring Boot stack 😅).  
It was a smooth build, and I kept everything lightweight, easy to test locally, and fully spec-compliant.

---

## 🚀 Features

For each analyzed string, the API computes and stores:

| Property | Description |
|-----------|--------------|
| **length** | Number of characters in the string |
| **is_palindrome** | Whether the string reads the same forwards & backwards (case-insensitive) |
| **unique_characters** | Count of distinct characters |
| **word_count** | Number of words (split by whitespace) |
| **sha256_hash** | SHA-256 hash of the string (used as unique ID) |
| **character_frequency_map** | Dictionary mapping each character → its count |

---

## 🧩 Endpoints Overview

| Method | Endpoint | Description |
|---------|-----------|-------------|
| `POST` | `/strings` | Analyze and store a new string |
| `GET` | `/strings/{string_value}` | Retrieve one analyzed string |
| `GET` | `/strings` | Retrieve all analyzed strings (with filters) |
| `GET` | `/strings/filter-by-natural-language` | Filter using plain-English queries |
| `DELETE` | `/strings/{string_value}` | Delete a string record |

---

## 🧠 Natural-Language Filtering

You can use simple English queries like:

| Example Query | Interpreted Filters |
|----------------|--------------------|
| `all single word palindromic strings` | `word_count=1`, `is_palindrome=true` |
| `strings longer than 10 characters` | `min_length=11` |
| `strings containing the letter z` | `contains_character=z` |
| `palindromic strings that contain the first vowel` | `is_palindrome=true`, `contains_character=a` |

---

## ⚙️ Tech Stack

- **Language:** Python 3.10+
- **Framework:** [FastAPI](https://fastapi.tiangolo.com)
- **Database:** SQLite (standard library)
- **Hashing:** SHA-256 (`hashlib`)
- **Server:** Uvicorn
- **Deployment:** Local or via Ngrok / custom VPS *(Render, Vercel and Railway forbidden this cohort)*

---

## 🧑‍💻 How to Run Locally

### 1️⃣ Clone the repo
 ```bash
 git clone https://github.com/enoumanah/stage0-hng13.git
 cd stage0-hng13
```

### 2️⃣ Create a virtual environment
python -m venv venv
# activate it
venv\Scripts\activate       # on Windows
source venv/bin/activate    # on Mac/Linux

### 3️⃣ Install dependencies
pip install -r requirements.txt
# or manually
pip install fastapi uvicorn

### 4️⃣ Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000


Your API docs are now live at:

Swagger UI → http://127.0.0.1:8000/docs

ReDoc → http://127.0.0.1:8000/redoc

## 🌍 Optional: Expose via Ngrok

If you need a public URL for testing:

ngrok http 8000


Copy the https://*.ngrok-free.app URL and use it in your requests.

### 🧪 Example Requests
➕ Create / Analyze a String
curl -X POST "http://127.0.0.1:8000/strings" \
  -H "Content-Type: application/json" \
  -d '{"value": "A man a plan a canal Panama"}'

### 🔍 Get a Specific String
curl "http://127.0.0.1:8000/strings/A%20man%20a%20plan%20a%20canal%20Panama"

### 📋 List All with Filters
curl "http://127.0.0.1:8000/strings?is_palindrome=true&min_length=5"

### 🗣️ Natural Language Filter
curl "http://127.0.0.1:8000/strings/filter-by-natural-language?query=all%20single%20word%20palindromic%20strings"

### ❌ Delete a String
curl -X DELETE "http://127.0.0.1:8000/strings/your%20string"

### 📦 Project Structure
stage1-string-analyzer/
│
├── main.py               # Core FastAPI app
├── strings.db            # SQLite database (auto-created)
└── README.md             # You’re here!

### 🧾 Example Response

POST /strings

{
  "id": "a1b2c3...",
  "value": "A man a plan a canal Panama",
  "properties": {
    "length": 27,
    "is_palindrome": true,
    "unique_characters": 11,
    "word_count": 7,
    "sha256_hash": "a1b2c3...",
    "character_frequency_map": {
      "A": 3,
      " ": 6,
      "m": 2,
      "...": "..."
    }
  },
  "created_at": "2025-10-20T10:00:00Z"
}

### 🧠 Error Responses
Code	Meaning	Example
400	Invalid request or bad query params	Missing value
409	Conflict – string already exists	Duplicate string submission
404	Not found	String doesn’t exist
422	Unprocessable entity	Wrong data type for value
💡 Next Steps / Future Improvements

Add pytest suite & CI checks.

Add pagination & caching for large datasets.

Improve natural-language understanding using small LLMs.

Add lightweight authentication & rate-limiting.

Convert to Docker for portable deployment.

### 🧑‍🎓 Author

Eno Umanah
Backend Developer | Student | AI Enthusiast

git clone https://github.com/enoumanah/stage0-hng13.git
cd stage0-hng13
