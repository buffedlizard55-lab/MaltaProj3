"""Exact-five-player identity proofs. Synthetic test values never enter the site."""
import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from scripts import originate
from scripts.domain import iso, name_key, timestamp
from scripts.hltv_match import parse_match

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'data/research/6426358d/observed-0723'
NOW = timestamp('2026-10-16T07:24:10Z')
START = '2026-10-17T11:00:00Z'
URL = 'https://www.hltv.org/matches/12345/alpha-vs-beta'
VALVE = 'https://github.com/ValveSoftware/counter-strike_regional_standings'


def markup(a='Alpha', b='Beta', players=None):
    players = players or [['a1', 'a2', 'a3', 'a4', 'a5'], ['b1', 'b2', 'b3', 'b4', 'b5']]
    out = (f'<div class="team1-gradient"><div class="teamName">{a}</div></div>'
           f'<div class="team2-gradient"><div class="teamName">{b}</div></div>'
           f'<div class="timeAndEvent"><div class="date" data-unix="{int(timestamp(START).timestamp()*1000)}">localized date</div>'
           '<div class="countdown">1d</div></div>')
    for name, roster in zip([a, b], players):
        out += (f'<div class="lineup"><div class="box-headline"><a href="/team/1/{name}">{name}</a></div>'
                '<div class="players">' + ''.join(f'<div class="text-ellipsis">{p}</div>' for p in roster) + '</div></div>')
    return out


def match():
    return {'id': 'synthetic', 'teams': [{'name': 'Alpha'}, {'name': 'Beta'}], 'competition': 'Synthetic event', 'starts_at': START}


def rating(name, players, points, standing):
    return {'name': name, 'roster': players, 'points': points, 'standing': standing,
            'snapshot_date': '2026-10-05', 'source_url': VALVE}


def registry():
    return originate.load_registry(ROOT / 'data/origination/aliases.json')


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.write(markup())

    def write(self, text, *, observed=None):
        raw = {'url': URL, 'observed_at': observed or iso(NOW), 'html': text}
        (self.path / 'live-hltv-match-synthetic.json').write_text(json.dumps(raw))
        manifest = [{'id': 'live-hltv-match-synthetic', 'url': URL, 'observed_at': raw['observed_at'], 'status': 'ok',
                     'response_sha256': hashlib.sha256(text.encode()).hexdigest()}]
        (self.path / 'live-collection-manifest.json').write_text(json.dumps(manifest))

    def proof(self, m=None, now=NOW):
        return originate.hltv_lineup_proof(self.path, m or match(), registry(), now)

    def test_proof_is_bound_to_both_teams_start_observation_and_original_hash(self):
        proof = self.proof()
        self.assertEqual(proof['fixture_id'], 'synthetic')
        self.assertEqual(proof['rosters']['alpha'], ['a1', 'a2', 'a3', 'a4', 'a5'])
        self.assertEqual(proof['source_url'], URL)

    def test_changed_original_cannot_retain_a_valid_hash(self):
        p = self.path / 'live-hltv-match-synthetic.json'
        raw = json.loads(p.read_text()); raw['html'] += '<p>tampered</p>'; p.write_text(json.dumps(raw))
        self.assertIsNone(self.proof())

    def test_stale_or_future_observations_are_not_current_lineup_proof(self):
        self.assertIsNone(self.proof(now=NOW + timedelta(hours=9)))
        self.assertIsNone(self.proof(now=NOW - timedelta(hours=1)))

    def test_wrong_schedule_or_team_cannot_disambiguate(self):
        m = match(); m['starts_at'] = iso(timestamp(START) + timedelta(seconds=61))
        self.assertIsNone(self.proof(m))
        self.write(markup('Alpha Academy', 'Beta'))
        self.assertIsNone(self.proof())

    def test_four_or_six_or_duplicate_players_stay_unverified(self):
        for players in [['a1', 'a2', 'a3', 'a4'], ['a1', 'a2', 'a3', 'a4', 'a5', 'coach'], ['a1'] * 5]:
            self.write(markup(players=[players, ['b1', 'b2', 'b3', 'b4', 'b5']]))
            self.assertIsNone(self.proof())

    def test_missing_manifest_is_not_verification(self):
        (self.path / 'live-collection-manifest.json').unlink()
        self.assertIsNone(self.proof())

    def test_only_a_unique_exact_five_player_rating_can_be_selected(self):
        ratings = [rating('Alpha', ['old1', 'old2', 'old3', 'old4', 'old5'], 500, 200),
                   rating('Alpha', ['a5', 'A4', 'a3', 'a2', 'a1'], 1000, 100),
                   rating('Beta', ['b1', 'b2', 'b3', 'b4', 'b5'], 900, 120)]
        meta = {'source_url': VALVE, 'snapshot_date': '2026-10-05', 'evidence_file': 'synthetic.json'}
        no_proof, _ = originate.model_estimate(match(), ratings, registry(), meta, NOW)
        self.assertIsNone(no_proof)
        quote, _ = originate.model_estimate(match(), ratings, registry(), meta, NOW, lineup=self.proof())
        self.assertEqual(quote['inputs'][0]['standing'], 100)
        self.assertEqual(quote['lineup_disambiguation'][0]['source_url'], URL)
        self.assertGreater(quote['probabilities'][0], 0.5)
        partial = copy.deepcopy(ratings); partial[1]['roster'][0] = 'substitute'
        self.assertIsNone(originate.model_estimate(match(), partial, registry(), meta, NOW, lineup=self.proof())[0])
        ratings.append(copy.deepcopy(ratings[1]))
        self.assertIsNone(originate.model_estimate(match(), ratings, registry(), meta, NOW, lineup=self.proof())[0])


class OriginalSourceReplayTests(unittest.TestCase):
    def test_every_retained_original_has_its_recorded_source_hash(self):
        report = json.loads((RESEARCH / 'source-report.json').read_text())
        for page in report['pages']:
            if page.get('original_response'):
                raw = gzip.decompress((RESEARCH / page['original_response']).read_bytes())
                self.assertEqual(hashlib.sha256(raw).hexdigest(), page['request']['response_sha256'], page['label'])

    def test_all_eight_historical_scores_and_maps_replay_without_using_votes(self):
        old_edge = json.loads((ROOT / 'data/edge-review.json').read_text())
        old_day3 = json.loads((ROOT / 'data/day3-guide.json').read_text())
        expected = old_edge['day_one'] + old_day3['day_two_results']
        report = json.loads((RESEARCH / 'source-report.json').read_text())
        history = [p for p in report['pages'] if p['label'].startswith(('day1-', 'day2-'))]
        self.assertEqual(len(history), 8)
        for page in history:
            facts = parse_match(gzip.decompress((RESEARCH / page['original_response']).read_bytes()).decode())
            row = next(m for m in expected if m['url'] == page['request']['url'])
            self.assertEqual(facts['teams'], [row['team_a'], row['team_b']])
            self.assertEqual(facts['score'], [int(x) for x in row['score'].split('-')])
            self.assertEqual(facts['maps'], row['maps'])

    def test_upcoming_deciders_have_epoch_starts_and_no_inferred_result(self):
        for label, start in [('day3-aurora-9z', '2026-10-16T14:00:00Z'), ('day3-betboom-legacy', '2026-10-16T17:00:00Z')]:
            facts = parse_match(gzip.decompress((RESEARCH / (label + '.html.gz')).read_bytes()).decode())
            self.assertEqual(facts['starts_at'], start)
            self.assertEqual(facts['best_of'], 3)
            self.assertFalse(facts['finished']); self.assertIsNone(facts['score'])

    def test_two_new_resolutions_and_four_player_overlaps_are_not_equivalent(self):
        report = json.loads((RESEARCH / 'source-report.json').read_text())
        ratings, meta = originate.valve_rows(ROOT / 'data', None)
        for mid, resolves in [('1081513', True), ('1081532', True), ('1079170', False), ('1081527', False)]:
            page = next(p for p in report['pages'] if p['label'] == 'unresolved-' + mid)
            m = next(m for m in report['fixtures'] if m['id'] == mid)
            facts = parse_match(gzip.decompress((RESEARCH / page['original_response']).read_bytes()).decode())
            proof = {'fixture_id': mid, 'source_url': page['request']['url'], 'observed_at': page['request']['observed_at'],
                     'starts_at': facts['starts_at'], 'names': facts['teams'],
                     'rosters': {name_key(t['name']): t['roster'] for t in facts['lineups']}, 'evidence_file': 'research-only'}
            q, _ = originate.model_estimate(m, ratings, registry(), meta, timestamp(page['request']['observed_at']), lineup=proof)
            self.assertEqual(q is not None, resolves, mid)
