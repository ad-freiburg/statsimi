# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

import xml.etree.ElementTree as ET
import math
import os
from statsimi.feature.stat_ident import StatIdent
from statsimi.feature.stat_group import StatGroup
import logging


RD_BUFFER = 1024 * 1000 * 1000

# prevents calling root.clear() too often = False
BUFFER = 1000

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

st_polygon_filter = [
    ("public_transport", "platform"),
    ("highway", "platform"),
    ("railway", "platform"),
    ("tram", "platform"),
    ("subway", "platform"),
    ("bus", "platform"),
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
    #  "int_name",
    "loc_name",
    "nat_name",
    "official_name",
    #  "old_name",
    "reg_name",
    "ref_name",
    "short_name",
    "sorting_name",
    "gtfs_name",
    "gtfs:name"
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
        self.way_group_idx = {}
        self.rel_meta_group_idx = {}
        self.groups = []
        self.stations = []

        self.num_osm_stats = 0
        self.num_osm_stat_orphans = 0
        self.num_osm_groups = 0
        self.num_osm_way_polys = 0

        self.way_kept_nds = set()
        self.way_nds = {}
        self.way_nd_pos = {}
        self.way_names = {}

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

    def is_st_poly(self, attr):
        return self.filter_match(attr, st_polygon_filter)

    def is_grp(self, attr):
        return self.filter_match(attr, grp_rel_filter)

    def is_grp_exl(self, attr):
        return self.filter_match(attr, grp_rel_ex_filter)

    def parse(self, path, unique=False, with_polygons=False):
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
        >>> p = OsmParser()
        >>> p.parse("testdata/test.osm", False, True)
        >>> sorted([str(grp) for grp in p.groups])
        ... # doctest: +NORMALIZE_WHITESPACE
        ['Group (rel_id=3271923) with 18 stations',\
        'Group (rel_id=None) with 1 stations',
        'Group (rel_id=None) with 1 stations']
        >>> sorted([stat.osmnid for stat in p.stations])
        ... # doctest: +NORMALIZE_WHITESPACE
        [-1, 25237964, 25237964, 25237964, 248609020, 248609020, 248609020, \
        248609028, 248609028, 248609028, 507039988, 507039988, 507039988, \
        2496897172, 2496897172, 2496897172, 2496897173, 2496897173, \
        2496897173, 4984926391]
        '''

        self.log.info("First pass, parsing relations...")
        nd_end, way_end = self.parse_relations(path, unique);

        for gid, g in enumerate(self.groups):
            if g.osm_rel_id in self.rel_meta_group_idx:
                g.set_meta_group(self.rel_meta_group_idx[g.osm_rel_id])

        self.log.info("Second pass, parsing ways...")
        if with_polygons:
            self.parse_ways(path, way_end, unique);

        self.log.info("Third pass, parsing nodes...")
        self.parse_nodes(path, nd_end, unique);

        self.log.info("Building station polygons")
        self.build_station_polys(unique)

        self.log.info("Parsed %d stations, %d station polygons, %s groups, %s orphan stats."
                      % (self.num_osm_stats, self.num_osm_way_polys, self.num_osm_groups, self.num_osm_stat_orphans))

    def parse_relations(self, path, unique=False):
        '''
        Parse the relations in an OSM file
        '''

        f_size = os.path.getsize(path)
        nd_end = f_size
        way_end = f_size

        perc_last = 0

        with open(path, 'r', encoding="utf-8", buffering=RD_BUFFER) as f:
            context = ET.iterparse(f, events=("start", "end"))
            context = iter(context)
            event, root = next(context)

            i = 0

            for event, c1 in context:
                if event == "start":
                    continue

                i = i + 1

                perc = int((f.tell() / f_size) * 100)
                if perc - perc_last >= 10:
                    perc_last = perc
                    self.log.info("@ %d%%" % (perc))
                if nd_end == f_size and c1.tag == "way":
                    nd_end = f.tell()
                if way_end == f_size and c1.tag == "relation":
                    way_end = f.tell()

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
                            name = " ".join(name.replace('\r', ' ').replace('\n', ' ').split())
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

                    self.num_osm_groups += 1

                    for c2 in c1:
                        if c2.tag != "member":
                            continue
                        if c2.attrib["type"] == "node":
                            self.nd_group_idx[int(c2.attrib["ref"])] = len(
                                self.groups) - 1
                        if c2.attrib["type"] == "way":
                            self.way_group_idx[int(c2.attrib["ref"])] = len(
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

        return nd_end, way_end

    def parse_nodes(self, path, nd_end, unique=False):
        '''
        Parse the nodes in an OSM file
        '''

        f_size = os.path.getsize(path)

        perc_last = 0

        with open(path, 'r', encoding="utf-8", buffering=RD_BUFFER) as f:
            context = ET.iterparse(f, events=("start", "end"))
            context = iter(context)
            event, root = next(context)

            i = 0

            for event, c1 in context:
                if event == "start":
                    continue

                i = i + 1

                perc = int((f.tell() / nd_end) * 100)
                if perc - perc_last >= 10:
                    perc_last = perc
                    self.log.info("@ %d%%" % (perc))

                if c1.tag == "way" or c1.tag == "relation":
                    break

                if c1.tag != "node":
                    if i % BUFFER == 0:
                        root.clear()
                    continue

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

                if nid in self.way_kept_nds:
                    self.way_nd_pos[nid] = (lon, lat)

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

                self.num_osm_stats += 1

                if nid not in self.nd_group_idx:
                    self.num_osm_stat_orphans += 1
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
                            name = " ".join(name.replace('\r', ' ').replace('\n', ' ').split())
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

    def parse_ways(self, path, way_end, unique=False):
        '''
        Parse the ways in an OSM file
        '''

        f_size = os.path.getsize(path)

        perc_last = 0

        with open(path, 'r', encoding="utf-8", buffering=RD_BUFFER) as f:
            context = ET.iterparse(f, events=("start", "end"))
            context = iter(context)
            event, root = next(context)

            i = 0

            for event, c1 in context:
                if event == "start":
                    continue

                i = i + 1

                perc = int((f.tell() / way_end) * 100)
                if perc - perc_last >= 10:
                    perc_last = perc
                    self.log.info("@ %d%%" % (perc))

                if c1.tag == "relation":
                    break

                if c1.tag != "way":
                    if i % BUFFER == 0:
                        root.clear()
                    continue

                wid = int(c1.attrib["id"])
                self.way_nds[wid] = []

                is_station = False
                for c2 in c1:
                    if c2.tag == "nd":
                        nid = int(c2.attrib["ref"])
                        self.way_kept_nds.add(nid)
                        self.way_nds[wid].append(nid)
                    if c2.tag != "tag":
                        continue
                    if self.is_st_poly(c2.attrib):
                        is_station = True

                if not is_station:
                    if i % BUFFER == 0:
                        root.clear()
                    continue

                self.num_osm_way_polys += 1

                cur_st_names = []

                # collect unique station names
                for c2 in c1:
                    if c2.tag != "tag":
                        continue
                    if c2.attrib["k"] in st_name_attrs:
                        for name in c2.attrib["v"].split(";"):
                            cur_st_names.append((name, c2.attrib["k"]))

                self.way_names[wid] = cur_st_names

                if i % BUFFER == 0:
                    root.clear()

    def build_station_polys(self, unique):
        for wid, names in self.way_names.items():
            if wid not in self.way_group_idx:
                self.num_osm_stat_orphans += 1
                # this node has its own group, possible with multiple
                # entries because it has multiple names!

                # add new orphan group
                self.groups.append(StatGroup())

                self.way_group_idx[wid] = len(self.groups) - 1

            unique_st_names = set()
            cur_st_names = []

            orig_nd_name = ""

            # collect unique station names
            for name, key in names:
                name = " ".join(name.replace('\r', ' ').replace('\n', ' ').split())
                if len(name) == 0:
                    continue
                if unique and name in unique_st_names:
                    continue

                unique_st_names.add(name)
                cur_st_names.append((name, key))

                if key == "name":
                    orig_nd_name = name

            poly = []
            for nid in self.way_nds[wid]:
                poly.append(self.way_nd_pos[nid])

            for name, attr in cur_st_names:
                self.stations.append(
                    StatIdent(
                        poly=poly,
                        name=name,
                        orig_nd_name=orig_nd_name,
                        osmnid=-wid,
                        gid=self.way_group_idx[wid],
                        srctype=1,
                        name_attr=attr))
                self.groups[self.way_group_idx[wid]].add_station(
                    len(self.stations) - 1)

            for grp_name in self.groups[self.way_group_idx[wid]].names:
                # we count each name of the group as a synonym for
                # the included stations and treat them as instances
                # of this node
                if unique:
                    if grp_name[0] in unique_st_names:
                        continue
                    unique_st_names.add(grp_name[0])

                self.stations.append(
                    StatIdent(
                        poly=poly,
                        name=grp_name[0],
                        orig_nd_name=orig_nd_name,
                        osmnid=-wid,
                        gid=self.way_group_idx[wid],
                        srctype=2,
                        name_attr=grp_name[1]))
                self.groups[self.way_group_idx[wid]].add_station(
                    len(self.stations) - 1)

