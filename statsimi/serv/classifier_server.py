# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, HTTPServer
from urllib import parse
from statsimi.util import hav
import logging
import os
import json
from statsimi.feature.stat_ident import StatIdent

HOST_NAME = '0.0.0.0'


def makeHandler(fb, model, log, webdir, cfg):
    class ClassifierHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                if self.path.split("?")[0] == '/api':
                    pars = dict(parse.parse_qsl(parse.urlsplit(self.path).query))
                    self.handle_api_req(pars)
                else:
                    self.handle_file_req()
            except BrokenPipeError:
                pass
            except Exception as e:
                log.error(
                    "(%s) Bad request, error was %s",
                    self.address_string(),
                    repr(e))
                try:
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    content = "Bad request."
                    self.wfile.write(bytes(content, "utf8"))
                except BrokenPipeError:
                    pass

        def handle_file_req(self):
            if self.path == '/':
                with open(os.path.join(webdir, "index.html")) as f:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    content = f.read()
                    self.end_headers()
                    self.wfile.write(bytes(content, "utf8"))
            elif self.path == '/cfg.js':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/javascript')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(bytes(cfg, "utf8"))
            elif self.path == '/script.js':
                with open(os.path.join(webdir, "script.js")) as f:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/javascript')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    content = f.read()
                    self.end_headers()
                    self.wfile.write(bytes(content, "utf8"))


        def handle_api_req(self, pars):
            s1 = StatIdent(
                name=pars.get("name1", ""), lat=float(
                    pars["lat1"]), lon=float(
                    pars["lon1"]))
            s2 = StatIdent(
                name=pars.get("name2", ""), lat=float(
                    pars["lat2"]), lon=float(
                    pars["lon2"]))

            log.info(
                "(%s) Request st1=\"%s\"@%f,%f vs st2=\"%s\"@%f,%f",
                self.address_string(),
                s1.name,
                s1.lat,
                s1.lon,
                s2.name,
                s2.lat,
                s2.lon)

            json_features = {}

            # cutoff distance
            if 1000 * hav(s1.lon, s1.lat, s2.lon, s2.lat) >= fb.cutoff:
                log.info("Distance %d greater than the cutoff distance %s",
                         1000 * hav(s1.lon, s1.lat, s2.lon, s2.lat), fb.cutoff)
                res = [[1, 0]]
            else:
                feat = fb.get_feature_vec(s1, s2)

                if int(pars.get("featvec", 0)):
                    for feat_name in fb.features:
                        json_features[feat_name] = int(feat[0, fb.get_feat_idx(feat_name)])

                    for i in range(fb.num_pos_pairs):
                        json_features["x" + str(i)] = int(feat[0, len(fb.features) + i * 2])
                        json_features["y" + str(i)] = int(feat[0, len(fb.features) + i * 2 + 1])

                    for i, ngram in enumerate(fb.get_top_ngrams()):
                        a = feat[0, len(fb.features) + fb.num_pos_pairs * 2 + i]
                        if a != 0:
                            json_features[ngram] = int(a)

                res = model.predict_proba(feat)

            self.send_response(200)
            self.send_header('Content-type', 'application/javascript')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            content = "{\"res\": " + str(res[0][1]) + ", \"featvec\" :" + json.dumps(json_features) + "}"
            self.wfile.write(bytes(content, "utf8"))

        def log_message(self, format, *args):
            return
    return ClassifierHandler


class ClassifierServer(object):
    def __init__(self, port, feature_builder, model, cfgfile=None):
        self.webdir = os.path.join(os.path.dirname(__file__), 'web')
        if cfgfile == None:
            cfgfile = os.path.join(self.webdir, 'default.cfg')

        self.port = port
        self.fb = feature_builder
        self.model = model

        with open(cfgfile) as f:
            self.cfg = f.read()

        self.log = logging.getLogger('classserv')

    def run(self):
        hndl = makeHandler(self.fb, self.model, self.log, self.webdir, self.cfg)
        hndl.server_version = "statsimi"
        hndl.sys_version = ""
        httpd = HTTPServer((HOST_NAME, self.port), hndl)

        logging.info("Listening on http://%s:%d", HOST_NAME, self.port)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

        httpd.server_close()
