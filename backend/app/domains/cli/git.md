## Git 版本控制命令
### 常用操作
- `git status` — 查看工作区状态
- `git log --oneline -10` — 查看最近提交历史
- `git diff` — 查看未暂存的更改
- `git diff --staged` — 查看已暂存的更改
- `git add <file>` — 暂存文件
- `git commit -m "msg"` — 提交更改
- `git push origin <branch>` — 推送到远程
- `git pull origin <branch>` — 拉取远程更新
- `git fetch` — 获取远程更新（不合并）

### 分支管理
- `git branch` — 列出本地分支
- `git branch -a` — 列出所有分支
- `git checkout <branch>` — 切换分支
- `git checkout -b <branch>` — 创建并切换分支
- `git merge <branch>` — 合并分支

### 注意
- `git push --force` 需要用户确认
- `git rebase` 需要谨慎使用
- `git reset --hard` 会丢弃本地更改
