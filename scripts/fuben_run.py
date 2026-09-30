#!/usr/bin/env python3
"""人生副本可拍剧本的机械检查（v3.0）。PASS ≠ 好看，也 ≠ 可发布。

python3 scripts/fuben_run.py 作品/NN_xxx/ --profile full --json
python3 scripts/fuben_run.py 作品/NN_xxx/旁白.md --profile short --json

目录形态优先读 旁白.md（没有则 正文.md）。v3.0 已删除产物齐备门禁与审核报告哈希绑定：
它们只能证明「文件在场」，不能证明有人读过稿子。
"""
from fuben_engine import cli

if __name__ == '__main__':
    raise SystemExit(cli(label='SCRIPT-CHECK'))
