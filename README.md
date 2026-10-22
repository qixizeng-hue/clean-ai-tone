# clean-ai-tone · 中文交付件终审门禁（跨系统 Skill）

标准 skill 包，可安装到任意支持 SKILL.md 约定的系统：Claude Code、Cursor 或其他 Agent 平台。
用于中文专业文稿的去 AI 味终检与确认后改稿：清洗说教腔、套话、修辞符号与空泛评价，保留事实口径与可核对数值。

## 两种用法

- **GATE 门禁**：审稿（只审不改）→ 人工确认问题清单 → 按清单改稿。适合交付前终审、「这份能不能发」。
- **clean 直通**：直接清洗润色，不出审稿报告。适合用户明确只要改稿的简单场景。

## 安装

### Claude Code / 通用 Agent

```bash
cp -r clean-ai-tone ~/.claude/skills/clean-ai-tone
```

项目级安装则复制到项目的 `.claude/skills/clean-ai-tone/`。

### Cursor

```bash
cp -r clean-ai-tone .cursor/skills/clean-ai-tone
```

Windows PowerShell：

```powershell
Copy-Item -Recurse clean-ai-tone .cursor\skills\clean-ai-tone
```

### 其他平台

放入平台对应的 skills 目录即可。本包仅依赖 `SKILL.md` + `references/`，无脚本、无外部依赖。

也可以把本目录发布为独立 Git 仓库，各系统 `git clone` 使用，便于统一升级。

## 目录结构（v5.17）

```
clean-ai-tone/
├── SKILL.md                # 入口：3 步最小路径、GATE→CONFIRM→FIX 工作流、clean 直通模式
├── README.md               # 本文件：安装、目录、抽取纪律
├── NOTICE                  # 第三方致谢与引用归因（8 来源，使用请保留）
├── LICENSE                 # MIT
├── CHANGELOG.md            # 变更记录（v1.0 → v5.17 全程）
├── references/             # 规则与流程（含 v5.13 语义保真 H 节）
│   ├── gate-checklist.md       # 审稿门禁 D1–D8、分级、场景路由、放行规则
│   ├── gate-report-template.md # 审稿报告模板（含人工确认区）
│   ├── readability-checklist.md # 可读性审查 R1–R7、快速评分法
│   ├── checklist.md            # A–H 终检清单（A2 修订 / G 请示稿 / H 语义保真）
│   ├── phrase-blacklist.md     # 禁用词与替换表（套话 / 夸张 / 黑话 / §23 结构表）
│   ├── rewrite-patterns.md     # 正反例改写范式 §1–38（含 §37 方向判据、§38 语义保真改法）
│   ├── style-profile.md        # 文风画像（P0/P1/P2 分层 + 交付件书面体）
│   ├── production-path.md      # 生产路径：句库组句、句式硬检（H23–H27）
│   ├── delivery-artifact-mode.md # 交付物模式：定稿句先于出图（H18–H22）
│   └── sentence-bank/          # 句库：已批页 / 词条 / 模板 / 术语表 / 冻结数 / 废弃句归档
├── tools/
│   ├── scan_ai_tone.py         # 扫描脚本（51 规则，HARD/SOFT 分级，--lite 轻量开关，防伪放行）
│   └── scan_config.example.json # 扫描 config 示例（rules 留空即用内置全量）
├── cursor-rules/           # Cursor 集成规则（blacklist / checklist / rewrite / style）
├── project/                # 项目覆盖层示例（机构口径放这里，不进公共核）
├── experience/             # 多轮复扫方法与迭代日志
└── evals/
    └── evals.json          # 测试用例（门禁退回、可读性、FIX 改稿 + 非金融语料）
```

历史迁移文件（v1.0 整合说明、core_legacy 旧版四件套等）不在发布包，存于包外 clean-ai-tone-archive/。

## 与项目层关系

本包是**公共核**，定位为金融、咨询、研报等专业报告类文档的终审与去 AI 腔。各项目的机构口径、验收锚点、专有隐喻放在该项目自己的 `project/` 覆盖层，
由项目入口先读本核、再读项目层。安装本包时不要附带任何项目的覆盖层（见下方「抽取纪律」）。

## 与 ll-humanizer-zh

MIT 上游，用于 H1–H8 说教腔诊断。本包吸收其诊断，**覆盖**其口语化默认（交付场景保持书面语）。详见 NOTICE。

## 抽取纪律

抽取到其他项目时：只复制本目录；不要附带原项目的 `project/` 覆盖层，除非已确认脱敏
（无机构名称、无监管未公开口径、无客户未授权数据）。第三方致谢与引用见 `NOTICE`，使用时请保留。
