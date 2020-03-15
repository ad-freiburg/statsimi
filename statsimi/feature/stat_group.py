# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''


class StatGroup(object):
    '''
    TODO
    '''

    def __init__(self, stations=[], osm_rel_id=None):
        '''
        '''

        self.names = []
        self.stats = stations.copy()
        self.osm_rel_id = osm_rel_id
        self.osm_meta_rel_id = None

    def add_name(self, name, attr):
        self.names.append((name, attr))

    def has_name(self, name):
        for i, p in enumerate(self.names):
            if p[0] == name:
                return True
        return False

    def add_station(self, sid):
        self.stats.append(sid)

    def remove_station(self, sid):
        self.stats.remove(sid)

    def set_meta_group(self, id):
        self.osm_meta_rel_id = id

    def __str__(self):
        if self.osm_rel_id:
            return "Group (rel_id=%d) with %d stations" % (
                self.osm_rel_id, len(self.stats))
        return "Group (rel_id=None) with %d stations" % (len(self.stats))
