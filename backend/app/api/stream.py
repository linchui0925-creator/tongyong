"""
流式聊天API路由模块
提供SSE流式输出功能，支持实时对话
"""
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field, validator
from typing import Optional
import asyncio
import json
import time
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class StreamChatRequest(BaseModel):
    """流式聊天请求模型"""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = Field(None)
    use_memory: bool = Field(True)

    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip()


async def generate_stream_response(
    message: str,
    session_id: Optional[str] = None,
    use_memory: bool = True
):
    """
    生成流式响应

    接收 agent.stream_chat() 的 dict yields，转换为 SSE 事件：
    - {"type": "progress", ...} → event: progress
    - {"type": "content", ...}  → event: content
    - {"type": "done", ...}     → event: done
    """
    try:
        from app.main import agent_engine
        if agent_engine is None:
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "message": "Agent引擎未初始化",
                    "code": "ENGINE_NOT_INITIALIZED"
                })
            }
            return

        logger.info(f"开始流式聊天: session={session_id}")

        yield {
            "event": "start",
            "data": json.dumps({"type": "start", "timestamp": time.time()})
        }

        full_response = ""
        try:
            async for item in agent_engine.stream_chat(
                session_id=session_id,
                message=message,
                use_memory=use_memory
            ):
                # 兼容旧的纯字符串 yield
                if isinstance(item, str):
                    full_response += item
                    yield {
                        "event": "content",
                        "data": json.dumps({
                            "type": "content",
                            "content": item,
                            "full_content": full_response,
                            "timestamp": time.time()
                        })
                    }
                    continue

                event_type = item.get("type", "content")

                if event_type == "progress":
                    yield {
                        "event": "progress",
                        "data": json.dumps({
                            "type": "progress",
                            "content": item.get("content", ""),
                            "timestamp": item.get("timestamp", time.time())
                        })
                    }

                elif event_type in ("tool_start", "tool_complete", "tool_error"):
                    yield {
                        "event": event_type,
                        "data": json.dumps(item)
                    }

                elif event_type == "thinking_delta":
                    yield {
                        "event": "thinking_delta",
                        "data": json.dumps({
                            "type": "thinking_delta",
                            "content": item.get("content", ""),
                            "timestamp": item.get("timestamp", time.time())
                        })
                    }

                elif event_type == "thinking_done":
                    yield {
                        "event": "thinking_done",
                        "data": json.dumps({
                            "type": "thinking_done",
                            "timestamp": item.get("timestamp", time.time())
                        })
                    }

                elif event_type == "tool_feedback":
                    yield {
                        "event": "tool_feedback",
                        "data": json.dumps({
                            "type": "tool_feedback",
                            "content": item.get("content", ""),
                            "timestamp": item.get("timestamp", time.time())
                        })
                    }

                elif event_type == "content":
                    chunk = item.get("content", "")
                    full_response += chunk
                    yield {
                        "event": "content",
                        "data": json.dumps({
                            "type": "content",
                            "content": chunk,
                            "full_content": full_response,
                            "timestamp": time.time()
                        })
                    }

                elif event_type == "done":
                    yield {
                        "event": "done",
                        "data": json.dumps({
                            "type": "done",
                            "session_id": session_id or "",
                            "tools_used": item.get("tools_used", []),
                            "commands_executed": item.get("commands_executed", []),
                            "processing_time": item.get("processing_time", 0),
                            "timestamp": time.time()
                        })
                    }

        except Exception as e:
            logger.error(f"流式处理错误: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "message": str(e),
                    "code": "STREAM_ERROR"
                })
            }
            return

        logger.info(f"流式聊天完成，响应长度: {len(full_response)}")

    except Exception as e:
        logger.error(f"流式聊天错误: {e}", exc_info=True)
        yield {
            "event": "error",
            "data": json.dumps({
                "type": "error",
                "message": str(e),
                "code": "INTERNAL_ERROR"
            })
        }


@router.post("/stream")
async def stream_chat(request: StreamChatRequest):
    """
    流式聊天接口
    
    使用Server-Sent Events (SSE) 实现实时流式输出
    
    Args:
        request: 流式聊天请求
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    return EventSourceResponse(
        generate_stream_response(
            message=request.message,
            session_id=request.session_id,
            use_memory=request.use_memory
        )
    )


@router.get("/stream/test")
async def test_stream():
    """测试流式输出端点"""
    async def test_generator():
        for i in range(10):
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "test",
                    "message": f"测试消息 {i+1}",
                    "timestamp": time.time()
                })
            }
            await asyncio.sleep(0.1)
        
        yield {
            "event": "done",
            "data": json.dumps({
                "type": "done",
                "timestamp": time.time()
            })
        }
    
    return EventSourceResponse(test_generator())
