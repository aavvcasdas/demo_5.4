# 工艺门禁回归测试（2026-09-24b 增补）
"""fuben_craft / fuben_ledger / fuben_products 的最小固定用例。

只测机械协议：红线 BLOCK、候选 REVIEW、描述 NOTE、豁免面与产物核对。
这些绿灯不代表开头留得住、账目真平或稿子好看——闭环义务仍在 04 审读。
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fuben_engine import finding, inspect_path, load_policy, text_sha256
from fuben_craft import craft_checks, ledger_rows, dialogue_stats


def craft(text, profile='full'):
    return craft_checks(text, Path('正文.md'), profile, load_policy(), finding)


def codes(findings):
    return [f['rule_id'] for f in findings]


class NumberBudgetTest(unittest.TestCase):
    """v3.1：数词堆要能咬（作品 88 初稿的实打实退步）。"""

    def _codes(self, text):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / '旁白.md'
            body.write_text(text, encoding='utf-8')
            out = subprocess.run(['python3', str(ROOT / 'scripts' / 'fuben_craft.py'), str(body)],
                                 capture_output=True, text=True, check=True).stdout
            return {m.group(2) for m in re.finditer(r'(NOTE|REVIEW|BLOCK)\s+(\S+)', out)}

    def test_number_stuffing_trips(self):
        line = '你今年练了三百次，吃了三百块，涨了三十斤，还剩九节课，值六百五十块，一天五块钱，一个月两千块。\n'
        self.assertIn('NUMBER_STUFFING', self._codes(line * 14))

    def test_plain_prose_quiet(self):
        """正常口语叙述（虚指「一个/一样」连篇）不该被打红——口径只数记账单位。"""
        text = ('你练了三年，一斤没瘦。这话你只在一个场合说：每年体检前那几天。\n'
                '今天你要体验的人生副本是：一个把健身卡用成偷吃许可证的人。\n'
                '你从器械区走出来，腿是软的，心跳还没落回去，脑子里那句话又准时到了。\n'
                '它比"要坚持"勤快得多，来得像闹钟，一样从不迟到。\n'
                '这五个字你从不当它是安慰，你拿它当凭证，面值就是屏上那个数。\n'
                '你推门进去，手机还停在刚拍的那张图上，屏幕亮着，像一张没撕的票根。\n')
        codes = self._codes(text)
        self.assertNotIn('NUMBER_STUFFING', codes)
        self.assertNotIn('NUMBER_REPEAT', codes)

    def test_repeated_number_flagged(self):
        text = ('屏上三百，手里三百，兜里三百，心里还是三百。\n') * 12
        self.assertIn('NUMBER_REPEAT', self._codes(text))

    def test_screenplay_visual_lines_do_not_count(self):
        """数字全写在画面单据上＝不占可念轨预算（v3.1 的推荐写法）。"""
        vo = ['你练了挺久，秤一直没动，这话你只在体检前那几天说。',
              '今天你要体验的人生副本是：一个把健身卡用成偷吃许可证的人。',
              '前台把收据推回来，食指压着最下面那行小字，没抬头。',
              '你把单子推回去，没签，转身出门，风把玻璃门撞得很响。',
              '你合上本子去煮面，打了个蛋，这回你没算它。',
              '第二天早上屏上的数你扫了一眼就走，没拍照，也没觉得亏。']
        parts = []
        for i, line in enumerate(vo, 1):
            parts += [f'## 场{i}（地点 · 夜 · 40—50 秒）', '',
                      '画面：收据特写：2599 元／三十六节／已上二十七节／扣两成八／剩九节／有效期到 2025 年 3 月 14 日。',
                      f'旁白：{line}', '']
        codes = self._codes('\n'.join(parts))
        self.assertNotIn('NUMBER_STUFFING', codes)
        self.assertNotIn('NUMBER_REPEAT', codes)


class SpokenHeadTest(unittest.TestCase):
    """v3.0 开头铁律量的是"要念的那条轨"，不是文件行号。"""

    def test_screenplay_head_ignores_layout_lines(self):
        text = ("# 标题\n\n> 说明行\n\n## 场1（A · 日 · 30 秒）\n\n"
                "画面：一件道具\n旁白：你今年三十岁，第一次被退货。\n"
                "旁白：今天你要体验的人生副本是：一个被退货的人。\n")
        from fuben_craft import opening_findings, spoken_head
        head = [l for l in spoken_head(text).splitlines() if l.strip()]
        self.assertEqual(head[0], '你今年三十岁，第一次被退货。')
        self.assertEqual(head[1], '今天你要体验的人生副本是：一个被退货的人。')
        cfg = json.loads((ROOT / 'scripts' / 'fuben_policy.json').read_text(encoding='utf-8'))['craft']
        op = opening_findings(text, cfg)
        self.assertTrue(op['sig'])          # 签名句在场1 第 2 句＝规则要求的第 2–3 行
        self.assertEqual(op['sig_line'], 2)

    def test_transcript_body_not_rewritten(self):
        from fuben_craft import spoken_head
        text = '首行钩子在这里。\n第二行走剧情。\n'
        self.assertEqual(spoken_head(text), text.strip())


class SmokeAndBanTests(unittest.TestCase):
    BODY = '今天你要体验的人生副本是测试\n'

    def test_smoke_is_block_for_own_works(self):
        text = self.BODY + '他点了一支烟，你递过去打火机。\n'
        self.assertIn('NO_SMOKE', codes(craft(text)))

    def test_smoke_exempt_for_reference_profile(self):
        text = self.BODY + '舌尖上像有人摁灭了一个烟头。\n'
        self.assertEqual([], [c for c in codes(craft(text, 'reference')) if c == 'NO_SMOKE'])

    def test_banword_candidate(self):
        text = self.BODY + '然而，你还是去了。\n'
        hits = [f for f in craft(text) if f['rule_id'] == 'BANWORD']
        self.assertEqual(1, len(hits))
        self.assertEqual('REVIEW', hits[0]['severity'])


class OpeningRuleTests(unittest.TestCase):
    def test_definition_upfront_flagged(self):
        text = ('今天你要体验的人生副本是测试\n\n系统提示\n本副本开启双倍解释模块\n'
                '你看到的穷一律按富理解\n\n先校准\nA 是资产，数字是位数\n' + (' filler\n' * 60))
        self.assertIn('DEFINITION_UPFRONT', codes(craft(text)))

    def test_short_joke_system_prompt_passes(self):
        text = ('今天你要体验的人生副本是测试\n\n系统提示\n本副本的穷\n均为隐藏款\n\n'
                '大一报到\n他最后一个到\n行李是一只纸箱子，他一个人扛上去的。\n' + ('垫了半沓纸。' + '账记在小本本上。\n' * 120))
        rs = craft(text)
        self.assertNotIn('SYS_PROMPT_OVER', codes(rs))
        self.assertNotIn('DEFINITION_UPFRONT', codes(rs))

    def test_system_prompt_over_limit(self):
        text = ('今天你要体验的人生副本是测试\n\n系统提示\n第一条\n第二条\n第三条\n\n'
                '你走过去。\n')
        self.assertIn('SYS_PROMPT_OVER', codes(craft(text)))

    def test_missing_signature_is_note_only(self):
        text = '随便起个头\n他拎着箱子走。\n'
        rs = {f['rule_id']: f['severity'] for f in craft(text)}
        self.assertEqual('NOTE', rs.get('SIGNATURE_ABSENT'))

    def test_signature_on_first_line_flagged_v2(self):
        # v2.0：第 1 行必须是钩，签名句占用首行会被点名（NOTE，非阻断）
        text = '今天你要体验的人生副本是测试\n\n系统提示\n本副本的穷\n均为隐藏款\n\n你走过去。\n'
        rs = {f['rule_id']: f['severity'] for f in craft(text)}
        self.assertEqual('NOTE', rs.get('SIGNATURE_FIRST_LINE'))

    def test_signature_late_flagged_v2(self):
        text = ('你先看见那道栏杆\n栏杆上挂着一把锁\n谁也没钥匙\n那是头一天的事\n'
                '今天你要体验的人生副本是测试\n\n你走过去。\n')
        self.assertIn('SIGNATURE_TOO_LATE', codes(craft(text)))

    def test_signature_second_line_passes_v2(self):
        text = ('村里人问了他三年的一句话\n今天你要体验的人生副本是测试\n'
                '他一个字也没答\n' + ('风从门口过去。\n' * 60))
        rs = codes(craft(text))
        self.assertNotIn('SIGNATURE_FIRST_LINE', rs)
        self.assertNotIn('SIGNATURE_TOO_LATE', rs)
        self.assertNotIn('SIGNATURE_ABSENT', rs)


class LedgerTests(unittest.TestCase):
    def test_scale_claim_mismatch_flagged(self):
        rows = ledger_rows('老头给你发工资\n一天一百二\n四十七天\n五千六百四\n你拿三千\n把账还了\n存成你的第一笔 A5\n')
        self.assertEqual(['mismatch'], [r['status'] for r in rows])

    def test_consistent_scale_not_flagged(self):
        rows = ledger_rows('第一笔分红到账\n你算了算身家\n三万块出头\nA5.3\n')
        self.assertEqual(['consistent'], [r['status'] for r in rows])
        self.assertNotIn('LEDGER_SCALE_MISMATCH', codes(craft('第一笔分红到账\n你算了算身家\n三万块出头\nA5.3\n')))

    def test_claim_without_amount_is_absent_not_verdict(self):
        rows = ledger_rows('他跟你摊牌\nA8，八位数\n千万级\n小数点后是首位数字\n三千万打头\n')
        self.assertTrue(all(r['status'] in ('consistent', 'absent') for r in rows))

    def test_small_sample_is_note_not_silence(self):
        # v3.0：短文不再"归零隐形"，而是明确报 NOTE；整稿（>=200 汉字）必须真判比例
        cues, quoted, pct = dialogue_stats('你讲，不对\n他说，回去\n')
        self.assertGreater(cues, 0)
        rs = {f['rule_id']: f['severity'] for f in craft('你讲，不对\n他说，回去\n')}
        self.assertEqual('NOTE', rs.get('DIALOGUE_STATS'))

    def test_dialogue_ratio_judged_on_600_char_draft(self):
        # 87 的教训：617 字的稿子必须被对白占比门禁看到（旧版 <800 字整段豁免）
        text = '今天你要体验的人生副本是测试\n' + '你讲，第一句钉子。\n他说，第二句钉子。\n' * 60
        self.assertIn('DIALOGUE_OVER_BUDGET', codes(craft(text)))


class DialogueBudgetTests(unittest.TestCase):
    def _many_nails(self, n):
        head = '今天你要体验的人生副本是测试\n' * 1 + '垫桌角。' * 0
        stanzas = [f'第{i}天\n他讲，{i}号钉子句说完就收。\n' for i in range(1, n + 1)]
        body = head + '你数着日子过，每段都有现场和账。\n' * 80
        return body + '\n'.join(stanzas)

    def test_over_budget_reviewed_not_silent(self):
        text = self._many_nails(14)
        rs = craft(text)
        self.assertIn('DIALOGUE_OVER_BUDGET', codes(rs))

    def test_within_budget_stats_are_note(self):
        text = self._many_nails(3)
        rs = {f['rule_id']: f['severity'] for f in craft(text)}
        self.assertEqual('NOTE', rs.get('DIALOGUE_STATS'))


class ScreenplayGateTests(unittest.TestCase):
    """v3.0 剧本口径门禁：可拍性、旁白驱动占比、终稿体量下限。"""

    def scene(self, n=6, visual=True, vo_each=40, dl_each=0):
        head = '你把年卡用成了三个家电\n今天你要体验的人生副本是测试\n'
        blocks = []
        for i in range(1, n + 1):
            lines = [f'## 场{i}（城中村·夜）', f'时长：30—45 秒']
            if visual:
                lines.append('画面：' + '一台落灰的风扇对着你的后颈吹，塑料盆里有半盆水。' * max(1, vo_each // 30))
            lines.append('旁白：' + ('这一年你把一张卡用出了三样功能，洗的时候你也把日子重新搓了一遍。' * max(1, vo_each // 33)))
            for j in range(dl_each):
                lines.append(f'教练（抬头）：今天练什么，练完记得把毛巾挂回去。')
            blocks.append('\n'.join(lines))
        return head + '\n\n' + '\n\n'.join(blocks) + '\n'

    def test_scene_without_visual_line_is_flagged(self):
        rs = {f['rule_id'] for f in craft(self.scene(visual=False), 'full')}
        self.assertIn('SCENE_NO_VISUAL', rs)
        self.assertNotIn('SCENE_NO_VISUAL', {f['rule_id'] for f in craft(self.scene(visual=True), 'full')})

    def test_scene_count_out_of_band(self):
        self.assertIn('SCENE_SPARSE', {f['rule_id'] for f in craft(self.scene(3), 'full')})
        self.assertNotIn('SCENE_SPARSE', {f['rule_id'] for f in craft(self.scene(6), 'full')})

    def test_dialogue_heavy_screenplay_hits_narration_share(self):
        rs = {f['rule_id']: f['severity'] for f in craft(self.scene(6, dl_each=14), 'full')}
        self.assertEqual('REVIEW', rs.get('VO_TRACK_OVER'))

    def test_final_draft_below_floor_is_review(self):
        # 87 的塌陷：617 字的终稿在 v2.0 只拿到一条可自我闭环的 NOTE
        short = '你把年卡用成了三个家电\n今天你要体验的人生副本是测试\n' + '你在楼道里算了一遍。\n' * 30
        rs = {f['rule_id']: f['severity'] for f in craft(short, 'full')}
        self.assertEqual('REVIEW', rs.get('VOLUME_UNDER_FLOOR'))
        self.assertNotIn('VOLUME_UNDER_FLOOR', {f['rule_id'] for f in craft(short, 'draft')})


class EngineWiringTests(unittest.TestCase):
    def test_craft_runs_by_default_and_reference_exempts(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / '正文.md'
            body.write_text('今天你要体验的人生副本是测试\n他点了一支烟。\n', encoding='utf-8')
            rep = inspect_path(body, profile='full', run_style=False)
            self.assertIn('craft_gate_redline_and_budget_candidates', rep['checked'])
            self.assertTrue(any(f['rule_id'] == 'NO_SMOKE' and f['severity'] == 'BLOCK' for f in rep['findings']))
            self.assertEqual(1, rep['exit_code'])
            ref = inspect_path(body, profile='reference', run_style=False)
            self.assertFalse(any(f['rule_id'] == 'NO_SMOKE' for f in ref['findings']))

    def test_explicit_components_without_craft_stay_quiet(self):
        with tempfile.TemporaryDirectory() as td:
            body = Path(td) / '正文.md'
            body.write_text('今天你要体验的人生副本是测试\n他点了一支烟。\n', encoding='utf-8')
            rep = inspect_path(body, profile='full', run_style=False, components={'facts'})
            self.assertFalse(any(f['rule_id'] == 'NO_SMOKE' for f in rep['findings']))


if __name__ == '__main__':
    unittest.main()
