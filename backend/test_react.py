#!/usr/bin/env python3
"""
ReAct 能力测试脚本
测试 Agent 是否能多轮思考选择合适的工具完成任务
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_react_capability():
    """测试 ReAct 能力"""
    from app.core.agent import AgentEngine
    from app.llm.factory import get_llm

    print("=" * 60)
    print("ReAct 能力测试")
    print("=" * 60)

    # 初始化 LLM
    print("\n[1] 初始化 LLM...")
    try:
        llm = get_llm()
        print(f"    LLM 初始化成功: {type(llm).__name__}")
    except Exception as e:
        print(f"    LLM 初始化失败: {e}")
        print("    请检查 .env 配置")
        return

    # 创建 Agent
    print("\n[2] 创建 Agent Engine...")
    agent = AgentEngine(llm=llm)

    # 测试任务：让 Agent 搜索信息并总结
    test_tasks = [
        {
            "name": "多工具调用测试",
            "message": "请帮我搜索今天北京的天气，然后读取 /Users/linc/Documents/tongyong-agent/README.md 文件的内容，最后总结一下你做了什么"
        },
        {
            "name": "文件操作测试",
            "message": "请帮我列出 /Users/linc/Documents/tongyong-agent 目录下有哪些文件和文件夹"
        },
        {
            "name": "复杂任务测试",
            "message": "请帮我搜索一下 Python 的官方文档网站，然后告诉我最新的 Python 版本是什么"
        }
    ]

    for i, task in enumerate(test_tasks, 1):
        print(f"\n{'=' * 60}")
        print(f"[测试 {i}] {task['name']}")
        print(f"[用户] {task['message']}")
        print("-" * 60)

        print("\n[Agent 响应流]")
        tool_call_count = 0
        budget_warnings = []

        try:
            async for event in agent.stream_chat(
                session_id=None,
                message=task["message"],
                use_memory=False
            ):
                event_type = event.get("type", "unknown")

                if event_type == "progress":
                    print(f"    [进度] {event['content']}")

                elif event_type == "content":
                    print(f"    [内容] {event['content'][:200]}{'...' if len(event.get('content', '')) > 200 else ''}")

                elif event_type == "tool_start":
                    tool_call_count += 1
                    print(f"    [工具开始 #{tool_call_count}] {event['emoji']} {event['tool_name']}({event.get('arguments', {})})")

                elif event_type == "tool_complete":
                    result = event.get('result_preview', '')
                    print(f"    [工具完成 #{tool_call_count}] {event['emoji']} {event['tool_name']} - {result[:80]}...")

                elif event_type == "tool_error":
                    print(f"    [工具错误 #{tool_call_count}] {event['emoji']} {event['tool_name']} - {event['error'][:100]}")

                elif event_type == "budget_warning":
                    budget_warnings.append(event['content'])
                    print(f"    [预算警告] {event['content']}")

                elif event_type == "done":
                    print(f"\n    [完成] 工具: {event.get('tools_used', [])}, 命令: {event.get('commands_executed', [])}, 耗时: {event.get('processing_time', 0)}s")

            print(f"\n[统计]")
            print(f"    工具调用次数: {tool_call_count}")
            print(f"    预算警告次数: {len(budget_warnings)}")

            if tool_call_count > 1:
                print(f"    ✓ 多轮工具调用成功 ({tool_call_count} 轮)")
            else:
                print(f"    - 单轮工具调用")

        except Exception as e:
            print(f"    [错误] {e}")

        await asyncio.sleep(1)  # 避免请求过快

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_react_capability())
