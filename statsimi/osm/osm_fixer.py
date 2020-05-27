# -*- coding: utf-8 -*-
'''
Copyright 2019, University of Freiburg.
Chair of Algorithms and Data Structures.
Patrick Brosi <brosi@informatik.uni-freiburg.de>
'''

from statsimi.feature.stat_group import StatGroup
from itertools import repeat
import numpy as np
import logging
import re


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

        self.tracknumbers = {}

        self.test_idx = None

        self.or_grp_rm_conf = {}

        # TODO: make configurable
        self.min_confidence = 0.6

        self.osm_stations = {}

        self.osm_relations = {}

    def analyze(self, model):
        self.log.info("Analyzing...")

        self.fill_osm_groups()

        self.fill_osm_stations()

        tm = self.features.get_matrix()
        y_input = tm[:, -1].toarray().ravel()
        X_input = tm[:, :-1]

        if getattr(model, "set_lookup_idx", None):
            model.set_lookup_idx(self.test_idx)

        y_proba = model.predict_proba(X_input)

        # make sure both classes are present in the y_proba, even
        # if only one occurred in the training data
        if y_proba.shape[1] != 2:
            all_classes = np.array([0, 1])
            # Get the probabilities for learnt classes
            # Create the result matrix, where all values are initially zero
            new_prob = np.zeros((y_proba.shape[0], all_classes.size))
            # Set the columns corresponding to clf.classes_
            new_prob[:, all_classes.searchsorted(model.classes_)] = y_proba
            y_proba = new_prob

        self.build_simi_index(model, y_proba)

        self.analyze_wrong_groups(model, y_input, y_proba)

        self.regroup()

        self.update_osm_stations()

        self.update_osm_relations()

        self.log.info("Done.")

    def fill_osm_groups(self):
        for gid, gr in enumerate(self.features.groups):
            if not gr.osm_rel_id:
                continue

            self.osm_relations[gr.osm_rel_id] = {
                "name_stations": {},
                "group_id": gid,
                "wrong_attrs": {}
            }


    def fill_osm_stations(self):
        for st_id, st in enumerate(self.features.stations):
            geom = []
            if st.lat is not None:
                geom = [(st.lon, st.lat)]
            else:
                geom = st.poly

            # we write every node to osm stations to catch
            # nodes without a name attribute
            if st.osmnid not in self.osm_stations:
                self.osm_stations[st.osmnid] = {
                    "geom": geom,
                    "name_stations": [],
                    "orig_group_id": st.gid,
                    "target_group_id": st.gid,
                    "wrong_attrs": {}
                }

            if st.srctype == 1:
                self.osm_stations[st.osmnid]["name_stations"].append(st_id)

            elif st.srctype == 2:
                group = self.get_group(st.gid)
                if not group.osm_rel_id:
                    continue

                if st.name_attr not in self.osm_relations[group.osm_rel_id]["name_stations"]:
                    self.osm_relations[group.osm_rel_id]["name_stations"][st.name_attr] = []

                self.osm_relations[group.osm_rel_id]["name_stations"][st.name_attr].append(st_id)

    def get_group(self, gid):
        return self.features.groups[gid]

    def get_station(self, sid):
        return self.features.stations[sid]

    def update_osm_relations(self):
        for osm_rel_id, osm_rel in self.osm_relations.items():
            self.update_osm_relation(osm_rel_id, osm_rel)

    def update_osm_relation(self, osm_rel_id, osm_rel):
        if len(osm_rel["name_stations"]) == 0:
            # no name stations, there was no name attribute for this
            # relations
            #  print("SUGG: Add 'name' attribute to station relation %d" % osm_rel_id)
            return

        for name in osm_rel["name_stations"]:
            dismatches = 0
            conf = 0

            individual_confs = {}
            individual_counts = {}
            for n_stat_id in osm_rel["name_stations"][name]:
                n_stat = self.get_station(n_stat_id)
                if n_stat.gid == osm_rel["group_id"] or n_stat_id not in self.or_grp_rm_conf:
                    continue

                new_group = self.get_group(n_stat.gid)
                if new_group.osm_rel_id:
                    # if the attribute is not in an orphan group, it was moved
                    # into another group. In this case, the two groups were merged and
                    # we don't report an attr error
                    continue

                dismatches += 1
                conf += self.or_grp_rm_conf[n_stat_id][0]

                # we have to collect the individual stations or attributes with
                # which this name does not match. Since we have inserted for each
                # relation tag multiple station identifiers, there might be several scores
                # and we have to average them and make the dismatches unique
                for n_stat_id2 in self.or_grp_rm_conf[n_stat_id][1]:
                    if n_stat_id2 not in individual_confs:
                        individual_confs[n_stat_id2] = 0
                        individual_counts[n_stat_id2] = 0

                    individual_confs[n_stat_id2] += self.or_grp_rm_conf[n_stat_id][1][n_stat_id2]
                    individual_counts[n_stat_id2] += 1

            # dismatch only if half or more of the name stations are a dismatch
            if dismatches == 0 or dismatches < len(osm_rel["name_stations"][name]) / 2.0:
                continue

            conf = conf / dismatches

            # dismatches is now the number of name stations for this attribute
            # which dont match the relation's group

            # conf is their average deletion confidence

            #  print(
                #  "INCO: in rel #%d, attribute '%s'='%s' did not match (conf = %.2f)" %
                #  (osm_rel_id,
                 #  n_stat.name_attr,
                 #  n_stat.name,
                 #  conf))

            osm_rel["wrong_attrs"][name] = []

            for n_stat_id2 in individual_confs:
                n_stat_2 = self.get_station(n_stat_id2)
                conf = individual_confs[n_stat_id2] / individual_counts[n_stat_id2]
                osm_rel["wrong_attrs"][name].append((n_stat_id2, conf))
                #  print("  no match for '%s'='%s' (conf = %.2f)" %
                    #  (n_stat_2.name_attr,
                     #  n_stat_2.name,
                     #  conf))

    def update_osm_stations(self):
        for osm_nd_id, osm_st in self.osm_stations.items():
            self.update_osm_station(osm_nd_id, osm_st)

    def update_osm_station(self, osm_nd_id, osm_st):
        if len(osm_st["name_stations"]) == 0:
            # no name stations, there was no name attribute for this
            # station
            #  print("SUGG: Add 'name' attribute to node %d" % osm_nd_id)
            return

        for n_stat_id in osm_st["name_stations"]:
            n_stat = self.get_station(n_stat_id)
            if n_stat.gid != osm_st["orig_group_id"] and n_stat_id in self.or_grp_rm_conf:
                #  print(
                    #  "INCO: in node #%d, attribute '%s'='%s' did not match group #%d (conf = %.2f)" %
                    #  (osm_nd_id,
                     #  n_stat.name_attr,
                     #  n_stat.name,
                     #  n_stat.gid,
                     #  self.or_grp_rm_conf[n_stat_id][0]))

                osm_st["wrong_attrs"][n_stat.name_attr] = []

                individual_confs = {}
                individual_counts = {}
                individual_stats = {}

                for n_stat_id2 in self.or_grp_rm_conf[n_stat_id][1]:
                    n_stat_2 = self.get_station(n_stat_id2)

                    conf = self.or_grp_rm_conf[n_stat_id][1][n_stat_id2]

                    if n_stat_2.srctype == 2:
                        group = self.get_group(n_stat_2.gid)
                        if group.osm_rel_id == None or group.osm_rel_id == 1:
                            # don't report negative matches to name attrs which
                            # have been removed from their original group
                            continue

                        if n_stat_2.gid not in individual_confs:
                            individual_confs[n_stat_2.gid] = {}
                            individual_counts[n_stat_2.gid] = {}
                            individual_stats[n_stat_2.gid] = {}

                        if n_stat_2.name_attr not in individual_confs[n_stat_2.gid]:
                            individual_confs[n_stat_2.gid][n_stat_2.name_attr] = 0
                            individual_counts[n_stat_2.gid][n_stat_2.name_attr] = 0
                            individual_stats[n_stat_2.gid][n_stat_2.name_attr] = n_stat_id2

                        individual_counts[n_stat_2.gid][n_stat_2.name_attr] += 1
                        individual_confs[n_stat_2.gid][n_stat_2.name_attr] += conf

                        continue

                    osm_st["wrong_attrs"][n_stat.name_attr].append((n_stat_id2, conf))
                    #  print("  no match for '%s'='%s' (conf = %.2f)" %
                        #  (n_stat_2.name_attr,
                         #  n_stat_2.name,
                         #  conf))

                for gid in individual_counts:
                    for attr_name in individual_counts[gid]:
                        stat = individual_stats[gid][attr_name]
                        conf = individual_confs[gid][attr_name] / individual_counts[gid][attr_name]
                        osm_st["wrong_attrs"][n_stat.name_attr].append((stat, conf))
                        #  print("  no match for '%s'='%s' (conf = %.2f)" %
                            #  (attr_name,
                             #  self.get_station(stat).name,
                             #  conf))

                group = self.get_group(n_stat.gid)
                if len(group.stats) == 1 and group.osm_rel_id == None and self.stat_is_tracknumber_heur(n_stat_id):
                    # track mistakes are marked by an attr error with the attribute itself!
                    osm_st["wrong_attrs"][n_stat.name_attr].append((n_stat_id, 0.6))
                    #  print("  ('%s' = '%s' seems to be a track number!)" %
                        #  (n_stat.name_attr, n_stat.name))

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
            orig_gid = osm_st["orig_group_id"]
            target_gid = sorted_groups[0][0]
            orig_gr = self.get_group(orig_gid)
            target_gr = self.get_group(target_gid)
            if target_gid != orig_gid:
                # ...and it is different than the original group id of this node...

                if orig_gr.osm_rel_id:
                    # ...and the original group was a OSM relation group...
                    if target_gr.osm_rel_id:
                        # ...and the new group is also an OSM relation group
                        if orig_gr.osm_meta_rel_id == None or target_gr.osm_meta_rel_id != orig_gr.osm_meta_rel_id:
                            # ...and the new group and the old group are not in the same meta group
                            #  print("SUGG: Move %d from relation #%d to relation #%d" %
                                #  (osm_nd_id, orig_gr.osm_rel_id, target_gr.osm_rel_id))
                            osm_st["target_group_id"] = target_gid
                        else:
                            # ... and they are in the same meta group, don't suggest anything
                            pass
                    else:
                        # ...and the new group is an orphan group
                        #  print("SUGG: Move %d out of relation #%d" %
                            #  (osm_nd_id, orig_gr.osm_rel_id))
                        osm_st["target_group_id"] = target_gid
                else:
                    # ...and the original group was an orphan group...
                    if target_gr.osm_rel_id:
                        # ...and the new group is an OSM relation group
                        #  print("SUGG: Move %d to relation #%d" %
                            #  (osm_nd_id, target_gr.osm_rel_id))
                        osm_st["target_group_id"] = target_gid
                    else:
                        # ... and the new group is a non-osm group ...
                        if len(target_gr.stations):
                            # ... which is NOT an orphan group.
                            #  print("SUGG: Move %d to new relation of group %d" %
                                  #  (osm_nd_id, target_gid))
                            osm_st["target_group_id"] = target_gid
                        else:
                            # ... which IS an orphan group.
                            pass
            else:
                # and it is still in the right group, don't make a
                # suggestion
                pass

    def print_to_file(self, path):
        osmnid_to_sid = {}
        with open(path, 'w', encoding='utf-8') as file:
            # first, write stations
            for id, osm_nid in enumerate(self.osm_stations):
                osmnid_to_sid[osm_nid] = id
                st = self.osm_stations[osm_nid]
                file.write(str(osm_nid) +
                           "\t" +
                           "\t" +
                           str(st["orig_group_id"]) +
                           "\t" +
                           str(st["target_group_id"]) +
                           "\t" +
                           "\t".join([str(coord) for tpl in st["geom"] for coord in tpl]))

                # attributes in name stations
                for _, fstid in enumerate(st["name_stations"]):
                    file.write("\t" + self.get_station(fstid).name_attr +
                               "\t" + self.get_station(fstid).name)

                file.write("\n")

            file.write("\n")

            # second, write groups
            for gid, group in enumerate(self.features.groups):
                if group.osm_rel_id:
                    file.write(str(group.osm_rel_id))

                    # NOTE: osm rel id 1 is used for new OSM relations
                    if group.osm_rel_id != 1:
                        osm_grp = self.osm_relations[group.osm_rel_id]

                        # attributes in group
                        for _, name in enumerate(osm_grp["name_stations"]):
                            file.write("\t" + name +
                                       "\t" + self.get_station(osm_grp["name_stations"][name][0]).name)
                else:
                    file.write("0")

                file.write("\n")

            file.write("\n")

            # third, write station attr errors
            for id, osm_nid in enumerate(self.osm_stations):
                st = self.osm_stations[osm_nid]

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
                                       str(osmnid_to_sid[fst.osmnid]) +
                                       "\n")
                        elif fst.srctype == 2:
                            file.write(str(id) +
                                       "\t" +
                                       attr_name +
                                       "\t" +
                                       fst.name_attr +
                                       "\t" +
                                       str(conf) +
                                       "\t" +
                                       # we use the original gid here because the attribute station may
                                       # have been moved to another relation
                                       str(-fst.orig_gid) +
                                       "\n")

            file.write("\n")

            # fourth, write group attr errors
            for osm_rel_id in self.osm_relations:
                rel = self.osm_relations[osm_rel_id]

                gid = rel["group_id"]

                # attributes in name stations
                for (attr_name, unmatches) in rel["wrong_attrs"].items():
                    for _, (sid, conf) in enumerate(unmatches):
                        fst = self.get_station(sid)
                        if fst.srctype == 1:
                            # no match to another station
                            file.write(str(gid) +
                                       "\t" +
                                       attr_name +
                                       "\t" +
                                       fst.name_attr +
                                       "\t" +
                                       str(conf) +
                                       "\t" +
                                       str(osmnid_to_sid[fst.osmnid]) +
                                       "\n")
                        elif fst.srctype == 2:
                            # no match to another attribute in a group
                            # important: because of our update rules,
                            # this can only happen to attrs in the same
                            # group!
                            file.write(str(gid) +
                                       "\t" +
                                       attr_name +
                                       "\t" +
                                       fst.name_attr +
                                       "\t" +
                                       str(conf) +
                                       "\t" +
                                       str(-gid) +
                                       "\n")

            file.write("\n")

            # fifth, write meta group (stop_area_groups)
            for gid, group in enumerate(self.features.groups):
                if group.osm_meta_rel_id:
                    file.write(str(gid) + "\t" + str(group.osm_meta_rel_id))
                    file.write("\n")

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

                if (self.features.stations[stid1].name_attr == "alt_name") != (
                        self.features.stations[stid2].name_attr == "alt_name"):
                    continue

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
                # we remove if half or more of the stations in this group
                # are a dismatch
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

        # removed tracknumber stats are always in a new orphan group at the moment
        if len(group.stats) == 1 and group.osm_rel_id == None and self.stat_is_tracknumber_heur(group.stats[0]):
            # and we dont want to merge them with any group
            return {}

        if len(group.stats) == 1 and group.osm_rel_id == None and self.get_station(group.stats[0]).srctype == 2:
            # we dont want to group with removed relation name stats
            return {}

        # collect groups near any station in group
        groups = {}

        a = False

        for _, sid1 in enumerate(group.stats):
            assert(self.get_station(sid1).gid == gid)

            for _, (sid2, simi_conf) in enumerate(self.simi_idx[sid1]):
                m_gid = self.get_station(sid2).gid
                if m_gid == gid:
                    # don't use the station as a merge candidate for itself
                    continue

                m_group = self.get_group(m_gid)
                # tracknumber stats are always in an orphan group at the moment
                if len(m_group.stats) == 1 and m_group.osm_rel_id == None and self.stat_is_tracknumber_heur(m_group.stats[0]):
                    # and we dont want to merge them with any group
                    continue

                if len(m_group.stats) == 1 and m_group.osm_rel_id == None and self.get_station(m_group.stats[0]).srctype == 2:
                    # we dont want to group with removed relation name stats
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

        minor_in_meta = minor_g.osm_meta_rel_id and not master_g.osm_meta_rel_id
        master_in_meta = master_g.osm_meta_rel_id and not minor_g.osm_meta_rel_id

        # always merge into a meta group, or into the larger

        if minor_in_meta or (not master_in_meta and len(master_g.stats) < len(minor_g.stats)):
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
        max_steps = 500
        i = 0

        while i < max_steps and self.regroup_step():
            self.log.info("== Regroup step %d ==" % i)
            i += 1

    def stat_is_tracknumber_heur(self, stid):
        # this is a heuristic to catch track numbers in name attributes,
        # a common mistake in OSM (track numbers should go into ref or local_ref,
        # the name attribute should contain the name of the station, see
        # e.g https://wiki.openstreetmap.org/wiki/Tag:public%20transport=platform)

        if stid in self.tracknumbers:
            return self.tracknumbers[stid]

        name = self.get_station(stid).name

        if len(name) == 0:
            self.tracknumbers[stid] = False
            return False

        if len(name) == 1:
            self.tracknumbers[stid] = True
            return True

        tokens = re.split(r'\W+', name)
        if len(tokens) < 3:
            if len(tokens[-1]) == 1:
                self.tracknumbers[stid] = True
                return True
            if tokens[-1].isnumeric():
                self.tracknumbers[stid] = True
                return True
            for char in tokens[-1]:
                if char.isdigit():
                    self.tracknumbers[stid] = True
                    return True

        self.tracknumbers[stid] = False
        return False

    def regroup_step(self):
        changed = False
        merge_cands = []

        # collect the best merge candidate for each group
        for gid1, group in enumerate(self.features.groups):
            cands = self.get_group_merge_cands(gid1)

            if len(cands) and cands[0][1] > self.min_confidence:
                merge_cands.append((gid1, cands[0][0], cands[0][1]))

        tainted = set()

        # order by confidence, highest confidence first
        merge_cands.sort(key=lambda x:x[2],reverse=True)

        # merge candidates ordered by confidence. if a
        # candidate has been changed during the process, mark as
        # tainted and do not merge in this round
        for (gid1, gid2, score) in merge_cands:
            if gid1 in tainted or gid2 in tainted:
                continue

            self.merge(gid1, gid2)
            changed = True

            tainted.add(gid1)
            tainted.add(gid2)

        return changed
