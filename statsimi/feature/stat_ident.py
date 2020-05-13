# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

from statsimi.util import centroid

class StatIdent(object):
    '''
    A station.
    '''

    def __init__(
            self,
            name,
            osmnid=0,
            lat=None,
            lon=None,
            poly=None,
            gid=None,
            srctype=None,
            name_attr=None,
            orig_nd_name="",
            spice_id=None):
        self.lat = lat
        self.lon = lon
        self.poly = poly
        self.name = name
        self.osmnid = osmnid
        self.gid = gid
        self.orig_nd_name = orig_nd_name
        self.spice_id = spice_id

        # 1 = attr
        # 2 = group
        self.srctype = srctype
        self.name_attr = name_attr

    def __str__(self):
        if self.lat != None:
            return "\"%s\" (nid=%d) @ (%f, %f)" % (
                self.name, self.osmnid, self.lat, self.lon)
        else:
            c = centroid(self.poly)
            return "\"%s\" (nid=%d) @ (polygon w center %f, %f)" % (
                self.name, self.osmnid, c[1], c[0])
