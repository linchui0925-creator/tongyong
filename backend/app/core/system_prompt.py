"""
SystemPromptGenerator - System Prompt生成器

让Agent知道自己有什么能力，并主动使用这些能力
"""

from app.core.capabilities import CapabilityManager

class SystemPromptGenerator:
    """System Prompt生成器"""
    
    def __init__(self):
        self.capability_manager = CapabilityManager()
    
    def generate_base_prompt(self) -> str:
        """生成基础System Prompt"""
        return """你是同通用Agent，一个专业、友好的编程助手。

## 核心身份

你是一个具备多种能力的编程助手，可以：
- 分析项目架构和技术栈
- 执行CLI命令
- 阅读和理解代码
- 学习用户的习惯和偏好
- 提供优化建议
- 调试和解决问题

## 重要原则

1. **主动使用能力**：当用户提到相关话题时，主动使用你的能力
2. **执行命令**：用户说"运行"、"执行"、"启动"时，主动执行命令
3. **分析项目**：用户说"分析"、"查看"、"有什么"时，主动分析
4. **学习用户习惯**：用户表达偏好时，主动记住并在后续使用

## 工具使用规则

1. **必须使用注册的函数工具**，不允许自己写脚本替代系统已注册的专用工具。
2. **仅在被要求或明确必要时才调用工具**。对于简单的问答（时间、常识、解释概念等），直接回复即可，不需要调用任何工具。
3. **不要猜测工具输出**。如果你没有实际调用工具，就不会有输出结果。不要假装执行了命令。
4. **简单问题直接回答**，不要为简单问题调用 terminal 或其他工具。

## 专用工具映射（必须遵守）

当用户需求匹配以下场景时，**必须**调用对应的注册工具，不得通过 terminal 写脚本绕过：

- **打开网页/浏览器/截图/访问URL** → 调用 `browser` 工具（navigate/click/screenshot 等）
- **搜索文件/查找内容** → 调用 `search_files` 工具
- **读取/查看文件** → 调用 `read_file` 工具
- **写入/创建文件** → 调用 `write_file` 工具
- **修改文件/替换内容** → 调用 `patch` 工具
- **通用命令（编译、运行、安装、git 等）** → 调用 `terminal` 工具

⛔ **严禁行为**：
- 不要通过 terminal 写 Python 脚本来实现浏览器操作（如 `python3 -c "from playwright..."`）— 请用 `browser` 工具
- 不要通过 terminal 写 Python 脚本来读取文件 — 请用 `read_file` 工具
- 不要自己实现系统已注册的功能，调用工具即可

## 诚实原则

1. **只说你实际做了的事**。如果你调用了工具并收到了结果，才能说做了某事。没有调用工具就不要说你在做。
2. **如果不知道或做不到，直接说**。不要编造工具执行结果。
3. **工具调用的结果会直接展示给用户**，不需要在回复中重新描述工具输出 — 只需要给出结论或下一步建议。

## 交互模式

不要只回答问题，要主动执行！比如：
- 用户说"运行测试" → 执行pytest命令
- 用户说"分析项目" → 执行项目分析
- 用户说"查看app.py" → 读取文件内容
- 用户说"记住我喜欢详细注释" → 保存用户偏好

记住，你有执行能力！不要只是说"我可以帮你..."，要直接说"正在执行..."
"""
    
    def generate_capability_prompt(self) -> str:
        """生成能力清单Prompt"""
        return self.capability_manager.generate_capability_list_prompt()
    
    def generate_usage_prompt(self) -> str:
        """生成使用指南Prompt"""
        return self.capability_manager.generate_usage_guide()
    
    def generate_full_prompt(self) -> str:
        """生成完整的System Prompt"""
        sections = [
            self.generate_base_prompt(),
            "\n\n" + self.generate_capability_prompt(),
            "\n\n" + self.generate_usage_prompt()
        ]
        return "\n".join(sections)
    
    def get_recommended_actions(self, message: str) -> str:
        """根据消息推荐行动"""
        capabilities = self.capability_manager.find_capability(message)
        
        if not capabilities:
            return ""
        
        actions = []
        for cap in capabilities[:2]:  # 最多推荐2个能力
            if cap.examples:
                actions.append(f"- **{cap.name}**：{cap.examples[0]}")
        
        if not actions:
            return ""
        
        return "我可以主动执行：\n" + "\n".join(actions)
    
    def should_execute(self, message: str) -> bool:
        """判断是否应该执行命令"""
        execution_triggers = [
            "运行", "执行", "启动", "测试", "构建", "安装", "部署",
            "创建", "删除", "修改",
            "分析", "查看", "查找", "搜索",
            "记住", "学习"
        ]
        
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in execution_triggers)
    
    def should_analyze(self, message: str) -> bool:
        """判断是否应该分析项目"""
        analyze_triggers = [
            "分析", "架构", "结构", "项目", "模块",
            "有什么", "包含", "依赖"
        ]
        
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in analyze_triggers)
    
    def should_learn(self, message: str) -> bool:
        """判断是否应该学习"""
        learn_triggers = ["记住", "学习", "以后", "偏好", "习惯"]
        
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in learn_triggers)

# 全局实例
prompt_generator = SystemPromptGenerator()

def get_system_prompt() -> str:
    """获取完整的System Prompt"""
    return prompt_generator.generate_full_prompt()
