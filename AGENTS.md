# CloudLink Finder 项目协作规则

## Git 远程仓库

本项目代码必须同时同步到以下两个仓库：

- Gitee：`git@gitee.com:jindekun_admin/cloudlink-finder.git`
- GitHub：`ssh://git@ssh.github.com:443/jindekun520-dev/cloudlink-finder.git`

## 默认推送规则

1. 完成代码修改和必要测试后，先创建本地 Git 提交。
2. 默认执行 `git push origin main`；本机 `origin` 已配置两个 push URL，该命令会同时推送 Gitee 和 GitHub。
3. 如果多 push URL 配置不存在或推送结果不明确，则分别执行：

   ```bash
   git push origin main
   git push github main
   ```

4. 推送完成后必须分别读取两个远程的 `refs/heads/main`，确认它们与本地 `HEAD` 完全一致。
5. 任意一个远程推送失败，都不能报告“推送完成”；必须明确指出失败的仓库和认证/网络错误。

## 提交前检查

- 不提交 `frontend/node_modules/`、`frontend/dist/`。
- 不提交 SQLite 运行数据库、`.env`、本地日志或 `.claude/` 配置。
- 修改前后端代码后，按影响范围运行后端测试和前端构建。
