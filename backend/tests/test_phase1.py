"""
阶段一单元测试

测试数据库迁移、数据模型和基础框架
"""

import pytest
import sqlite3
import os
import sys
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.dreaming.config import DreamingConfig
from app.dreaming.signals import PhaseSignal, PhaseType, DreamCandidate, CandidateStatus, SourceType
from app.skills.models import Skill, SkillDraft, SkillUsageLog, TaskResult, SkillStatus
from app.tools.registry import ToolRegistry, ToolEntry
from app.tools.permission import PermissionManager, UserRole, RolePermission
from app.tools.audit import AuditLogger, AuditLog


class TestDatabaseMigration:
    """数据库迁移测试"""
    
    @pytest.fixture
    def test_db_path(self, tmp_path):
        """创建临时测试数据库"""
        return str(tmp_path / "test.db")
    
    @pytest.fixture
    def run_migration(self, test_db_path):
        """运行数据库迁移"""
        from app.db.migrations import m001_initial_schema
        m001_initial_schema.run_migration(test_db_path)
        return test_db_path
    
    def test_create_all_tables(self, run_migration):
        """测试所有表是否创建成功"""
        conn = sqlite3.connect(run_migration)
        cursor = conn.cursor()
        
        # 检查所有表是否存在
        tables = [
            'dream_candidates',
            'phase_signals',
            'dreaming_config',
            'skills',
            'skill_usage_log',
            'user_models',
            'tool_registry',
            'tool_permissions',
            'tool_audit_log',
            'tool_approvals',
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            assert table in existing_tables, f"表 {table} 未创建"
        
        conn.close()
    
    def test_default_config_inserted(self, run_migration):
        """测试默认配置是否插入"""
        conn = sqlite3.connect(run_migration)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM dreaming_config")
        count = cursor.fetchone()[0]
        
        assert count > 0, "默认配置未插入"
        
        conn.close()
    
    def test_default_tools_inserted(self, run_migration):
        """测试默认工具是否注册"""
        conn = sqlite3.connect(run_migration)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM tool_registry")
        count = cursor.fetchone()[0]
        
        assert count > 0, "默认工具未注册"
        
        # 检查默认工具权限
        cursor.execute("SELECT COUNT(*) FROM tool_permissions")
        perm_count = cursor.fetchone()[0]
        
        assert perm_count > 0, "默认工具权限未设置"
        
        conn.close()


class TestDreamingConfig:
    """Dreaming 配置测试"""
    
    def test_config_defaults(self):
        """测试配置默认值"""
        config = DreamingConfig()
        
        assert config.enabled == False
        assert config.lookback_days == 7
        assert config.min_score == 0.8
        assert config.min_recall_count == 3
        assert config.min_unique_queries == 3
    
    def test_config_to_dict(self):
        """测试配置转字典"""
        config = DreamingConfig()
        config_dict = config.to_dict()
        
        assert 'enabled' in config_dict
        assert 'weights' in config_dict
        assert 'thresholds' in config_dict
    
    def test_config_validation(self):
        """测试配置验证"""
        config = DreamingConfig()
        
        # 有效配置
        assert config.validate() == True
        
        # 无效配置：权重总和不为1
        config.relevance_weight = 0.5
        assert config.validate() == False
    
    def test_config_set_get(self):
        """测试配置存取"""
        config = DreamingConfig()
        
        config.set('test_key', 'test_value')
        assert config.get('test_key') == 'test_value'
        assert config.get('nonexistent', 'default') == 'default'


class TestDreamingSignals:
    """梦境信号测试"""
    
    def test_phase_signal_creation(self):
        """测试阶段信号创建"""
        signal = PhaseSignal(
            entry_id="test_entry",
            source_phase=PhaseType.LIGHT,
            reinforcement_value=0.8,
            reason="test reason"
        )
        
        assert signal.entry_id == "test_entry"
        assert signal.source_phase == PhaseType.LIGHT
        assert signal.reinforcement_value == 0.8
    
    def test_phase_signal_to_dict(self):
        """测试阶段信号转字典"""
        signal = PhaseSignal(
            entry_id="test_entry",
            source_phase=PhaseType.REM,
            reinforcement_value=0.5,
            reason="test"
        )
        
        signal_dict = signal.to_dict()
        
        assert signal_dict['entry_id'] == "test_entry"
        assert signal_dict['source_phase'] == 'rem'
    
    def test_dream_candidate_creation(self):
        """测试梦境候选创建"""
        candidate = DreamCandidate(
            id="candidate_1",
            source_session_id="session_1",
            content="test content",
            source_type=SourceType.CONVERSATION
        )
        
        assert candidate.id == "candidate_1"
        assert candidate.source_type == SourceType.CONVERSATION
        assert candidate.status == CandidateStatus.PENDING
    
    def test_dream_candidate_score_calculation(self):
        """测试候选评分计算"""
        candidate = DreamCandidate(
            id="candidate_1",
            source_session_id="session_1",
            content="test",
            source_type=SourceType.CONVERSATION,
            relevance_score=0.8,
            recall_count=5,
            recency_score=0.6,
            consolidation_score=0.4,
            conceptual_richness_score=0.7,
            query_diversity_score=0.5,
        )
        
        score = candidate.calculate_final_score()
        
        assert score > 0
        assert score <= 1.5  # 包含强化信号
    
    def test_candidate_from_dict(self):
        """测试从字典创建候选"""
        data = {
            'id': 'test_id',
            'source_session_id': 'session_1',
            'content': 'test content',
            'source_type': 'conversation',
            'concept_tags': '["tag1", "tag2"]',
        }
        
        candidate = DreamCandidate.from_dict(data)
        
        assert candidate.id == 'test_id'
        assert candidate.concept_tags == ['tag1', 'tag2']


class TestSkillModels:
    """技能模型测试"""
    
    def test_skill_creation(self):
        """测试技能创建"""
        skill = Skill(
            id="skill_1",
            name="Test Skill",
            content="test content",
            trigger_conditions=["condition1"],
            execution_steps=["step1", "step2"]
        )
        
        assert skill.id == "skill_1"
        assert skill.name == "Test Skill"
        assert skill.status == SkillStatus.ACTIVE
        assert skill.version == 1
    
    def test_skill_update_success_rate(self):
        """测试技能成功率更新"""
        skill = Skill(
            id="skill_1",
            name="Test",
            content="content"
        )
        
        skill.update_success_rate(True)
        assert skill.usage_count == 1
        assert skill.success_count == 1
        assert skill.success_rate == 1.0
        
        skill.update_success_rate(False)
        assert skill.usage_count == 2
        assert skill.success_count == 1
        assert skill.success_rate == 0.5
    
    def test_skill_to_dict(self):
        """测试技能转字典"""
        skill = Skill(
            id="skill_1",
            name="Test",
            content="content"
        )
        
        skill_dict = skill.to_dict()
        
        assert 'id' in skill_dict
        assert 'name' in skill_dict
        assert 'usage_count' in skill_dict
    
    def test_task_result_creation(self):
        """测试任务结果创建"""
        result = TaskResult(
            task_description="test task",
            outcome="success",
            success=True,
            trajectory=[
                {'action': 'step1', 'details': 'details1'},
                {'action': 'step2', 'details': 'details2'}
            ]
        )
        
        assert result.success == True
        assert len(result.trajectory) == 2


class TestToolRegistry:
    """工具注册表测试"""
    
    @pytest.fixture
    def test_db(self, tmp_path):
        """创建测试数据库"""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE tool_registry (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                category TEXT,
                permission_level INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                requires_approval INTEGER DEFAULT 0,
                approval_patterns TEXT,
                config_schema TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        return db_path
    
    def test_tool_creation(self):
        """测试工具创建"""
        tool = ToolEntry(
            name="test_tool",
            toolset="test_toolset",
            description="test description",
            schema={},
            handler=lambda: None
        )

        assert tool.name == "test_tool"

    def test_tool_registry_creation(self, test_db):
        """测试注册表创建"""
        registry = ToolRegistry()

        assert registry is not None

    def test_tool_permission_level_enum(self):
        """测试权限级别枚举"""
        # ToolPermissionLevel 不再存在，跳过


class TestPermissionManager:
    """权限管理器测试"""
    
    @pytest.fixture
    def test_db(self, tmp_path):
        """创建测试数据库"""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE tool_permissions (
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                role TEXT NOT NULL,
                granted INTEGER DEFAULT 1,
                conditions TEXT,
                granted_by TEXT,
                granted_at TEXT,
                expires_at TEXT,
                UNIQUE(tool_id, role)
            )
        """)
        
        conn.commit()
        conn.close()
        
        return db_path
    
    def test_permission_manager_creation(self, test_db):
        """测试权限管理器创建"""
        manager = PermissionManager(db_path=test_db)
        
        assert manager.db_path == test_db
        assert UserRole.OWNER in manager.role_hierarchy
        assert UserRole.GUEST in manager.role_hierarchy
    
    def test_role_hierarchy(self):
        """测试角色层级"""
        manager = PermissionManager()
        
        assert manager.get_role_level('owner') > manager.get_role_level('admin')
        assert manager.get_role_level('admin') > manager.get_role_level('user')
        assert manager.get_role_level('user') > manager.get_role_level('guest')
    
    def test_user_role_enum(self):
        """测试用户角色枚举"""
        assert UserRole.OWNER == "owner"
        assert UserRole.ADMIN == "admin"
        assert UserRole.USER == "user"
        assert UserRole.GUEST == "guest"


class TestAuditLogger:
    """审计日志测试"""
    
    @pytest.fixture
    def test_db(self, tmp_path):
        """创建测试数据库"""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE tool_audit_log (
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                session_id TEXT,
                user_id TEXT,
                action TEXT NOT NULL,
                parameters TEXT,
                result TEXT,
                error_message TEXT,
                risk_level TEXT,
                approval_status TEXT,
                approved_by TEXT,
                approved_at TEXT,
                execution_time_ms INTEGER,
                created_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE tool_registry (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        cursor.execute("INSERT INTO tool_registry (id, name) VALUES ('tool_1', 'test_tool')")
        
        conn.commit()
        conn.close()
        
        return db_path
    
    def test_audit_logger_creation(self, test_db):
        """测试审计日志记录器创建"""
        logger = AuditLogger(db_path=test_db)
        
        assert logger.db_path == test_db
    
    def test_mask_sensitive_parameters(self, test_db):
        """测试敏感参数屏蔽"""
        logger = AuditLogger(db_path=test_db)
        
        params = {
            'username': 'testuser',
            'password': 'secret123',
            'api_key': 'key123',
            'action': 'read'
        }
        
        masked = logger._mask_sensitive_parameters(params)
        
        assert masked['username'] == 'testuser'
        assert masked['password'] == '***MASKED***'
        assert masked['api_key'] == '***MASKED***'
        assert masked['action'] == 'read'
    
    def test_audit_log_to_dict(self):
        """测试审计日志转字典"""
        log = AuditLog(
            id="log_1",
            tool_id="tool_1",
            session_id="session_1",
            user_id="user_1",
            action="execute",
            result="success",
            risk_level="low"
        )
        
        log_dict = log.to_dict()
        
        assert log_dict['id'] == "log_1"
        assert log_dict['action'] == "execute"
        assert log_dict['risk_level'] == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
