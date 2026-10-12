import re, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TONES = {'紧张', '轻松', '悲伤', '热血', '爽', '甜', '温馨', '恐怖', '压抑', '其他'}
THEMES = {'爱情', '亲情', '友情', '权力', '金钱', '成长', '复仇', '悬念', '搞笑', '热血', '日常', '其他'}

errors = []
summary = []
for n in range(114, 138):
    p = os.path.join(BASE, '第%d章_摘要.md' % n)
    if not os.path.exists(p):
        errors.append('第%d章 文件缺失' % n)
        continue
    lines = open(p, encoding='utf-8').read().split('\n')
    plines = [l for l in lines if re.match(r'^P\d+ ', l)]
    tones = [l for l in lines if re.match(r'^主题标签[^ ]* \| 基调：', l)]
    errs = []
    if len(plines) != len(tones):
        errs.append('P行数%d != 基调行数%d' % (len(plines), len(tones)))
    if not (10 <= len(plines) <= 40):
        errs.append('情节点数%d 越界' % len(plines))
    nums = [int(re.match(r'^P(\d+) ', l).group(1)) for l in plines]
    if nums != list(range(1, len(nums) + 1)):
        errs.append('P序号不连续: %s' % nums[:12])
    # tone / theme lines
    tl = [l for l in lines if l.startswith('主题标签')]
    if len(tl) != len(tones):
        errs.append('主题标签行%d != 合规基调行%d' % (len(tl), len(tones)))
    prev = None
    for i, l in enumerate(tl):
        m = re.match(r'^主题标签([^ ｜|]+) \| 基调：(.+)$', l.strip())
        if not m:
            errs.append('标签行格式错误: %s' % l[:40])
            continue
        if m.group(1) not in THEMES:
            errs.append('主题标签非法[%s] @%s' % (m.group(1), l[:30]))
        if m.group(2) not in TONES:
            errs.append('基调非法[%s] @%s' % (m.group(2), l[:30]))
    for i, l in enumerate(plines):
        if '类型' not in l or ' | ' not in l:
            errs.append('P%d 缺类型段' % (i + 1))
            continue
        seg = l.split(' | ')
        if len(seg) < 3:
            errs.append('P%d 段数不足' % (i + 1))
            continue
        m = re.match(r'^P\d+ \*\*[^*]+\*\*：类型(.+)$', seg[0])
        if not m:
            errs.append('P%d 标题或类型格式错' % (i + 1))
        if not seg[1].strip():
            errs.append('P%d 白描为空' % (i + 1))
        if not seg[2].startswith('涉及'):
            errs.append('P%d 涉及段缺失' % (i + 1))
    summary.append((n, len(plines), len(tones), 'OK' if not errs else 'ERR'))
    for e in errs:
        errors.append('第%d章 %s' % (n, e))

for s in summary:
    print(s)
print('---- ERRORS ----')
for e in errors:
    print(e)
print('total errors', len(errors))
