"""Copyright (c) 2021 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""
import AnalysisCore
import re
import collections
import ipaddress
import json
import ParseCommands
import os


def LogIt(message, level):
    if re.match(r"^debug", message.lower()):
        pass
    elif re.match(r"^notice", message.lower()):
        print(message)
    else:
        print(message)


''' Gets Database information to determine Edge Devices'''


def LispDBAnalysis(dnac, dnac_core):
    statdevs = 0
    statteids = 0
    stateid = 0
    statfail = 0
    localstat = 0
    failedeid = []
    cpnodes = []
    lispdb = dnac_core.get(["lisp", "database"])
    tcpnodes = dnac_core.get(["lisp", "site"])
    for AF in tcpnodes.keys():
        cpnodes.extend(dnac_core.get(["lisp", "site", AF]).keys())  # Assuming all CP nodes have IP
    if len(cpnodes) == 0:
        print("No CP nodes found , exiting")
        return
    if lispdb is None:
        LogIt(
            f"Error: No LISP Database entries found to parse", 1)
        return
    # print (print(json.dumps(lispdb, indent=4)))
    for edgename in lispdb.keys():
        statdevs = statdevs + 1
        edgeip = dnac_core.get(["Global", "Devices", edgename]).get("IP Address")
        for edgeinstance in lispdb.get(edgename):
            if re.match(r"^8", edgeinstance):
                edgeinstanceaf = "ethernet"
            else:
                edgeinstanceaf = "ip"
            local_macs = dnac_core.get(["lisp", "svi_interface", edgename])
            local_addr = []
            if local_macs is not None:
                for locals in local_macs:
                    for vals in local_macs[locals].keys():
                        local_addr.append(local_macs[locals][vals])
            else:
                local_addr = []
            # print(lispdb.get(edgename).get(edgeinstance).keys())
            wlcdb = dnac_core.get(["lisp", "wlcip"])
            if wlcdb is not None:
                wlcip = wlcdb["ip addresses"]
            else:
                wlcip = []

            for edgeeid in lispdb.get(edgename).get(edgeinstance).keys():
                # print (lispdb.get(edgename).get(edgeinstance).get(edgeeid).get("Source"))
                # if lispdb.get(edgename).get(edgeinstance).get(edgeeid).get("eSource") != "dynamic-eid":
                if "site-registration," not in lispdb.get(edgename).get(edgeinstance).get(edgeeid).get("Source"):
                    edgeeid = edgeeid.split(",")[0]
                    if edgeeid.split('/')[0] in local_addr:
                        # print(  f"Debug: {edgename} {edgeinstance} {edgeeid} {edgeinstanceaf} is local address")
                        localstat = localstat + 1
                    else:
                        success = True
                        for cp in cpnodes:
                            if edgeeid in dnac_core.get(["lisp", "site", edgeinstanceaf, cp, edgeinstance]).keys():
                                # print(f"LISP Database Analysis: found {edgeeid} on CP node {cp}")
                                rloc = dnac_core.get(["lisp", "site", edgeinstanceaf, cp, edgeinstance, edgeeid]).get(
                                    'Last Register').split(':')[0]
                                if rloc == edgeip:
                                    pass
                                elif rloc == "--":
                                    pass
                                elif rloc in wlcip:
                                    pass
                                else:
                                    success = False
                                    print(
                                        f"LISP Database Analysis: {edgeeid} : In LISP database on {edgename}({edgeip}) CP node: {cp} reports RLOC {rloc} ")
                                    failedeid.append(edgeeid)
                        if success == False:
                            statfail = statfail + 1
                        else:
                            stateid = stateid + 1
    print(f"LISP Database Analysis: Number of EID checked {stateid}, failed {statfail}")
    print(f"LISP Database Analysis: Number of Local EID {localstat}")
    print(f"LISP Database Analysis: Number of Devices checked {statdevs}")
    return failedeid


def CheckEdgeDB():
    statdevs = 0
    statteids = 0
    stateids = 0
    statfail = 0
    lispdb = dnac_core.get(["lisp", "database"])
    if lispdb is None:
        LogIt(
            f"Error: No LISP Database entries found to parse", 1)
        return
    for edgename in lispdb.keys():
        statdevs = statdevs + 1
        edgeip = dnac_core.get(["Global", "Devices", edgename]).get("IP Address")
        for edgeinstance in lispdb.get(edgename):
            if re.match(r"^8", edgeinstance):
                edgeinstanceaf = "ethernet"
            else:
                edgeinstanceaf = "ip"
            for edgeeid in lispdb.get(edgename).get(edgeinstance).keys():
                cpinfo = dnac_core.get(["fabric", edgeinstanceaf, edgeinstance, edgeeid, "Register"])
                statteids = statteids + 1
                if cpinfo is None:
                    if 'skip' not in lispdb.get(edgename).get(edgeinstance).get(edgeeid).get(edgeip).get("Source"):
                        local_macs = dnac_core.get(["lisp", "svi_interface", edgename])
                        local_addr = []
                        for locals in local_macs:
                            for vals in local_macs[locals].keys():
                                local_addr.append(local_macs[locals][vals])
                        if edgeeid.split('/')[0] in local_addr:
                            LogIt(
                                f"Warning: {edgename} {edgeinstance} {edgeeid} {edgeinstanceaf} not present on CP nodes, is local address",
                                10)
                        else:
                            print(
                                f"Database Analysis:{edgename} has {edgeinstance} {edgeeid} {edgeinstanceaf} , not present on CP nodes ")
                            statfail = statfail + 1
                else:
                    if edgeip in cpinfo:
                        LogIt(
                            f"Debug: {edgename} {edgeip} {edgeinstance} {edgeeid} {edgeinstanceaf}  present on CP nodes",
                            99)
                    else:
                        LogIt(
                            f"Debug: {edgename} {edgeip} {edgeinstance} {edgeeid} {edgeinstanceaf} not showing as RLOC on CP nodes but RLOC is {cpinfo}",
                            4)
                        statfail = statfail + 1

    LogIt(f"LISP Database Analysis : Found {statteids} database entries on {statdevs} devices with {statfail} failures",
          0)
    return


def CheckEdgeMC(dnac, dnac_core):
    lispmc = dnac_core.get(["lisp", "map-cache"])
    # print(lispmc)
    statdevs = 0
    statteids = 0
    stateids = 0
    statfail = 0
    if lispmc is None:
        LogIt(
            f"Error: No LISP Map Cache entries found to parse", 1)
        return
    for edgename in lispmc.keys():
        statdevs = statdevs + 1
        edgeip = dnac_core.get(["Global", "Devices", edgename]).get("IP Address")
        for edgeinstance in lispmc.get(edgename):
            if re.match(r"^8", edgeinstance):
                edgeinstanceaf = "ethernet"
            else:
                edgeinstanceaf = "ip"
            for mcentry in lispmc[edgename][edgeinstance].keys():
                statteids = statteids + 1
                if lispmc[edgename][edgeinstance][mcentry]["State"] == "complete":
                    stateids = stateids + 1
                    cpinfo = dnac_core.get(["fabric", edgeinstance, mcentry, "RLOC"])
                    if cpinfo is None:
                        print(
                            f"Map Cache Analysis : Device:{edgename} reporting {edgeinstance}:{mcentry} with RLOC {lispmc[edgename][edgeinstance][mcentry]['RLOC']}" +
                            f" in map-cache entry not present on CP nodes. Expires in {lispmc[edgename][edgeinstance][mcentry]['Expired']} " +
                            f"Uptime: {lispmc[edgename][edgeinstance][mcentry]['Uptime']} ")
                        statfail = statfail + 1
                        pass
                    else:
                        if lispmc[edgename][edgeinstance][mcentry]["RLOC"] in cpinfo:
                            LogIt(
                                f"Debug:Map Cache Analysis : Device:{edgename} reporting {edgeinstance}:{mcentry} with RLOC {lispmc[edgename][edgeinstance][mcentry]['RLOC']} in map cache consistent with CP info RLOC  {cpinfo}",
                                20)
                        else:
                            print(
                                f"Map Cache Analysis : Device:{edgename} reporting {edgeinstance}:{mcentry} with RLOC {lispmc[edgename][edgeinstance][mcentry]['RLOC']} in map cache inconsistent with CP info RLOC  {cpinfo}")
                            statfail = statfail + 1
                elif lispmc[edgename][edgeinstance][mcentry]["State"] == "drop":
                    # print(f"{lispmc[edgename][edgeinstance][mcentry]}   {mcentry}")
                    pass
                elif re.match(r"^Negative", lispmc[edgename][edgeinstance][mcentry]['RLOC']):
                    # print(f"{lispmc[edgename][edgeinstance][mcentry]}   {mcentry}")
                    pass
    LogIt(
        f"Map Cache Analysis : Found {statteids} entries, verified {stateids} entry on {statdevs} devices with {statfail} failures",
        0)
    return


def Stats():
    devices = dnac_core.get(["lisp", "roles"])
    if devices is None:
        print(f"No fabric devices found, not printing stats")
        return

    totaldevices = len(devices.keys())
    totalborder = totalcp = totaledge = totalcpborder = 0
    print(f"Number of Fabric Devices parsed : {totaldevices}")
    for fabricdev in devices.keys():
        if (devices[fabricdev]['CP']) and (devices[fabricdev]['Border']):
            totalcpborder = totalcpborder + 1
        elif devices[fabricdev]['CP']:
            totalcp = totalcp + 1
        elif devices[fabricdev]['Border']:
            totalborder = totalborder + 1
        elif devices[fabricdev]['XTR']:
            totaledge = totaledge + 1
        else:
            print("uh,dunno!" + devices[fabricdev])
    aps = dnac_core.get(["fabric", "ap"])
    if aps is None:
        totalap = 0
    else:
        totalap = len(aps.keys())
    print(f"Number of Border/CP nodes       : {totalcpborder}")
    print(f"Number of CP nodes              : {totalcp}")
    print(f"Number of Border nodes          : {totalborder}")
    print(f"Number of edge nodes            : {totaledge}")
    print(f"Number of Fabric Enabled AP     : {totalap}")
    return


def CheckBFD(dnac, dnac_core):
    bfdb = dnac_core.get(["Global", "bfd"])
    if bfdb is None:
        return
    oksession = 0
    sessions = 0
    noksession = 0
    for device in bfdb.keys():
        for session in bfdb[device].keys():
            uptime = bfdb[device][session]['uptime']
            neigbor = bfdb[device][session]['neighbor']
            interface = bfdb[device][session]['interface']
            state = bfdb[device][session]['State']
            sessions = sessions + 1
            if state.lower() != "up":
                print(
                    f"BFD: Device {device} has BFD session {state} to neighbor {neigbor} on interface {interface}")
                noksession = noksession + 1
            elif re.match(r".*[wd].*", uptime):
                oksession = oksession + 1
            else:
                print(
                    f"BFD: Device {device} has BFD session uptime lower then 1 day ({uptime}) to neighbor {neigbor} on interface {interface}")
                noksession = noksession + 1
    print(f"BFD: Checked {len(bfdb.keys())} , Stable sessions {oksession}, short sessions {noksession} ")


def CheckRLOCreach(dnac, dnac_core):
    # devices = dnac_core.get(["lisp", "roles"])
    # if devices is None:
    #    return
    rlocips = []
    rlocnames = []
    reachfail = reachsuccess = 0
    reachtotal = 0
    devices = {}
    roles = ["EDGENODE", "BORDERNODE"]
    for role in roles:
        devices.update(dnac_core.get(["devices", dnac.fabric, role]))
    for device in devices:
        rlocips.append(device)
        rlocnames.append(devices[device]["name"])
        reachtotal = reachtotal + 1
    iptables = dnac_core.get(["Global", "routing"])
    for lispdevice in rlocnames:
        if lispdevice in iptables.keys():
            iptable = set(iptables[lispdevice]["Global"])
        else:
            print(f"Notice: Routing table of {lispdevice} not gathered, skipping")
            break
        if set(rlocips).issubset(iptable):
            reachsuccess = reachsuccess + 1
            pass
        else:
            reachfail = reachfail + 1
            t = iptable.copy()
            t.intersection_update(set(rlocips))
            print(f"Reachability Analysis: {lispdevice} missing /32 reachability to :  {set(rlocips).difference(t)}")
    print(
        f"Reachability Analysis: Fabric Devices with full (/32) reachabily {reachsuccess}, devices without full reachability {reachfail}," +
        f" not checked {reachtotal - (reachsuccess + reachfail)}")
    CheckBFD(dnac, dnac_core)
    return


def CheckLispSession(dnac, dnac_core):
    edgenodes = dnac_core.get(["devices", dnac.fabric, "EDGENODE"])
    borders = dnac_core.get(["devices", dnac.fabric, "BORDERNODE"])
    cpnodes = dnac_core.get(["devices", dnac.fabric, "MAPSERVER"])
    if edgenodes is None:
        edgenodes = []
    if borders is None:
        borders = []
    if cpnodes is None:
        print("No CP nodes found, exiting")
        return
    devices = []
    cp_nodes = []
    if cpnodes is None:
        print(f"no devices found in fabric {dnac.fabric} exiting")
        exit()
    for cp in cpnodes:
        # print (cpnodes[cp]["name"])
        cp_nodes.append(cpnodes[cp]["name"])
    for border in borders:
        # print(borders[border]["name"])
        devices.append(borders[border]["name"])
    for edge in edgenodes:
        # print(edgenodes[edge]["name"])
        devices.append(edgenodes[edge]["name"])
    esession = fsession = fails = 0
    for device in set(devices):
        sesdbraw = dnac_core.get(['lisp', 'session', device])
        if sesdbraw is not None:
            sesdb = dnac_core.get(['lisp', 'session', device]).keys()
            # print("keys",sesdb)
            for session in cpnodes:
                # print ("cpnodes",session,cpnodes)
                cpname = dnac_core.get(['devices', dnac.fabric, 'MAPSERVER', session])["name"]
                if session not in sesdb:
                    if cpname == device:
                        pass
                    else:
                        fsession = fsession + 1
                        print(f"Session Analysis: CP session to {cpname} not present on {device}")
                else:
                    # print(f"Session Analysis: CP session to {cpname} present on {device}")
                    esession = esession + 1
                    users = dnac_core.get(['lisp', 'session', device]).get(session).get('Users')
                    if dnac_core.get(['lisp', 'session', device]).get(session).get('status') == "Down":
                        if dnac_core.get(['lisp', 'database', device]) is None:
                            print(f"Informational:Session Down on device {device} but no Database entries found")
                        else:
                            print(
                                f"Session Analysis: {device} has LISP session in Down state to {cpname} with Database Entries present")
                            fails = fails + 1
                    elif int(users) < 2:
                        print(
                            f"Session Analysis: {device} has LISP session in Up state to {cpname} but only has {users} Users. ")

    print(
        f"Session Analysis: Checked LISP sessions on {len(set(devices))} nodes towards {len(cpnodes)} CP nodes. Found {esession} sessions, missing {fsession}, failures {fails}")
    return


def CheckAccessTunnels():
    successap = successdevice = faileddevice = 0
    apinfo = dnac_core.get(['Access-Tunnel', 'Summary'])
    if apinfo is None:
        return
    for apdevice in apinfo:
        apcount = len(apinfo[apdevice].keys())
        fapcount = int(dnac_core.get(['Access-Tunnel', 'F0', 'Count', apdevice, 'Number'])['Tunnel Count'])
        rapcount = int(dnac_core.get(['Access-Tunnel', 'R0', 'Count', apdevice, 'Number'])['Tunnel Count'])
        if apcount == fapcount and apcount == rapcount:
            successap = successap + apcount
            successdevice = successdevice + 1
            pass
        else:
            print(
                f"AccessTunnel Analysis: Device {apdevice} has {apcount} Access Tunnels but showns  {rapcount} on R0 and {fapcount} on F0 ")
            faileddevice = faileddevice + 1
    print(
        f"Access Tunnel Analysis: verified {successdevice + faileddevice} nodes with {successap} AccessTunnels verified " +
        f"and {faileddevice} nodes with failures")
    return


def CheckCTS(dnac, dnac_core):
    ctsdevs = ctsfailed = 0
    ctsinfo = dnac_core.get(["Authentication", "CTS", "Devices"])
    if ctsinfo is None:
        return
    for ctsdevice in ctsinfo.keys():
        state = ctsinfo.get(ctsdevice).get("State")
        ctsdevs = ctsdevs + 1
        if state == "COMPLETE":
            pass
        else:
            print(f"CTS Enviroment error: CTS enviroment data not complete on {ctsdevice} state is {state}")
            ctsfailed = ctsfailed + 1
    print(
        f"CTS Analysis: verified CTS on {ctsdevs} nodes, {ctsfailed} failures found")
    return


def checksvi(dnac, dnac_core):
    devices = dnac_core.get(["lisp", "roles"])
    good_svi = bad_svi = 0
    if devices is None:
        return
    edgelist = []
    svilist = []
    for device in devices.keys():
        if devices[device]["Border"] is False and devices[device]["CP"] is False and devices[device]["XTR"] is True:
            svi_info = dnac_core.get(["lisp", "svi_interface", device])
            for svi in svi_info.keys():
                svilist.append(json.dumps(svi_info))
            edgelist.append(device)
    best_svi = collections.Counter(svilist).most_common(1)[0][0]
    for device in edgelist:
        svi_info = dnac_core.get(["lisp", "svi_interface", device])
        if json.dumps(svi_info) == best_svi:
            good_svi = good_svi + 1
        else:
            print(
                f"SVI Analysis: Device {device} has inconsistent Interface Vlan configuration with all other edge devices")
            bad_svi = bad_svi + 1
    print(f"SVI Analysis: Analyzed Interface Vlan config on {bad_svi + good_svi} , found inconsistency on {bad_svi} ")
    return


def check_locals(svi, sifs, device):
    succes = mismatch = notfound = 0
    local_svis = {}
    local_sifs = {}
    for vlans in sifs.keys():
        for IPs in sifs[vlans].keys():
            if sifs[vlans][IPs]["source"] == "L":
                local_sifs[vlans] = {"mac": sifs[vlans][IPs]["mac"], "IP": IPs}
    for svis in svi.keys():
        svi_id = re.findall(r"\d{4}$", svis)[0]
        local_sifs.get(svi_id)
        if local_sifs.get(svi_id) is None:
            print(f"Device-tracking analysis: No Device-Tracking local entry for SVI Vlan{svi_id} on {device}")
            notfound = notfound + 1
        else:
            if local_sifs.get(svi_id)["mac"] == svi[f"Vlan{svi_id}"]["mac"]:
                succes = succes + 1
            else:
                print(
                    f"Device-tracking analysis: Mismatch between Device Tracking and SVI configuration for Vlan{svi_id} on {device}")
                mismatch = mismatch + 1
    return succes, notfound, mismatch


def check_dt(dnac, dnac_core):
    devices = dnac_core.get(["Global", "Device-tracking"]).keys()
    if devices is None:
        return
    succes = mismatch = notfound = 0
    total_succes = total_mismatch = total_notfound = 0
    for device in devices:
        svi_info = dnac_core.get(["lisp", "svi_interface", device])
        dt_info = dnac_core.get(["Global", "Device-tracking", device])
        if svi_info is None or dt_info is None:
            print(f"Device-tracking analysis:missing info to validate SVI to Device-Tracking for node: {device}")
            mismatch = succes = 0
            notfound = 1
        else:
            succes, notfound, mismatch = check_locals(svi_info, dt_info, device)
        total_succes = total_succes + succes
        total_notfound = notfound + total_notfound
        total_mismatch = mismatch + total_mismatch
    print(
        f"Device-tracking analysis: Verified {len(devices)} edge devices with SVI info, {total_succes} success, {total_mismatch} mismatches {total_notfound} info missing")
    return


def check_MTU(dnac, dnac_core):
    mtus = []
    badmtu = goodmtu = 0
    devices = dnac_core.get(["Global", "MTU"]).keys()
    if devices is None:
        return
    for device in devices:
        MTU = dnac_core.get(["Global", "MTU", device])
        if MTU is None:
            print(f"MTU Analysis: System MTU not configured on device {device}")
        else:
            mtus.append(MTU["MTU"])
    best_mtu = collections.Counter(mtus).most_common(1)[0][0]
    if int(best_mtu) < 2000:
        print(f"MTU Analysis: System MTU {best_mtu} used in fabric lower then 2000")
    for device in devices:
        MTU = dnac_core.get(["Global", "MTU", device])
        if MTU is not None:
            if MTU["MTU"] == best_mtu:
                goodmtu = goodmtu + 1
            else:
                badmtu = badmtu + 1
                print(
                    f"MTU Analysis: System MTU on device {device} is {MTU['MTU']} inconsistent with most used MTU {best_mtu}")
    print(
        f"MTU Analysis: System MTU in fabric {best_mtu}, configured on {goodmtu} devices, misconfigured on {badmtu} devices")


def CheckAuth(dnac, dnac_core):
    apipa = noip = okip = total = not_authenticated = 0
    auth_db = dnac_core.get(["Global", "Authentication"])
    if auth_db is None:
        return
    for device in auth_db.keys():
        for interface in auth_db[device].keys():
            for mac in auth_db[device][interface].keys():
                if auth_db[device][interface][mac].get("Status") == "Authorized" \
                        or ((auth_db[device][interface][mac].get("Status") == "Unauthorized") and
                            (re.match(r".*Open", auth_db[device][interface][mac].get("Current Policy")))):
                    total = total + 1
                    ipv4 = auth_db[device][interface][mac].get("IPv4 Address")
                    ipv6 = auth_db[device][interface][mac].get("IPv6 Address")
                    if ipv4 == "Unknown":
                        print(
                            f"Authentication Analysis: client {mac} on {interface} {device} not showing an IPv4 Address")
                        noip = noip + 1
                    elif re.match(r"169.254", ipv4):
                        print(
                            f"Authentication Analysis: client {mac} on {interface} {device} using an APIPA IPv4 Address")
                        apipa = apipa + 1
                    else:
                        okip = okip + 1
                else:
                    not_authenticated = not_authenticated + 1
    print(f"Authentication Analysis: Verified {total} sessions on {len(auth_db.keys())} edges",
          f"found {okip} complete sessions, {noip} without an IP address and {apipa} with an APIPA IP address")
    print(f"Authentication Analysis: Found {not_authenticated} Failed Authentication sessions")

    return


def DatabaseTooFabric(dnac, dnac_core):
    statdevs = 0
    deids = 0
    ieids = 0
    leids = 0
    stateids = 0
    statfail = 0
    lispdb = dnac_core.get(["lisp", "database"])
    print(lispdb)
    if lispdb is None:
        LogIt(
            f"Error: No LISP Database entries found to parse", 1)
        return
    for edgename in lispdb.keys():
        statdevs = statdevs + 1
        edgeip = dnac_core.get(["Global", "Devices", edgename]).get("IP Address")
        for edgeinstance in lispdb.get(edgename):
            if re.match(r"^8", edgeinstance):
                edgeinstanceaf = "ethernet"
            else:
                edgeinstanceaf = "ip"
            for edgeeid in lispdb.get(edgename).get(edgeinstance).keys():
                eidinfo = dnac_core.get(["lisp", "database", edgename, edgeinstance, edgeeid])
                if eidinfo is None:
                    print("Error! what to do , what to do, we have an error. Panic!!!!!!")
                else:
                    eidsource = eidinfo["eSource"]
                    eidtype = eidinfo["eSource"]
                    rloc = eidinfo["RLOC"][0]
                    print(f"{rloc.keys()} {eidtype} {eidsource} {edgeeid}")
                    eidtest = dnac_core.get(["fabric", edgeinstance, edgeeid])
                    local_macs = dnac_core.get(["lisp", "svi_interface", edgename])
                    if local_macs is None:
                        local_macs = []
                    local_addr = []
                    for locals in local_macs:
                        for vals in local_macs[locals].keys():
                            local_addr.append(local_macs[locals][vals])
                    if edgeeid.split('/')[0] in local_addr:
                        eidtest = 'local'
                    if eidtest is None:
                        dnac_core.add(
                            ["fabric", edgeinstance, edgeeid, {"RLOC": rloc, "source": eidsource, "type": eidtype}])
                        if eidtype == "dynamic-eid":
                            deids = deids + 1
                        elif eidtype == "route-import,":
                            ieids = ieids + 1
                        elif re.match(r"^other.*", eidtype):
                            leids = leids + 1
                        stateids = stateids + 1
                    elif eidtest == 'local':
                        pass
                    else:
                        LogIt(
                            f"Debug:LISP Database Analysis: Duplicate Entry {edgeeid} {edgeinstance} on {rloc},likely SVI IP and Mac, to be improved soon!",
                            10)
                        statfail = statfail + 1
    print(f"LISP Database Analysis: Parsed {statfail + stateids} entries with {statfail} failures")
    print(f"LISP Database Analysis: {deids} Dynamic eids, {ieids} imported eids, {leids} local configured eids")
    return


def CPTooFabric(dnac, dnac_core):
    CPnodes = dnac_core.get(["lisp", "site"])
    if CPnodes is None:
        LogIt(
            f"Error: No LISP Control Plane Information found ,parsing results may be inconclusive", 1)
        return
    statecps = 0
    cpfabric = {}
    allid = set()
    for ar in CPnodes.keys():
        areid = CPnodes[ar]
        for nodes in areid.keys():
            node = areid[nodes]
            statecps = statecps + 1
            for lispinst in node.keys():
                instanceinfo = node[lispinst]
                for eidsp in instanceinfo.keys():
                    who = instanceinfo[eidsp]["Last Register"].split(':')[0]
                    state = instanceinfo[eidsp]["Status"]
                    # print (f"{eidsp} {lispinst} {who}")
                    dbinfo = dnac_core.get(["fabric", lispinst, eidsp])
                    if who == "--":
                        pass
                    elif dbinfo is None:
                        if re.match(r"yes", state):
                            LogIt(f"Notice:{eidsp} in {lispinst} not found in analyzed lisp databases, RLOC is {who}",
                                  11)
                        else:
                            LogIt(f"Debug:{eidsp} in {lispinst} not found state is {state},ignoring", 11)
                    else:
                        if who == dbinfo['RLOC']:
                            LogIt(f"Debug:{eidsp} {lispinst} {who} matches RLOC in LISP DB on {dbinfo['RLOC']}", 20)
                        else:
                            print(
                                f"CP Analysis:CP {nodes} reporting for {eidsp}:{lispinst} RLOC {who} but is present on  {dbinfo['RLOC']}")


def CP2Fabric(dnac, dnac_core):
    CPnodes = dnac_core.get(["lisp", "site"])
    if CPnodes is None:
        LogIt(
            f"Error: No LISP Control Plane Information found ,parsing results may be inconclusive", 1)
        return
    statecps = 0
    cpfabric = {}
    allid = set()
    for ar in CPnodes.keys():
        areid = CPnodes[ar]
        for nodes in areid.keys():
            node = areid[nodes]
            statecps = statecps + 1
            for lispinst in node.keys():
                instanceinfo = node[lispinst]
                for eidsp in instanceinfo.keys():
                    who = instanceinfo[eidsp]["Last Register"].split(':')[0]
                    state = instanceinfo[eidsp]["Status"]
                    # print (f"{eidsp} {lispinst} {who}{state}")
                    dnac_core.add(
                        ["fabric", lispinst, eidsp, {"RLOC": who, "state": state}])
    return


def Config2Fabric(dnac, dnac_core):
    devices = dnac_core.get(["lisp", "config"])
    instances = {}
    for device in devices.keys():
        for instance in devices[device]["instances"].keys():
            if instance not in instances:
                instances[instance] = devices[device]["instances"][instance]
    dnac_core.add(
        ["fabric", "configured instances", instances])
    return


def UnderlayMcastAnalysis(dnac, dnac_core, mcastunder):
    devinstances = dnac_core.get(["lisp", "config"])
    mcastdevices = []
    instances = set()
    for mcastgr in mcastunder:
        underlay = dnac_core.get(["Global", "underlay mroute", mcastgr])
        for device in devinstances.keys():
            for instance in devinstances[device]['instances'].keys():
                if devinstances[device]['instances'][instance]['broadcast'] == mcastgr:
                    mcastdevices.append(device)
                    instances.add(instance)
        mcastdevices = list(set(mcastdevices))
        print(f"Checking mcast for Layer 2 flood group(s) {mcastgr} on {len(mcastdevices)} devices")
        for mcastdevice in mcastdevices:
            minfo = dnac_core.get(["Global", "underlay mroute", mcastgr, mcastdevice])
            devip = dnac_core.get(["Global", "Devices", mcastdevice]).get("IP Address")
            if devip in minfo.keys():
                if len(minfo[devip]['egress']) == 0:
                    print(
                        f"Underlay Mcast: Device {mcastdevice} has no Egress interfaces as sender with {devip} to {mcastgr}")
                elif re.match(r".*Registering.*", minfo[devip]['RPF']):
                    print(
                        f"Underlay Mcast: Device {mcastdevice} is showing {minfo[devip]['RPF']} for source {devip}(self) to {mcastgr}")
            else:
                for instance in instances:
                    vlan = dnac_core.get(["lisp", "config", mcastdevice, "instances", instance]).get("value")
                    if vlan is not None:
                        mactable = devinstances = dnac_core.get(["Global", "mac", mcastdevice, vlan])
                        nummacs = 0
                        for mac in mactable:
                            if re.match(r"^Vl.*", mactable[mac].get("Int")):
                                pass
                            else:
                                nummacs = nummacs + 1
                print(
                    f"Underlay Mcast: Device {mcastdevice} has no Mroute with itself as sender({devip}) to {mcastgr} , "
                    f"{nummacs} endpoints present in IP pools with flooding")
    return


def BuildFabric(dnac, dnac_core):
    #   findip()
    print("*" * 80)
    DatabaseTooFabric(dnac, dnac_core)
    print("*" * 80)
    CPTooFabric(dnac, dnac_core)
    return


def FindMac(dnac, dnac_core, inp):
    Location = ""
    Instance = ""

    return Location, Instance


def ListEndStationsDevice(dnac, dnac_core):
    instance = input("What instance should be listed(* for all):")
    fabric = dnac_core.get(["fabric"])
    for instances in fabric.keys():
        if instance in instances or instance == "*":
            for host in fabric[instances].keys():
                print(f"{instances} {host} {fabric[instances]}")
    return


def digger_commands(dnac, dnac_core, debug_core, hostname, dataset):
    digfile = open("dig_commands.txt", "r")
    edgedig_cmd = []
    borderdig_cmd = []
    cpdig_cmd = []
    wlan_cmd = []
    digcommands = digfile.readlines()
    digfile.close()
    cpid = []
    borderid = []
    if dnac_core.get(["devices", dnac.fabric, "MAPSERVER"]) is not None:
        cpip = (dnac_core.get(["devices", dnac.fabric, "MAPSERVER"]))
        for device in cpip.keys():
            cpid.append(cpip[device]["id"])
    if dnac_core.get(["devices", dnac.fabric, "BORDERNODE"]) is not None:
        borderip = (dnac_core.get(["devices", dnac.fabric, "BORDERNODE"]))
        for device in borderip.keys():
            borderid.append(borderip[device]["id"])
    for line in digcommands:
        splitline = line.split(":")
        cmdsplit = splitline[-1].strip()
        cmdbuild = []
        allparsed = True
        for cmdpart in cmdsplit.split(" "):
            if re.match(r"^\$", cmdpart):
                if cmdpart.strip("$") in dataset.keys():
                    cmdpart = dataset[cmdpart.strip("$")]
                else:
                    # print(f"f{cmdpart} not found, skipping command")
                    # dig_cmd_resolve() function to be implemented
                    allparsed = False
            cmdbuild.append(cmdpart)
        if allparsed is True:
            if re.match(r".*EDGE", splitline[1]):
                edgedig_cmd.append(" ".join(cmdbuild))
            elif re.match(r".*CP", splitline[1]):
                cpdig_cmd.append(" ".join(cmdbuild))
            elif re.match(r".*BORDER", splitline[1]):
                borderdig_cmd.append(" ".join(cmdbuild))
            elif re.match(r".*WLC", splitline[1]):
                wlan_cmd.append(" ".join(cmdbuild))

    if len(edgedig_cmd) != 0:
        # executing Edge commands (if any)
        rlocuid = dnac.topo['hostnames'][hostname]
        ret = dnac.command_run(edgedig_cmd,
                               [rlocuid])
        for responses in ret:
            print(responses["output"])
            ParseCommands.ParseSingleDev(responses["output"], responses["host"], debug_core)

    if len(borderdig_cmd) != 0:
        # executing Border commands (if any)
        ret = dnac.command_run(borderdig_cmd,
                               borderid)
        for responses in ret:
            print(responses["output"])
            ParseCommands.ParseSingleDev(responses["output"], responses["host"], debug_core)
    if len(cpdig_cmd) != 0:
        # executing CP commands (if any)
        ret = dnac.command_run(cpdig_cmd,
                               cpid)
        for responses in ret:
            print(responses["output"])
            ParseCommands.ParseSingleDev(responses["output"], responses["host"], debug_core)
    if len(cpdig_cmd) != 0:
        # executing CP commands (if any)
        if dnac.wlc.get('uuid') is not None:
            ret = dnac.command_run(wlan_cmd,
                                   [dnac.wlc.get('uuid')])
            for responses in ret:
                print(responses["output"])
                ParseCommands.ParseSingleDev(responses["output"], responses["host"], debug_core)
    return


def mac2ip(dttable, vlan, macaddress):
    if vlan in dttable.keys():
        for ip in dttable[vlan].keys():
            if dttable[vlan][ip]['mac'] == macaddress:
                return ip
    return None


def Device2Mac(dnac, dnac_core, debug_core, inp):
    print(f"Device {inp} present in Fabric, gathering information")
    # ListEndStationsDevice(dnac,dnac_core)
    uuid = dnac.topo['hostnames'][inp]
    ret = dnac.command_run(["show device-tracking database", "show mac add"], [uuid])
    for responses in ret:
        ParseCommands.ParseSingleDev(responses["output"], responses["host"], debug_core)
    mactable = debug_core.get(["Global", "mac", inp])
    dttable = debug_core.get(["Global", "Device-tracking", inp])
    i = 0
    entries = {}
    for vlan in mactable.keys():
        for macaddress in mactable[vlan].keys():
            if re.match(r".*/.*", mactable[vlan][macaddress]['Int']) or re.match(r".*Ac*",
                                                                                 mactable[vlan][macaddress]['Int']):
                i = i + 1
                ip = mac2ip(dttable, vlan, macaddress)
                inter = mactable[vlan][macaddress]['Int']
                vn = dnac_core.get(["lisp", "svi_interface", inp, "Vlan" + vlan])
                if vn is not None:
                    vrf = vn.get("vrf")
                else:
                    vrf = "Unknown"
                print(f"{i}: Vlan:{vlan}  Mac:{macaddress} IP:{ip} Interface :{inter} VRF/VN:{vrf}")
                entries[str(i)] = {'vlan': vlan, 'macaddress': macaddress, 'interface': inter}
                l2dat = dnac_core.get(["lisp", "config", inp, "vlan_vrf", vlan])
                if ip is not None:
                    entries[str(i)]["ipv4"] = ip
                    entries[str(i)]["ipv4tot"] = ip + '\32'
                    if re.match(r"Global Routing.*", vrf):
                        vrf = ""
                    else:
                        vrf = f"vrf {vrf}"
                    entries[str(i)]["vrf"] = vrf
                    l3info = dnac_core.get(["lisp", "config", inp, "vlan_vrf", vrf])
                    if l3info is not None:
                        entries[str(i)]["l3inst"] = l3info['instance']
                if l2dat is not None:
                    entries[str(i)]["l2inst"] = l2dat['instance']
    if len(entries.keys()) == 0:
        print(f"No Endpoints found on {inp}")
        return
    while len(entries.keys()) > 0:
        choice = input("What entry should be used:")
        if choice in entries.keys():
            destip = input("(Optional)Destination IP: ")
            if re.match(r"\d{0,3}\.\d{0,3}\.\d{0,3}.\.\d{0,3}.", destip):
                entries[choice]["ipdest"] = destip
            destmac = input("(Optional) Destination Mac: ")
            if re.match(r".{4}\..{4}\..{4}", destmac):
                entries[choice]["macdest"] = destmac
            digger_commands(dnac, dnac_core, debug_core, inp, entries[choice])
            return
        elif choice == "q":
            return

    return


def Digger(dnac, dnac_core):
    debug_core = AnalysisCore.Analysis_Core()
    while True:
        inp = input("Please enter Hostname of Fabric Device or list: ")
        if inp == "quit" or inp == "q":
            return
        elif re.match(r"\d{0,3}\.\d{0,3}\.\d{0,3}.\.\d{0,3}.", inp):
            print(f"IP {inp}")
        elif re.match(r".{4}\..{4}\..{4}", inp):
            Host, Instance = FindMac(dnac, dnac_core, inp)
        elif dnac_core.get(["Global", "Devices", inp]) is not None:
            Device2Mac(dnac, dnac_core, debug_core, inp)
        elif inp == "list":
            for devs in dnac_core.get(["Global", "Devices"]):
                print(devs)
    return
