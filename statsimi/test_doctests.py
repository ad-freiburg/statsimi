import doctest
import statsimi.util
import statsimi.feature.feature_builder
import statsimi.osm.osm_parser


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(statsimi.util))
    tests.addTests(doctest.DocTestSuite(statsimi.feature.feature_builder))
    tests.addTests(doctest.DocTestSuite(statsimi.osm.osm_parser))
    return tests
