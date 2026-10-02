#!/usr/bin/env python3
"""人生副本剧本技术核对入口（v3.0）。

只核对技术事实，不判创作：

  python3 scripts/fuben_run.py 作品/NN_主题/ --json          # 输入/算术/指标
  python3 scripts/fuben_run.py 作品/NN_主题/正文.md --style   # 附加 AI 腔句式候选（可选）

创作规则（无烟红线/禁词/开头铁律/对白限额/账目纪律/体量/结构评分）已整体写入
`skills/fuben-write/` 的提示词与 references，由写作者与审读者逐条自检；脚本
不为它们设卡。发布前证据另见 fuben_release.py；产物与哈希绑定见 fuben_products.py。

PASS 只说明没有检出确定的输入或算术错误，不是创作批准。
"""
from fuben_engine import cli

if __name__ == '__main__':
    raise SystemExit(cli(label='TECHNICAL'))
