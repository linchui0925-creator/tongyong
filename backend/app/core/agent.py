from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
from app.core.base import Message, Session, Memory
from app.core.context import ContextManager
from app.core.iteration_budget import IterationBudget
from app.memory.storage import MemoryStorage
from app.memory.vector import VectorStore
from app.llm.base import LLMResponse
from app.tools.registry import registry as _tool_registry
import re
import logging

logger = logging.getLogger(__name__)


class AgentEngine:
    def __init__(self, llm=None):
        self.llm = llm
        self.context = ContextManager()
        self.memory_storage = MemoryStorage()
        self.vector_store = VectorStore()
        self._cli_executor = None  # 延迟初始化

    def _get_cli_executor(self):
        """获取 CLI 执行器（延迟初始化）"""
        if self._cli_executor is None:
            try:
                from app.domains import CLIExecutor
                self._cli_executor = CLIExecutor(working_dir=".")
                logger.info("CLIExecutor 已初始化")
            except Exception as e:
                logger.warning(f"CLIExecutor 初始化失败: {e}")
        return self._cli_executor

    async def _ensure_domain_prompts(self, session_id: str):
        """注入身份与能力认知提示词（每次对话都注入，覆盖 LLM 默认自我认知）"""
        try:
            from app.domains import get_integrator
            integrator = get_integrator()
            prompt = integrator.get_all()
            if prompt:
                self.context.messages.insert(0, Message(
                    role="system",
                    content=prompt,
                    created_at=""
                ))
                logger.info(f"注入全部领域认知 ({len(integrator.get_domain_keys())} 个领域)")
        except Exception as e:
            logger.warning(f"领域认知注入失败: {e}")

    async def _inject_hermes_memory(self, session_id: str):
        """注入 Hermes 平文件记忆内容（MEMORY.md / USER.md）"""
        try:
            from app.hermes.memory_file import MemoryFileManager
            mfm = MemoryFileManager(base_dir="./data/hermes")
            mem_content = mfm.read_memory()
            user_content = mfm.read_user()
            if mem_content:
                self.context.messages.insert(0, Message(
                    role="system",
                    content=f"[长期事实记忆]\n{mem_content}",
                    created_at=""
                ))
                logger.info("注入 MEMORY.md 长期记忆")
            if user_content:
                self.context.messages.insert(0, Message(
                    role="system",
                    content=f"[用户偏好]\n{user_content}",
                    created_at=""
                ))
                logger.info("注入 USER.md 用户画像")
        except Exception as e:
            logger.debug(f"Hermes 记忆注入跳过: {e}")

    async def _get_or_create_session(self) -> str:
        sessions = await self.memory_storage.get_sessions()
        if sessions:
            session_id = sessions[0].id
            await self._load_operation_habits(session_id)
            return session_id
        
        session = await self.memory_storage.create_session("默认会话")
        session_id = session.id
        
        await self._load_operation_habits(session_id)
        
        return session_id

    async def _load_operation_habits(self, session_id: str):
        if not self.llm:
            return
        
        try:
            shared_memories = await self.vector_store.get_shared()
            for habit in shared_memories[:3]:
                self.context.add_message("system", f"记住：{habit.content}")
                logger.info(f"加载操作习惯: {habit.content[:30]}...")
        except Exception as e:
            logger.warning(f"加载操作习惯失败: {e}")

    async def _try_execute_from_response(self, text: str) -> Optional[Tuple[str, str]]:
        """从 LLM 回复中检测并执行命令"""
        executor = self._get_cli_executor()
        if not executor:
            return None
        command = executor.extract_from_response(text)
        if not command:
            return None
        logger.info(f"检测到命令: {command}")
        result = await executor.execute("run", {"command": command})
        formatted = executor.format_result(result)
        return command, formatted

    async def chat(
        self,
        session_id: Optional[str],
        message: str,
        use_memory: bool = True
    ) -> Dict[str, Any]:
        if not session_id:
            session_id = await self._get_or_create_session()
            logger.info(f"创建新会话: {session_id}")

        # 注入身份认知和 Hermes 记忆（放在上下文最前面，覆盖 LLM 默认认知）
        await self._inject_hermes_memory(session_id)
        await self._ensure_domain_prompts(session_id)

        # 注入环境能力（让 Agent 知道实际安装了哪些工具）
        from app.core.env_capabilities import get_env_prompt
        env_prompt = get_env_prompt()
        if env_prompt:
            self.context.add_message("system", env_prompt)

        # 加载历史对话
        historical_messages = await self.memory_storage.get_messages(session_id)
        for msg in historical_messages:
            self.context.add_message(msg.role, msg.content)

        self.context.add_message("user", message)

        memories = []
        if use_memory and self.llm:
            try:
                embedding = await self.llm.get_embedding(message)
                memories = await self.vector_store.search(
                    message, embedding, k=5, session_id=session_id
                )
                if memories:
                    context = "\n".join([m.content for m in memories])
                    self.context.add_message("system", f"相关记忆：\n{context}")
                    logger.info(f"检索到 {len(memories)} 条记忆")
            except Exception as e:
                logger.error(f"记忆检索失败: {e}")

        response = "智能体已收到消息"
        tools_used = []
        commands_executed = []
        MAX_TOOL_ROUNDS = 10

        if self.llm:
            try:
                import json as _json
                from app.tools.manager import get_tool_manager
                tool_mgr = get_tool_manager()
                tool_schemas = tool_mgr.get_schemas()
                logger.info(f"Agent 可用工具: {tool_mgr.list_tools()}")

                # 工具调用循环 — 每轮都传递工具 schema，让 LLM 可在任意轮次调用工具
                for round_num in range(MAX_TOOL_ROUNDS):
                    llm_messages = [Message(role=m.role, content=m.content) for m in self.context.get_messages()]
                    try:
                        llm_response = await self.llm.chat(messages=llm_messages, tools=tool_schemas)
                    except Exception as _tool_err:
                        # 部分模型（如 deepseek-reasoner）不支持工具调用，降级为无工具请求
                        logger.warning(f"带工具的 LLM 调用失败，降级为无工具请求: {_tool_err}")
                        llm_response = await self.llm.chat(messages=llm_messages, tools=None)
                        # 降级后直接取文本回复，不再尝试工具调用
                        response = llm_response.content
                        break

                    if not llm_response.has_tool_calls:
                        response = llm_response.content
                        break

                    # 处理工具调用
                    # 先将 assistant 的 tool_calls 消息加入上下文
                    tool_calls_data = [
                        {
                            "id": tc.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": tc.tool_name,
                                "arguments": _json.dumps(tc.arguments, ensure_ascii=False)
                            }
                        }
                        for tc in llm_response.tool_calls
                    ]
                    assistant_tc_content = _json.dumps({
                        "content": llm_response.content or "",
                        "tool_calls": tool_calls_data
                    }, ensure_ascii=False)
                    self.context.add_message("assistant", assistant_tc_content)

                    for tc in llm_response.tool_calls:
                        tools_used.append(tc.tool_name)
                        emoji = _tool_registry.get_emoji(tc.tool_name)
                        logger.info(f"工具调用: {emoji} {tc.tool_name}({tc.arguments})")

                        # 执行工具
                        try:
                            tool_result = await tool_mgr.execute(tc.tool_name, tc.arguments)
                        except Exception as _tool_exec_err:
                            logger.error(f"工具执行失败 {emoji} {tc.tool_name}: {_tool_exec_err}")
                            tool_result = f"工具执行失败: {_tool_exec_err}"

                        # 记录命令执行
                        if tc.tool_name == "terminal":
                            commands_executed.append(tc.arguments.get("command", ""))

                        # 将工具结果以 JSON 格式追加到上下文（含 tool_call_id 供 DashScope 使用）
                        tool_msg_content = _json.dumps({
                            "tool_call_id": tc.tool_call_id,
                            "content": f"[工具 {tc.tool_name} 的返回结果]\n{tool_result}"
                        }, ensure_ascii=False)
                        self.context.add_message("tool", tool_msg_content)

                    logger.info(f"工具调用轮次 {round_num + 1}/{MAX_TOOL_ROUNDS}，工具: {[tc.tool_name for tc in llm_response.tool_calls]}")

                else:
                    # 循环耗尽仍未得到纯文本响应
                    response = "工具调用轮次已达上限，请基于已有结果回复。"
                    logger.warning(f"工具调用轮次耗尽 (max={MAX_TOOL_ROUNDS})")

            except Exception as e:
                logger.error(f"LLM调用失败: {e}", exc_info=True)
                response = "智能体已收到消息"

        # 如果使用了工具，在回复末尾附加执行反馈
        if tools_used:
            unique_tools = list(dict.fromkeys(tools_used))
            tool_summary = "\n\n---\n**已调用工具:** " + "、".join(unique_tools)
            if commands_executed:
                tool_summary += "\n**执行命令:** " + "、".join(commands_executed)
            response += tool_summary

        self.context.add_message("assistant", response)

        await self.memory_storage.add_message(session_id, "user", message)
        await self.memory_storage.add_message(session_id, "assistant", response)

        if self.llm:
            try:
                user_embedding = await self.llm.get_embedding(message)
                user_vector_id = await self.vector_store.add_text(
                    session_id, "user", message, user_embedding
                )
                if not user_vector_id:
                    logger.error(f"用户消息向量存储失败，返回空ID")

                assistant_embedding = await self.llm.get_embedding(response)
                assistant_vector_id = await self.vector_store.add_text(
                    session_id, "assistant", response, assistant_embedding
                )
                if not assistant_vector_id:
                    logger.error(f"助手回复向量存储失败，返回空ID")
            except Exception as e:
                logger.error(f"向量存储失败: {e}")

        self.context.clear()
        logger.info(f"会话 {session_id} 对话完成，消息已保存")

        return {
            "reply": response,
            "session_id": session_id,
            "memory_added": [m.dict() for m in memories],
            "tools_used": tools_used,
            "commands_executed": commands_executed,
        }

    async def stream_chat(
        self,
        session_id: Optional[str],
        message: str,
        use_memory: bool = True
    ):
        """流式聊天（支持工具调用 + 进度反馈）

        Yields:
            dict: {"type": "progress", "content": str}  进度事件
            dict: {"type": "content", "content": str}   文本内容块
            dict: {"type": "done", ...}                 完成事件
        """
        import time as _time
        start_time = _time.time()

        def _progress(text: str):
            return {"type": "progress", "content": text, "timestamp": _time.time()}

        def _content(chunk: str):
            return {"type": "content", "content": chunk, "timestamp": _time.time()}

        def _tool_start(name: str, args: dict):
            emoji = _tool_registry.get_emoji(name)
            return {"type": "tool_start", "tool_name": name, "arguments": args,
                    "emoji": emoji, "timestamp": _time.time()}

        def _tool_complete(name: str, result: str, duration: float, error: bool = False):
            emoji = _tool_registry.get_emoji(name)
            preview = result.strip()[:120].replace("\n", " ")
            if len(result.strip()) > 120:
                preview += "..."
            return {"type": "tool_complete", "tool_name": name,
                    "result_preview": preview, "duration": round(duration, 2),
                    "error": error, "emoji": emoji, "timestamp": _time.time()}

        def _tool_error(name: str, error_msg: str):
            emoji = _tool_registry.get_emoji(name)
            return {"type": "tool_error", "tool_name": name, "error": error_msg,
                    "emoji": emoji, "timestamp": _time.time()}

        def _tool_result_structured(name: str, tool_call_id: str, success: bool,
                                    result: str = "", error_msg: str = "",
                                    error_type: str = "") -> dict:
            """构建结构化的工具执行结果，供模型自我修正参考"""
            emoji = _tool_registry.get_emoji(name)
            content = result if success else error_msg
            # 根据错误类型提供建议
            suggestion = ""
            if not success:
                if error_type == "not_found":
                    suggestion = "可尝试检查路径是否正确，或使用其他工具获取信息"
                elif error_type == "permission":
                    suggestion = "请检查权限设置，或尝试其他操作方式"
                elif error_type == "timeout":
                    suggestion = "可尝试减小操作范围或增加超时时间"
                elif error_type == "invalid_args":
                    suggestion = "请检查参数格式是否正确"
            return {
                "tool_call_id": tool_call_id,
                "tool_name": name,
                "success": success,
                "content": content,
                "error_type": error_type,
                "suggestion": suggestion,
                "emoji": emoji,
            }

        def _classify_error_type(error_msg: str) -> str:
            """根据错误消息分类错误类型"""
            msg = error_msg.lower()
            if "not found" in msg or "不存在" in msg or "找不到" in msg:
                return "not_found"
            elif "permission" in msg or "权限" in msg or "denied" in msg:
                return "permission"
            elif "timeout" in msg or "超时" in msg or "timed out" in msg:
                return "timeout"
            elif "invalid" in msg or "参数" in msg or "格式" in msg:
                return "invalid_args"
            return "generic"

        def _thinking_delta(text: str):
            return {"type": "thinking_delta", "content": text, "timestamp": _time.time()}

        def _thinking_done():
            return {"type": "thinking_done", "timestamp": _time.time()}

        def _done():
            return {"type": "done", "tools_used": list(dict.fromkeys(tools_used)),
                    "commands_executed": commands_executed,
                    "processing_time": round(_time.time() - start_time, 2)}

        def _tool_feedback(text: str):
            return {"type": "tool_feedback", "content": text, "timestamp": _time.time()}

        def _clean_thinking(text: str):
            """清理文本中的 <think>...晖 内容，返回 (清理后文本, thinking内容)"""
            import re
            match = re.search(r'<think>([\s\S]*?)晖', text)
            if match:
                thinking = match.group(1)
                cleaned = re.sub(r'<think>[\s\S]*?晖', '', text, count=1).strip()
                return cleaned, thinking
            return text, ""
            return {"type": "tool_feedback", "content": text, "timestamp": _time.time()}

        tools_used = []
        commands_executed = []
        budget = IterationBudget(max_rounds=10, soft_limit=8, grace_calls=2)

        def _classify_and_group_tools(tool_calls: list) -> Dict[str, list]:
            """按并行模式分组工具调用"""
            return _tool_registry.classify_tool_calls(tool_calls)

        async def _execute_safe_parallel(tool_calls: list, tool_mgr) -> Dict[str, str]:
            """并行执行 safe 模式的工具调用"""
            if not tool_calls:
                return {}
            tasks = [
                tool_mgr.execute(tc["function"]["name"], _json.loads(tc["function"]["arguments"]))
                for tc in tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return {
                tc["id"]: str(r) if not isinstance(r, Exception) else f"工具执行失败: {r}"
                for tc, r in zip(tool_calls, results)
            }

        if not session_id:
            session_id = await self._get_or_create_session()

        # ── 阶段 1: 加载上下文 ──
        yield _progress("加载身份认知...")
        await self._inject_hermes_memory(session_id)
        await self._ensure_domain_prompts(session_id)

        from app.core.env_capabilities import get_env_prompt
        env_prompt = get_env_prompt()
        if env_prompt:
            self.context.add_message("system", env_prompt)

        yield _progress("加载历史对话...")
        historical_messages = await self.memory_storage.get_messages(session_id)
        for msg in historical_messages:
            self.context.add_message(msg.role, msg.content)

        self.context.add_message("user", message)

        # ── 阶段 2: 检索记忆 ──
        if use_memory and self.llm:
            yield _progress("检索相关记忆...")
            try:
                embedding = await self.llm.get_embedding(message)
                memories = await self.vector_store.search(
                    message, embedding, k=5, session_id=session_id
                )
                if memories:
                    context = "\n".join([m.content for m in memories])
                    self.context.add_message("system", f"相关记忆：\n{context}")
                    yield _progress(f"已检索 {len(memories)} 条相关记忆")
            except Exception:
                pass

        # ── 阶段 3: LLM 对话（支持工具调用） ──
        if not self.llm:
            yield _content("智能体已收到消息（LLM未初始化）")
            yield _done()
            self.context.clear()
            return

        try:
            import json as _json
            from app.tools.manager import get_tool_manager
            tool_mgr = get_tool_manager()
            tool_schemas = tool_mgr.get_schemas()
            logger.info(f"Agent stream_chat 可用工具: {tool_mgr.list_tools()}")

            # ── ReAct 工具调用循环（支持并行 + 预算控制） ──
            while True:
                # 检查预算是否耗尽
                if budget.is_exhausted:
                    yield _content(budget.get_exhausted_message())
                    break

                llm_messages = [Message(role=m.role, content=m.content) for m in self.context.get_messages()]

                if budget.current_round == 0:
                    yield _progress("正在思考...")
                else:
                    yield _progress(f"继续处理 (第 {budget.current_round + 1} 轮)...")

                # 预算警告
                warning = budget.get_warning_message()
                if warning:
                    yield {"type": "budget_warning", "content": warning, "timestamp": _time.time()}

                try:
                    llm_response = await self.llm.chat(messages=llm_messages, tools=tool_schemas)
                except Exception as _tool_err:
                    logger.warning(f"带工具的 LLM 调用失败，降级为无工具请求: {_tool_err}")
                    llm_response = await self.llm.chat(messages=llm_messages, tools=None)
                    full_text = llm_response.content
                    if full_text:
                        cleaned, _ = _clean_thinking(full_text)
                        yield _content(cleaned)
                    break

                if not llm_response.has_tool_calls:
                    full_text = llm_response.content
                    if full_text:
                        cleaned, _ = _clean_thinking(full_text)
                        yield _content(cleaned)
                    break

                # ── 处理工具调用 ──
                tool_calls_data = [
                    {"id": tc.tool_call_id, "type": "function",
                     "function": {"name": tc.tool_name, "arguments": _json.dumps(tc.arguments, ensure_ascii=False)}}
                    for tc in llm_response.tool_calls
                ]
                self.context.add_message("assistant", _json.dumps({
                    "content": llm_response.content or "", "tool_calls": tool_calls_data
                }, ensure_ascii=False))

                # 按并行模式分组
                groups = _classify_and_group_tools(tool_calls_data)
                never_calls = groups.get("never", [])
                safe_calls = groups.get("safe", [])
                path_scoped_calls = groups.get("path_scoped", [])

                # 执行 never 模式（串行）
                for tc in never_calls:
                    tool_name = tc["function"]["name"]
                    args = _json.loads(tc["function"]["arguments"])
                    tools_used.append(tool_name)

                    yield _tool_start(tool_name, args)
                    _tool_t0 = _time.time()

                    try:
                        tool_result = await tool_mgr.execute(tool_name, args)
                        _elapsed = _time.time() - _tool_t0
                        yield _tool_complete(tool_name, tool_result, _elapsed)
                        result_structured = _tool_result_structured(tool_name, tc["id"], True, result=tool_result)
                    except Exception as _tool_exec_err:
                        _elapsed = _time.time() - _tool_t0
                        error_msg = str(_tool_exec_err)
                        error_type = _classify_error_type(error_msg)
                        yield _tool_error(tool_name, error_msg)
                        tool_result = f"工具执行失败: {_tool_exec_err}"
                        result_structured = _tool_result_structured(
                            tool_name, tc["id"], False, error_msg=error_msg, error_type=error_type
                        )

                    if tool_name == "terminal":
                        commands_executed.append(args.get("command", ""))

                    self.context.add_message("tool", _json.dumps(result_structured, ensure_ascii=False))

                # 执行 safe 模式（并行）
                if safe_calls:
                    safe_results = await _execute_safe_parallel(safe_calls, tool_mgr)
                    for tc in safe_calls:
                        tool_name = tc["function"]["name"]
                        args = _json.loads(tc["function"]["arguments"])
                        tools_used.append(tool_name)
                        tool_result = safe_results.get(tc["id"], "Unknown result")

                        yield _tool_start(tool_name, args)
                        _tool_t0 = _time.time()
                        _elapsed = _time.time() - _tool_t0

                        is_error = tool_result.startswith("工具执行失败")
                        yield _tool_complete(tool_name, tool_result, _elapsed, error=is_error)
                        result_structured = _tool_result_structured(
                            tool_name, tc["id"], not is_error, result=tool_result if not is_error else "",
                            error_msg=tool_result if is_error else "", error_type=_classify_error_type(tool_result) if is_error else ""
                        )

                        if tool_name == "terminal":
                            commands_executed.append(args.get("command", ""))

                        self.context.add_message("tool", _json.dumps(result_structured, ensure_ascii=False))

                # 执行 path_scoped 模式（目前串行，后续可扩展路径冲突检测）
                for tc in path_scoped_calls:
                    tool_name = tc["function"]["name"]
                    args = _json.loads(tc["function"]["arguments"])
                    tools_used.append(tool_name)

                    yield _tool_start(tool_name, args)
                    _tool_t0 = _time.time()

                    try:
                        tool_result = await tool_mgr.execute(tool_name, args)
                        _elapsed = _time.time() - _tool_t0
                        yield _tool_complete(tool_name, tool_result, _elapsed)
                        result_structured = _tool_result_structured(tool_name, tc["id"], True, result=tool_result)
                    except Exception as _tool_exec_err:
                        _elapsed = _time.time() - _tool_t0
                        error_msg = str(_tool_exec_err)
                        error_type = _classify_error_type(error_msg)
                        yield _tool_error(tool_name, error_msg)
                        tool_result = f"工具执行失败: {_tool_exec_err}"
                        result_structured = _tool_result_structured(
                            tool_name, tc["id"], False, error_msg=error_msg, error_type=error_type
                        )

                    self.context.add_message("tool", _json.dumps(result_structured, ensure_ascii=False))

                # 推进预算
                if not budget.advance():
                    yield _content(budget.get_exhausted_message())
                    break

        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            yield _content(f"智能体已收到消息（发生错误: {str(e)}）")

        # ── 附加工具反馈 ──
        if tools_used:
            unique_tools = list(dict.fromkeys(tools_used))
            feedback = "\n\n---\n**已调用工具:** " + "、".join(unique_tools)
            if commands_executed:
                feedback += "\n**执行命令:** " + "、".join(commands_executed)
            yield _tool_feedback(feedback)

        # ── 保存 ──
        yield _progress("保存对话记录...")
        # 收集完整回复用于存储（从 context 最后的 assistant 消息中取）
        import re
        final_reply = ""
        for m in reversed(self.context.get_messages()):
            if m.role == "assistant":
                try:
                    d = _json.loads(m.content)
                    final_reply = d.get("content", "")
                except (_json.JSONDecodeError, AttributeError):
                    final_reply = m.content
                if final_reply:
                    break
        if not final_reply:
            final_reply = "（无回复内容）"
        # 清理 <think>... 标记，不存入数据库
        final_reply = re.sub(r'<think>.*?', '', final_reply, flags=re.DOTALL).strip()

        self.context.add_message("assistant", final_reply)
        await self.memory_storage.add_message(session_id, "user", message)
        await self.memory_storage.add_message(session_id, "assistant", final_reply)
        self.context.clear()

        yield _done()

    async def create_session(self, name: str) -> Session:
        return await self.memory_storage.create_session(name)

    async def get_sessions(self) -> List[Session]:
        return await self.memory_storage.get_sessions()

    async def get_session_memories(self, session_id: str) -> List[Memory]:
        return await self.memory_storage.get_memories(session_id)

    async def search_memories(
        self,
        query: str,
        k: int = 10,
        session_id: Optional[str] = None
    ) -> List[Memory]:
        if not self.llm:
            return await self.memory_storage.get_memories(session_id)

        try:
            embedding = await self.llm.get_embedding(query)
            return await self.vector_store.search(query, embedding, k=k, session_id=session_id)
        except Exception as e:
            logger.error(f"记忆搜索失败: {e}")
            return await self.memory_storage.get_memories(session_id)

    async def add_memory(
        self,
        memory_type: str,
        content: str,
        importance: int = 1,
        session_id: Optional[str] = None
    ) -> Memory:
        from uuid import uuid4
        from datetime import datetime

        memory = Memory(
            id=str(uuid4()),
            type=memory_type,
            content=content,
            importance=importance,
            session_id=session_id,
            created_at=datetime.now().isoformat()
        )

        await self.memory_storage.add_memory(memory)
        logger.info(f"添加记忆: {memory_type} - {content[:20]}...")

        if self.llm:
            try:
                embedding = await self.llm.get_embedding(content)
                memory.vector_id = await self.vector_store.add(memory, embedding)
                logger.info(f"记忆已向量化: {memory.id}")
            except Exception as e:
                logger.error(f"记忆向量化失败: {e}")

        return memory

    async def update_memory(self, memory_id: str, content: str, importance: Optional[int] = None) -> Optional[Memory]:
        return await self.memory_storage.update_memory(memory_id, content, importance)

    async def delete_memory(self, memory_id: str) -> bool:
        return await self.memory_storage.delete_memory(memory_id)

    async def update_session(self, session_id: str, name: str) -> Optional[Session]:
        return await self.memory_storage.update_session(session_id, name)

    async def delete_session(self, session_id: str):
        await self.memory_storage.delete_session(session_id)

    async def get_previous_message(self, session_id: str, current_sequence: int) -> Optional[Message]:
        return await self.memory_storage.get_previous_message(session_id, current_sequence)

    async def get_last_user_message(self, session_id: str) -> Optional[Message]:
        return await self.memory_storage.get_last_user_message(session_id)

    async def get_message_by_sequence(self, session_id: str, sequence: int) -> Optional[Message]:
        return await self.memory_storage.get_message_by_sequence(session_id, sequence)

    async def get_conversation_stats(self, session_id: str) -> dict:
        messages = await self.memory_storage.get_messages(session_id)
        memories = await self.memory_storage.get_memories(session_id)
        return {
            "total_messages": len(messages),
            "total_memories": len(memories),
            "session_id": session_id,
        }

    async def get_memory_versions(self, memory_id: str):
        return await self.memory_storage.get_memory_versions(memory_id)

    async def verify_memory_loading(self, session_id: str) -> dict:
        memories = await self.memory_storage.get_memories(session_id)
        settings = await self.memory_storage.get_all_settings(session_id)
        return {
            "total_memories": len(memories),
            "settings": settings,
            "operation_habits": [m for m in memories if m.type == "操作习惯"],
            "conclusions": [m for m in memories if m.type == "分析结论"],
            "decisions": [m for m in memories if m.type == "关键决策"],
        }

    async def add_setting(self, session_id: str, key: str, value: str, setting_type: str = "string") -> dict:
        return await self.memory_storage.add_setting(session_id, key, value, setting_type)

    async def get_all_settings(self, session_id: str) -> list:
        return await self.memory_storage.get_all_settings(session_id)

    async def get_setting(self, session_id: str, key: str) -> Optional[dict]:
        return await self.memory_storage.get_setting(session_id, key)

    async def update_setting(self, session_id: str, key: str, value: str) -> Optional[dict]:
        return await self.memory_storage.update_setting(session_id, key, value)

    async def delete_setting(self, session_id: str, key: str) -> bool:
        return await self.memory_storage.delete_setting(session_id, key)

    async def get_conversation_history(self, session_id: str) -> List[Message]:
        return await self.memory_storage.get_messages(session_id)

    async def get_shared_memories(self, query: str, k: int = 5) -> List[Memory]:
        if not self.llm:
            return []

        try:
            embedding = await self.llm.get_embedding(query)
            return await self.vector_store.search(
                query, embedding, k=k, session_id=None, is_shared=True
            )
        except Exception:
            return []