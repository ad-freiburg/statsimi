# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import numpy as np
from util.util import print_confusion_matrix
from util.util import print_classification_report
from util.util import pick_args
from sklearn.metrics import confusion_matrix


class Evaluator(object):
    '''
    TODO
    '''

    def __init__(
            self,
            model=None,
            X_test=None,
            y_test=None,
            test_idx=None,
            test_data=None):
        if X_test is None:
            raise RuntimeError("No test matrix given.")

        self.model = model
        self.X_test = X_test
        self.y_test = y_test
        self.test_idx = test_idx
        self.test_data = test_data

    def evaluate(self):
        args = {
            "X": self.X_test,
            "test_data": self.test_data,
            "test_data_idx": self.test_idx}
        y_pred = self.model.predict(**pick_args(self.model.predict, args))
        self.print_report(y_pred)

    def print_typical(self, res, compstr):
        if len(res) == 0:
            print("  (none)")
            return

        samples = np.random.choice(res, 20)
        for sample in samples:
            sample_lookup = sample
            if self.test_idx is not None:
                sample_lookup = self.test_idx[sample]
            pair = self.test_data.pairs[sample_lookup]
            st1 = self.test_data.stations[pair[0]]
            st2 = self.test_data.stations[pair[1]]
            print("  Predicted " + str(st1) + " " + compstr + " " + str(st2))

    def print_report(self, y_pred):
        print("\n == Typical FALSE negatives ==\n")
        t = np.where(np.logical_and(self.y_test != y_pred, y_pred == 0))
        self.print_typical(t[0], "!=")

        print("\n == Typical FALSE positives ==\n")
        t = np.where(np.logical_and(self.y_test != y_pred, y_pred == 1))
        self.print_typical(t[0], "==")

        print("\n == Typical TRUE negatives ==\n")
        t = np.where(np.logical_and(self.y_test == y_pred, y_pred == 0))
        self.print_typical(t[0], "!=")

        print("\n == Typical TRUE positives ==\n")
        t = np.where(np.logical_and(self.y_test == y_pred, y_pred == 1))
        self.print_typical(t[0], "==")

        print("\n == Confusion matrix ==\n")
        print_confusion_matrix(self.y_test, y_pred)

        conf_matrix = confusion_matrix(self.y_test, y_pred)
        print_classification_report(conf_matrix, digits=5)
