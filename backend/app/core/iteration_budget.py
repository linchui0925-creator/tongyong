"""
IterationBudget - 工具调用迭代预算控制

Hermes风格的预算控制，支持 soft/hard limit 和 grace call 机制。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IterationBudget:
    """Tracks tool-call iteration budget with grace call support.

    Attributes:
        max_rounds: 硬性上限，最大工具调用轮次
        soft_limit: 软性上限，触发警告的阈值
        grace_calls: 达到软上限后允许的额外调用次数
        current_round: 当前轮次计数
        grace_used: 已使用的 grace calls 数量
    """
    max_rounds: int = 10
    soft_limit: int = 8
    grace_calls: int = 2
    current_round: int = 0
    grace_used: int = 0

    @property
    def remaining(self) -> int:
        """剩余可用轮次"""
        return max(0, self.max_rounds - self.current_round)

    @property
    def is_exhausted(self) -> bool:
        """预算是否已耗尽"""
        return self.current_round >= self.max_rounds

    @property
    def is_approaching_limit(self) -> bool:
        """是否接近上限（已达到软上限）"""
        return self.current_round >= self.soft_limit

    @property
    def can_grace_call(self) -> bool:
        """是否可以使用 grace call"""
        return self.grace_used < self.grace_calls

    @property
    def in_grace_period(self) -> bool:
        """是否处于 grace period"""
        return self.is_approaching_limit and not self.is_exhausted

    def advance(self) -> bool:
        """推进轮次计数器

        Returns:
            True 如果迭代应该继续，False 如果应该停止
        """
        self.current_round += 1

        if self.is_exhausted:
            return False

        if self.is_approaching_limit and not self.can_grace_call:
            return False

        if self.is_approaching_limit and self.can_grace_call:
            self.grace_used += 1

        return True

    def get_warning_message(self) -> Optional[str]:
        """获取接近上限警告消息"""
        if self.current_round == self.soft_limit:
            return (
                f"[预算警告] 工具调用轮次即将耗尽（已使用 {self.current_round} 轮，"
                f"剩余 {self.remaining} 轮）。请准备结束或合并后续操作。"
            )
        if self.in_grace_period:
            return (
                f"[预算警告] 进入 grace period（已用 {self.grace_used}/{self.grace_calls} 次 grace）。"
                f"剩余 {self.remaining} 轮。"
            )
        return None

    def get_exhausted_message(self) -> str:
        """获取预算耗尽消息"""
        return (
            f"[预算耗尽] 工具调用已达上限（{self.max_rounds} 轮）。"
            "请基于已有结果生成最终回复。"
        )

    def reset(self):
        """重置预算状态"""
        self.current_round = 0
        self.grace_used = 0
