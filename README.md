# 🤖 LLM-Post-Social-Media

This project is about building an **AI assistant that crafts LinkedIn posts** tailored to a user’s profile.  
The goal: help users share frequent, relevant posts that match their style, increase visibility, and attract recruiters.  

### 🛠 Tools & Tech
- **Python** for orchestration and extractors  
- **MongoDB** (via Docker) for storing raw documents  
- **PyPDF2** for PDF parsing  
- **GitHub REST API** for repo crawling  
- **feedparser** for news feeds (AI/ML/DL papers & blogs)  
- **dotenv** for config management  

---

## 🔄 Current Flow

### 1. Config
- Simple `config.yaml` stores user profile links (LinkedIn, GitHub, Resume).

### 2. Data Collection
- **Resume Extractor** (`resume.py`) → pulls raw text from a resume PDF.  
- **LinkedIn Extractor** (`linkedin.py`) → pulls raw text from a LinkedIn profile PDF.  
- **GitHub Extractor** (`github.py`) → crawls all repos, collects root files + README text.  
- **News Extractor** (`news.py`) → scrapes RSS feeds (last 7 days) for AI/ML/DL research updates.

All outputs are stored in `processed/` as JSON/JSONL.

### 3. Orchestration
- **`main.py`** runs all extractors in one go and refreshes processed data.

### 4. Storage
- **`load_to_mongo.py`** loads everything from `processed/` into MongoDB  
  → database: `postcraft`, collection: `raw_docs`.  
- Current state: ✅  resume, linkedin, github, and news successfully inserted.

---

At this point:  
We have a **working data collection pipeline** with MongoDB storage as the raw source of truth.  
Next steps will involve **feature processing → chunking → embeddings → vector database**.