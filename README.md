# music-education-prose

面向中文音乐教育学博士论文、期刊论文、研究报告、专著与教材写作的 Codex Skill。它补充音乐教育领域的概念关系、音乐材料锚点、教学过程、学习者活动与证据推论规则；通用中文逐句校审由 `chinese-prose-quality` 等通用流程承担。

Skill 不收录或再发布原始书籍、OCR、长引文和私人项目材料。示例均为新写的构造示例。它不代替文献检索、谱音核验、数据分析或作者的学术判断。

## 安装到 Codex 项目

在项目根目录运行：

```bash
python3 /path/to/music-education-prose/tools/install.py --project /path/to/codex-project
```

安装器只向项目内的 `.agents/skills/music-education-prose/` 新增 Skill 入口、界面元数据和参考文件；目标已存在时会停止，不覆盖现有文件。安装后在新任务中调用 `$music-education-prose`，或直接用自然语言提出相关音乐教育中文写作任务。Skill 默认允许隐式发现。

若要全局安装，将 Skill 目录复制到 `$CODEX_HOME/skills/`（未设置时通常为 `~/.codex/skills/`）。本仓库安装器面向项目级部署，不会自动改写全局 `AGENTS.md`。

## Skill 内容

- `SKILL.md`：触发范围、工作流程、学科边界和职责限制。
- `references/`：音乐术语与描述锚点、证据与论证、学术写作、教材活动、反例诊断。
- `evals/`：正反例任务和盲测评分方法。
- `tools/`：本地包校验、完整性清单生成及安全的项目安装。
- `tests/`：不依赖第三方库的结构、校验器和安装器测试。

## 验证

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py .
python3 tools/check_package.py
python3 -m unittest discover -s tests -v
```

这里的结构测试不等于写作效果评测。行为评测应随机化条件，分别在无专门 Skill、仅启用通用中文 Skill、两者同时启用的条件下生成同题文本；每条件重复生成，去除条件信息后由多位音乐教育评阅者评分。应分别检查词汇、句法、论证、学科性与事实闸门，并包含材料充足的正例和证据不足、要求过度推断的反例。

## 状态

版本 `0.1.0` 为首个可用原型。当前项目的初始盲测由同一模型生成并评分，A*条件也受到环境写作规则影响，因此不能当作独立效能验证。后续应以独立会话、重复生成和外部评阅完成验证。

## 许可

MIT License，见 [LICENSE](LICENSE)。
