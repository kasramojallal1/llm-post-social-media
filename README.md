# 🤖 LLM-Post-Social-Media

This project is about building an **AI assistant that crafts LinkedIn posts** tailored to a user’s profile using modern data + LLM pipelines.  

---

## 🛠 Tools & Tech (planned in the flow)
- **AWS** (SageMaker for training, Lambda for orchestration, S3 for storage)  
- **MongoDB** (raw data storage)  
- **Qdrant** (vector database for embeddings & retrieval)  
- **RabbitMQ** (messaging between pipelines)  
- **Bytewax** (stream processing for cleaning & chunking)  
- **Comet** (experiment tracking & model registry)  
- **Opik** (model evaluation)  

---

## 🔄 Flow

### 1. Data Collection
Raw sources are ingested from LinkedIn, GitHub, Resume, and AI/ML/DL news.  
Data is normalized into JSON/JSONL and stored in **MongoDB**.

### 2. Feature Pipeline
Documents are cleaned, chunked, embedded with LLM-based models, and stored in **Qdrant** for semantic retrieval.  
Processing and updates are streamed through **Bytewax**, with **RabbitMQ** ensuring reliable communication between stages.

### 3. Training
Instruction-style datasets are generated from user content.  
Fine-tuning is performed with **QLoRA** on **AWS SageMaker**, tracked in **Comet**, and evaluated via **Opik**.  
The best-performing models are pushed to a registry.

### 4. Inference
Deployed models are served on **SageMaker endpoints**, enhanced with RAG queries from **Qdrant**.  
Requests flow through **AWS Lambda** for orchestration.  
An optional UI layer allows direct interaction, monitoring, and drafting LinkedIn posts.