# clean-ai-tone v5.17 · 安装

相对外部已发布的 v5.15，本包含 v5.15.1 / v5.16 / v5.17（H30 呼吸感、H31 PPT/总部汇报同构等）。详见 CHANGELOG.md。

## Cursor（用户级）

```powershell
Expand-Archive -Path clean-ai-tone-v5.17.zip -DestinationPath $env:USERPROFILE\.cursor\skills -Force
# 解压后目录应为：$env:USERPROFILE\.cursor\skills\clean-ai-tone\
```

若 zip 内已含 `clean-ai-tone` 文件夹，也可先解压到临时目录再整夹覆盖到 `.cursor\skills\clean-ai-tone`。

## Cursor / Claude（项目级）

```powershell
Expand-Archive -Path clean-ai-tone-v5.17.zip -DestinationPath .\ -Force
Copy-Item -Recurse -Force .\clean-ai-tone .cursor\skills\clean-ai-tone
# 或 .claude\skills\clean-ai-tone
```

## 校验

1. 打开 `SKILL.md` 文末版本应为 **v5.17**
2. 可选：`python tools/scan_ai_tone.py --base <稿件目录>`；日常加 `--lite`

## 抽取纪律

只安装本公共核；机构口径放各项目自己的覆盖层，不要把未脱敏 project 内容当公共核分发。
