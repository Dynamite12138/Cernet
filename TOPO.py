#!/usr/bin/env python 
# -*- coding:utf-8 -*-
"""
参数拓扑模块：
拓扑文件使用json格式
节点属性：名称，型号
边：双向，源节点，目的节点，接口
以networkx为基础构建有向图。为节点与边设置属性
属性读取

拓扑文件读取
设备性能文件读取及与topo对应（解耦）
"""
import networkx as nx
import json

class Topo:
    """
    参数拓扑数据结构
    """
    def __init__(self):
        self.topo = nx.DiGraph()

    def getFromJson(self, json_topo):
        """
        读取json格式的拓扑文件，构建拓扑
        :param json_topo:
        :return: self.topo
        """

        edge_num = 1
        with open(json_topo, 'r', encoding= 'utf-8') as file:
            data = json.load(file)
            for element in data:
                if 'nodes' in element:
                    for node in element['nodes']:
                        if node['model'] != 'user':
                            self.topo.add_node(node['name'], model = node['model'],Int_Type = node['Int_Type'])
                        # print(self.topo.nodes[node['name']]['model'])
                        else:
                            self.topo.add_node(node['name'], model=node['model'])
                else:
                    for edge in element['edges']:
                        self.topo.add_edge(edge['src'],edge['dst'],int=edge['int'],weight=1) #边的权重为接口的cost值，都设为1
                        edge_num += 1
        return self.topo



def findFromModel(dev_per,model, key_work):
    """
    根据型号与关键字查找对应型号与关键字的参数
    :param model, key_work:
    :return: 关键字的参数
    """
    with open(dev_per, 'r') as file:
        data = json.load(file)
        for device in data:
            Model = device.keys()
            for key in Model:
                if model == key:
                    if key_work == "L3":
                        return device[key]['L3']
                    elif key_work == "Int_N":
                        return device[key]['Int_N']
                    else:
                        print("The input parameter of key_work is wrong.")


def getDeviceNodes(G):
    """
    网络拓扑中除去用户节点的设备节点
    :param G:
    :return: list，网络拓扑中的设备节点
    """

    deviceNodes = []
    nodes = list(G.nodes)
    for node in nodes:
        if G.nodes[node]['model'] != 'user':
            deviceNodes.append(node)

    return deviceNodes



