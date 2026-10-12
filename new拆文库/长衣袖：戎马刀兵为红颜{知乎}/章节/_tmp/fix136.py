import re

p = '第136章_摘要.md'
lines = open(p, encoding='utf-8').read().split('\n')

head, blocks, rest = [], [], []
i = 0
while i < len(lines):
    if lines[i].startswith('P') and i + 1 < len(lines) and lines[i + 1].startswith('主题标签'):
        blocks.append([lines[i], lines[i + 1]])
        i += 2
    else:
        (head if not blocks else rest).append(lines[i])
        i += 1

print('blocks', len(blocks))


def merge(a, b):
    A = blocks[a - 1]
    B = blocks[b - 1]
    ka, va = A[0].split(' | ', 1)
    kb, vb = B[0].split(' | ', 1)
    da = va.split(' | 涉及')[0]
    db = vb.split(' | 涉及')[0]
    fa = ' | 涉及' + va.split(' | 涉及', 1)[1]
    A[0] = ka + ' | ' + da.rstrip() + '；' + db + fa
    del blocks[b - 1]


for a, b in sorted([(1, 2), (8, 9), (24, 25), (39, 40), (43, 44)], reverse=True):
    merge(a, b)

for idx, blk in enumerate(blocks, 1):
    blk[0] = re.sub(r'^P\d+ ', 'P%d ' % idx, blk[0])

out = []
out.extend(head)
for blk in blocks:
    out.append(blk[0])
    out.append(blk[1])
    out.append('')
out.extend(rest)
open(p, 'w', encoding='utf-8').write('\n'.join(out))
print('final', len(blocks))
