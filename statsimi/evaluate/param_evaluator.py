# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import numpy as np
import os
import itertools as it
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import precision_recall_fscore_support
from sklearn.metrics import f1_score
from statsimi.feature.model_builder import ModelBuilder
from statsimi.util import print_classification_report
from matplotlib.ticker import (
    MultipleLocator,
    AutoMinorLocator)
from statsimi.util import pick_args
import logging


class ParamEvaluator(object):
    '''
    TODO
    '''

    def __init__(
            self,
            method=None,
            norm_file=None,
            p=0.2,
            modelargs={},
            fbargs={},
            fbtestargs={},
            modeltestargs={},
            trainfiles=[],
            testfiles=[],
            outputdir=".",
            voting="soft",
            unique_names=False,
            with_polygons=False,
            runs=5):
        self.p = p
        self.log = logging.getLogger('pareval')
        self.method = method
        self.norm_file = norm_file
        self.trainfiles = trainfiles
        self.testfiles = testfiles
        if not self.trainfiles:
            self.trainfiles = []
        if not self.testfiles:
            self.testfiles = []
        self.modelargs = modelargs
        self.fbargs = fbargs
        self.fbtestargs = fbtestargs
        self.modeltestargs = modeltestargs
        self.outputdir = outputdir
        self.vote = voting
        self.unique = unique_names
        self.with_polygons = with_polygons

        self.fbargs_test_prev = None
        self.run_testfile_prev = None
        self.test_data_prev = None

        # number of evaluation runs per test
        self.runs = runs

    def merge_pars(self, a, b):
        c = a.copy()
        c.update(b)
        return c

    def run(self, run, mb, train_data, run_testfile,
            modelargs, fbargs, precs, recs, f1s, p_neg, r_neg, f1_neg,
            p_pos, r_pos, f1_pos, conf_ms):
        self.log.info("======================================================")
        self.log.info(" Running #" + str(run + 1) + "/" + str(self.runs))
        self.log.info("    fbargs=" + repr(fbargs))
        self.log.info("    modelargs=" + repr(modelargs))
        self.log.info("")

        test_data = None
        y_test = None
        X_test = None
        test_idx = None

        if run_testfile:
            model, ngram_model, _, _, _, _, _, _, _, _, _ = mb.build_model(train_data, self.p, modelargs)
            # if testfile is given, build the test data from them
            if run_testfile:
                if run_testfile == self.run_testfile_prev and fbargs == self.fbargs_test_prev:
                    self.log.info("(Using previously parsed test data)")
                    fbargs_test = fbargs.copy()
                    fbargs_test["ngram_idx"] = ngram_model
                    test_data = self.test_data_prev
                else:
                    fbargs_test = fbargs.copy()
                    fbargs_test["ngram_idx"] = ngram_model
                    test_data = mb.build_from_file(run_testfile, fbargs_test)

                self.fbargs_test_prev = fbargs
                self.run_testfile_prev = run_testfile
                self.test_data_prev = test_data
                tm = test_data.get_matrix()
                y_test = tm[:, -1].toarray().ravel()
                X_test = tm[:, :-1]
        else:
            model, ngram_model, _, _, X_test, y_test, test_idx, train_data, X_train, y_train, train_idx = mb.build_model(train_data, self.p, modelargs)
            test_data = train_data

        args = {"X": X_test, "test_data": test_data, "test_data_idx": test_idx}

        y_pred = model.predict(**pick_args(model.predict, args))

        precs_tp, recs_tp, f1s_tp, _ = precision_recall_fscore_support(y_test, y_pred, average=None, labels=[0, 1])

        p_neg[run].append(precs_tp[0])
        r_neg[run].append(recs_tp[0])
        f1_neg[run].append(f1s_tp[0])

        p_pos[run].append(precs_tp[1])
        r_pos[run].append(recs_tp[1])
        f1_pos[run].append(f1s_tp[1])

        # macro averaged
        precs[run].append(np.average(precs_tp))
        recs[run].append(np.average(recs_tp))
        f1s[run].append(np.average(f1s_tp))

        conf_ms[run].append(confusion_matrix(y_test, y_pred, labels=[0, 1]))

        if run == self.runs - 1:
            # during last run, print the avg classification report
            curi = len(conf_ms[run]) - 1
            print_classification_report(*[c[curi] for c in conf_ms], digits=5)

    def evaluate(self):
        mb = ModelBuilder(self.method, self.norm_file, self.vote, self.unique, self.with_polygons)

        modelargs_base = self.modelargs
        fbargs_base = self.fbargs

        precs = [[] for i in range(self.runs)]
        recs = [[] for i in range(self.runs)]
        f1s = [[] for i in range(self.runs)]

        p_pos = [[] for i in range(self.runs)]
        r_pos = [[] for i in range(self.runs)]
        f1_pos = [[] for i in range(self.runs)]

        p_neg = [[] for i in range(self.runs)]
        r_neg = [[] for i in range(self.runs)]
        f1_neg = [[] for i in range(self.runs)]

        f1_neg = [[] for i in range(self.runs)]

        confusion_matrices = [[] for i in range(self.runs)]

        fbargs_col = []
        modelargs_col = []

        a = [[(p, v) for v in self.fbtestargs[p]]
             for p in self.fbtestargs.keys()]
        fbargs_prod = list(it.product(*a))
        b = [[(p, v) for v in self.modeltestargs[p]]
             for p in self.modeltestargs.keys()]
        modelargs_prod = list(it.product(*b))

        if len(self.testfiles) > 1 and self.runs != len(self.testfiles):
            self.log.error("%d runs for param evaluator requested, by %d test files were given. Either give the exact same number of test files as the requested number of runs, then run N will use testfiles[N]. Or give one test file, then each run will use the same test file." %
                          len(self.testfiles), self.runs)
            exit(1)

        if len(self.trainfiles) > 1  and self.runs != len(self.trainfiles):
            self.log.error("%d runs for param evaluator requested, by %d train files were given. Either give the exact same number of train files as the requested number of runs, then run N will use trainfiles[N]. Or give one train file, then each run will use the same train file." %
                          len(self.testfiles), self.runs)
            exit(1)


        for run in range(self.runs):
            if self.runs > 1:
                self.log.info("Run " + str(run + 1) + "/" + str(self.runs))

            run_testfile = []
            run_trainfile = []

            if len(self.trainfiles) > 1:
                run_trainfile = [self.trainfiles[run]]
            elif len(self.trainfiles) == 1:
                run_trainfile = self.trainfiles

            if len(self.testfiles) > 1:
                run_testfile = [self.testfiles[run]]
            elif len(self.testfiles) == 1:
                run_testfile = self.testfiles

            self.log.info("Running on trainfile %s, testfile %s", run_trainfile, run_testfile)

            for fbargs_cur in fbargs_prod:
                fbargs = self.merge_pars(fbargs_base, fbargs_cur)
                train_data = mb.build_from_file(run_trainfile, fbargs)

                for modelargs_cur in modelargs_prod:
                    modelargs = self.merge_pars(modelargs_base, modelargs_cur)

                    if run == 0:
                        fbargs_col.append(fbargs)
                        modelargs_col.append(modelargs)

                    self.run(run, mb, train_data,
                        run_testfile, modelargs, fbargs, precs, recs, f1s,
                        p_neg, r_neg, f1_neg, p_pos, r_pos, f1_pos,
                        confusion_matrices)

        # averaging values
        p_avg = np.average(np.array(precs), axis=0)
        r_avg = np.average(np.array(recs), axis=0)
        f1_avg = np.average(np.array(f1s), axis=0)

        p_pos_avg = np.average(np.array(p_pos), axis=0)
        r_pos_avg = np.average(np.array(r_pos), axis=0)
        f1_pos_avg = np.average(np.array(f1_pos), axis=0)

        p_neg_avg = np.average(np.array(p_neg), axis=0)
        r_neg_avg = np.average(np.array(r_neg), axis=0)
        f1_neg_avg = np.average(np.array(f1_neg), axis=0)

        # print results
        self.log.info(" == Done == ")
        self.log.info("  Best scores, avg'ed from %d runs:" % self.runs)
        self.log.info("   BEST F1 'SIMILAR' scores: "
                      "prec=%.2f rec=%.2f f1_pos_avg=%.2f" % (
                          p_pos_avg[np.argmax(f1_pos_avg)],
                          r_pos_avg[np.argmax(f1_pos_avg)],
                          max(f1_pos_avg)))
        self.log.info("   BEST F1 'SIMILAR' model args: %s" %
                      modelargs_col[np.argmax(f1_pos_avg)])
        self.log.info("   BEST F1 'SIMILAR' fb args: %s" %
                      fbargs_col[np.argmax(f1_pos_avg)])
        self.log.info("")
        self.log.info("   best f1 'not similar' scores: "
                      "prec=%.2f rec=%.2f f1=%.2f" % (
                          p_neg_avg[np.argmax(f1_neg_avg)],
                          r_neg_avg[np.argmax(f1_neg_avg)],
                          max(f1_neg_avg)))
        self.log.info("   best f1 'not similar' fb args: %s" %
                      fbargs_col[np.argmax(f1_neg_avg)])
        self.log.info("")
        self.log.info("   best f1 macro avg scores: "
                      "prec=%.2f rec=%.2f f1=%.2f" % (
                          p_avg[np.argmax(f1_avg)],
                          r_avg[np.argmax(f1_avg)],
                          max(f1_avg)))
        self.log.info("   best f1 macro avg model args: %s" %
                      modelargs_col[np.argmax(f1_avg)])
        self.log.info("   best f1 macro avg fb args: %s" %
                      fbargs_col[np.argmax(f1_avg)])

        x = None

        if len(self.fbtestargs) == 1 and len(self.modeltestargs) == 0:
            x = self.fbtestargs[list(self.fbtestargs.keys())[0]]

        if len(self.fbtestargs) == 0 and len(self.modeltestargs) == 1:
            x = self.modeltestargs[list(self.modeltestargs.keys())[0]]

        if x is not None:
            scale = 0.68
            fsize = (7 * scale, 2 * scale)
            fig, axes = plt.subplots(
                1, 1, figsize=fsize, sharex=True, sharey=False, squeeze=False)

            #  axes[0, 0].set_title('"Similar"', fontsize='medium')
            axes[0, 0].set_ylim(0, 1)
            axes[0, 0].yaxis.set_minor_locator(AutoMinorLocator())
            axes[0, 0].plot(x, p_pos_avg, "r.-", label="Precision",
                            clip_on=False, linewidth=1.0, markersize=3.5)
            axes[0, 0].plot(x, r_pos_avg, "b.-", label="Recall",
                            clip_on=False, linewidth=1.0, markersize=3.5)
            axes[0, 0].plot(x, f1_pos_avg, "g--", label="F1",
                            clip_on=False, linewidth=1.0, markersize=3.5)
            axes[0, 0].spines['right'].set_visible(False)
            axes[0, 0].spines['top'].set_visible(False)
            axes[0, 0].set_xlabel('threshold', fontsize='medium')

            plt.grid(
                b=True,
                which='major',
                color='#BBBBBB',
                linestyle='-',
                alpha=0.8)

            plt.minorticks_on()
            plt.grid(
                b=True,
                which='minor',
                color='#CCCCCC',
                linestyle='-',
                alpha=0.2)

            if max(x) <= 1:
                axes[0, 0].xaxis.set_major_locator(MultipleLocator(0.1))

            plt.legend(
                loc='best',
                fancybox=False,
                borderpad=0.2,
                handletextpad=0.3,
                labelspacing=0.1,
                fontsize="medium",
                frameon=False,
                borderaxespad=0)
            plt.tight_layout(pad=0.25)

            # pgf for inclusion in LaTeX
            plt.savefig(os.path.join(self.outputdir, 'result.pgf'),
                bbox_inches='tight',
                pad_inches=0)

            # PDF for inspection
            plt.savefig(os.path.join(self.outputdir, 'result.pdf'),
                bbox_inches='tight',
                pad_inches=0)

            plt.close()

        # results summary as single line
        print("%.2f\t%.2f\t%.2f\t%s\t%s" % (
                          p_pos_avg[np.argmax(f1_pos_avg)],
                          r_pos_avg[np.argmax(f1_pos_avg)],
                          max(f1_pos_avg),
                          modelargs_col[np.argmax(f1_pos_avg)],
                          fbargs_col[np.argmax(f1_pos_avg)]))

