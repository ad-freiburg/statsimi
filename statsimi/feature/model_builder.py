# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import logging
import numpy as np
import math

from statsimi.osm.osm_parser import OsmParser
from statsimi.feature.feature_builder import FeatureBuilder

from statsimi.classifiers.geodist_classifier import GeoDistClassifier
from statsimi.classifiers.ed_classifier import EditDistClassifier
from statsimi.classifiers.ped_classifier import PrefixEditDistClassifier
from statsimi.classifiers.sed_classifier import SuffixEditDistClassifier
from statsimi.classifiers.bts_classifier import BTSClassifier
from statsimi.classifiers.jaro_classifier import JaroClassifier
from statsimi.classifiers.jarowinkler_classifier import JaroWinklerClassifier
from statsimi.classifiers.tfidf_classifier import TFIDFClassifier
from statsimi.classifiers.jaccard_classifier import JaccardClassifier
from statsimi.classifiers.soft_vote_classifier import SoftVoteClassifier
from statsimi.classifiers.hard_vote_classifier import HardVoteClassifier
from statsimi.feature.stat_ident import StatIdent

from statsimi.util import pick_args

from statsimi.normalization.normalizer import Normalizer

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

meth_feats = {
    "null": [],
    "rf": ["missing_ngram_count", "geodist"],
    "geodist": ["geodist"],
    "editdist": ["lev_simi"],
    "stringeq": ["lev_simi"],
    "ped": ["ped_simi_fw", "ped_simi_bw"],
    "sed": ["sed_simi_fw", "sed_simi_bw"],
    "jaccard": ["jaccard_simi"],
    "bts": ["bts_simi"],
    "jaro": ["jaro_simi"],
    "jaro_winkler": ["jaro_winkler_simi"]
}

EPSILON = 0.0001


class ModelBuilder(object):
    '''
    Build a model from parameters.
    '''

    def __init__(self, method="rf", norm_rule_file=None, voting='soft',
                 unique_names=False, with_polygons=False):
        '''
        Constructor.
        '''
        self.log = logging.getLogger('modelbld')
        self.method = method
        self.normzer = None
        self.voting = voting
        self.unique_names = unique_names
        self.with_polygons = with_polygons

        if norm_rule_file:
            self.normzer = Normalizer(norm_rule_file)

    def build(self, trainfiles=[], p=0.2, modelargs={}, fbargs={}):
        train_data = self.build_from_file(trainfiles, fbargs)
        return self.build_model(train_data, p, modelargs)

    def build_model(self, train_data=None, p=0.2, modelargs={}):
        test_data = train_data
        ngram_model = train_data.get_ngram_idx()
        fbargs = train_data.initargs

        methods = self.method.split(",")
        models = []

        for method in methods:
            method = method.strip()
            if method == "rf":
                args = {"n_estimators": 100, "random_state": 0,
                        "verbose": 1, "n_jobs": -1}
                modelargs.update(args)
                args = pick_args(RandomForestClassifier.__init__, modelargs)
                models.append(RandomForestClassifier(**args))
            elif method == "mlp":
                args = {
                    "hidden_layer_sizes": (1000, ),
                    "max_iter": 500,
                    "alpha": 0.0001,
                    "solver": 'sgd',
                    "verbose": 10,
                    "random_state": 21,
                    "tol": 0.000000001}
                models.append(MLPClassifier(**args))
            elif method == "log":
                models.append(LogisticRegression())
            elif method == "geodist":
                args = pick_args(GeoDistClassifier.__init__, modelargs)
                models.append(GeoDistClassifier(**args))
            elif method == "bts":
                args = pick_args(BTSClassifier.__init__, modelargs)
                models.append(BTSClassifier(**args))
            elif method == "jaro":
                args = pick_args(JaroClassifier.__init__, modelargs)
                models.append(JaroClassifier(**args))
            elif method == "jaro_winkler":
                args = pick_args(JaroWinklerClassifier.__init__, modelargs)
                models.append(JaroWinklerClassifier(**args))
            elif method == "tfidf":
                args = pick_args(TFIDFClassifier.__init__, modelargs)
                models.append(TFIDFClassifier(**args))
            elif method == "jaccard":
                args = pick_args(JaccardClassifier.__init__, modelargs)
                models.append(JaccardClassifier(**args))
            elif method == "editdist":
                args = pick_args(EditDistClassifier.__init__, modelargs)
                models.append(EditDistClassifier(**args))
            elif method == "ped":
                args = pick_args(PrefixEditDistClassifier.__init__, modelargs)
                models.append(PrefixEditDistClassifier(**args))
            elif method == "sed":
                args = pick_args(SuffixEditDistClassifier.__init__, modelargs)
                models.append(SuffixEditDistClassifier(**args))
            elif method == "stringeq":
                models.append(
                    EditDistClassifier(
                        editdist_threshold=1 -
                        EPSILON))
            elif method == "null":
                pass
            else:
                self.log.error("Unknown method " + method)
                exit(1)

        model = None

        if len(models) > 1:
            if self.voting == 'soft':
                model = SoftVoteClassifier(
                    train_data.stations, train_data.pairs, models)
            else:
                model = HardVoteClassifier(
                    train_data.stations, train_data.pairs, models)
        elif len(models) > 0:
            model = models[0]

        tm = train_data.get_matrix()
        y = tm[:, -1].toarray()
        y = y.ravel()
        X = tm[:, :-1]

        ind = np.arange(X.shape[0])
        X_test = None
        y_test = None
        test_idx = None
        train_idx = None

        if model is not None and X.shape[0] > 0:
            if p == 1:
                X_train = X
                y_train = y
            else:
                X_train, X_test, y_train, y_test, train_idx, test_idx = \
                    train_test_split(X, y, ind, train_size=p, random_state=0)

            self.log.info("Fitting using %d%% of train data..." % (p * 100))
            args = {
                "X": X_train,
                "y": y_train,
                "train_data": train_data,
                "train_data_idx": train_idx}
            model.fit(**pick_args(model.fit, args))

        return model, ngram_model, fbargs, test_data, X_test, y_test, test_idx

    def file_type(self, path):
        if path[-3:] == 'bz2':
            return "osm_bzip"
        with open(path, 'r', encoding='utf-8') as f:
            line = f.readline()
            if len(line.split("\t")) == 9:
                return "pfile"
        return "osm"

    def parse_pairs(self, path, stations, pairs, simi, bounds):
        stats = {}

        ll = [math.inf, math.inf]
        ur = [-math.inf, -math.inf]

        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                lparts = line.split("\t")

                sid1 = int(lparts[0])
                sname1 = lparts[1]
                lat1 = float(lparts[2])
                lon1 = float(lparts[3])

                sid2 = int(lparts[4])
                sname2 = lparts[5]
                lat2 = float(lparts[6])
                lon2 = float(lparts[7])

                if lat1 < ll[0]:
                    ll[0] = lat1
                if lon1 < ll[1]:
                    ll[1] = lon1
                if lat1 > ur[0]:
                    ur[0] = lat1
                if lon1 > ur[1]:
                    ur[1] = lon1

                if lat2 < ll[0]:
                    ll[0] = lat2
                if lon2 < ll[1]:
                    ll[1] = lon2
                if lat2 > ur[0]:
                    ur[0] = lat2
                if lon2 > ur[1]:
                    ur[1] = lon2

                match = lparts[8].strip() == '1'

                if sid1 not in stats:
                    stats[sid1] = (
                        len(stations), StatIdent(
                            lat1, lon1, sname1, gid=0))
                    stations.append(stats[sid1][1])

                if sid2 not in stats:
                    stats[sid2] = (
                        len(stations), StatIdent(
                            lat2, lon2, sname2, gid=0))
                    stations.append(stats[sid2][1])

                pairs.append((stats[sid1][0], stats[sid2][0]))
                simi.append(match)

        bounds[0] = ll
        bounds[1] = ur

    def build_from_file(self, files, fbargs={}):
        self.log.info("Reading '%s'..." % ", ".join(files))
        meths = self.method.split(",")
        fbargs['features'] = list(
            set(sum([meth_feats.get(m.strip(), []) for m in meths], [])))
        self.log.info("Building features...")

        # build dataset from OSM file
        osmp = OsmParser()
        t = ""

        groups = []
        stations = []
        pairs = []
        simi = []
        bounds = [0, 0]

        for filepath in files:
            if self.file_type(filepath) == "osm":
                if t == "pfile":
                    self.log.error("Cannot mix OSM and pairs input files")
                    exit(1)
                osmp.parse_xml(filepath, unique=self.unique_names, with_polygons=self.with_polygons)
                t = "osm"
            if self.file_type(filepath) == "osm_bzip":
                if t == "pfile":
                    self.log.error("Cannot mix OSM and pairs input files")
                    exit(1)
                osmp.parse_bz2(filepath, unique=self.unique_names, with_polygons=self.with_polygons)
                t = "osm"
            if self.file_type(filepath) == "pfile":
                if t == "osm":
                    self.log.error("Cannot mix OSM and pairs input files")
                    exit(1)
                self.parse_pairs(filepath, stations, pairs, simi, bounds)
                t = "pfile"

        if t == "osm":
            bounds = osmp.bounds

        f = FeatureBuilder(bbox=bounds, **fbargs)

        if t == "osm":
            groups = osmp.groups
            stations = osmp.stations
            bounds = osmp.bounds

            if self.normzer:
                self.log.info("Applying label normalization...")
                self.normzer.normalize(groups, stations)

            f.build_from_stat_grp(osmp.stations, osmp.groups)
        else:
            f.build_from_pairs(stations, pairs, simi)

        return f
