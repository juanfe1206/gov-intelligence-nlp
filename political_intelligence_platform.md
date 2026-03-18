# 🧠 Political Intelligence Platform (Spain)
### Project Information Document (MVP)

## 📌 1. Overview
This project is a **political intelligence platform** designed for political parties in Spain. It collects public political discourse from online platforms, processes it using machine learning, and provides structured insights through a dashboard and an LLM-powered query interface.

The system transforms large volumes of unstructured online data into **actionable insights**, enabling political teams to better understand public opinion, track trends, and make informed strategic decisions.

## 🎯 2. Objective
- Monitor public opinion across multiple online platforms  
- Identify key political topics and sentiment trends  
- Detect emerging issues and shifts in discourse  
- Provide data-driven answers to natural language queries  
- Offer strategic recommendations when requested  

## 👥 3. Target Users
- Political party strategy teams  
- Campaign managers  
- Communications teams  
- Policy analysts  

## 💡 4. Core Value Proposition
This platform converts **noisy, fragmented public discourse** into:
- Structured insights  
- Quantifiable trends  
- Queryable intelligence  

## ⚙️ 5. System Architecture

### 5.1 Data Collection Layer
Sources (MVP):
- X (Twitter)  
- Threads  
- Bluesky  
- Reddit  

Collected fields:
- text  
- platform  
- date  
- url/reference  
- engagement metrics  
- language  

### 5.2 Raw Data Storage
All collected data is stored in its original form to maintain a **source of truth**.

### 5.3 ML Processing Layer
Extracted features:
- Topic  
- Subtopic  
- Sentiment  
- Target  
- Intensity  
- Timestamp  
- Platform  

### 5.4 Topic Taxonomy (MVP)
- Economy  
- Housing  
- Immigration  
- Healthcare  
- Education  
- Employment  
- Taxation  
- Security  
- Environment  
- Corruption  
- Social Policy  
- Infrastructure  

### 5.5 Structured Database
| Field | Description |
|------|------------|
| text | original content |
| topic | main category |
| subtopic | refined classification |
| sentiment | polarity |
| target | entity discussed |
| intensity | strength |
| date | timestamp |
| platform | source |

### 5.6 Analytics & Dashboard Layer
- Sentiment trends over time  
- Most discussed topics  
- Most negative topics  
- Platform comparison  
- Topic spikes  

### 5.7 Retrieval + LLM Layer (RAG)
1. User query  
2. Data retrieval  
3. Aggregation  
4. LLM response grounded in data  

### 5.8 Agentic Layer
Provides strategic recommendations when requested:
- Messaging improvements  
- Policy suggestions  
- Risk alerts  

## 🔎 6. Query Capabilities
- What are people saying about housing?  
- Which topics are most negative?  
- Compare sentiment between parties  
- Suggest strategies  

## 📊 7. Key Features (MVP)
- Multi-platform ingestion  
- Sentiment + topic classification  
- Structured dataset  
- LLM query interface  
- Dashboard  

## 📈 8. Future Features
- Trend detection  
- Early warning system  
- Stance detection  
- Geographic analysis  
- Issue ownership  

## ⚠️ 9. Challenges
- Source bias  
- Political language complexity  
- Topic consistency  
- Cost management  

## 🧱 10. Tech Stack
- Backend: FastAPI  
- ML: HuggingFace / OpenAI  
- DB: PostgreSQL + Vector DB  
- Frontend: React  

## 🧾 11. Pitch
We are building a political intelligence platform for Spain that aggregates public opinion from platforms such as X, Threads, Bluesky, and Reddit. The system uses machine learning to convert unstructured political discourse into structured insights. Users can explore trends or query the system using natural language, receiving grounded insights and optional strategic recommendations.
