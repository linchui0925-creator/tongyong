## 系统与文件操作命令
### 文件查看
- `ls -la` — 列出目录内容（含隐藏文件）
- `cat <file>` — 查看文件内容
- `head -n 20 <file>` — 查看文件前 N 行
- `tail -n 20 <file>` — 查看文件后 N 行
- `tail -f <file>` — 实时跟踪文件（日志）
- `wc -l <file>` — 统计文件行数

### 文件搜索
- `grep -r "pattern" --include="*.py"` — 在 Python 文件中搜索
- `grep -rn "pattern" .` — 递归搜索所有文件
- `find . -name "*.py"` — 按名称查找文件
- `find . -type f -name "*.tsx"` — 查找特定类型文件

### 文件操作
- `touch <file>` — 创建空文件
- `mkdir -p <path>` — 创建目录（含父目录）
- `cp <src> <dst>` — 复制文件
- `mv <src> <dst>` — 移动/重命名文件
- `pwd` — 显示当前目录
- `echo <text>` — 输出文本

### 进程管理
- `ps aux` — 查看所有进程
- `ps aux | grep python` — 查看 Python 进程
- `kill <pid>` — 终止进程
