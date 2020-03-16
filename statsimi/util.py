# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import os
import itertools
import inspect
import re
import sys
import cutil
import numpy as np
from sklearn.metrics import confusion_matrix


def hav(lon1, lat1, lon2, lat2):
    '''
    Calculate the great-circle distance in km between two lat/lon pairs
    using the haversine formula.

    >>> import math
    >>> math.floor(hav(47.994775, 7.849889, 47.998165, 7.852861) * 1000)
    498
    >>> math.floor(hav(47.994775, 7.849889, 47.994775, 7.849889) * 1000)
    0
    '''
    return cutil.haversine(lat1, lon1, lat2, lon2)


def hav_approx(lon1, lat1, lon2, lat2):
    '''
    Calculate the great-circle distance in km between two lat/lon pairs
    using the haversine formula, but as an approximation which uses less
    trigonometric functions.

    >>> import math
    >>> math.floor(hav_approx(47.994775, 7.849889,
    ...     47.998165, 7.852861) * 1000)
    498
    >>> math.floor(hav_approx(47.994775, 7.849889,
    ...     47.994775, 7.849889) * 1000)
    0
    '''
    return cutil.haversine_approx(lat1, lon1, lat2, lon2)


def jaro_simi(s, t):
    '''
    Compute the Jaro similarity

    >>> '%.2f' % jaro_simi("Hallo", "Test")
    '0.00'
    >>> '%.2f' % jaro_simi("CRATE", "TRACE")
    '0.73'
    >>> '%.2f' % jaro_simi("MARTHA", "MARHTA")
    '0.94'
    >>> '%.2f' % jaro_simi("Freiburg Hauptbahnhof", "Freiburg")
    '0.79'
    >>> '%.2f' % jaro_simi("Hauptbahnhof", "Freiburg Hauptbahnhof")
    '0.77'
    '''
    return cutil.jaro(s, t)


def jaro_winkler_simi(s, t):
    '''
    Compute the Jaro-Winkler similarity

    >>> '%.2f' % jaro_winkler_simi("Hallo", "Test")
    '0.00'
    >>> '%.2f' % jaro_winkler_simi("CRATE", "TRACE")
    '0.73'
    >>> '%.2f' % jaro_winkler_simi("MARTHA", "MARHTA")
    '0.96'
    >>> '%.2f' % jaro_winkler_simi("Freiburg Hauptbahnhof", "Freiburg")
    '0.88'
    >>> '%.2f' % jaro_winkler_simi("Hauptbahnhof", "Freiburg Hauptbahnhof")
    '0.77'
    '''
    l = 0
    for i in range(0, min(len(s), len(t), 4)):
        if s[i] != t[i]:
            break
        l += 1
    j = cutil.jaro(s, t)

    # is usually set to 0.1
    p = 0.1
    return j + l * p * (1 - j)


def ed(s, t):
    '''
    Compute the edit distance / levenshtein distance

    >>> ed("Hallo", "Test")
    5
    >>> ed("Hallo", "Hallo")
    0
    >>> ed("Hallo", "Halloblablabla")
    9
    >>> ed("Hallo", "halloblablabla")
    10
    >>> ed("Hallo", "hAlloblablabla")
    11
    >>> ed("Hallo", "Hlloa")
    2
    >>> ed("Hallo", "Hllo")
    1
    >>> ed("Hallo", "alloH")
    2
    >>> ed("A", "Hallo")
    5
    >>> ed("A", "Aallo")
    4
    >>> ed("Ü", "U")
    1
    >>> ed("Ü", "Ö")
    1
    >>> ed("Ü", "")
    1
    >>> ed("Ü", "Ü")
    0
    >>> ed("", "")
    0
    '''
    return cutil.ed(s, t)


def sed(s, t):
    '''
    Compute suffix edit distance.

    >>> sed("Deutschlands", "Sozialdemokratische Einheitspartei Deutschlands")
    0
    >>> sed("Deutschlands", "Sozialdemokratische Deutschlands")
    0
    >>> sed("Deutschlands", "Deutschlands")
    0
    >>> sed("Deutschlands", "Deutschland")
    1
    >>> sed("Deutschlands Einheitspartei", "Deutschlands")
    15
    >>> sed("Blubb Deutschlands Einheitspartei", "Deutschlands")
    21
    >>> sed("Ü", "U")
    1
    >>> sed("Ü", "Ä")
    1
    >>> sed("Ü", "þ")
    1
    >>> sed("Ü", "Ü")
    0
    '''

    return cutil.sed(s, t)


def ped(s, t):
    '''
    Compute prefix edit distance.

    >>> ped("Hallo", "Test")
    5
    >>> ped("Hallo", "Hallo")
    0
    >>> ped("Hallo", "Halloblablabla")
    0
    >>> ped("Hallo", "halloblablabla")
    1
    >>> ped("Hallo", "hAlloblablabla")
    2
    >>> ped("Hallo", "Hlloa")
    1
    >>> ped("Hallo", "Hllo")
    1
    >>> ped("Hallo", "alloH")
    1
    >>> ped("A", "Hallo")
    1
    >>> ped("A", "Aallo")
    0
    >>> ped("Rebstock, Denzlingen", "Steinbühl, Denzlingen")
    8
    >>> ped("Steinbühl, Denzlingen", "Rebstock, Denzlingen")
    8
    '''

    return cutil.ped(s, t)


def jaccard_set(seta, setb):
    '''
    '''
    return len(seta & setb) / len(seta | setb)


def jaccard(a, b):
    '''
    TODO: baseline implementation, replace with better performace

    >>> jaccard("Hallo", "Test")
    0.0
    >>> jaccard("Test", "Test")
    1.0
    >>> jaccard("bla blubb blobb", "blubb blibb")
    0.25
    >>> jaccard("Weddigenstraße", "Reiterstraße, Freiburg im Breisgau")
    0.0
    >>> jaccard("Newton, High Str.", "Newton, Main Street")
    0.2
    >>> jaccard("newton high street", "newton main street")
    0.5
    '''

    seta = set(re.split(r"[^\w]+", a))
    setb = set(re.split(r"[^\w]+", b))
    seta = set(filter(lambda x: len(x) > 0, seta))
    setb = set(filter(lambda x: len(x) > 0, setb))
    return jaccard_set(seta, setb)


def bts_inner(seta, b, best):
    for l in range(1, len(seta) + 1):
        i = 0
        for subset in itertools.combinations(seta, l):
            tmp = len(" ".join(subset))

            # ed between the two string will always be at least their length
            # difference - if this is already too big, skip it right now
            dt = 1 - abs(tmp - len(b)) / max(tmp, len(b))
            if dt <= best:
                continue

            i += 1

            for perm in itertools.permutations(subset):
                combination = " ".join(perm)

                d = 1 - (cutil.ed(combination, b) /
                         max(len(combination), len(b)))
                if d == 1:
                    return 1.0

                if d > best:
                    best = d
    return best


def bts_simi(a, b):
    '''
    TODO: baseline implementation, replace with better performace

    >>> bts_simi("", "")
    1.0
    >>> bts_simi("Hallo", "Test")
    0.0
    >>> bts_simi("Test", "Test")
    1.0
    >>> bts_simi("Milner Road / Wandlee Road", "Wandlee Road")
    1.0
    >>> bts_simi("bla blubb blob", "blubb blib")
    0.9
    >>> '%.2f' % bts_simi("St Pancras International", "London St Pancras")
    '0.59'
    >>> bts_simi("Reiterstraße", "Reiterstraße Freiburg im Breisgau")
    1.0
    >>> bts_simi("Reiterstraße", "Reiter Freiburg im Breisgau")
    0.5
    >>> bts_simi("AA", "Reiterstraße, Freiburg im Breisgau")
    0.0
    >>> bts_simi("blibb blabbel bla blubb blob", "blubb blib blabb")
    0.875
    >>> bts_simi("blibb blabbel bla blubb blobo", "blubb blib blabb blabo")
    0.84
    >>> bts_simi("blubb blib blabb", "blibb blabbel bla blubb blob")
    0.875
    >>> bts_simi("blubbb blib blabb blobo", "blibb blabbel bla blubb blobo")
    0.84
    >>> '%.2f' % bts_simi("Reiter Freiburg im Breisgau",
    ... "Rei ter Frei burg im Brei sgau blabbbbbb")
    '0.90'
    >>> '%.2f' % bts_simi("Reiter Freiburg im Breisgau",
    ... "Rei ter Frei burg im Brei sgau blab b b b bb")
    '0.90'
    >>> '%.2f' % bts_simi("Rei ter Frei im burgo Brei sgau blabbbbbbb",
    ... "Rei ter Frei burg im Brei sgau blabbbbbb")
    '0.95'
    '''

    # shortcut
    if a == b:
        return 1.0

    seta = set(re.split(r"[\s]+", a))
    setb = set(re.split(r"[\s]+", b))

    if len(seta) == len(setb) == 1:
        return 1 - ed(a, b) / max(len(a), len(b))

    if len(seta) > len(setb):
        seta, setb = setb, seta
        a, b = b, a

    # this is already our best known value - simply the edit
    # distance similarity between the strings
    best = 1 - ed(a, b) / max(len(a), len(b))

    if best == 0.0:
        return 0.0

    best = bts_inner(seta, b, best)

    if best == 1:
        return 1.0

    best = bts_inner(setb, a, best)

    return best


def print_classification_report(*args, digits=5):
    # print classification report from confusion matrix,
    # with possibility to give multiple matrices for an avg report,
    # for example after multiple runs

    prec_0 = 0
    prec_1 = 0

    rec_0 = 0
    rec_1 = 0

    sup_0 = 0
    sup_1 = 0

    for confuse in args:
        tn = confuse[0][0]
        fn = confuse[1][0]
        tp = confuse[1][1]
        fp = confuse[0][1]

        prec_0 += tn / (tn + fn)
        rec_0 += tn / (tn + fp)

        prec_1 += tp / (tp + fp)
        rec_1 += tp / (tp + fn)

        sup_0 += tn + fp
        sup_1 += tp + fn

    prec_0 /= len(args)
    rec_0 /= len(args)
    prec_1 /= len(args)
    rec_1 /= len(args)
    sup_0 /= len(args)
    sup_1 /= len(args)

    f1_0 = 2 * (prec_0 * rec_0) / (prec_0 + rec_0)
    f1_1 = 2 * (prec_1 * rec_1) / (prec_1 + rec_1)

    mat = [[prec_0,
            rec_0,
            f1_0,
            sup_0],
           [prec_1,
            rec_1,
            f1_1,
            sup_1],
           [(prec_0 + prec_1) / 2,
            (rec_0 + rec_1) / 2,
            (f1_0 + f1_1) / 2,
            sup_0 + sup_1],
           [(prec_0 * sup_0 + prec_1 * sup_1) / (sup_0 + sup_1),
            (rec_0 * sup_0 + rec_1 * sup_1) / (sup_0 + sup_1),
            (f1_0 * sup_0 + f1_1 * sup_1) / (sup_0 + sup_1),
            sup_0 + sup_1]]

    colw = 10
    legend = "          "
    lbls_row = ["0", "1", "macro avg", "weigh. avg"]
    lbls_col = ["precision", "recall", "f1", "support"]

    if len(args) > 1:
        print("\n == Avg classification report from " +
              str(len(args)) + " runs ==\n")
    else:
        print("\n == Classification report ==\n")

    print("  " + legend, end=" ")
    for lbl in lbls_col:
        print("%{0}s".format(colw) % lbl, end=" ")

    print("\n")

    for i, lbl in enumerate(lbls_row):
        if i == 2:
            print("\n" + legend + "      " + "-" * colw * len(lbls_row))
        print("  %{0}s".format(colw) % lbl, end=" ")
        for j in range(len(lbls_col)):
            if j == len(lbls_col) - 1:
                cell = "%{0}.1f".format(colw) % mat[i][j]
            else:
                cell = "%{0}.{1}f".format(colw, digits) % mat[i][j]
            print(cell, end=" ")
        print()
    print()


def print_confusion_matrix(y_test, y_pred):
    # Based on https://gist.github.com/zachguo/10296432
    mat = confusion_matrix(y_test, y_pred)
    colw = 10
    legend = r"     gt\pr"
    lbls = ["0", "1"]

    print("  " + legend, end=" ")
    for lbl in lbls:
        print("%{0}s".format(colw) % lbl, end=" ")

    print("\n")

    for i, lbl in enumerate(lbls):
        print("  %{0}s".format(colw) % lbl, end=" ")
        for j in range(len(lbls)):
            cell = "%{0}.0f".format(colw) % mat[i, j]
            print(cell, end=" ")
        print()


def pick_args(func, args):
    '''
    Pick args fitting a function from a list of args,
    together with their default values.
    '''

    a = inspect.getargspec(func)
    if a.defaults is not None:
        wdef = list(zip(a.args[-len(a.defaults):], a.defaults))
        wodef = [(k, None) for k in a.args[:-len(a.defaults)]]
        argsdef = wdef + wodef
    else:
        argsdef = [(k, None) for k in a.args]
    fitargs = {k: v for k, v in argsdef}
    del fitargs["self"]
    fitargs.update((k, args[k]) for k in fitargs.keys() & args.keys())
    return fitargs


class FileList(object):
    '''
    Implementation of a list stored in a file, used as a backing
    for the training matrix.
    '''

    def __init__(self, w, fname):
        #  print("Opening " + fname)
        self.file = open(fname, "wb", buffering=1024 * 1000 * 100)
        # write something as we cannot map empty file
        self.fname = fname
        self.size = 0
        self.w = -(-w // 8)
        self.file.write((0).to_bytes(self.w, byteorder=sys.byteorder))
        self.file.seek(0)

    def __del__(self):
        self.file.close()
        os.remove(self.fname)

    def __len__(self):
        return self.size

    def append(self, i):
        self.file.write((i).to_bytes(self.w, byteorder=sys.byteorder))
        self.size = self.size + 1

    def get_mmap(self):
        self.file.flush()
        code = (sys.byteorder == 'little') and '<' or '>'
        return np.memmap(self.fname, dtype=code + "i" +
                         str(self.w), mode='r', shape=(self.size))
