"""Session fbdc97d6: a research-model row is labelled by the rung that priced it."""
import unittest

from scripts.originate import model_label, network_limitation


class ModelLabelTests(unittest.TestCase):
    def test_network_rows_are_not_labelled_as_valve_ratings(self):
        # Four fixtures in the 2026-10-22T01:20Z snapshot were priced by the
        # bo3.gg network fit but carried the Valve-ratings label.
        self.assertEqual(model_label({'family': 'network', 'provider': 'Own network model (bo3.gg results graph)'}),
                         'Own network estimate (bo3.gg results graph)')
        self.assertEqual(model_label({'family': 'form'}), 'Own results-based estimate (bo3.gg series results)')
        self.assertEqual(model_label({}), 'Research model estimate (Valve official ratings)')
        self.assertEqual(model_label({'family': 'valve'}), 'Research model estimate (Valve official ratings)')

    def test_network_limitation_states_the_model_and_the_interval(self):
        text = network_limitation({'graph_matches': 4645, 'graph_anchors': 269, 'rating_sd_diff': 166.9,
                                   'interval': [0.3, 0.7], 'low_confidence': True})
        self.assertIn('Own uncalibrated network model', text)
        self.assertIn('4645 finished bo3.gg series', text)
        self.assertIn('0.300-0.700', text)
        self.assertIn('Low confidence', text)

    def test_the_label_matches_the_researched_method_copy_used_on_the_site(self):
        from scripts.build import researched_method
        match = {'origination': {'method': 'model',
                                 'label': model_label({'family': 'network'}),
                                 'source': 'Own network model (bo3.gg results graph)',
                                 'source_url': 'https://bo3.gg/matches'}}
        label, source, url = researched_method(match)
        self.assertIn('bo3.gg results network', label)
        self.assertEqual(url, 'https://bo3.gg/matches')


if __name__ == '__main__':
    unittest.main()
