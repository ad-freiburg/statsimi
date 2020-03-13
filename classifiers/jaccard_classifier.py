# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import numpy as np


class JaccardClassifier(object):
    '''
    TODO
    '''

    def __init__(self, jaccard_threshold=0.7):
        '''
        Constructor
        '''

        self.t = jaccard_threshold

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
        Predict based on a prefix edit distance similarity threshold.
        We use max(ped(a, b), ped(b, a)) as the similarity to ensure
        symmetry.
        '''
        idx = test_data.get_feat_idx("jaccard_simi")
        ret = np.column_stack(
            (X[:, idx].todense(), np.empty([X.shape[0], ], dtype=np.float)))

        a = ret[:, 0].A1

        # careful: edit distance is mapped from the [0,1] range to the [0, 255]
        # range
        gr = a > self.t * 255.0
        smeq = a <= self.t * 255.0
        a[gr] = 0.5 + (a[gr] / 255.0 - self.t) / (2.0 * (1.0 - self.t))
        a[smeq] = (a[smeq] / 255.0) / (2 * self.t)

        ret[:, 1] = a.reshape(a.shape[0], 1)
        ret[:, 0] = 1 - ret[:, 1]

        return ret
