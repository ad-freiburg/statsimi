# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import xml.etree.ElementTree as ET
import math
import os
from feature.stat_ident import StatIdent
from feature.stat_group import StatGroup
import logging

st_filter = [
    ("public_transport", "stop"),
    ("public_transport", "stop_position"),
    ("public_transport", "platform"),
    ("public_transport", "station"),
    ("public_transport", "halt"),
    ("highway", "bus_stop"),
    ("railway", "stop"),
    ("railway", "station"),
    ("railway", "halt"),
    ("railway", "tram_stop"),
    ("railway", "platform"),
    ("tram", "stop"),
    ("subway", "stop")
]

grp_rel_filter = [
    ("public_transport", "stop_area"),
]

meta_grp_rel_filter = [
    ("public_transport", "stop_area_group"),
]

# try to catch some common errors ans suspicious relations
# in OSM to try to keep the training data clean
grp_rel_ex_filter = [
    ("from", "*"),
    ("to", "*"),
    ("route_master", "bus"),
    ("route_master", "ferry"),
    ("route_master", "aerialway"),
    ("route_master", "monorail"),
    ("route_master", "subway"),
    ("route_master", "train"),
    ("route_master", "tram"),
    ("route_master", "trolleybus"),
    ("route", "bus"),
    ("route", "ferry"),
    ("route", "aerialway"),
    ("route", "monorail"),
    ("route", "subway"),
    ("route", "train"),
    ("route", "tram"),
    ("route", "trolleybus"),
    ("type", "route"),
    ("type", "route_master"),
    ("type", "superroute"),
    ("type", "restriction"),
    ("type", "boundary"),
    ("type", "site"),
    ("type", "associatedStreet"),
    ("type", "network"),
    ("type", "street"),
    ("type", "destination_sign"),
    ("type", "waterway"),
    ("type", "enforcement"),
    ("type", "bridge"),
    ("type", "tunnel"),
]

st_name_attrs = [
    "name",
    "uic_name",
    "alt_name",
    #    "int_name",
    "loc_name",
    "nat_name",
    "official_name",
    #    "old_name",
    "reg_name",
    "ref_name",
    "short_name",
    "sorting_name",
    "gtfs_name"
]


class OsmParser(object):
    '''
    Parses an OSM file into a list of groups (generated from relations)
    and nodes. After parsing, they are available as members of this
    class.
    '''

    def __init__(self):
        '''
        Constructor
        '''

        self.log = logging.getLogger('osmp')
        self.nd_group_idx = {}
        self.rel_meta_group_idx = {}
        self.groups = []
        self.stations = []

        self.ll = [math.inf, math.inf]
        self.ur = [-math.inf, -math.inf]

    @property
    def bounds(self):
        '''
        Return the parsed geographic bounds.
        '''
        return [self.ll, self.ur]

    def filter_match(self, attr, fil):
        return (attr["k"], attr["v"]) in fil or (attr["k"], "*") in fil

    def is_meta_grp(self, attr):
        return self.filter_match(attr, meta_grp_rel_filter)

    def is_st(self, attr):
        return self.filter_match(attr, st_filter)

    def is_grp(self, attr):
        return self.filter_match(attr, grp_rel_filter)

    def is_grp_exl(self, attr):
        return self.filter_match(attr, grp_rel_ex_filter)

    def parse(self, path, unique=False):
        '''
        Parse an OSM XML file.

        >>> p = OsmParser()
        >>> p.parse("testdata/test.osm")
        >>> sorted([str(grp) for grp in p.groups])
        ... # doctest: +NORMALIZE_WHITESPACE
        ['Group (rel_id=3271923) with 18 stations',\
        'Group (rel_id=None) with 1 stations']
        >>> sorted([stat.osmnid for stat in p.stations])
        ... # doctest: +NORMALIZE_WHITESPACE
        [25237964, 25237964, 25237964, 248609020, 248609020, 248609020, \
        248609028, 248609028, 248609028, 507039988, 507039988, 507039988, \
        2496897172, 2496897172, 2496897172, 2496897173, 2496897173, \
        2496897173, 4984926391]
        >>> p = OsmParser()
        >>> p.parse("testdata/test.osm", unique=True)
        >>> sorted([str(grp) for grp in p.groups])
        ... # doctest: +NORMALIZE_WHITESPACE
        ['Group (rel_id=3271923) with 12 stations',\
        'Group (rel_id=None) with 1 stations']
        >>> sorted([stat.osmnid for stat in p.stations])
        ... # doctest: +NORMALIZE_WHITESPACE
        [25237964, 25237964, 248609020, 248609020, 248609028, 248609028, \
        507039988, 507039988, 2496897172, 2496897172, 2496897173,\
        2496897173, 4984926391]
        '''

        # prevents calling root.clear() too often = False
        BUFFER = 1000

        f_size = os.path.getsize(path)
        nd_end = f_size
        perc_last = 0

        num_osm_stats = 0
        num_osm_stat_orphans = 0
        num_osm_groups = 0

        with open(path, 'r', buffering=1024 * 1000 * 1000) as f:
            context = ET.iterparse(f, events=("start", "end"))
            context = iter(context)
            event, root = next(context)

            i = 0
            lvl = 0

            self.log.info("First pass, parsing relations...")
            for event, c1 in context:
                if event == "start":
                    lvl = lvl + 1
                    continue

                lvl = lvl - 1

                i = i + 1

                perc = int((f.tell() / f_size) * 100)
                if perc - perc_last >= 10:
                    perc_last = perc
                    self.log.info("@ %d%% (%d/%d)" % (perc, f.tell(), f_size))
                if nd_end == f_size and lvl == 1 and c1.tag != "node" \
                        and c1.tag != "bounds":
                    nd_end = f.tell()

                if c1.tag != "relation":
                    if i % BUFFER == 0:
                        root.clear()
                    continue

                is_st_area = 2  # 2 == undecided
                is_meta_st_area = 2  # 2 == undecided
                curGroup = StatGroup(osm_rel_id=int(c1.attrib["id"]))

                for c2 in c1:
                    if c2.tag != "tag":
                        continue
                    if is_st_area == 2 and self.is_grp(c2.attrib):
                        is_st_area = 1
                    if self.is_grp_exl(c2.attrib):
                        is_st_area = 0

                    if is_meta_st_area == 2 and self.is_meta_grp(c2.attrib):
                        is_meta_st_area = 1

                    # collect attrs for group
                    if c2.attrib["k"] in st_name_attrs:
                        for name in c2.attrib["v"].split(";"):
                            if len(name) == 0:
                                continue
                            if not unique or not curGroup.has_name(name):
                                curGroup.add_name(name, c2.attrib["k"])

                if not is_st_area == 1 and not is_meta_st_area == 1:
                    if i % BUFFER == 0:
                        root.clear()
                    continue

                if is_st_area == 1:
                    # add new group
                    self.groups.append(curGroup)

                    num_osm_groups += 1

                    for c2 in c1:
                        if c2.tag != "member" or c2.attrib["type"] != "node":
                            continue
                        self.nd_group_idx[int(c2.attrib["ref"])] = len(
                            self.groups) - 1

                if is_meta_st_area == 1:
                    for c2 in c1:
                        if c2.tag != "member":
                            continue
                        if c2.attrib["type"] != "relation":
                            continue
                        self.rel_meta_group_idx[int(
                            c2.attrib["ref"])] = c1.attrib["id"]

                if i % BUFFER == 0:
                    root.clear()

        for gid, g in enumerate(self.groups):
            if g.osm_rel_id in self.rel_meta_group_idx:
                g.set_meta_group(self.rel_meta_group_idx[g.osm_rel_id])

        self.log.info("Second pass, parsing nodes...")

        perc_last = 0

        with open(path, 'r') as f:
            context = ET.iterparse(f, events=("start", "end"))
            context = iter(context)
            event, root = next(context)

            i = 0
            lvl = 0

            for event, c1 in context:
                if event == "start":
                    lvl = lvl + 1
                    continue

                i = i + 1
                lvl = lvl - 1

                perc = int((f.tell() / nd_end) * 100)
                if perc - perc_last >= 10:
                    perc_last = perc
                    self.log.info("@ %d%% (%d/%d)" % (perc, f.tell(), nd_end))

                if c1.tag != "node":
                    if i % BUFFER == 0:
                        root.clear()
                    continue

                if c1.tag == "way" or c1.tag == "relation":
                    break

                nid = int(c1.attrib["id"])
                lat = float(c1.attrib["lat"])
                lon = float(c1.attrib["lon"])

                if lat < self.ll[0]:
                    self.ll[0] = lat
                if lon < self.ll[1]:
                    self.ll[1] = lon
                if lat > self.ur[0]:
                    self.ur[0] = lat
                if lon > self.ur[1]:
                    self.ur[1] = lon

                is_station = False
                for c2 in c1:
                    if c2.tag != "tag":
                        continue
                    if self.is_st(c2.attrib):
                        is_station = True

                if not is_station:
                    if i % BUFFER == 0:
                        root.clear()
                    continue

                num_osm_stats += 1

                if nid not in self.nd_group_idx:
                    num_osm_stat_orphans += 1
                    # this node has its own group, possible with multiple
                    # entries because it has multiple names!

                    # add new orphan group
                    self.groups.append(StatGroup())

                    self.nd_group_idx[nid] = len(self.groups) - 1

                unique_st_names = set()
                cur_st_names = []

                orig_nd_name = ""

                # collect unique station names
                for c2 in c1:
                    if c2.attrib["k"] in st_name_attrs:
                        for name in c2.attrib["v"].split(";"):
                            if len(name) == 0:
                                continue
                            if unique and name in unique_st_names:
                                continue

                            unique_st_names.add(name)
                            cur_st_names.append((name, c2.attrib["k"]))
                    if c2.attrib["k"] == "name":
                        orig_nd_name = c2.attrib["v"]

                for name, attr in cur_st_names:
                    self.stations.append(
                        StatIdent(
                            lat=lat,
                            lon=lon,
                            name=name,
                            orig_nd_name=orig_nd_name,
                            osmnid=nid,
                            gid=self.nd_group_idx[nid],
                            srctype=1,
                            name_attr=attr))
                    self.groups[self.nd_group_idx[nid]].add_station(
                        len(self.stations) - 1)

                for grp_name in self.groups[self.nd_group_idx[nid]].names:
                    # we count each name of the group as a synonym for
                    # the included stations and treat them as instances
                    # of this node
                    if unique:
                        if grp_name[0] in unique_st_names:
                            continue
                        unique_st_names.add(grp_name[0])

                    self.stations.append(
                        StatIdent(
                            lat=lat,
                            lon=lon,
                            name=grp_name[0],
                            orig_nd_name=orig_nd_name,
                            osmnid=nid,
                            gid=self.nd_group_idx[nid],
                            srctype=2,
                            name_attr=grp_name[1]))
                    self.groups[self.nd_group_idx[nid]].add_station(
                        len(self.stations) - 1)

                if i % BUFFER == 0:
                    root.clear()
        self.log.info("Parsed %d stations, %s groups, %s orphan stats."
                      % (num_osm_stats, num_osm_groups, num_osm_stat_orphans))
