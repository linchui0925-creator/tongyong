import React, { useState, useEffect } from 'react';

interface Skill {
  id: string;
  name: string;
  content: string;
  category: string;
  usage_count: number;
  success_rate: number;
  version: number;
  trigger_conditions: string[];
  execution_steps: string[];
}

export const SkillManagement: React.FC = () => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/skills');
      const data = await response.json();
      setSkills(data.skills || []);
    } catch (error) {
      console.error('获取技能列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredSkills = skills.filter(skill =>
    skill.name.toLowerCase().includes(filter.toLowerCase()) ||
    skill.content.toLowerCase().includes(filter.toLowerCase())
  );

  const deleteSkill = async (skillId: string) => {
    if (!confirm('确定要删除此技能吗？')) return;
    try {
      await fetch(`/api/skills/${skillId}`, { method: 'DELETE' });
      fetchSkills();
    } catch (error) {
      console.error('删除技能失败:', error);
    }
  };

  const modalOverlay: React.CSSProperties = {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  };

  const modalContent: React.CSSProperties = {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-xl)',
    padding: '24px',
    maxWidth: '520px',
    width: '90%',
    maxHeight: '80vh',
    overflow: 'auto',
    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        padding: '12px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-surface)',
      }}>
        <span style={{
          fontSize: '11px',
          fontWeight: 600,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.8px',
        }}>
          技能库
        </span>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button className="btn btn-ghost" onClick={() => setShowHelp(!showHelp)}>
            {showHelp ? '收起帮助' : '帮助'}
          </button>
          <input
            type="text"
            placeholder="搜索技能..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input"
            style={{ width: '200px' }}
          />
          <button className="btn btn-ghost" onClick={fetchSkills}>刷新</button>
        </div>
      </div>

      {/* Help */}
      {showHelp && (
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-secondary)',
          fontSize: '13px',
          lineHeight: 1.6,
          color: 'var(--text-secondary)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}>
          <div>
            <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>📋 什么是技能？</strong>
            <p style={{ margin: 0 }}>技能是 Agent 可执行的功能模块，包含触发条件、执行步骤和使用统计。每项技能都经过版本管理，支持持续优化。</p>
          </div>
          <div>
            <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>📖 使用说明</strong>
            <ul style={{ margin: 0, paddingLeft: '20px' }}>
              <li style={{ marginBottom: '4px' }}><strong>查看详情</strong> — 点击任意技能卡片查看完整信息（描述、触发条件、执行步骤）</li>
              <li style={{ marginBottom: '4px' }}><strong>搜索</strong> — 在搜索框输入关键词快速定位技能</li>
              <li style={{ marginBottom: '4px' }}><strong>删除</strong> — 鼠标悬停时显示删除按钮</li>
              <li style={{ marginBottom: '4px' }}>技能由 Agent 自动管理，无需手动创建</li>
            </ul>
          </div>
        </div>
      )}

      {/* List */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}>
        {loading ? (
          <div className="empty-state">加载中...</div>
        ) : filteredSkills.length === 0 ? (
          <div className="empty-state">暂无技能</div>
        ) : (
          filteredSkills.map(skill => (
            <div
              key={skill.id}
              onClick={() => setSelectedSkill(skill)}
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-lg)',
                padding: '16px',
                cursor: 'pointer',
                transition: 'border-color 0.12s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-hover)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '8px',
              }}>
                <span style={{
                  fontSize: '14px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}>
                  {skill.name}
                </span>
                <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                  <span style={{
                    fontSize: '12px',
                    color: 'var(--text-tertiary)',
                  }}>
                    使用 {skill.usage_count} 次
                  </span>
                  <span style={{
                    fontSize: '12px',
                    color: skill.success_rate > 80 ? 'var(--success)' : 'var(--text-tertiary)',
                  }}>
                    {skill.success_rate.toFixed(0)}%
                  </span>
                  <span style={{
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    background: 'var(--bg-elevated)',
                    padding: '1px 6px',
                    borderRadius: 'var(--r-sm)',
                  }}>
                    v{skill.version}
                  </span>
                </div>
              </div>
              <div style={{
                fontSize: '13px',
                color: 'var(--text-tertiary)',
                lineHeight: 1.5,
                marginBottom: '8px',
              }}>
                {skill.content.substring(0, 120)}...
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  className="btn btn-ghost"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSkill(skill.id);
                  }}
                >
                  删除
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Detail modal */}
      {selectedSkill && (
        <div style={modalOverlay} onClick={() => setSelectedSkill(null)}>
          <div style={modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={{
              fontSize: '16px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: '20px',
            }}>
              {selectedSkill.name}
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: '6px',
              }}>
                描述
              </div>
              <p style={{
                fontSize: '14px',
                color: 'var(--text-secondary)',
                lineHeight: 1.6,
              }}>
                {selectedSkill.content}
              </p>
            </div>

            {selectedSkill.trigger_conditions.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  marginBottom: '6px',
                }}>
                  触发条件
                </div>
                <ul style={{
                  paddingLeft: '20px',
                  fontSize: '14px',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.8,
                }}>
                  {selectedSkill.trigger_conditions.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {selectedSkill.execution_steps.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  marginBottom: '6px',
                }}>
                  执行步骤
                </div>
                <ol style={{
                  paddingLeft: '20px',
                  fontSize: '14px',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.8,
                }}>
                  {selectedSkill.execution_steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              </div>
            )}

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '12px 0',
              borderTop: '1px solid var(--border)',
              marginBottom: '16px',
              fontSize: '13px',
              color: 'var(--text-tertiary)',
            }}>
              <span>使用次数: {selectedSkill.usage_count}</span>
              <span>成功率: {selectedSkill.success_rate.toFixed(1)}%</span>
              <span>版本: {selectedSkill.version}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setSelectedSkill(null)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SkillManagement;
