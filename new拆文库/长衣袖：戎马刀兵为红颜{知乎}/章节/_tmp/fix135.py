import re, io

p = '第135章_摘要.md'
s = open(p, encoding='utf-8').read()
lines = s.split('\n')

# locate P blocks: each P line followed by a 主题标签 line
out = []
i = 0
blocks = []
while i < len(lines):
    if lines[i].startswith('P') and i + 1 < len(lines) and lines[i + 1].startswith('主题标签'):
        blocks.append([lines[i], lines[i + 1]])
        i += 2
    else:
        out.append(lines[i])
        i += 1

print('blocks', len(blocks))

def merge(a, b):
    """merge block index b into a (1-based)"""
    A = blocks[a - 1]
    B = blocks[b - 1]
    ha, ra = A[0].split('：', 1)
    hb, rb = B[0].split('：', 1)
    ka, va = ra.split(' | ', 1)
    kb, vb = rb.split(' | ', 1)
    # keep A header; append B's 白描 then A's field groups
    fields = va.split(' | ', 1)[1] if ' | 涉及' in va else va
    A[0] = ha + '：' + ka + ' | ' + va.split(' | 涉及')[0].rstrip() + '；' + vb.split(' | 涉及')[0] + ' | 涉及' + fields
    del blocks[b - 1]

merge(15, 16)
merge(34, 35)

# renumber
for idx, blk in enumerate(blocks, 1):
    blk[0] = re.sub(r'^P\d+ ', 'P%d ' % idx, blk[0])

res = []
for ln in out:
    res.append(ln)
    if ln.strip() == '**情节点**：':
        for blk in blocks:
            res.append(blk[0])
            res.append(blk[1])
            res.append('')
# fallback: append at end if marker not found
if not any(b[0] in res for b in blocks):
    res.extend([x for b in blocks for x in b])

open(p, 'w', encoding='utf-8').write('\n'.join(res))
print('final', len(blocks))
