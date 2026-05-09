# TongYong Agent 技术实现文档（第一阶段：基础架构）

## 阶段一：基础架构

### 1.1 项目初始化

#### 1.1.1 目录结构创建

**目标**：创建完整的项目目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── memory.py
│   │   ├── data.py
│   │   └── chart.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── context.py
│   │   └── base.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── storage.py
│   │   ├── vector.py
│   │   └── compress.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── tongyi.py
│   │   └── openai.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── file.py
│   │   ├── http.py
│   │   └── vision.py
│   └── services/
│       ├── __init__.py
│       ├── data_processor.py
│       └── exporter.py
├── requirements.txt
└── .env.example
```

**实现方式**：
- 使用 Python 创建空目录和 `__init__.py` 文件

---

#### 1.1.2 requirements.txt

**目标**：定义依赖

```
fastapi==0.109.0
uvicorn==0.27.0
python-dotenv==1.0.0
pydantic==2.5.0
sqlalchemy==2.0.25
chromadb==0.4.22
openai==1.10.0
httpx==0.26.0
python-multipart==0.0.6
pandas==2.2.0
openpyxl==3.1.2
pymupdf==1.23.26
Pillow==10.2.0
```

**实现方式**：
- 创建 requirements.txt 文件

---

### 1.2 FastAPI 入口

#### 1.2.1 main.py

**目标**：创建 FastAPI 应用入口

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import chat, memory, data, chart

app = FastAPI(
    title="TongYong Agent",
    description="通用智能体 API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(chart.router, prefix="/api/chart", tags=["chart"])

@app.get("/")
async def root():
    return {"message": "TongYong Agent API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**实现方式**：
- 创建 backend/app/main.py

**验收**：
- 访问 http://localhost:8000/ 返回 JSON
- 访问 http://localhost:8000/health 返回 {"status": "ok"}

---

#### 1.2.2 config.py

**目标**：配置管理

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "TongYong Agent"
    debug: bool = True
    
    # 数据库
    database_url: str = "sqlite:///./data/tongyong.db"
    
    # ChromaDB
    chroma_persist_directory: str = "./data/chroma"
    
    # LLM 配置
    default_llm_provider: str = "tongyi"
    tongyi_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # 记忆配置
    memory_top_k: int = 10
    compress_threshold: int = 5000
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**实现方式**：
- 创建 backend/app/config.py

---

#### 1.2.3 API 路由占位

**目标**：创建简单的 API 路由占位，避免启动报错

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello"}
```

**实现方式**：
- 创建 backend/app/api/chat.py、memory.py、data.py、chart.py

**验收**：
- FastAPI 可正常启动，无报错

---

### 1.3 前端初始化

#### 1.3.1 Vite + React 项目

**目标**：创建前端项目

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install axios echarts echarts-for-react ag-grid-react ag-grid-community
```

**实现方式**：
- 使用 Vite 创建 React + TypeScript 项目

---

#### 1.3.2 App.tsx

**目标**：创建基础页面

```tsx
import React from 'react'

function App() {
  return (
    <div>
      <h1>Hello World</h1>
    </div>
  )
}

export default App
```

**实现方式**：
- 修改 frontend/src/App.tsx

---

#### 1.3.3 代理配置

**目标**：配置代理解决跨域

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**实现方式**：
- 修改 vite.config.ts

**验收**：
- 访问 http://localhost:5173 显示 "Hello World"

---

### 1.4 测试验收

| 测试项 | 预期结果 | 验收条件 |
|--------|----------|----------|
| 后端启动 | uvicorn 启动成功 | 无报错 |
| / 端点 | 返回 JSON | 返回 {"message": "TongYong Agent API", "version": "0.1.0"} |
| /health 端点 | 返回 {"status": "ok"} | 状态码 200 |
| 前端启动 | Vite 启动成功 | 页面显示 "Hello World" |
| 联调 | 前后端可通信 | API 请求正常 |

---

### 1.5 启动命令

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm run dev
```

---

## 阶段二：核心引擎 + 记忆模块

### 2.1 核心引擎骨架

#### 2.1.1 base.py

**目标**：定义基础接口

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None

class Session(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str

class Memory(BaseModel):
    id: str
    type: str
    content: str
    importance: int
    session_id: Optional[str] = None
    created_at: str

class ToolResult(BaseModel):
    tool: str
    success: bool
    result: Any
    error: Optional[str] = None
```

**实现方式**：
- 创建 backend/app/core/base.py

---

#### 2.1.2 context.py

**目标**：上下文管理

```python
from typing import List, Optional
from datetime import datetime
from app.core.base import Message, Session

class ContextManager:
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.messages: List[Message] = []
    
    def add_message(self, role: str, content: str) -> Message:
        message = Message(
            role=role,
            content=content,
            created_at=datetime.now().isoformat()
        )
        self.messages.append(message)
        return message
    
    def get_messages(self) -> List[Message]:
        return self.messages
    
    def get_context_str(self) -> str:
        return "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in self.messages
        ])
    
    def clear(self):
        self.messages = []
    
    def should_compress(self) -> bool:
        total_chars = sum(len(m.content) for m in self.messages)
        return total_chars > self.max_tokens * 4
```

**实现方式**：
- 创建 backend/app/core/context.py

---

#### 2.1.3 agent.py

**目标**：Agent 引擎

```python
from typing import Dict, List, Optional, Any
from app.core.base import Message, Session, Memory, ToolResult
from app.core.context import ContextManager
from app.memory.storage import MemoryStorage
from app.memory.vector import VectorStore
from app.llm.base import BaseLLM

class AgentEngine:
    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self.context = ContextManager()
        self.memory_storage = MemoryStorage()
        self.vector_store = VectorStore()
    
    async def chat(
        self,
        session_id: Optional[str],
        message: str,
        use_memory: bool = True
    ) -> Dict[str, Any]:
        self.context.add_message("user", message)
        
        memories = []
        if use_memory:
            memories = await self.vector_store.search(message, k=3)
            if memories:
                context = "\n".join([m.content for m in memories])
                self.context.add_message("system", f"相关记忆：\n{context}")
        
        response = await self.llm.chat(
            messages=self.context.get_messages()
        )
        
        self.context.add_message("assistant", response)
        
        return {
            "reply": response,
            "session_id": session_id,
            "memory_added": [],
            "tools_used": []
        }
    
    async def create_session(self, name: str) -> Session:
        return await self.memory_storage.create_session(name)
    
    async def get_sessions(self) -> List[Session]:
        return await self.memory_storage.get_sessions()
```

**实现方式**：
- 创建 backend/app/core/agent.py

---

### 2.2 SQLite 表设计

#### 2.2.1 storage.py

**目标**：SQLite 存储

```python
import sqlite3
from typing import List, Optional
from datetime import datetime
from app.core.base import Session, Message, Memory
import os

class MemoryStorage:
    def __init__(self, db_path: str = "./data/tongyong.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path.replace("sqlite:///", "")), exist_ok=True)
        self.init_tables()
    
    def init_tables(self):
        conn = sqlite3.connect(self.db_path.replace("sqlite:///", ""))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                session_id TEXT,
                created_at TEXT NOT NULL,
                vector_id TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def create_session(self, name: str) -> Session:
        from uuid import uuid4
        session = Session(
            id=str(uuid4()),
            name=name,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        conn = sqlite3.connect(self.db_path.replace("sqlite:///", ""))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session.id, session.name, session.created_at, session.updated_at)
        )
        conn.commit()
        conn.close()
        
        return session
    
    async def get_sessions(self) -> List[Session]:
        conn = sqlite3.connect(self.db_path.replace("sqlite:///", ""))
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at, updated_at FROM sessions ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Session(id=row[0], name=row[1], created_at=row[2], updated_at=row[3])
            for row in rows
        ]
    
    async def add_message(self, session_id: str, role: str, content: str) -> Message:
        from uuid import uuid4
        message = Message(
            id=str(uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.now().isoformat()
        )
        
        conn = sqlite3.connect(self.db_path.replace("sqlite:///", ""))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, message.created_at)
        )
        conn.commit()
        conn.close()
        
        return message
    
    async def get_messages(self, session_id: str) -> List[Message]:
        conn = sqlite3.connect(self.db_path.replace("sqlite:///", ""))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, session_id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Message(id=row[0], session_id=row[1], role=row[2], content=row[3], created_at=row[4])
            for row in rows
        ]
    
    async def add_memory(self, memory: Memory) -> Memory:
        conn = sqlite3.connect(self.db_path.replace("sqlite:///", ""))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memories (id, type, content, importance, session_id, created_at, vector_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (memory.id, memory.type, memory.content, memory.importance, memory.session_id, memory.created_at, memory.vector_id)
        )
        conn.commit()
        conn.close()
        
        return memory
    
    async def get_memories(self, session_id: Optional[str] = None) -> List[Memory]:
        conn = sqlite3.connect(self.db_path.replace("sqlite:///", ""))
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute(
                "SELECT id, type, content, importance, session_id, created_at, vector_id FROM memories WHERE session_id = ? ORDER BY created_at DESC",
                (session_id,)
            )
        else:
            cursor.execute(
                "SELECT id, type, content, importance, session_id, created_at, vector_id FROM memories ORDER BY created_at DESC"
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Memory(id=row[0], type=row[1], content=row[2], importance=row[3], session_id=row[4], created_at=row[5], vector_id=row[6])
            for row in rows
        ]
```

**实现方式**：
- 创建 backend/app/memory/storage.py

---

### 2.3 ChromaDB 集成

#### 2.3.1 vector.py

**目标**：向量存储、相似搜索

```python
import chromadb
from typing import List, Optional
from app.core.base import Memory

class VectorStore:
    def __init__(self, persist_directory: str = "./data/chroma"):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name="memories",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add(self, memory: Memory, embedding: List[float]) -> str:
        self.collection.add(
            ids=[memory.id],
            documents=[memory.content],
            embeddings=[embedding],
            metadatas=[{
                "type": memory.type,
                "importance": memory.importance,
                "session_id": memory.session_id or ""
            }]
        )
        return memory.id
    
    async def search(self, query: str, embedding: List[float], k: int = 3) -> List[Memory]:
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k
        )
        
        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append(Memory(
                    id=results["ids"][0][i],
                    type=results["metadatas"][0][i].get("type", ""),
                    content=doc,
                    importance=results["metadatas"][0][i].get("importance", 1),
                    session_id=results["metadatas"][0][i].get("session_id"),
                    created_at=""
                ))
        
        return memories
    
    async def delete(self, memory_id: str):
        self.collection.delete(ids=[memory_id])
    
    async def get_all(self) -> List[Memory]:
        results = self.collection.get()
        
        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"]):
                memories.append(Memory(
                    id=results["ids"][i],
                    type=results["metadatas"][i].get("type", ""),
                    content=doc,
                    importance=results["metadatas"][i].get("importance", 1),
                    session_id=results["metadatas"][i].get("session_id"),
                    created_at=""
                ))
        
        return memories
```

**实现方式**：
- 创建 backend/app/memory/vector.py

---

#### 2.3.2 compress.py

**目标**：记忆压缩逻辑

```python
from typing import List, Dict, Any
from app.core.base import Memory
from app.llm.base import BaseLLM
import json

COMPRESS_PROMPT = """你是一个记忆提炼助手。请从以下对话中提炼出新的知识点：
- 用户操作习惯（偏好什么图表、什么时候活跃）
- 关键决策（做了什么决定、为什么）
- 重要结论（分析结果、报告结论）

规则：
1. 只提取之前记忆中没有的新信息
2. 已有的类似内容不重复存储
3. 输出格式：JSON 数组，每项含 type、content、importance（1-5）

对话内容：
{conversation}

请直接输出 JSON 数组，不要其他内容。"""

class MemoryCompressor:
    def __init__(self, llm: BaseLLM):
        self.llm = llm
    
    async def compress(
        self,
        conversation: str,
        existing_memories: List[Memory]
    ) -> List[Dict[str, Any]]:
        existing_str = "\n".join([
            f"- {m.type}: {m.content}"
            for m in existing_memories
        ])
        
        prompt = COMPRESS_PROMPT.format(
            conversation=conversation,
            existing=existing_str
        )
        
        response = await self.llm.chat_simple(prompt)
        
        try:
            new_memories = json.loads(response)
            return new_memories
        except json.JSONDecodeError:
            return []
    
    async def should_compress(self, messages: List[str]) -> bool:
        total_chars = sum(len(m) for m in messages)
        return total_chars > 5000
```

**实现方式**：
- 创建 backend/app/memory/compress.py

---

### 2.4 记忆 CRUD 接口

#### 2.4.1 memory.py

**目标**：记忆 API

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.core.base import Memory
from app.core.agent import AgentEngine

router = APIRouter()

class CreateSessionRequest(BaseModel):
    name: str

class SearchRequest(BaseModel):
    query: str
    k: int = 10

class AddMemoryRequest(BaseModel):
    type: str
    content: str
    importance: int = 1
    session_id: Optional[str] = None

@router.post("/create")
async def create_session(request: CreateSessionRequest, engine: AgentEngine = Depends(get_agent)):
    session = await engine.create_session(request.name)
    return {"session": session}

@router.get("/sessions")
async def get_sessions(engine: AgentEngine = Depends(get_agent)):
    sessions = await engine.get_sessions()
    return {"sessions": sessions}

@router.get("/{session_id}")
async def get_session_memories(session_id: str, engine: AgentEngine = Depends(get_agent)):
    memories = await engine.get_session_memories(session_id)
    return {"memories": memories}

@router.post("/search")
async def search_memories(request: SearchRequest, engine: AgentEngine = Depends(get_agent)):
    memories = await engine.search_memories(request.query, request.k)
    return {"results": memories}

@router.post("/add")
async def add_memory(request: AddMemoryRequest, engine: AgentEngine = Depends(get_agent)):
    memory = await engine.add_memory(request.type, request.content, request.importance, request.session_id)
    return {"memory": memory}

def get_agent():
    from app.main import agent_engine
    return agent_engine
```

**实现方式**：
- 修改 backend/app/api/memory.py

---

### 2.5 记忆查看器（前端）

#### 2.5.1 MemoryCard.tsx

**目标**：记忆卡片组件

```tsx
import React from 'react'
import './MemoryCard.css'

interface Memory {
  id: string
  type: string
  content: string
  importance: number
  created_at: string
}

interface MemoryCardProps {
  memory: Memory
}

function MemoryCard({ memory }: MemoryCardProps) {
  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      '操作习惯': '#1890ff',
      '分析结论': '#52c41a',
      '关键决策': '#faad14'
    }
    return colors[type] || '#666'
  }

  return (
    <div className="memory-card">
      <div className="memory-card-header">
        <span 
          className="memory-type"
          style={{ backgroundColor: getTypeColor(memory.type) }}
        >
          {memory.type}
        </span>
        <span className="memory-importance">
          {'★'.repeat(memory.importance)}
        </span>
      </div>
      <div className="memory-content">
        {memory.content}
      </div>
      <div className="memory-time">
        {new Date(memory.created_at).toLocaleString()}
      </div>
    </div>
  )
}

export default MemoryCard
```

**实现方式**：
- 创建 frontend/src/components/Memory/MemoryCard.tsx

---

#### 2.5.2 MemoryPanel.tsx

**目标**：记忆面板

```tsx
import React, { useState, useEffect } from 'react'
import MemoryCard from './MemoryCard'
import { getMemories } from '../api/memory'
import './MemoryPanel.css'

interface Memory {
  id: string
  type: string
  content: string
  importance: number
  created_at: string
}

function MemoryPanel() {
  const [memories, setMemories] = useState<Memory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadMemories()
  }, [])

  const loadMemories = async () => {
    try {
      const data = await getMemories()
      setMemories(data.memories)
    } catch (error) {
      console.error('加载记忆失败', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="memory-panel">
      <h2>记忆流</h2>
      {loading ? (
        <div className="loading">加载中...</div>
      ) : (
        <div className="memory-list">
          {memories.length === 0 ? (
            <div className="empty">暂无记忆</div>
          ) : (
            memories.map(memory => (
              <MemoryCard key={memory.id} memory={memory} />
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default MemoryPanel
```

**实现方式**：
- 创建 frontend/src/components/Memory/MemoryPanel.tsx

---

### 2.6 测试验收

| 测试项 | 预期结果 | 验收条件 |
|--------|----------|----------|
| 创建会话 | 返回会话信息 | 会话创建成功 |
| 保存消息 | 消息保存成功 | 可查询到 |
| 记忆搜索 | 返回相似记忆 | 搜索结果相关 |
| 记忆压缩 | 重复内容不重复存 | 向量库无重复 |
| 前端查看 | 显示记忆卡片 | 卡片展示正常 |

---

## 阶段三：LLM 集成

### 3.1 LLM 接口抽象

#### 3.1.1 base.py

**目标**：LLM 基础接口

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from app.core.base import Message

class BaseLLM(ABC):
    @abstractmethod
    async def chat(self, messages: List[Message]) -> str:
        pass
    
    @abstractmethod
    async def chat_simple(self, prompt: str) -> str:
        pass
    
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        pass
```

**实现方式**：
- 创建 backend/app/llm/base.py

---

### 3.2 通义千问实现

#### 3.2.1 tongyi.py

**目标**：通义千问 LLM

```python
from typing import List, Optional
from openai import OpenAI
from app.llm.base import BaseLLM
from app.core.base import Message

class TongyiLLM(BaseLLM):
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "qwen-plus"
    
    async def chat(self, messages: List[Message]) -> str:
        oai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=oai_messages
        )
        
        return response.choices[0].message.content
    
    async def chat_simple(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    async def get_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model="text-embedding-v3",
            input=text
        )
        
        return response.data[0].embedding
```

**实现方式**：
- 创建 backend/app/llm/tongyi.py

---

### 3.3 OpenAI 实现

#### 3.3.1 openai.py

**目标**：OpenAI LLM

```python
from typing import List
from openai import OpenAI
from app.llm.base import BaseLLM
from app.core.base import Message

class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4"
    
    async def chat(self, messages: List[Message]) -> str:
        oai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=oai_messages
        )
        
        return response.choices[0].message.content
    
    async def chat_simple(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    async def get_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        
        return response.data[0].embedding
```

**实现方式**：
- 创建 backend/app/llm/openai.py

---

### 3.4 配置管理

#### 3.4.1 llm_factory.py

**目标**：LLM 工厂

```python
from app.llm.base import BaseLLM
from app.llm.tongyi import TongyiLLM
from app.llm.openai import OpenAILLM
from app.config import settings

def get_llm(provider: str = None) -> BaseLLM:
    provider = provider or settings.default_llm_provider
    
    if provider == "tongyi":
        return TongyiLLM(settings.tongyi_api_key)
    elif provider == "openai":
        return OpenAILLM(settings.openai_api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

**实现方式**：
- 创建 backend/app/llm/factory.py

---

### 3.5 测试验收

| 测试项 | 预期结果 | 验收条件 |
|--------|----------|----------|
| 通义千问对话 | 返回回答 | 对话正常 |
| OpenAI 对话 | 返回回答 | 对话正常 |
| 模型切换 | 切换成功 | 可切换 |
| 向量生成 | 生成成功 | 向量可用来搜索 |

---

## 阶段四：数据处理 + 可视化

### 4.1 数据上传

#### 4.1.1 data.py

**目标**：数据处理服务

```python
from typing import Dict, Any, List, Optional
import pandas as pd
import json
from pathlib import Path

class DataProcessor:
    def __init__(self):
        self.supported_formats = {
            "csv": self.parse_csv,
            "json": self.parse_json,
            "xlsx": self.parse_excel,
            "xls": self.parse_excel,
            "pdf": self.parse_pdf,
            "png": self.parse_image,
            "jpg": self.parse_image,
            "jpeg": self.parse_image
        }
    
    async def process(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        ext = Path(filename).suffix.lower().lstrip(".")
        
        parser = self.supported_formats.get(ext)
        if not parser:
            raise ValueError(f"不支持的文件格式: {ext}")
        
        return await parser(file_data)
    
    async def parse_csv(self, data: bytes) -> Dict[str, Any]:
        import io
        df = pd.read_csv(io.BytesIO(data))
        return self.df_to_table(df)
    
    async def parse_json(self, data: bytes) -> Dict[str, Any]:
        obj = json.loads(data)
        if isinstance(obj, list):
            df = pd.DataFrame(obj)
        else:
            df = pd.DataFrame([obj])
        return self.df_to_table(df)
    
    async def parse_excel(self, data: bytes) -> Dict[str, Any]:
        import io
        df = pd.read_excel(io.BytesIO(data))
        return self.df_to_table(df)
    
    async def parse_pdf(self, data: bytes) -> Dict[str, Any]:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        text = "\n".join([page.get_text() for page in doc])
        
        return {
            "type": "text",
            "content": text,
            "columns": [{"field": "text", "header": "文本"}],
            "rows": [{"text": text}]
        }
    
    async def parse_image(self, data: bytes) -> Dict[str, Any]:
        import base64
        b64 = base64.b64encode(data).decode()
        
        return {
            "type": "image",
            "content": f"data:image/png;base64,{b64}",
            "columns": [],
            "rows": []
        }
    
    def df_to_table(self, df: pd.DataFrame) -> Dict[str, Any]:
        columns = [
            {"field": col, "header": col}
            for col in df.columns
        ]
        
        rows = df.to_dict("records")
        
        return {
            "type": "table",
            "columns": columns,
            "rows": rows,
            "rowCount": len(rows)
        }
```

**实现方式**：
- 创建 backend/app/services/data_processor.py

---

#### 4.1.2 data.py API

**目标**：数据 API

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.data_processor import DataProcessor

router = APIRouter()
processor = DataProcessor()

class DataFromUrlRequest(BaseModel):
    url: str

class DataFromClipboardRequest(BaseModel):
    content: str
    data_type: str

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    
    try:
        result = await processor.process(content, file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/url")
async def from_url(request: DataFromUrlRequest):
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(request.url)
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "")
        filename = "data." + ("xlsx" if "excel" in content_type else "csv")
        
        try:
            result = await processor.process(response.content, filename)
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@router.post("/clipboard")
async def from_clipboard(request: DataFromClipboardRequest):
    content = request.content.encode()
    filename = f"data.{request.data_type}"
    
    try:
        result = await processor.process(content, filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**实现方式**：
- 修改 backend/app/api/data.py

---

### 4.2 表格组件

#### 4.2.1 Table.tsx

**目标**：表格组件

```tsx
import React, { useState, useMemo } from 'react'
import { AgGridReact } from 'ag-grid-react'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'

interface Column {
  field: string
  header: string
}

interface TableProps {
  columns: Column[]
  rows: any[]
  onEdit?: (row: any) => void
}

function Table({ columns, rows, onEdit }: TableProps) {
  const [colDefs, setColDefs] = useState(columns)
  const [rowData, setRowData] = useState(rows)

  const defaultColDef = useMemo(() => ({
    sortable: true,
    filter: true,
    editable: true,
    resizable: true
  }), [])

  const handleCellValueChanged = (event: any) => {
    if (onEdit) {
      onEdit(event.data)
    }
  }

  return (
    <div className="ag-theme-alpine" style={{ height: 400, width: '100%' }}>
      <AgGridReact
        rowData={rowData}
        columnDefs={colDefs}
        defaultColDef={defaultColDef}
        onCellValueChanged={handleCellValueChanged}
        pagination={true}
        paginationPageSize={20}
      />
    </div>
  )
}

export default Table
```

**实现方式**：
- 创建 frontend/src/components/Table/Table.tsx

---

### 4.3 图表组件

#### 4.3.1 ChartModal.tsx

**目标**：图表类型选择弹窗

```tsx
import React from 'react'
import './ChartModal.css'

interface ChartModalProps {
  visible: boolean
  onClose: () => void
  onSelect: (types: string[]) => void
}

const CHART_TYPES = [
  { value: 'pie', label: '饼图', icon: '🥧' },
  { value: 'bar', label: '柱状图', icon: '📊' },
  { value: 'line', label: '折线图', icon: '📈' },
  { value: 'funnel', label: '漏斗图', icon: '🔻' },
  { value: 'scatter', label: '散点图', icon: '⚪' },
  { value: 'gauge', label: '仪表盘', icon: '📉' }
]

function ChartModal({ visible, onClose, onSelect }: ChartModalProps) {
  const [selected, setSelected] = React.useState<string[]>([])

  const handleToggle = (value: string) => {
    if (selected.includes(value)) {
      setSelected(selected.filter(v => v !== value))
    } else {
      setSelected([...selected, value])
    }
  }

  const handleConfirm = () => {
    if (selected.length > 0) {
      onSelect(selected)
      onClose()
    }
  }

  if (!visible) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h3>选择图表类型</h3>
        <div className="chart-types">
          {CHART_TYPES.map(chart => (
            <div
              key={chart.value}
              className={`chart-type-item ${selected.includes(chart.value) ? 'selected' : ''}`}
              onClick={() => handleToggle(chart.value)}
            >
              <span className="chart-icon">{chart.icon}</span>
              <span className="chart-label">{chart.label}</span>
            </div>
          ))}
        </div>
        <div className="modal-actions">
          <button onClick={onClose}>取消</button>
          <button onClick={handleConfirm} disabled={selected.length === 0}>
            确定
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChartModal
```

**实现方式**：
- 创建 frontend/src/components/Chart/ChartModal.tsx

---

#### 4.3.2 ChartView.tsx

**目标**：图表展示

```tsx
import React from 'react'
import ReactECharts from 'echarts-for-react'

interface ChartViewProps {
  type: string
  data: any
}

function ChartView({ type, data }: ChartViewProps) {
  const getOption = () => {
    switch (type) {
      case 'pie':
        return {
          tooltip: { trigger: 'item' },
          series: [{
            type: 'pie',
            data: data,
            radius: '60%'
          }]
        }
      case 'bar':
        return {
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: data.categories },
          yAxis: { type: 'value' },
          series: [{
            type: 'bar',
            data: data.values
          }]
        }
      case 'line':
        return {
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: data.categories },
          yAxis: { type: 'value' },
          series: [{
            type: 'line',
            data: data.values
          }]
        }
      default:
        return {}
    }
  }

  return <ReactECharts option={getOption()} style={{ height: 400 }} />
}

export default ChartView
```

**实现方式**：
- 创建 frontend/src/components/Chart/ChartView.tsx

---

### 4.4 数据导出

#### 4.4.1 exporter.py

**目标**：数据导出

```python
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import pandas as pd
import io

router = APIRouter()

class Exporter:
    def export_csv(self, columns: List[str], rows: List[Dict[str, Any]]) -> bytes:
        df = pd.DataFrame(rows)
        output = io.BytesIO()
        df.to_csv(output, index=False)
        return output.getvalue()
    
    def export_excel(self, columns: List[str], rows: List[Dict[str, Any]]) -> bytes:
        df = pd.DataFrame(rows)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()

exporter = Exporter()

@router.post("/export/csv")
async def export_csv(columns: List[str], rows: List[Dict[str, Any]]):
    return exporter.export_csv(columns, rows)

@router.post("/export/excel")
async def export_excel(columns: List[str], rows: List[Dict[str, Any]]):
    return exporter.export_excel(columns, rows)
```

**实现方式**：
- 修改 backend/app/services/exporter.py

---

### 4.5 测试验收

| 测试项 | 预期结果 | 验收条件 |
|--------|----------|----------|
| CSV 上传 | 表格显示 | 数据正确 |
| Excel 上传 | 表格显示 | 数据正确 |
| PDF 解析 | 文字提取 | 文字正确 |
| 图片解析 | 图像显示 | 图像显示 |
| 表格编辑 | 修改生效 | 可保存 |
| 图表弹窗 | 弹窗显示 | 可选择 |
| 图表展示 | 图表显示 | 类型正确 |
| 数据导出 | 文件下载 | 文件正确 |

---

## 阶段五：记忆迭代

### 5.1 操作习惯记忆

#### 5.1.1 habit_tracker.py

**目标**：操作习惯追踪

```python
from typing import Dict, Any, List
from datetime import datetime
from app.core.base import Memory
import uuid

class HabitTracker:
    def __init__(self, memory_storage, vector_store):
        self.memory_storage = memory_storage
        self.vector_store = vector_store
    
    async def record_chart_preference(self, session_id: str, chart_type: str):
        memory = Memory(
            id=str(uuid.uuid4()),
            type="操作习惯",
            content=f"偏好 {chart_type} 图表类型",
            importance=2,
            session_id=session_id,
            created_at=datetime.now().isoformat()
        )
        
        await self.memory_storage.add_memory(memory)
        return memory
    
    async def record_upload_time(self, session_id: str, hour: int):
        time_range = self._get_time_range(hour)
        memory = Memory(
            id=str.uuid.uuid4(),
            type="操作习惯",
            content=f"通常在 {time_range} 时间段活跃",
            importance=1,
            session_id=session_id,
            created_at=datetime.now().isoformat()
        )
        
        await self.memory_storage.add_memory(memory)
        return memory
    
    def _get_time_range(self, hour: int) -> str:
        if 6 <= hour < 9:
            return "早上"
        elif 9 <= hour < 12:
            return "上午"
        elif 12 <= hour < 14:
            return "中午"
        elif 14 <= hour < 18:
            return "下午"
        elif 18 <= hour < 22:
            return "晚上"
        else:
            return "深夜"
```

**实现方式**：
- 创建 backend/app/services/habit_tracker.py

---

### 5.2 分析结论记忆

#### 5.2.1 conclusion_tracker.py

**目标**：分析结论追踪

```python
from typing import Dict, Any
from datetime import datetime
from app.core.base import Memory
import uuid

class ConclusionTracker:
    def __init__(self, memory_storage, vector_store):
        self.memory_storage = memory_storage
        self.vector_store = vector_store
    
    async def record_conclusion(
        self,
        session_id: str,
        conclusion: str,
        data_summary: Dict[str, Any]
    ):
        summary = self._summarize_data(data_summary)
        
        memory = Memory(
            id=str(uuid.uuid4()),
            type="分析结论",
            content=f"{conclusion}。数据概览：{summary}",
            importance=3,
            session_id=session_id,
            created_at=datetime.now().isoformat()
        )
        
        await self.memory_storage.add_memory(memory)
        return memory
    
    def _summarize_data(self, data: Dict[str, Any]) -> str:
        if "rowCount" in data:
            return f"共 {data['rowCount']} 条数据，{len(data.get('columns', []))} 个字段"
        return "数据已处理"
```

**实现方式**：
- 创建 backend/app/services/conclusion_tracker.py

---

### 5.3 记忆时间线

#### 5.3.1 MemoryTimeline.tsx

**目标**：记忆时间线

```tsx
import React from 'react'

function MemoryTimeline({ memories }: { memories: any[] }) {
  const grouped = React.useMemo(() => {
    const groups: Record<string, any[]> = {}
    memories.forEach(m => {
      const date = new Date(m.created_at).toLocaleDateString()
      if (!groups[date]) {
        groups[date] = []
      }
      groups[date].push(m)
    })
    return groups
  }, [memories])

  return (
    <div className="memory-timeline">
      {Object.entries(grouped).map(([date, mems]) => (
        <div key={date} className="timeline-group">
          <div className="timeline-date">{date}</div>
          <div className="timeline-items">
            {mems.map(m => (
              <div key={m.id} className="timeline-item">
                <span className="timeline-type">{m.type}</span>
                <span className="timeline-content">{m.content}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export default MemoryTimeline
```

**实现方式**：
- 创建 frontend/src/components/Memory/MemoryTimeline.tsx

---

### 5.4 测试验收

| 测试项 | 预期结果 | 验收条件 |
|--------|----------|----------|
| 图表偏好 | 记住偏好 | 记忆存在 |
| 上传时间 | 记住时间 | 记忆存在 |
| 分析结论 | 记住结论 | 可回顾 |
| 记忆时间线 | 正常显示 | 时间线展示 |

---

### 5.3 记忆迭代机制（本地大模型审查）

#### 5.3.1 记忆审查 Skill

**目标**：用本地大模型自动审查对话，决定是否存储为长期记忆

```python
# 记忆审查 Skill Prompt
MEMORY_REVIEW_SKILL = """
## 记忆审查 Skill

你是一个记忆审查助手。当用户对话达到一定轮数时，你需要审查对话内容并决定是否需要存储为长期记忆。

### 你的任务
1. 判断当前对话是否包含值得存储的新知识
2. 如果是，提炼出精要内容
3. 自动判断记忆类型

### 记忆类型分类
- 操作习惯：用户偏好、操作模式、常用功能
- 分析结论：数据洞察、报告结论、发现
- 关键决策：重要决定、业务选择
- 其他：不属于上述的内容

### 输出格式
请直接输出以下 JSON 格式，不要其他内容：
{
    "need_store": true/false,
    "type": "操作习惯/分析结论/关键决策/其他",
    "content": "精要内容",
    "reason": "判断原因"
}

### 规则
- 只提取之前记忆中没有的新信息
- 已有的类似内容不重复存储
"""
```

#### 5.3.2 memory_reviewer.py

**目标**：批量审查对话并提取记忆

```python
from typing import List, Dict, Any
from datetime import datetime
from app.core.base import Memory
import uuid

class MemoryReviewer:
    def __init__(
        self,
        memory_storage,
        vector_store,
        local_llm,
        review_threshold: int = 5
    ):
        self.memory_storage = memory_storage
        self.vector_store = vector_store
        self.local_llm = local_llm  # 本地大模型
        self.conversation_buffer = []
        self.review_threshold = review_threshold

    async def add_to_buffer(self, role: str, content: str):
        self.conversation_buffer.append({"role": role, "content": content})

        if len(self.conversation_buffer) >= self.review_threshold * 2:
            return True  # 达到审查阈值
        return False

    async def review_and_extract(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """审查并提取记忆"""
        # 获取已有记忆用于去重
        existing = await self.vector_store.get_all_by_session(session_id)

        # 调用本地大模型审查
        prompt = self._build_prompt(existing)
        result = await self.local_llm.chat(prompt)

        # 解析 JSON 结果
        review_result = self._parse_json(result)

        if review_result.get("need_store"):
            # 存储新记忆（类型由模型自动判断）
            memory = Memory(
                id=str(uuid.uuid4()),
                type=review_result["type"],  # 自动判断的类型
                content=review_result["content"],
                importance=2,
                session_id=session_id,
                created_at=datetime.now().isoformat()
            )
            await self.memory_storage.add_memory(memory)

            # 向量化存储
            embedding = await self.local_llm.get_embedding(
                review_result["content"]
            )
            await self.vector_store.add(memory, embedding)

        # 清空缓冲
        self.conversation_buffer = []
        return review_result

    def _build_prompt(self, existing_memories: List[Memory]) -> str:
        # 构建审查 prompt
        return f"""
{MEMORY_REVIEW_SKILL}

当前对话历史：
{self.conversation_buffer}

已有记忆：
{[m.content for m in existing_memories]}

请审查并输出 JSON 结果。
"""

    async def _parse_json(self, result: str) -> Dict[str, Any]:
        # 解析 JSON
        import json
        import re

        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"need_store": False}
```

**实现方式**：
- 创建 backend/app/services/memory_reviewer.py
- 在 agent.py 中集成 MemoryReviewer
- 配置本地大模型服务

**触发条件**：
- 固定轮数：每 N 轮对话后触发（建议 N=5）
- 可选：token 阈值触发

---

## 阶段六：工具能力

### 6.1 文件操作

#### 6.1.1 file.py

**目标**：文件工具

```python
from fastapi import APIRouter, UploadFile, File
from pathlib import Path
import os

router = APIRouter()

class FileTool:
    def __init__(self, base_dir: str = "./data/uploads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    async def read(self, filename: str) -> str:
        file_path = self.base_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {filename}")
        
        return file_path.read_text(encoding="utf-8")
    
    async def write(self, filename: str, content: str):
        file_path = self.base_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return {"filename": filename, "size": len(content)}
    
    async def delete(self, filename: str):
        file_path = self.base_dir / filename
        if file_path.exists():
            file_path.unlink()
        return {"deleted": filename}
    
    async def upload(self, file: UploadFile) -> str:
        content = await file.read()
        file_path = self.base_dir / file.filename
        file_path.write_bytes(content)
        return {"filename": file.filename, "size": len(content)}

file_tool = FileTool()

@router.get("/read")
async def read_file(filename: str):
    return await file_tool.read(filename)

@router.post("/write")
async def write_file(filename: str, content: str):
    return await file_tool.write(filename, content)

@router.delete("/delete")
async def delete_file(filename: str):
    return await file_tool.delete(filename)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    return await file_tool.upload(file)
```

**实现方式**：
- 创建 backend/app/tools/file.py

---

### 6.2 HTTP 请求

#### 6.2.1 http.py

**目标**：HTTP 工具

```python
from fastapi import APIRouter
import httpx

router = APIRouter()

class HttpTool:
    async def request(
        self,
        method: str,
        url: str,
        headers: dict = None,
        params: dict = None,
        json: dict = None,
        data: dict = None
    ) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                data=data
            )
            
            return {
                "status": response.status_code,
                "headers": dict(response.headers),
                "content": response.text
            }

http_tool = HttpTool()

@router.get("/get")
async def get(url: str, params: dict = None):
    return await http_tool.request("GET", url, params=params)

@router.post("/post")
async def post(url: str, json: dict = None, data: dict = None):
    return await http_tool.request("POST", url, json=json, data=data)

@router.put("/put")
async def put(url: str, json: dict = None):
    return await http_tool.request("PUT", url, json=json)

@router.delete("/delete")
async def delete(url: str):
    return await http_tool.request("DELETE", url)
```

**实现方式**：
- 创建 backend/app/tools/http.py

---

### 6.3 视觉工具

#### 6.3.1 vision.py

**目标**：视觉识别工具

```python
from fastapi import APIRouter, UploadFile, File
from PIL import Image
import io
import base64

router = APIRouter()

class VisionTool:
    async def analyze_image(self, image_data: bytes, prompt: str = "描述这张图片") -> str:
        image = Image.open(io.BytesIO(image_data))
        
        width, height = image.size
        mode = image.mode
        
        return f"图片尺寸: {width}x{height}, 模式: {mode}"

vision_tool = VisionTool()

@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...), prompt: str = "描述这张图片"):
    content = await file.read()
    result = await vision_tool.analyze_image(content, prompt)
    return {"result": result}
```

**实现方式**：
- 创建 backend/app/tools/vision.py

---

### 6.4 测试验收

| 测试项 | 预期结果 | 验收条件 |
|--------|----------|----------|
| 文件读取 | 返回内容 | 读取成功 |
| 文件写入 | 保存成功 | 写入成功 |
| HTTP 请求 | 返回响应 | 请求成功 |
| 图像分析 | 返回分析 | 分析成功 |

---

## 启动和测试命令

### 后端启动
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### 前端启动
```bash
cd frontend
npm run dev
```

### ���段测试

| 阶段 | 测试验收点 |
|------|----------|
| 一 | 访问 http://localhost:5173 显示 "Hello World" |
| 二 | 记忆创建/搜索/压缩正常 |
| 三 | 多模型对话正常 |
| 四 | 数据上传→表格→图表 正常 |
| 五 | 记忆迭代正常 |
| 六 | 工具调用正常 |