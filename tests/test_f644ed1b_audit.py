import copy
import unittest
from scripts.f644ed1b_audit import audit, external_source


class SafetyAudit(unittest.TestCase):
    def setUp(self):
        self.snapshot = {'generated_at': '2026-10-26T00:00:00Z', 'matches': [{
            'id': 'test', 'availability': 'open', 'teams': [{'name': 'A'}, {'name': 'B'}],
            'source_url': 'https://play.hotspawn.com/lobby', 'pick_index': 0,
            'analysis': {'method': 'market', 'source_url': 'https://polymarket.com/event/test',
                         'observed_at': '2026-10-25T23:59:00Z', 'probabilities': [.6, .4],
                         'quotes': [{'bid': .59, 'ask': .61}]}}]}

    def test_valid(self):
        self.assertFalse(audit(self.snapshot)['errors'])

    def test_mutations_fail_closed(self):
        for change in ({'probabilities': [float('nan'), .4]},
                       {'probabilities': [True, 0]},
                       {'observed_at': '2026-10-26T00:01:00Z'},
                       {'observed_at': '2026-10-25T23:59:00'},
                       {'source_url': 'https://play.hotspawn.com/picks'},
                       {'quotes': [{'bid': .7, 'ask': .6}]}):
            with self.subTest(change=change):
                s = copy.deepcopy(self.snapshot)
                s['matches'][0]['analysis'].update(change)
                self.assertTrue(audit(s)['errors'])

    def test_sources(self):
        for url in ('https://user@polymarket.com', 'https://hotspawn.com',
                    'https://foo.hotspawn.com', 'http://hltv.org', None):
            self.assertFalse(external_source(url))
        self.assertTrue(external_source('https://www.hltv.org/matches'))

    def test_unresolved_contract(self):
        m = self.snapshot['matches'][0]
        m.update(analysis=None, pick_index=None, limitations=['No verified pair'],
                 research=[{'source_url': 'https://www.hltv.org/matches', 'status': 'unresolved'}])
        self.assertFalse(audit(self.snapshot)['errors'])
        m['pick_index'] = 0
        self.assertTrue(audit(self.snapshot)['errors'])


class ModelToMoneyUpgrade(unittest.TestCase):
    def setUp(self):
        from scripts import f644ed1b_audit
        self.verify = f644ed1b_audit
        self.match = {'teams': [{'name': 'A'}, {'name': 'B'}], 'starts_at': '2026-10-27T00:00:00Z',
                      'analysis': {'method': 'model'}}
        self.row = {'method': 'consensus', 'links': ['https://thunderpick.io/test']}
        self.candidate = dict(self.match, upgraded_from_featured_model=True, pick_index=0,
                              origination={'method': 'consensus', 'source_url': self.row['links'][0],
                                           'probabilities': [.6, .4],
                                           'quotes': [{'odds': [1.5, 2.25]}, {'odds': [1.5, 2.25]}]})

    def test_money_inputs_replay(self):
        result = self.verify._verified_upgrade(self.match, self.row, self.candidate)
        self.assertIsNotNone(result)
        self.assertEqual(result[1], 0)

    def test_mutated_inputs_do_not_bypass_featured_check(self):
        mutations = [lambda c: c['origination'].update(probabilities=[.7, .3]),
                     lambda c: c['origination'].update(quotes=[]),
                     lambda c: c.update(starts_at='2026-10-28T00:00:00Z'),
                     lambda c: c.update(pick_index=1),
                     lambda c: c['origination'].update(source_url='https://hotspawn.com/test')]
        for mutate in mutations:
            c = copy.deepcopy(self.candidate)
            mutate(c)
            self.assertIsNone(self.verify._verified_upgrade(self.match, self.row, c))
