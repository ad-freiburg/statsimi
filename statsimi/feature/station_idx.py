# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import math


class StationIdx(object):
    '''
    TODO
    '''

    def __init__(self, cell_size, bbox):
        '''
        Constructor, initialization is done with WGS84 (lon/lat) coordinates
        '''

        ll_x = bbox[0][1]
        ll_y = bbox[0][0]
        ur_x = bbox[1][1]
        ur_y = bbox[1][0]

        self.cell_size = cell_size
        self.ll = self.lonlat_to_merc(ll_x, ll_y)
        self.ur = self.lonlat_to_merc(ur_x, ur_y)

        self.width = self.ur[0] - self.ll[0]
        self.height = self.ur[1] - self.ll[1]

        self.x_size = math.ceil(self.width / self.cell_size)
        self.y_size = math.ceil(self.height / self.cell_size)

        self.idx = [[set() for y in range(self.y_size + 1)]
                    for x in range(self.x_size + 1)]

    def get_cell(self, x, y):
        '''
        Retrieve cell coordinate from lon/lat pair
        '''

        dx = max(0, x - self.ll[0])
        dy = max(0, y - self.ll[1])
        return (
            math.floor(
                dx /
                self.cell_size),
            math.floor(
                dy /
                self.cell_size))

    def add_stat_group(self, id, lon, lat):
        '''
        Add station to lon/lat position
        '''

        xy = self.lonlat_to_merc(lon, lat)

        coords = self.get_cell(xy[0], xy[1])
        self.idx[coords[0]][coords[1]].add(id)

    def add_stat_group_poly(self, id, poly):
        '''
        Add station based on polyon [lon, lat]
        '''

        # TODO! we have to check whether the polygon boundary crosses the grid cell

        for lon, lat in poly:
            self.add_stat_group(id, lon, lat)

    def get_neighbors_poly(self, poly, d):
        '''
        Return neighbors at distance d (meters) from  the polygon.
        d is a lower bound: each station with distance d from the lon/lat pair
        is included, but additional stations with a distance > d may be
        included.
        '''

        # TODO! we have to check whether the polygon boundary crosses the grid cell

        ret = set()

        for lon, lat in poly:
            ret.update(self.get_neighbors(lon, lat, d))

        return ret

    def get_neighbors(self, lon, lat, d):
        '''
        Return neighbors at distance d (meters) from lon/lat pair.
        d is a lower bound: each station with distance d from the lon/lat pair
        is included, but additional stations with a distance > d may be
        included.
        '''

        xy = self.lonlat_to_merc(lon, lat)

        ll = self.get_cell(xy[0] - d, xy[1] - d)
        ur = self.get_cell(xy[0] + d, xy[1] + d)

        ret = set()

        for x in range(max(0, ll[0]), min(len(self.idx) - 1, ur[0]) + 1):
            for y in range(max(0, ll[1]), min(
                    len(self.idx[x]) - 1, ur[1]) + 1):
                ret.update(self.idx[x][y])

        return ret

    def lonlat_to_merc(self, lon, lat):
        a = math.sin(lat * 0.017453292519943295)
        return (6378137.0 * lon * 0.017453292519943295,
                3189068.5 * math.log((1.0 + a) / (1.0 - a)))

    def webmerc_scale(self, y):
        return math.cos(2 * math.atan(math.exp(y / 6378137)) - 1.5707965)
