# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

from .evaluate.param_evaluator import ParamEvaluator
from .osm.osm_fixer import OsmFixer
from .evaluate.evaluator import Evaluator
from .feature.feature_builder import FeatureBuilder
from .feature.model_builder import ModelBuilder
from .serv.classifier_server import ClassifierServer
import pickle
import argparse
import time
import logging
FORMAT = "[%(asctime)-15s] (%(name)-8s) %(levelname)-8s: %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)


class ArgFormat(argparse.ArgumentDefaultsHelpFormatter,
                argparse.RawDescriptionHelpFormatter):
    pass


def main():
    start = time.time()
    parser = argparse.ArgumentParser(
        prog="statsimi",
        formatter_class=ArgFormat,

        description="(C) 2019 University of Freiburg\nChair of "
        "Algorithms and Data Structures\nAuthors: Patrick Brosi "
        "<brosi@cs.uni-freiburg.de>\n\nframework for "
        "similarity classification "
        "of public transit station"
    )

    parser.add_argument('cmd', metavar='<cmd>', type=str, nargs=1,
            help='command, either: pairs, model, evaluate, fix or http')

    parser.add_argument(
        '--model', type=str, default=None,
        help='Model input file'
    )

    parser.add_argument(
        '--model_out', type=str, default="model.lib",
        help='Model output file'
    )

    parser.add_argument(
        '--pairs_train_out', type=str, default=None,
        help='Output training station pairs as TSV to this file'
    )

    parser.add_argument(
        '--pairs_test_out', type=str, default=None,
        help='Output testing station pairs as TSV to this file'
    )

    parser.add_argument(
        '--fix_out', type=str, default="fixer.res",
        help='Output path for OSM fixer result.'
    )

    parser.add_argument(
        '--train', type=str, nargs='+', default=[],
        help='Input training data, as OSM XML or pairs file.'
    )

    parser.add_argument(
        '--test', type=str, nargs='+',
        help='Input test data, as OSM XML or pairs file.'
    )

    parser.add_argument(
        '--method', type=str, default="rf",
        help='Prediction method'
    )

    parser.add_argument(
        '--voting', type=str, default="soft",
        help='Voting method, hard or soft'
    )

    parser.add_argument(
        '--norm_file', type=str, default="",
        help='File with normalization rules.'
    )

    parser.add_argument(
        '--clean_data', action='store_true', default=False,
        help='Apply some basic heuristics to clean the ground truth data.'
    )

    parser.add_argument(
        '--unique', action='store_true', default=False,
        help='Remove duplicates from OSM input data'
    )

    parser.add_argument(
        '--with_polygons', action='store_true', default=False,
        help='Also parse OSM ways for polyonal stations'
    )

    parser.add_argument(
        '--topk', type=int, default=200,
        help='Top q-grams to use as features in training'
    )

    parser.add_argument(
        '-p', type=float, default=0.2,
        help='train on <p> * 100 percent of dataset'
    )

    parser.add_argument(
        '-q', type=int, default=3,
        help='q parameter for q-grams'
    )

    parser.add_argument(
        '--cutoffdist', type=int, default=1000,
        help='Max distance in meters between stations from OSM input to be considered similar'
    )

    parser.add_argument(
        '--modelargs', type=str, default="",
        help='modelargs, semicolon separated, e.g. "\
                editdist_threshold=0.6;geodist_threshold=40'
    )

    parser.add_argument(
        '--modeltestargs', type=str, default="",
        help='modeltestargs'
    )

    parser.add_argument(
        '--fbtestargs', type=str, default="",
        help='fbtestargs'
    )

    parser.add_argument(
        '--eval-out', type=str, default=".",
        help='output directory for evaluation run'
    )

    parser.add_argument(
        '--spice', default=0, type=float,
        help='Spice stations for training with constructed "\
                fake-negatives with probability [0, 1].'
    )

    parser.add_argument(
        '--http_port', type=int, default=8282,
        help='Port the HTTP server will listen on'
    )

    args = parser.parse_args()

    test_data = None

    # feature matrices
    X_test = None
    X_train = None

    # if the datasets are subsetted, these are the original indices
    test_idx = None
    train_idx = None

    # classes, 1 = similar, 0 = not similar
    y_test = None
    y_train = None

    model = None
    ngram_model = None
    fbargs_model = None

    modelargs = {}
    modeltestargs = {}
    fbtestargs = {}

    if args.modelargs:
        modelargs = dict([a.split("=") for a in args.modelargs.split(";")])
    for k in modelargs:
        modelargs[k] = eval(modelargs[k])

    if args.modeltestargs:
        modeltestargs = dict([a.split("=")
                              for a in args.modeltestargs.split(";")])
    for k in modeltestargs:
        modeltestargs[k] = [eval(val) for val in modeltestargs[k].split(",")]

    if args.fbtestargs:
        fbtestargs = dict([a.split("=") for a in args.fbtestargs.split(";")])
    for k in fbtestargs:
        fbtestargs[k] = [eval(val) for val in fbtestargs[k].split(",")]

    if args.cmd[0] not in ["http", "evaluate", "fix", "evaluate-par", "model", "pairs"]:
        logging.error("Invalid mode '%s', use either 'http', 'evaluate', 'evaluate-par', 'pairs' or 'fix'." % args.cmd[0])
        exit(1)

    if args.cmd[0] == "pairs":
        logging.info(" === Pairs out mode ===\n")
        # special null method which doesn't build any features
        args.method = "null";
        args.topk = 0
        args.model_out = None

    mb = ModelBuilder(args.method, args.norm_file, args.voting, args.unique, args.with_polygons)

    if args.cmd[0] == "evaluate-par":
        logging.info(" === Parameter evaluation mode ===\n")

        pareval = ParamEvaluator(
            norm_file=args.norm_file,
            trainfiles=args.train,
            testfiles=args.test,
            method=args.method,
            p=args.p,
            modelargs=modelargs,
            fbargs={
                "spice": args.spice,
                "cutoffdist": args.cutoffdist,
                "topk": args.topk,
                "clean_data": args.clean_data
            },
            modeltestargs=modeltestargs,
            fbtestargs=fbtestargs,
            outputdir=args.eval_out,
            voting=args.voting,
            unique_names=args.unique,
            with_polygons=args.with_polygons)
        pareval.evaluate()

        exit(0)

    # TODO: pairs mode is just train mode with method null, topk=0 and model output discarded

    if args.model:
        logging.info("Reading trained model from " + args.model)
        with open(args.model, "rb") as f:
            tmp = pickle.load(f)
            model = tmp["model"]
            ngram_model = tmp["ngram"]
            fbargs_model = tmp["fbargs"]
    elif args.train:
        logging.info("Building model from %.1f%% of '%s'", args.p * 100, ", ".join(args.train))
        # this also builds test data from the part of the training data
        # that is not used for training - if explicit test data is given,
        # the test data is overwritten below
        model, ngram_model, fbargs, test_data, X_test, y_test, test_idx, train_data, X_train, y_train, train_idx = mb.build(
            trainfiles=args.train, p=args.p,
            modelargs=modelargs, fbargs={
                "spice": args.spice,
                "cutoffdist": args.cutoffdist,
                "topk": args.topk,
                "clean_data": args.clean_data
            })

        fbargs_model = fbargs

        # dump model
        if args.cmd[0] == "model":
            if len(args.model_out) > 0:
                with open(args.model_out, "wb") as f:
                    pickle.dump({"model": model, "ngram": ngram_model,
                                 "fbargs": fbargs_model}, f, protocol=4)
    else:
        logging.error("No model (--model) or training data (--train) given.")
        exit(1)

    if args.test:
        # if prediction dataset was explicitly given, use it
        logging.info("Test dataset(s) '%s' were given" % ", ".join(args.test))

        fbargs = fbargs_model
        fbargs["spice"] = args.spice
        fbargs["cutoffdist"] = args.cutoffdist
        fbargs["force_orphans"] = args.cmd[0] == "fix"
        fbargs["clean_data"] = args.clean_data
        fbargs["ngram_idx"] = ngram_model  # re-use the model ngrams
        fbargs["topk"] = len(ngram_model[2])  # re-use the top k

        test_data = mb.build_from_file(args.test, fbargs=fbargs)
        tm = test_data.get_matrix()
        y_test = tm[:, -1].toarray().ravel()
        X_test = tm[:, :-1]
        test_idx = None
    else:
        logging.info("Using remaining %.1f%% of '%s' as test dataset.", (1 - args.p) * 100, ", ".join(args.train))


    # write train pairs file
    if args.pairs_train_out is not None:
        logging.info("Writing train data to %s..." % args.pairs_train_out)
        mb.write_pairs(args.pairs_train_out, train_data, train_idx, y_train)

    # write test pairs file
    if args.pairs_test_out is not None:
        logging.info("Writing test data to %s..." % args.pairs_test_out)
        mb.write_pairs(args.pairs_test_out, test_data, test_idx, y_test)

    if args.cmd[0] == "evaluate":
        logging.info(" === Evaluation mode ===\n")

        evaluator = Evaluator(
            model=model,
            X_test=X_test,
            y_test=y_test,
            test_idx=test_idx,
            test_data=test_data)
        evaluator.evaluate()

    if args.cmd[0] == "fix":
        logging.info(" === Fix mode ===\n")

        osmfixer = OsmFixer(vars(args), test_data, test_idx)
        osmfixer.analyze(model)

        logging.info(" === Took %d seconds ===" % (time.time() - start))

        logging.info(" === Printing fix result to %s ===" % args.fix_out)
        osmfixer.print_to_file(args.fix_out)

    if args.cmd[0] == "http":
        logging.info(" === HTTP mode ===\n")

        fbargs = fbargs_model
        fbargs["spice"] = args.spice
        fbargs["cutoffdist"] = args.cutoffdist
        fbargs["force_orphans"] = False
        fbargs["clean_data"] = False
        fbargs["ngram_idx"] = ngram_model  # re-use the model ngrams
        fbargs["topk"] = len(ngram_model[2])  # re-use the top k

        fb = FeatureBuilder(bbox=None, **fbargs)
        fb.build_ngrams()

        serv = ClassifierServer(args.http_port, fb, model)
        serv.run()


if __name__ == '__main__':
    main()
