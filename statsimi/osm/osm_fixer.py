# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

from statsimi.feature.stat_group import StatGroup
import logging


class OsmFixer(object):
    '''
    TODO
    '''

    def __init__(self, cfg, features, test_idx=None):
        '''
        Constructor
        '''

        self.log = logging.getLogger('osmfix')
        self.cfg = cfg
        self.features = features

        self.simi_idx = []

        self.test_idx = None

        self.or_grp_rm_conf = {}

        # TODO: make configurable
        self.min_confidence = 0.6

        self.osm_stations = {}

    def analyze(self, model):
        self.log.info("Analyzing...")

        self.fill_osm_stations()

        tm = self.features.get_matrix()
        y_input = tm[:, -1].toarray().ravel()
        X_input = tm[:, :-1]

        if getattr(model, "set_lookup_idx", None):
            model.set_lookup_idx(self.test_idx)

        y_proba = model.predict_proba(X_input)

        self.build_simi_index(model, y_proba)

        self.analyze_wrong_groups(model, y_input, y_proba)

        self.regroup()

        self.update_osm_stations()

        self.log.info("Done.")

    def fill_osm_stations(self):
        for st_id, st in enumerate(self.features.stations):
            geom = []
            if st.lat != None:
                geom = [st.lat, st.lon]
            else:
                geom = st.poly
            if st.osmnid not in self.osm_stations:
                self.osm_stations[st.osmnid] = {
                    "geom": geom,
                    "name_stations": [],
                    "rel_name_stations": [],
                    "orig_group_id": st.gid,
                    "target_group_id": st.gid,
                    "wrong_attrs": {}
                }

            if st.srctype == 1:
                self.osm_stations[st.osmnid]["name_stations"].append(st_id)
            else:
                self.osm_stations[st.osmnid]["rel_name_stations"].append(st_id)

    def get_group(self, gid):
        return self.features.groups[gid]

    def get_station(self, sid):
        return self.features.stations[sid]

    def update_osm_stations(self):
        for osm_nd_id, osm_st in self.osm_stations.items():
            self.update_osm_station(osm_nd_id, osm_st)

    def update_osm_station(self, osm_nd_id, osm_st):
        if len(osm_st["name_stations"]) == 0:
            # no name stations, there was no name attribute for this
            # station
            print("SUGG: Add 'name' attribute to station node %d" % osm_nd_id)
            return

        for n_stat_id in osm_st["name_stations"]:
            n_stat = self.get_station(n_stat_id)
            if n_stat.gid != osm_st["orig_group_id"] and n_stat_id in self.or_grp_rm_conf:
                print("INCO: in node #%d, attribute '%s'='%s' did not match group #%d (conf = %.2f)" % (
                    osm_nd_id, n_stat.name_attr, n_stat.name, n_stat.gid, self.or_grp_rm_conf[n_stat_id][0]))

                if n_stat.srctype == 1:
                    osm_st["wrong_attrs"][n_stat.name_attr] = []

                for n_stat_id2 in self.or_grp_rm_conf[n_stat_id][1]:
                    n_stat_2 = self.get_station(n_stat_id2)
                    osm_st["wrong_attrs"][n_stat.name_attr].append(
                        (n_stat_id2, self.or_grp_rm_conf[n_stat_id][1][n_stat_id2]))
                    print("  no match for '%s'='%s' (conf = %.2f)" % (
                        n_stat_2.name_attr, n_stat_2.name, self.or_grp_rm_conf[n_stat_id][1][n_stat_id2]))

        group_counts = {}
        for n_stat_id in osm_st["name_stations"]:
            n_stat = self.get_station(n_stat_id)
            if n_stat.gid not in group_counts:
                group_counts[n_stat.gid] = 0
            group_counts[n_stat.gid] += 1

        sorted_groups = [(k, group_counts[k]) for k in sorted(
            group_counts, key=group_counts.__getitem__, reverse=True)]

        if sorted_groups[0][1] <= len(osm_st["name_stations"]) * 0.5:
            # we don't have a main group -> don't make a suggestion, just
            # report the error
            pass
        else:
            # we have a main group...
            if sorted_groups[0][0] != osm_st["orig_group_id"]:
                # ...and it is different than the original group id of this node...

                if self.get_group(osm_st["orig_group_id"]).osm_rel_id:
                    # ...and the original group was a OSM relation group...
                    if self.get_group(sorted_groups[0][0]).osm_rel_id:
                        # ...and the new group is also a OSM relation group
                        print("SUGG: Move %d from relation #%d to relation #%d" % (osm_nd_id, self.get_group(
                            osm_st["orig_group_id"]).osm_rel_id, self.get_group(sorted_groups[0][0]).osm_rel_id))
                        osm_st["target_group_id"] = sorted_groups[0][0]
                    else:
                        # ...and the new group is an orphan group
                        print("SUGG: Move %d out of relation #%d" % (
                            osm_nd_id, self.get_group(osm_st["orig_group_id"]).osm_rel_id))
                        osm_st["target_group_id"] = sorted_groups[0][0]
                else:
                    # ...and the original group was an orphan group...
                    if self.get_group(sorted_groups[0][0]).osm_rel_id:
                        # ...and the new group is a OSM relation group
                        print("SUGG: Move %d to relation #%d" % (
                            osm_nd_id, self.get_group(sorted_groups[0][0]).osm_rel_id))
                        osm_st["target_group_id"] = sorted_groups[0][0]
                    else:
                        # ... and the new group is a non-osm group ...
                        if len(
                            self.get_group(
                                sorted_groups[0][0]).stations):
                            # ... which is NOT an orphan group.
                            print("SUGG: Move %d to new relation of group %d" %
                                  (osm_nd_id, sorted_groups[0][0]))
                            osm_st["target_group_id"] = sorted_groups[0][0]
                        else:
                            # ... which IS an orphan group.
                            pass
            else:
                # and it is still in the right group, don't make a
                # suggestion
                pass

    def print_to_file(self, path):
        osmid_to_id = {}
        with open(path, 'w', encoding='utf-8') as file:
            # first, write stations
            for id, osm_id in enumerate(self.osm_stations):
                osmid_to_id[osm_id] = id
                st = self.osm_stations[osm_id]
                file.write(str(osm_id) +
                           "\t" +
                           "\t" +
                           str(st["orig_group_id"]) +
                           "\t" +
                           str(st["target_group_id"])+
                           "\t" +
                           "\t".join(st["geom"]))

                # attributes in name stations
                for _, fstid in enumerate(st["name_stations"]):
                    file.write("\t" + self.get_station(fstid).name_attr +
                               "\t" + self.get_station(fstid).name)

                file.write("\n")

            file.write("\n")

            # second, write groups
            for gid, group in enumerate(self.features.groups):
                if group.osm_rel_id:
                    file.write(str(group.osm_rel_id) + "\n")
                else:
                    file.write("0\n")

            file.write("\n")

            # third, write attr errors
            for id, osm_id in enumerate(self.osm_stations):
                st = self.osm_stations[osm_id]

                # attributes in name stations
                for (attr_name, unmatches) in st["wrong_attrs"].items():
                    for _, (sid, conf) in enumerate(unmatches):
                        fst = self.get_station(sid)
                        if fst.srctype == 1:
                            file.write(str(id) +
                                       "\t" +
                                       attr_name +
                                       "\t" +
                                       fst.name_attr +
                                       "\t" +
                                       str(conf) +
                                       "\t" +
                                       str(osmid_to_id[fst.osmnid]) +
                                       "\n")
                        #  elif st["src"] == "relation":

            file.write("\n")

    def analyze_wrong_groups(self, model, y_input, y_proba):

        in_group_dismatches = [0] * len(self.features.stations)
        in_group_dismatches_conf = [0] * len(self.features.stations)

        for id, (input, (nomatch_p, match_p)) in enumerate(
                zip(y_input, y_proba)):
            if input == 1 and nomatch_p > self.min_confidence:
                lid = id
                if self.test_idx is not None:
                    lid = self.test_idx[id]

                stid1 = self.features.pairs[lid][0]
                stid2 = self.features.pairs[lid][1]

                # wrongly grouped as similar according to our model!
                in_group_dismatches[stid1] += 1
                in_group_dismatches[stid2] += 1

                in_group_dismatches_conf[stid1] += nomatch_p
                in_group_dismatches_conf[stid2] += nomatch_p

                for stid in (stid1, stid2):
                    if stid not in self.or_grp_rm_conf:
                        self.or_grp_rm_conf[stid] = (0, {})

                self.or_grp_rm_conf[stid1][1][stid2] = nomatch_p
                self.or_grp_rm_conf[stid2][1][stid1] = nomatch_p

        removes = []

        for stid, dismatches in enumerate(in_group_dismatches):
            if dismatches == 0:
                continue

            in_group_dismatches_conf[
                stid] = in_group_dismatches_conf[stid] / dismatches

            st = self.features.stations[stid]
            group = self.features.groups[st.gid]

            if dismatches >= (len(group.stats) / 2.0):
                # print(st["name"] + " (" + str(st["osm_nd_id"]) + ") seems to
                # be grouped incorrectly to group #" + str(st["group"]) + "(" +
                # str(group["osm_rel_id"]) + ", " + str(dismatches) + "
                # dismatches, confidence " +
                # str(in_group_dismatches_conf[stid]) + ")")
                removes.append(stid)

                self.or_grp_rm_conf[stid] = (
                    in_group_dismatches_conf[stid],
                    self.or_grp_rm_conf[stid][1])

        for idx, stid in enumerate(removes):
            self.remove_from_group(stid)

    def remove_from_group(self, stid):
        st = self.features.stations[stid]

        # remove station from group
        self.features.groups[st.gid].remove_station(stid)

        # remove a station from its group and add it to a new standalone group
        self.features.groups.append(StatGroup(stations=[stid]))
        st.gid = len(self.features.groups) - 1

    def build_simi_index(self, model, y_proba):
        self.simi_idx = [[] for i in range(len(self.features.stations))]
        for id, (nomatch_p, match_p) in enumerate(y_proba):
            lid = id
            if self.test_idx is not None:
                lid = self.test_idx[id]

            stid1 = self.features.pairs[lid][0]
            stid2 = self.features.pairs[lid][1]

            self.simi_idx[stid1].append((stid2, match_p))
            self.simi_idx[stid2].append((stid1, match_p))

        # sort buckets by id
        for id, buck in enumerate(self.simi_idx):
            self.simi_idx[id] = sorted(buck, key=lambda a: a[0])

    def get_group_merge_cands(self, gid):
        group = self.get_group(gid)

        # collect groups near any station in group
        groups = {}

        for _, sid1 in enumerate(group.stats):
            assert(self.get_station(sid1).gid == gid)
            for _, (sid2, simi_conf) in enumerate(self.simi_idx[sid1]):
                m_gid = self.get_station(sid2).gid
                if m_gid == gid:
                    # don't use the station as a merge candidate for itself
                    continue
                if m_gid not in groups:
                    groups[m_gid] = 0

                groups[m_gid] += simi_conf

        for m_gid in groups:
            groups[m_gid] = groups[m_gid] / \
                (len(group.stats) *
                 len(self.get_group(m_gid).stats))

        return sorted(groups.items(), key=lambda x: x[1], reverse=True)

    def merge(self, gid1, gid2):
        # use the larger group as master
        master_g = self.get_group(gid1)
        master_gid = gid1
        minor_g = self.get_group(gid2)
        minor_gid = gid2

        if len(master_g.stats) < len(minor_g.stats):
            master_g = minor_g
            master_gid = minor_gid
            minor_g = self.get_group(gid1)
            minor_gid = gid1

        for _, sid in enumerate(minor_g.stats):
            self.get_station(sid).gid = master_gid
            master_g.add_station(sid)

        # empty old group
        minor_g.stats = []

        # mark new group as added group if it has no osm id
        # TODO: not nice to use id 1 here...
        if not master_g.osm_rel_id:
            master_g.osm_rel_id = 1

    def stat_to_group_simi(self, sid, gid):
        group = self.get_group(gid)
        tot_conf = 0

        # TODO: use the fact that simi_idx buckets are sorted here

        for _, sid1 in enumerate(group.stats):
            for _, (sid2, simi_conf) in enumerate(self.simi_idx[sid1]):
                if sid2 == sid:
                    tot_conf += simi_conf
                    break

        return tot_conf / len(group.stats)

    def regroup(self):
        max_steps = 10
        i = 0

        while i < max_steps and self.regroup_step():
            self.log.info("== Regroup step %d ==" % i)
            i += 1

    def regroup_step(self):
        changed = False
        for gid1, group in enumerate(self.features.groups):
            cands = self.get_group_merge_cands(gid1)

            if len(cands) and cands[0][1] > self.min_confidence:
                print("SUGG: Merge those groups with confidence " +
                      str(cands[0][1]))
                print("  " + str(gid1))
                for sid in group.stats:
                    print("    " +
                          str(self.get_station(sid)) +
                          " (to-group simi conf to group " +
                          str(cands[0][0]) +
                          ": " +
                          str(self.stat_to_group_simi(sid, cands[0][0])) +
                          ")")
                print("  " + str(cands[0][0]))
                for sid in self.get_group(cands[0][0]).stats:
                    print("    " +
                          str(self.get_station(sid)) +
                          " (to-group simi conf to group " +
                          str(gid1) +
                          ": " +
                          str(self.stat_to_group_simi(sid, gid1)) +
                          ")")
                print()

                self.merge(gid1, cands[0][0])
                changed = True
        return changed
