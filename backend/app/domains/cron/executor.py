"""
CronExecutor - 定时调度执行器

提供定时任务的管理能力，包装 AgentScheduler。
"""

from typing import Dict, Any, List, Optional
import logging

from app.domains.base import BaseDomainExecutor

logger = logging.getLogger(__name__)


class CronExecutor(BaseDomainExecutor):
    """定时调度执行器"""

    @property
    def name(self) -> str:
        return "cron"

    @property
    def description(self) -> str:
        return "定时调度系统：查看和管理定时任务"

    def __init__(self, scheduler=None):
        self.scheduler = scheduler

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "list":
            if self.scheduler:
                try:
                    jobs = self.scheduler.get_jobs()
                    return {
                        "success": True,
                        "jobs": [
                            {"id": j.id, "name": j.name, "next_run": str(j.next_run_time)}
                            for j in jobs
                        ],
                    }
                except Exception as e:
                    return {"success": False, "error": str(e)}
            return {"success": False, "error": "调度器未初始化"}

        elif action == "status":
            running = self.scheduler.is_running() if self.scheduler else False
            return {"success": True, "running": running}

        return {"success": False, "error": f"不支持的动作: {action}"}

    def get_capabilities(self) -> List[Dict[str, Any]]:
        return [
            {"action": "list", "description": "查看所有定时任务"},
            {"action": "status", "description": "查看调度器运行状态"},
        ]
