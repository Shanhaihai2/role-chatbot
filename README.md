# 🤖 AI 角色陪伴聊天机器人 (Role-Chatbot)

基于 RAG + Agent 的 AI 虚拟角色交互系统。支持角色素材上传、自动人设提取、风格化对话生成、长短期记忆留存、内容安全风控，并可通过微信公众号实时聊天。

## ✨ 核心功能
- 📤 角色素材上传（TXT/PDF），自动解析与向量化存储
- 🎭 自动人设提取：从对话素材中提炼角色性格、语气、口头禅
- 💬 RAG + Agent 智能对话：检索角色原始素材，生成风格化回复
- 🧠 长短时记忆系统：会话上下文 + 跨会话长期记忆
- 🛡️ 内容安全双层风控：关键词黑名单 + LLM 语义审核
- 🕐 时令节日与角色作息：角色能感知时间、节日，并做出符合人设的反应
- 📱 微信公众号接入：支持微信好友式消息收发
- 👥 多用户支持：JWT 认证，数据按用户隔离
- 🌊 流式输出：支持 SSE 逐字生成回复

## 🛠️ 技术栈
| 层级 | 技术 |
| :--- | :--- |
| 后端框架 | FastAPI + Uvicorn |
| AI 框架 | LangChain + LangGraph |
| 大语言模型 | Ollama + Qwen2.5 (7B) |
| Embedding | BAAI/bge-small-zh-v1.5（本地部署） |
| 向量数据库 | Chroma |
| Reranker | BAAI/bge-reranker-base（本地部署） |
| 数据库 | SQLite + SQLAlchemy |
| 认证 | JWT + HTTPBearer |
| 部署 | Cloudflare Tunnel |

## 🚀 快速开始
### 1. 环境要求
- Python 3.12+
- Ollama（下载 qwen2.5:7b 模型）
- 模型文件（手动下载放置于 models/ 目录）
- 微信公众号测试号（用于微信接入）

### 2. 安装依赖
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt