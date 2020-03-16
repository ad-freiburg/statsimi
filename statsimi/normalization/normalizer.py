# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import re
import logging


class Normalizer(object):
    '''
    Normalizes stations and station groups according to rules from
    a normalization file.
    '''

    def __init__(self, rulesfile=None):
        '''
        >>> n = Normalizer("testdata/test.rules")
        >>> len(n.chain)
        110
        '''

        self.log = logging.getLogger('normzer')
        self.chain = []

        self.log.info("Reading normalization rules from %s" % rulesfile)
        with open(rulesfile, 'r') as f:
            for line in f:
                line = line.strip()
                if len(line) < 1 or line[0] == '#':
                    # skip comments
                    continue
                entry = line.split(" -> ")
                entry[1] = entry[1].rstrip(";")
                entry[0] = entry[0].strip("'")
                entry[1] = entry[1].strip("'")
                self.chain.append((re.compile(entry[0]), entry[1]))

    def normalize(self, groups, stats):
        '''
        Normalize all names and all stations in groups and stats

        >>> from osm.osm_parser import OsmParser
        >>> p = OsmParser()
        >>> p.parse("testdata/test.osm")
        >>> n = Normalizer("testdata/test.rules")
        >>> n.normalize(p.groups, p.stations)
        >>> p.groups[0].names[0]
        ('schwabentorbruecke', 'name')
        '''
        for gid, g in enumerate(groups):
            for nid, n in enumerate(g.names):
                normed = self.normalize_string(n[0])
                if len(normed) == 0:
                    self.log.warn("Normalization for '%s' is empty!" % n[0])
                g.names[nid] = (normed, n[1])
        for sid, st in enumerate(stats):
            if st.name is not None:
                normed = self.normalize_string(st.name)
                if len(normed) == 0:
                    self.log.warn("Normalization for '%s' is empty!" % st.name)
                stats[sid].name = normed

    def normalize_string(self, a):
        '''
        >>> n = Normalizer("testdata/test.rules")
        >>> n.normalize_string("Freiburg,    Hbf")
        'freiburg hauptbahnhof'
        >>> n.normalize_string("Freiburg,    Hbf Gleis 5")
        'freiburg hauptbahnhof'
        >>> n.normalize_string("Freibürg; Teststr.+Testav.  ")
        'freibuerg test street and testavenue'
        >>> n.normalize_string("Freibürg; Test str.+Testav.  ")
        'freibuerg test street and testavenue'
        '''
        for rule in self.chain:
            a = rule[0].sub(rule[1], a.lower())
        return a
