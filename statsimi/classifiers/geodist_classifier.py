# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import numpy as np


class GeoDistClassifier(object):
    '''
    TODO
    '''

    def __init__(self, geodist_threshold=20):
        '''
        Constructor
        '''

        self.t = geodist_threshold

    def fit(self, X, y, train_data, train_data_idx=None):
        '''
        We don't do any fitting here...
        '''
        pass

    def predict(self, X, test_data, test_data_idx=None):
        '''
        Predict based by a simple geographical distance threshold
        '''
        scores = self.predict_proba(X, test_data, test_data_idx)
        return scores.argmax(axis=1).A1

    def predict_proba(self, X, test_data, test_data_idx=None):
        '''
        Predict based on a simple geographical distance threshold
        '''
        idx = test_data.get_feat_idx("geodist")
        ret = np.column_stack(
            (X[:, idx].todense(), np.empty([X.shape[0], ], dtype=np.float)))

        # careful: meter distance is in units of 4 meters!
        ret[:, 1] = 0.5 - 0.5 * \
            np.tanh((ret[:, 0] * 4 - self.t) / (self.t / 4))
        ret[:, 0] = 1 - ret[:, 1]

        return ret
