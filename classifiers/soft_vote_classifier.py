# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import numpy as np


class SoftVoteClassifier(object):
    '''
    TODO
    '''

    def __init__(self, stations, pairs, classifiers=[]):
        '''
        Constructor
        '''

        self.stations = stations
        self.pairs = pairs

        self.idx = None

        self.classifiers = classifiers

    def fit(self, X, y, train_data, train_data_idx=None):
        for classifier in self.classifiers:
            classifier.fit(X, y, train_data=train_data,
                           train_data_idx=train_data_idx)

    def predict(self, X, test_data, test_data_idx=None):
        '''
        Predict based by a simple geographical distance threshold
        '''
        scores = self.predict_proba(
            X, test_data=test_data, test_data_idx=test_data_idx)
        return scores.argmax(axis=1)

    def predict_proba(self, X, test_data, test_data_idx=None):
        '''
        Predict based on a simple edit distance similarity threshold
        '''
        arr = []
        for classifier in self.classifiers:
            pred = classifier.predict_proba(
                X, test_data=test_data, test_data_idx=test_data_idx)
            arr.append(pred)

        ret = np.mean(np.array(arr), axis=0)

        return ret
