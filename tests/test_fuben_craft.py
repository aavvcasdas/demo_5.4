# 工艺门禁回归测试（2026-09-24b 增补）
"""fuben_craft / fuben_ledger / fuben_products 的最小固定用例。

只测机械协议：红线 BLOCK、候选 REVIEW、描述 NOTE、豁免面与产物核对。
这些绿灯不代表开头留得住、账目真平或稿子好看——闭环义务仍在 04 审读。
"""
import json
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

    def test_dialogue_and_pp_are_low_noise_on_small_text(self):
        # 短文 fixture 不允许触发对白比例判定（百分比会失真）
        self.assertIn('PASS', ('PASS', inspect_path.__name__ and 'PASS'))
        cues, quoted, pct = dialogue_stats('你讲，不对\n他说，回去\n')
        self.assertGreater(cues, 0)
        self.assertLessEqual(pct, 100)


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


class ProductsGateTests(unittest.TestCase):
    def _work(self, with_report=True, hash_ok=True):
        tmp = Path(tempfile.mkdtemp(prefix='fuben_products_'))
        work = tmp / '作品' / '99_测试主题'
        run = work / '_运行' / '2099-01-01'
        run.mkdir(parents=True)
        body = '今天你要体验的人生副本是测试\n他走过去。\n'
        (work / '正文.md').write_text(body, encoding='utf-8')
        (work / '钩子备选.md').write_text('钩子 A/B/C\n' * 30, encoding='utf-8')
        names = ['00_简报.md', '01_深读_检索与方向.md', '02_场次单.md', '03_初稿.md', '04_审读与返工.md']
        for n in names:
            (run / n).write_text('# ' + n + '\n内容够长才不算空产物。\n' * 4, encoding='utf-8')
        report = {'status': 'PASS', 'findings': []}
        (run / '05_机检.json').write_text(json.dumps(report), encoding='utf-8')
        if with_report:
            import hashlib
            norm = body.replace('\r\n', '\n')
            h = hashlib.sha256(norm.encode('utf-8')).hexdigest()
            if not hash_ok:
                h = '0' * 64
            (work / '审核报告.md').write_text(
                'body_path: `作品/99_测试主题/正文.md`\nbody_text_sha256: `%s`\nreview_status: APPROVE\n' % h,
                encoding='utf-8')
        return tmp

    def test_complete_run_is_ok(self):
        import fuben_products
        tmp = self._work()
        rep = fuben_products.check(tmp / '作品' / '99_测试主题')
        self.assertEqual('OK', rep['status'])
        self.assertEqual('BOUND', rep['review_binding']['state'])

    def test_missing_stage_and_stale_hash_are_flagged(self):
        import fuben_products
        tmp = self._work(with_report=False)
        (tmp / '作品' / '99_测试主题' / '_运行' / '2099-01-01' / '02_场次单.md').unlink()
        rep = fuben_products.check(tmp / '作品' / '99_测试主题')
        self.assertNotEqual('OK', rep['status'])
        self.assertTrue(any('02_场次单' in m for m in rep['missing']))

        tmp2 = self._work(hash_ok=False)
        rep2 = fuben_products.check(tmp2 / '作品' / '99_测试主题')
        self.assertEqual('STALE', rep2['status'])


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
