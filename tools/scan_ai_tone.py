#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean-ai-tone 文风约束扫描（可移植版）

用法：
  python scan_ai_tone.py --base <稿件目录> [--config <config.json>] [--lite]

  --lite        : 轻量模式，仅输出 HARD 级规则命中（非金融日常文案降噪快扫；规则内容零改动，完整 51 规则去掉本开关即回）

配置（JSON）：
  articles      : 正文文件 glob（相对 --base），如 ["*.md", "*.html"]
  svg_patterns  : 结构图 SVG glob，如 ["*.svg"]
  scripts       : 生成脚本文件名，如 ["gen_illustrations.py"]
  rules         : [{name, pattern, severity}]  severity=HARD 必须修 / SOFT 可保留

未提供 --config 时，默认扫描 --base 目录下 *.md 文件（开箱即扫），并使用内置公共核默认规则。
输出：按文件 + 规则列出命中（正文组 / 配图组），同行同规则多命中合并计数；最后给 PASS/FAIL 结论。

上下文感知（只扫对外发布文本，避免代码误报）：
  .md     : 原文直扫
  .html   : 去标签与属性，只留可见文本（src/style 等不算对外文本）
  .svg    : 直扫；箭头 → 降为 SOFT（图元素）
  .py/.pyw: 去注释与 docstring、去 print、只取字符串字面量、排除路径类字符串；箭头 → 降为 SOFT
"""
import argparse
import glob
import json
import os
import re
import sys

# 公共核默认规则（跨项目通用；项目专有规则放调用方配置）
DEFAULT_RULES = [
    ("修辞引号「」『』", r"[「」『』]", "HARD"),
    ("破折号 — – ──（数字间连接号豁免，如 T/BFIA 070—2026 国标号）", r"(?<!\d)[—–─](?!\d)", "HARD"),
    ("正文箭头 →", r"→", "HARD"),
    ("套话/AI腔", r"综上所述|值得一提的是|很多人都在问|一句话总结|不难看出|关键在于|核心是|绕不开|主战场|堪称|卓越|极显著|显而易见|毫无疑问|换句话说|实实在在|标配|完整图景|按下快进键|顺手带进来", "HARD"),
    ("夸张/贬义", r"短板|洼地|天花板|令人|巨大|严峻", "HARD"),
    ("emoji/装饰符", r"[✅❌⚠✨💡📌★☆✦✧＊●◆■□▶►➤‣✓✔✕✖☑☒]", "HARD"),
    ("口号点号堆砌 A·B·C", r"·[^，。；\n]{0,14}·", "SOFT"),
    ("方头括号【】", r"[【】]", "HARD"),
    ("不必要约(精确数前)", r"约\s*\d", "SOFT"),
    ("字母编号G项E项", r"[A-G]项", "SOFT"),
    ("页码代替动作", r"写入第\d+页|详见第\d+页", "SOFT"),
    ("截止+日期(宜用截至)", r"截止\s*\d{4}|截止行内", "SOFT"),
    ("口语拦下", r"拦下", "SOFT"),
    ("路径长串写入…中的…项", r"写入[^。；\n]{0,40}中的[^。；\n]{0,12}项", "SOFT"),
    ("自动高额电报", r"自动高额", "SOFT"),
    ("冗余指代该条写入", r"该条写入|该条同步写入|该条由", "SOFT"),
    ("冗余指代上述动作", r"上述动作写入", "SOFT"),
    ("冗余主语系统记为", r"系统记为|审批系统记录为", "SOFT"),
    ("口语化不是线性关系", r"不是线性关系", "SOFT"),
    ("冗余大于等于", r"大于等于", "SOFT"),
    ("口语前列原因", r"前列原因|后列原因", "SOFT"),
    ("重复完整完成", r"未完整完成|完整完成", "SOFT"),
    ("口语不另写", r"不另写|不另做", "SOFT"),
    ("口语剔出", r"剔出", "SOFT"),
    ("同向反向无主语", r"与通过率同向|与不良反向|同向、与", "SOFT"),
    ("无支撑利息推断", r"贡献利息收入", "SOFT"),
    ("模糊量词大量", r"误拒了大量|大量的", "SOFT"),
    ("或代且须同时", r"区分度或提升度", "SOFT"),
    ("模糊量词大量", r"误拒了大量|大量的申请", "SOFT"),
    ("过强因果推断", r"受策略松紧、模型迭代和观察期长短影响", "SOFT"),
    ("内部代号价值页类", r"价值页|抓手|赋能|闭环|看板|拉通", "SOFT"),
    ("压缩数量词", r"[三四五六双][项类大]?(指数|分型|档位|维度|象限|标签|稳健性)|五档结论", "SOFT"),
    ("加工层编号", r"L[1-5]\s*(层|阶段)|五层(加工|流水线|架构)", "SOFT"),
    ("称谓话术领导", r"领导(要求|关切|确认|采信|汇报|关注|反应)", "HARD"),
    ("交付用语", r"交付物", "SOFT"),
    ("行业黑话", r"双证|安慰剂|金叉|死叉", "SOFT"),
    ("自述式引导句", r"(本文|本节|本报告|下面)(将|会)?(说明|介绍|回答|给出)|需要回答[一二三四五]个|包括以下[一二三四五]部分|逐步结论如下", "SOFT"),
    # --- H28 对话粘贴残留（AI 助手输出直接入稿）---
    ("对话残留客套", r"希望(这|以上|以上内容)?对(您|你|大家)有帮助|请告诉我(是否|需要|如果|还)|如果(您|你)需要[^。；\n]{0,16}(请|欢迎)(告诉|联系|随时)", "HARD"),
    ("对话残留应答", r"当然！|明白了！|好的，(下面|我来)|这是一个(很)?好(的)?问题|(您|你)说得(完全)?正确", "HARD"),
    ("AI截止免责", r"截至(我的知识|20\d\d年)[^。；\n]{0,20}(训练|更新|数据)|根据我(最后)?的?训练|基于(目前)?可(以)?获得的信息", "HARD"),
    # --- H29 AI 句式结构（跨句模式机器只提示，人工裁决）---
    ("AI否定排比", r"不仅仅是[^。；\n]{0,20}(而是|更是)|这不只是[^。；\n]{0,20}(而是|还)|与其说[^。；\n]{0,20}(不如说|倒不如|毋宁)|并非[^。；\n]{0,30}而是|不在于[^。；\n]{0,30}而在于|表面(上)?[^。；\n]{0,30}(其实|实际|实则)|看似[^。；\n]{0,30}(其实|实际|实则)|以为[^。；\n]{0,30}(其实|才发现|才明白|才知道)|回头(看)?才(发现|明白|知道)|恰恰相反|从来(都)?不是[^。；\n]{0,10}，?而是|[^，。；\n]{1,10}不重要，[^。；\n]{0,10}重要的是", "SOFT"),
    ("AI虚假范围", r"从[^。；\n，]{0,10}(到|至)[^。；\n，]{0,10}的?(全流程|全景|旅程|演进|蓝图|全生命周期|一站式|端到端)|覆盖全生命周期", "SOFT"),
    # --- v5.13 详细层扩容（思想对标 human-writing / humanize-chinese / lieflat / qu-ai-wei，见 NOTICE 第 7 条；词表为本包原创）---
    ("AI路标词", r"值得注意的是|需要指出的是|需要强调的是|更微妙的是|还有一层|只说对了一半|从某种意义上说|不难发现|总而言之|由此可见|不仅如此|归根结底|毋庸置疑|不言而喻|如前所述|由此可以看出", "HARD"),
    ("AI起手式", r"说白了|说穿了|先说结论", "HARD"),
    ("AI深刻腔", r"这意味着|更深层次的|不可否认", "SOFT"),
    ("互联网黑话", r"全链路|组合拳|技术底座|内容矩阵|认知跃迁|降本增效|商业闭环|顶层设计|底层逻辑|结构性机会|打开想象空间|单点风险|能力沉淀|深层逻辑", "SOFT"),
    ("新媒体腔", r"赛道|破圈|出圈|内卷|躬身入局|长期主义|加持", "SOFT"),
    ("模板开头句式", r"随着[^。；\n]{0,20}的(不断)?发展|在当今[^。；\n]{0,12}时代|对于[^。；\n]{0,16}而言[^。；\n]{0,24}至关重要", "SOFT"),
    ("性化后缀堆叠", r"[\u4e00-\u9fa5]{1,6}性[^。；\n，]{0,8}[\u4e00-\u9fa5]{1,6}性", "SOFT"),
    ("AI段首评论(零回指)", r"^(听起来|看起来|更重要的是|问题在于)(?![^。\n]{0,30}[这那其此])", "SOFT"),
    ("时间锚点(宜改具体日期)", r"截至今日|(截至目前|截止目前)(?![^。\n]{0,30}(20|19)\d\d年)", "SOFT"),
    # --- H31 PPT/总部汇报同构（2026-10-21 金服 AI 汇报沉淀；细则 ppt-deck-isomorphism.md）---
    ("PPT段末同构诉求", r"需要总部给的是", "HARD"),
    ("PPT不是而是简式", r"(?<![不非])不是[^。；\n]{0,28}，?而是|(已经)?不是[^。；\n]{0,16}，?是(?!否)|目标不是[^。；\n]{0,20}，?而是", "SOFT"),
    ("PPT正反同拍", r"集中在[^。；\n]{0,24}(偏少|不足|不够)", "SOFT"),
    ("PPT对外禁漏", r"不作对外引用|内部口径(?!表)|白嫖", "SOFT"),
    ("PPT口头括号补充", r"[（(]口头补充[：:][^）)]{0,80}[）)]", "SOFT"),
]


def load_config(path):
    # v5.14：未提供 --config 时默认扫描 base 目录下 *.md（开箱即扫，修复裸跑 FAIL）；
    # 显式提供 config 时以配置为准（配置里 articles 为空仍按 0 文件处理，保留空扫描防伪放行）
    cfg = {"articles": ["*.md"] if path is None else [],
           "svg_patterns": [], "scripts": [], "rules": []}
    if path:
        if not os.path.exists(path):
            # v5.13 修复：config 路径无效时显式报错，不再静默回退默认规则（防伪放行）
            raise SystemExit(f"错误：--config 指定的文件不存在：{path}")
        try:
            with open(path, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except json.JSONDecodeError as e:
            raise SystemExit(f"错误：--config JSON 解析失败：{e}")
    if not cfg.get("rules"):
        cfg["rules"] = [{"name": n, "pattern": p, "severity": s}
                        for n, p, s in DEFAULT_RULES]
    return cfg


def resolve_files(base, cfg):
    articles = []
    for pat in cfg.get("articles", []):
        articles += glob.glob(os.path.join(base, pat))
    illus = []
    for pat in cfg.get("svg_patterns", []):
        illus += glob.glob(os.path.join(base, pat))
    for s in cfg.get("scripts", []):
        p = os.path.join(base, s)
        if os.path.exists(p):
            illus.append(p)
    return articles, illus


def _strip_html_tags(lines):
    """HTML：去掉标签与属性，只保留可见文本（src/style 等属性不算对外文本）"""
    return [re.sub(r"<[^>]*>", "", ln) for ln in lines]


def _strip_comments_docstrings(lines):
    """脚本：去掉整行注释与文档字符串（docstring 不渲染进配图）"""
    out = []
    in_doc = False
    for ln in lines:
        s = ln.strip()
        if in_doc:
            if '"""' in s or "'''" in s:
                in_doc = False
            out.append("")
            continue
        if s.startswith("#"):
            out.append("")
            continue
        if s.startswith('"""') or s.startswith("'''"):
            if s.count('"""') + s.count("'''") < 2:
                in_doc = True
            out.append("")
            continue
        out.append(ln)
    return out


def _extract_string_literals(line):
    """脚本：只保留会渲染进配图的字符串字面量，排除 print 与路径类字符串"""
    line = re.sub(r"print\s*\([^)]*\)", "", line)
    keep = []
    for lit in re.findall(r'f?"[^"]*"|\'[^\']*\'', line):
        body = lit.strip('f"\'').strip()
        if not body:
            continue
        if re.search(r"\.(png|svg|py|jpg|jpeg|gif|docx|md|json|ttc)\b", body, re.I):
            continue
        if re.search(r"[/\\]", body):
            continue
        keep.append(body)
    return " ".join(keep)


def scan_file(path, rules):
    hits = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return [("读取失败", str(e), 0, "HARD")]
    ext = os.path.splitext(path)[1].lower()
    if ext == ".html":
        lines = _strip_html_tags(lines)
    elif ext in (".py", ".pyw"):
        lines = _strip_comments_docstrings(lines)
        lines = [_extract_string_literals(ln) for ln in lines]
    # 配图（svg / 生成脚本）内箭头为图元素，允许 → 降为 SOFT 提示
    is_diagram = ext in (".svg", ".py", ".pyw")
    for i, ln in enumerate(lines, 1):
        for r in rules:
            sev = r["severity"]
            if is_diagram and "箭头" in r["name"]:
                sev = "SOFT"
            for m in re.finditer(r["pattern"], ln):
                ctx = ln.strip()[:60]
                hits.append((r["name"], ctx, i, sev))
    return hits


def run_group(label, files, rules):
    print(f"\n===== {label} =====")
    total_hard = 0
    for fn in files:
        if not os.path.exists(fn):
            continue
        hits = scan_file(fn, rules)
        if not hits:
            print(f"  [OK] {os.path.basename(fn)}")
            continue
        hard = [h for h in hits if h[3] == "HARD"]
        soft = [h for h in hits if h[3] == "SOFT"]
        total_hard += len(hard)
        tag = f"{len(hard)}硬 / {len(soft)}软" if soft else f"{len(hard)}硬"
        print(f"  [{tag}] {os.path.basename(fn)}")
        # v5.14：同行同规则多命中合并为一条（×N 计数），修复整行摘录重复刷屏
        merged = {}
        for name, ctx, i, sev in hits:
            key = (i, name)
            if key in merged:
                merged[key][0] += 1
            else:
                merged[key] = [1, name, ctx, i, sev]
        for (ln, _k), (n, name, ctx, _i, sev) in merged.items():
            cnt = f" ×{n}" if n > 1 else ""
            print(f"      L{ln:>3} [{sev}] {name}{cnt}: {ctx}")
    return total_hard


def main():
    ap = argparse.ArgumentParser(description="clean-ai-tone 文风约束扫描")
    ap.add_argument("--base", default=".", help="待扫描目录")
    ap.add_argument("--config", default=None, help="JSON 配置（规则+文件清单）")
    ap.add_argument("--lite", action="store_true",
                    help="轻量模式：仅扫描 HARD 级规则（规则内容零改动，纯过滤）")
    args = ap.parse_args()
    cfg = load_config(args.config)
    articles, illus = resolve_files(args.base, cfg)
    if not articles and not illus:
        # v5.13 修复：扫描 0 个文件时判 FAIL，禁止空扫描伪放行
        print("  FAIL：未找到任何待扫描文件。请检查 --base 目录与 config 的 articles/svg_patterns/scripts 通配。")
        sys.exit(1)
    rules = cfg["rules"]
    if args.lite:
        # v5.15 轻量模式：仅保留 HARD 级（含 config 自定义规则的 severity 过滤），不修改任何规则内容
        rules = [r for r in rules if r.get("severity", "HARD") == "HARD"]
        print(f"  [轻量模式] 仅扫描 HARD 级规则（{len(rules)} 条）；完整规则请去掉 --lite。")
    h1 = run_group("对外正文", articles, rules)
    h2 = run_group("配图文本", illus, rules)
    print("\n===== 结论 =====")
    print(f"  正文硬命中: {h1}  |  配图硬命中: {h2}")
    if h1 == 0 and h2 == 0:
        print("  PASS：对外正文与配图文本均无 clean-ai-tone 硬约束命中。")
    else:
        print("  FAIL：存在需修订的硬约束命中，见上。")
    sys.exit(1 if (h1 or h2) else 0)


if __name__ == "__main__":
    main()
