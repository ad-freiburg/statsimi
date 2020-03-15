# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import multiprocessing as mp
from scipy.sparse import csr_matrix
from sklearn.preprocessing import Normalizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy
import logging
import re
import math


class TFIDFClassifier(object):
    '''
    TODO
    '''

    def __init__(self, tfidf_threshold=0.7):
        '''
        Constructor
        '''

        self.log = logging.getLogger('tfidf-cl')
        self.word_idx = {}
        self.words = []
        self.dfs = []

        self.train_num_stations = 0

        self.t = tfidf_threshold

    def fit(self, X, y, train_data, train_data_idx=None):
        '''
        With fitting, we mean the generation of the document frequencies here.
        This is done via the training data, because we naturally want to do
        similarity classification for pairs that have not occured in the
        trainining data, for example, free user input.
        '''

        train_station_ids = set()

        # take only the pairs present in the training data set
        for i in range(X.shape[0]):
            lookup = i
            if train_data_idx is not None:
                lookup = train_data_idx[i]

            stid1 = train_data.pairs[lookup][0]
            stid2 = train_data.pairs[lookup][1]

            train_station_ids.add(stid1)
            train_station_ids.add(stid2)

        self.log.info(
            "Fitting words and document freqs for tf.idf scores on %d "
            "stations from training data..." % len(train_station_ids))

        for sid in train_station_ids:
            station = train_data.stations[sid]
            self.train_num_stations += 1
            # no normalization here!
            for word in re.split(r"[^\w]+", station.name):
                word = word.strip()
                # Ignore the word if it is empty.
                if len(word) == 0:
                    continue

                if word not in self.word_idx:
                    self.dfs.append(0)
                    self.words.append(word)
                    self.word_idx[word] = len(self.words) - 1

                wid = self.word_idx[word]
                self.dfs[wid] += 1

        for id, df in enumerate(self.dfs):
            self.dfs[id] = df / len(train_data.stations)

    def predict(self, X, test_data, test_data_idx=None):
        '''
        '''
        scores = self.predict_proba(X, test_data, test_data_idx)

        return scores.argmax(axis=1)

    def predict_proba(self, X, test_data, test_data_idx=None):
        '''
        Predict based by a simple geographical distance threshold
        '''

        tfs = []

        # words that only occur in the test data
        test_word_idx = {}
        test_words = []

        test_station_ids = set()

        # take only the pairs present in the test data set
        for i in range(X.shape[0]):
            lookup = i
            if test_data_idx is not None:
                lookup = test_data_idx[i]

            stid1 = test_data.pairs[lookup][0]
            stid2 = test_data.pairs[lookup][1]

            test_station_ids.add(stid1)
            test_station_ids.add(stid2)

        test_station_ids = list(test_station_ids)

        for _, sid in enumerate(test_station_ids):
            station = test_data.stations[sid]

            tfs.append({})

            for word in re.split(r"[^\w]+", station.name):
                word = word.strip()

                if len(word) == 0:
                    continue

                if word not in self.word_idx:
                    if word not in test_word_idx:
                        test_words.append(word)
                        test_word_idx[word] = len(test_words) - 1

                    # test word ids begin at the end of the training word ids
                    wid = len(self.words) + test_word_idx[word]
                else:
                    wid = self.word_idx[word]

                if wid not in tfs[-1]:
                    tfs[-1][wid] = 0

                tfs[-1][wid] += 1

        # build tf.idf matrix
        data = []
        indices = []
        indptr = [0]

        # mapping maps station ids to rows in the td.idf matrix
        glob_mapping = {}

        for iid, sid in enumerate(test_station_ids):
            station = test_data.stations[sid]
            glob_mapping[sid] = iid
            for _, wid in enumerate(tfs[iid]):
                indices.append(wid)
                tf = tfs[iid][wid]

                if wid >= len(self.dfs):
                    # no document frequency, count as unique word
                    idf = math.log(self.train_num_stations)
                else:
                    idf = math.log(1 / self.dfs[wid])
                data.append(tf * idf)
            indptr.append(len(indices))

        matrix = csr_matrix(
            (data, indices, indptr), shape=(
                len(test_station_ids), len(
                    self.words) + len(test_words)), dtype=float)

        # L2 normalize
        norm = Normalizer(norm="l2", copy=False)
        norm.transform(matrix)

        ret = numpy.empty([X.shape[0], 2], dtype=numpy.float)

        # we build the similarity scores in chunks, because
        # otherwise the cosine similarity matrix would get way too big
        chunksize = 5000

        def proc_chunk(a, b, out):
            for minr in range(a, b, chunksize):
                maxr = min(b, minr + chunksize)

                locret = numpy.empty([maxr - minr, 2], dtype=numpy.float)

                chunkstationids = set()
                for i in range(minr, maxr):
                    lookup = i
                    if test_data_idx is not None:
                        lookup = test_data_idx[i]

                    stid1 = test_data.pairs[lookup][0]
                    stid2 = test_data.pairs[lookup][1]

                    chunkstationids.add(stid1)
                    chunkstationids.add(stid2)

                chunkstationids = list(chunkstationids)

                # build a view of our tfidf score matrix containing the
                # stations in this chunk
                chunk_map = {}
                mapping_l = []
                chunk_matrix = None

                for iid, sid in enumerate(chunkstationids):
                    chunk_map[sid] = iid
                    mapping_l.append(glob_mapping[sid])

                chunk_matrix = matrix[mapping_l, :]
                simi_mat = cosine_similarity(chunk_matrix)

                for i in range(minr, maxr):
                    lookup = i
                    if test_data_idx is not None:
                        lookup = test_data_idx[i]

                    simi = simi_mat[chunk_map[test_data.pairs[lookup][
                        0]], chunk_map[test_data.pairs[lookup][1]]]

                    if simi > self.t:
                        simi = 0.5 + (simi - self.t) / (2.0 * (1.0 - self.t))
                    else:
                        simi = simi / (2 * self.t)

                    locret[i - minr, 1] = simi
                    locret[i - minr, 0] = 1 - locret[i - minr, 1]
                out.append([locret, minr, maxr])

        manager = mp.Manager()
        rets = manager.list()
        procs = []

        processors = mp.cpu_count()
        csize = int(X.shape[0] / processors)

        for a in range(0, X.shape[0], csize):
            b = min(X.shape[0], a + csize)
            procs.append(mp.Process(target=proc_chunk, args=(a, b, rets)))

        for p in procs:
            p.start()

        for p in procs:
            p.join()

        for locret in rets:
            ret[locret[1]:locret[2], :] = locret[0]

        return ret
