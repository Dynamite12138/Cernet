#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import os
import shutil
import UNIT


class Template:
    public_1 = ""
    public_1 += "[V200R003C00]\n"

    public_2 = "#\n"
    public_2 += " snmp-agent local-engineid 800007DB03000000000000\n"
    public_2 += " snmp-agent\n"
    public_2 += "#\n"
    public_2 += " clock timezone China-Standard-Time minus 08:00:00\n"
    public_2 += "#\n"
    public_2 += "portal local-server load portalpage.zip\n"
    public_2 += "#\n"
    public_2 += " drop illegal-mac alarm\n"
    public_2 += "#\n"
    public_2 += " set cpu-usage threshold 80 restore 75\n"
    public_2 += "#\n"

    public_3 = "#\n"
    public_3 += "aaa\n"
    public_3 += " authentication-scheme default\n"
    public_3 += " authorization-scheme default\n"
    public_3 += " accounting-scheme default\n"
    public_3 += " domain default\n"
    public_3 += " domain default_admin\n"
    public_3 += "#\n"

    pubilc_end = "#\n"
    pubilc_end += "user-interface con 0\n"
    pubilc_end += " authentication-mode password\n"
    pubilc_end += "user-interface vty 0 4\n"
    pubilc_end += "user-interface vty 16 20\n"
    pubilc_end += "#\n"
    pubilc_end += "return\n"

    def __init__(self, topo, device_node):
        self.topo = topo
        self.configs = {}
        self.num = 0
        self.device_node = device_node  # 设备节点

    def gen_configs(self):
        for node, ner_node in self.topo.adj.items():
            if node in self.device_node:
                int_to_aclnum = {}
                config = ''
                config += Template.public_1
                config += "#\n"
                config += "sysname %s\n" %(node)
                config += "#\n"
                config += Template.public_2
                vlan_num_str = ''
                if 'vlan' in self.topo.nodes[node]:
                    for vlan in self.topo.nodes[node]['vlan']:
                        vlan_num_str += str(vlan)
                        vlan_num_str += ' '
                    config += 'vlan batch %s\n' % (vlan_num_str)

                config += Template.public_3

                if 'vlanif' in self.topo.nodes[node]:
                    for key in self.topo.nodes[node]['vlanif']:
                        config += "interface Vlanif%s\n" % (key)
                        config += "#\n"

                for ner in ner_node:
                    if ner in self.device_node:
                        config += "#\n"
                        config += "interface %s\n" % (ner_node[ner]['int'])
                        config += " undo shutdown\n"
                        if 'vlan' in ner_node[ner]:
                            config += " portswitch\n"
                            config += " port link-type trunk\n"
                            vlan_n = ""
                            for vlan in ner_node[ner]['vlan']:
                                vlan_n += str(vlan)
                                vlan_n += ' '
                            config += " port trunk allow-pass vlan %s\n" % (vlan_n)
                    else:
                        config += "#\n"
                        config += "interface %s\n" % (ner_node[ner]['int'])
                        config += " undo shutdown\n"
                        if 'vlan' in ner_node[ner]:
                            config += " portswitch\n"
                            config += " port link-type access\n"
                            vlan_n = ""
                            for vlan in ner_node[ner]['vlan']:
                                vlan_n += str(vlan)
                                vlan_n += ' '
                            config += " port default vlan %s\n" % (vlan_n)
                    if ner_node[ner]['int'] in int_to_aclnum:
                        config += " traffic-filter inbound acl %s\n" % (int_to_aclnum[ner_node[ner]['int']])

                config += Template.pubilc_end
                self.configs[node] = config


def config_output(topo, dev_node, out_folder):
    template = Template(topo, dev_node)
    template.gen_configs()
    configs_folder = os.path.join(out_folder, 'configs')
    if os.path.exists(configs_folder):
        shutil.rmtree(configs_folder)
    os.makedirs(configs_folder)
    for node in template.configs:
        cfg = template.configs[node]
        cfg_file = os.path.join(configs_folder, "%s.cfg" % node)
        with open(cfg_file, 'w') as fhandle:
            fhandle.write(cfg)




















