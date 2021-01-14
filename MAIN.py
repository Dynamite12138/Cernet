#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from LY import *
from TOPO import Topo
import TOPO
import L2
import TEMPLATE


with open(r'./policy_admin.txt', 'r') as file1:
    admin_policy = file1.read()
with open(r'./policy_user.txt', 'r') as file2:
    user_policy = file2.read()


gateway_set = gateway_set(admin_policy)  # 网关集合
user_info = user_info(user_policy)  # 用户信息集合
t = Topo()
Graph = t.getFromJson('./TOPO.json')
dev_per = './DEVPER.json'

deviceNodes = TOPO.getDeviceNodes(Graph)  # 拓扑中的设备节点

if user_info is None:
    print("重复定义了用户，请检查用户策略文件")
else:
    completion = L2.Completion(user_info, Graph, gateway_set)  # Completion类的实例
    completion.complete()  # 进行计算
    completed_info_graph = completion.change_to_directed_graph()
    output_path = './ConfigurationFiles'
    TEMPLATE.config_output(completed_info_graph, deviceNodes, output_path)  # 输出配置文件
