# System Architecture

This document provides a detailed overview of the Firmable AI Agent's architecture, illustrating how the components interact to provide autonomous website analysis and context-aware chat.

## High-Level Architecture Diagram

```mermaid
graph TD
    %% Nodes
    Client([Client / Frontend])
    
    subgraph "Application Server (FastAPI)"
        API[API Endpoints]
        Scraper[Web Scraper Module]
        AISvc[AI Service Layer]
        VecMgr[Vector Store Manager]
    end

    subgraph "External Cloud Services"
        Groq[Groq API<br/>(Llama 3 / Mixtral)]
        Pinecone[Pinecone Serverless<br/>(Vector DB + Inference)]
    end

    subgraph "Persistence"
        SQLite[(SQLite DB<br/>Chat History)]
    end

    %% Flows
    Client -->|POST /analyze| API
    Client -->|POST /chat| API

    %% Analysis Flow
    API -->|1. Trigger Scrape| Scraper
    Scraper -->|2. Raw Content| AISvc
    AISvc -->|3. Upsert Chunks| VecMgr
    VecMgr -->|4. Index Records| Pinecone
    AISvc -->|5. Analyze Content| Groq
    Groq -- JSON --> API

    %% Chat Flow
    API -->|1. Query| AISvc
    AISvc -->|2. Check State| SQLite
    AISvc -->|3. Retrieval Query| VecMgr
    VecMgr -->|4. Semantic Search| Pinecone
    Pinecone -- Context --> AISvc
    AISvc -->|5. Generate Answer| Groq
    Groq -- Response --> API
    AISvc -->|6. Save State| SQLite
```

## Component Overview

### 1. Application Layer (FastAPI)
The core entry point for the system.
-   **Security**: Implements Bearer Token authentication.
-   **Rate Limiting**: Uses `SlowAPI` to prevent abuse (e.g., 5 requests/minute for analysis).
-   **Request Validation**: Utilizes `Pydantic` models to ensure strict data schemas for inputs and outputs.
-   **Async Architecture**: Fully asynchronous route handlers to handle non-blocking I/O for scraping and API calls.

### 2. Deep Web Scraper
-   **Logic**: Located in `app/scraper.py`.
-   **Capabilities**: Performs a Breadth-First Search (BFS) crawl with a depth of 3.
-   **Filtering**: Intelligently ignores non-content pages (login, signup, policies) to focus on business value.
-   **Output**: Returns a structured list of pages with clean text content.

### 3. Dynamic Vector Store (Pinecone)
Managed by `app/vector_store.py`.
-   **Dynamic Indexing**: Creates a *separate, isolated index* for each unique website domain.
    -   *Example*: `https://tesla.com` -> Index `idx-tesla-a1b2c3d4`
-   **Serverless Inference**: 
    -   We do **not** generate embeddings locally (e.g., using OpenAI or HuggingFace libraries).
    -   Instead, we use Pinecone's `llama-text-embed-v2` model running on their serverless infrastructure.
    -   We simply send text chunks, and Pinecone handles the vectorization and storage.
-   **Querying**: Uses RAG (Retrieval-Augmented Generation) to find the top-k most relevant text chunks for a user query.

### 4. Intelligence Layer (Groq)
Managed by `app/ai.py`.
-   **Provider**: Groq.
-   **Model**: Integrated with models like `llama-3-70b-8192` or `gpt-oss-120b` for ultra-low latency inference.
-   **Tasks**:
    -   **Structured Analysis**: Extracts strictly formatted JSON (Company Info, Sentiment, Contacts) from raw text.
    -   **Chat**: Engages in natural language conversations grounded in the retrieved website context.

### 5. Orchestration (LangGraph & SQLite)
-   **LangGraph**: Manages the control flow of the chat agent. It represents the conversation as a graph of states (`StateGraph`).
-   **Persistence**: 
    -   Uses `AsyncSqliteSaver` to store specific checkpoints of the conversation graph.
    -   This allows the user to resume a conversation thread (`thread_id`) at any time, maintaining perfect memory of previous turns.

## Data Flow Details

### Analysis Pipeline
1.  **User** submits a URL.
2.  **Scraper** fetches HTML, parses text, and traverses links.
3.  **Vector Store Manager** chunks the text (1000 chars) and creates a designated Pinecone index.
4.  **Pinecone** embeds and indexes the chunks.
5.  **Groq** is prompted with the full homepage text to generate a high-level extracted summary (JSON).
6.  **Results** are returned to the user.

### Chat Pipeline (RAG)
1.  **User** asks a question about a specific URL + `thread_id`.
2.  **Vector Store** converts the question into a semantic query for that URL's specific Pinecone index.
3.  **Context** is retrieved (top 5 relevant chunks).
4.  **System Prompt** is constructed dynamically: *"You are an assistant. Answer ONLY using this context: [Context]..."*
5.  **LangGraph** loads previous messages for this `thread_id` from separate **SQLite** storage.
6.  **Groq** generates the answer.
7.  **LangGraph** saves the new interaction to **SQLite**.
