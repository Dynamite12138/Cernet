#!/usr/bin/env python 
# -*- coding:utf-8 -*-
"""
L2网络综合模块（VLAN）
输入：
用户信息集合
网关集合
参数拓扑（连接关系）
输出：
补全用户信息集合
拓扑参数集合（需调用topo模块相应函数读取）
"""
import networkx as nx
from sklearn.cluster import KMeans
import copy


vlan_pool = [True for i in range(4096)]
vlan_sum = 0


def get_a_vlan_number():
    for i in range(2, 4095):
        if vlan_pool[i]:
            vlan_pool[i] = False
            return i


def use_one_vlan(vlan):
    vlan_pool[vlan] = False


def get_user_userG(user_info):
    return user_info.userG


class Completion:

    class VlanTree:
        def __init__(self):
            self.user_set = []
            self.access_device_set = set()
            self.vlan_number = -1
            self.spanning_tree = None
            self.userG = ''
            self.vlanif_device = ''

        def find_user_by_name(self, name):
            """
            通过名字找到对应用户的信息
            :param name:
            :return:
            """
            for i in range(len(self.user_set)):
                if self.user_set[i].name == name:
                    return copy.deepcopy(self.user_set[i])

        def insert_user(self, user_info):
            """
            向vlan中添加用户
            :param user_info:
            :return:
            """
            self.user_set.append(user_info)
            self.access_device_set.add(user_info.access)

        def set_vlan_number(self, num):
            """
            设置vlan的vlan编号
            :param num:
            :return:
            """
            self.vlan_number = num
            for i in range(len(self.user_set)):
                self.user_set[i].vlan = num

    def __init__(self, input_user_set, input_topo, input_gateway):
        """
        把输入备份到当前部分
        """
        self.get_data_rate_by_interface = {
            "10GE": "10 Gbps",
            "GE": "1 Gbps"
        }
        self.user_set = copy.deepcopy(input_user_set)
        self.topo = copy.deepcopy(input_topo).to_undirected()
        self.completed_user_set = []
        self.partition_user_set = []
        self.STP_cost = {"4 Mbps": 250,
                         "10 Mbps": 100,
                         "16 Mbps": 62,
                         "100 Mbps": 19,
                         "1 Gbps": 4,
                         "10 Gbps": 2}
        self.interface_date_rate_compare_list = {  # 这里的端口类型需要更改
            "10GE": 100,
            "GE": 10
        }
        self.alpha = 0.5
        self.beta = 0.35
        self.b_plus_max = 300.0
        self.vlan_limit = 500
        self.g_path_set_predecessors = {}
        self.g_path_set_distances = {}
        self.total_vlan_dir = {}
        self.gateway = copy.deepcopy(input_gateway)
        self.original_topo = input_topo

    def change_to_directed_graph(self):
        ans_topo = copy.deepcopy(self.original_topo)  # directed
        ans_topo.add_nodes_from(self.topo.nodes.data())
        for source, target, edge_dir in self.topo.edges.data():
            if 'vlan' in edge_dir:
                ans_topo.add_edge(source, target, vlan=edge_dir['vlan'])
                ans_topo.add_edge(target, source, vlan=edge_dir['vlan'])
        return ans_topo

    def make_user_graph(self, v):
        """
        根据vlan v中的所有用户，以及全局的所有最短路径，生成只有用户的一个图
        :param v: VlanTree的一个实例
        :return: 一个无向图
        """
        graph = nx.Graph()
        for user in v.user_set:
            graph.add_node(user.name)
        for source in v.user_set:
            for target in v.user_set:
                if source != target:
                    graph.add_edge(source.name, target.name, weight=self.g_path_set_distances[source.name][target.name])
        return graph

    def complete(self):
        """
        完成整个L2代码的调用函数
        :return:
        """
        for user_info in self.user_set.values():
            user_info.access = [access for access in nx.all_neighbors(self.topo, user_info.name)][0]
            self.mark_access_device(user_info.access)
            if user_info.vlan != 0:
                self.completed_user_set.append(user_info)
            else:
                self.partition_user_set.append(user_info)
        # 对补全完的用户进行分堆
        for user_info in self.completed_user_set:
            if user_info.userG not in self.total_vlan_dir:
                self.total_vlan_dir[user_info.userG] = {}
            if user_info.vlan not in self.total_vlan_dir[user_info.userG]:
                now_vlan_tree = Completion.VlanTree()
                now_vlan_tree.vlan_number = user_info.vlan
                now_vlan_tree.userG = user_info.userG
                self.total_vlan_dir[user_info.userG][user_info.vlan] = now_vlan_tree
            self.total_vlan_dir[user_info.userG][user_info.vlan].insert_user(user_info)
        for userG in self.total_vlan_dir:
            self.init_topo_edge()
            self.g_path_set_predecessors, self.g_path_set_distances \
                = nx.floyd_warshall_predecessor_and_distance(self.topo, weight='current_cost')
            for vlan in self.total_vlan_dir[userG]:
                self.total_vlan_dir[userG][vlan].spanning_tree, self.total_vlan_dir[userG][vlan].vlanif_device, _ \
                    = self.calculate_spanning_tree(self.total_vlan_dir[userG][vlan])
        if len(self.partition_user_set) != 0:
            # 对剩余user进行划分
            self.partition()
        # 对拓扑中的属性进行补充
        self.complete_topo_info()

        self.print_user_info()

    def delete_node_from_graph(self):
        for user_info in self.completed_user_set:
            self.topo.remove_node(user_info.name)

    def sort_partition_user_set(self):
        self.partition_user_set.sort(key=get_user_userG)

    def get_edge_basic_cost(self, edge):
        node_0_type = self.topo.nodes[edge[0]]['Int_Type']
        node_1_type = self.topo.nodes[edge[1]]['Int_Type']
        if self.interface_date_rate_compare_list[node_0_type] \
                < self.interface_date_rate_compare_list[node_1_type]:
            return self.STP_cost[self.get_data_rate_by_interface[node_0_type]]
        else:
            return self.STP_cost[self.get_data_rate_by_interface[node_1_type]]

    def init_topo_edge(self):
        for edge in list(self.topo.edges()):
            if self.topo.nodes[edge[0]]['model'] != 'user' and self.topo.nodes[edge[1]]['model'] != 'user':
                basic_cost = self.get_edge_basic_cost(edge)
                self.topo.add_edge(edge[0], edge[1],
                                   pi=0, current_cost=basic_cost, basic_cost=basic_cost)

    def partition_one_user_userG(self, now_userG_user_set, now_userG):
        """
        对一个用户组的所有成员分配vlan
        :param now_userG:
        :param now_userG_user_set: 一个用户组的所有成员的列表
        :return: vlan_set: 一个列表，包含所有划分后的若干个VlanTree
        """
        self.init_topo_edge()
        if now_userG in self.total_vlan_dir:
            if len(self.total_vlan_dir[now_userG]) > 0:
                for vlan in self.total_vlan_dir[now_userG]:
                    self.increase_current_cost(self.total_vlan_dir[now_userG][vlan])
        cat_vlan_set = []
        v = Completion.VlanTree()
        v.user_set = now_userG_user_set
        v.userG = now_userG
        v.access_device_set = {user_info.access for user_info in now_userG_user_set}  # 建立的是一个集合
        self.g_path_set_predecessors, self.g_path_set_distances \
            = nx.floyd_warshall_predecessor_and_distance(self.topo, weight='current_cost')
        v.spanning_tree, v.vlanif_device, b_plus = self.calculate_spanning_tree(v)
        if b_plus < self.alpha * self.b_plus_max:
            v.set_vlan_number(get_a_vlan_number())
            v.userG = now_userG
            cat_vlan_set = [v]
        elif self.alpha * self.b_plus_max <= b_plus < self.b_plus_max \
                and b_plus <= ((self.alpha + (1 - self.alpha) * vlan_sum / self.vlan_limit) * self.b_plus_max):
            v.set_vlan_number(get_a_vlan_number())
            v.userG = now_userG
            cat_vlan_set = [v]
        else:
            if len(v.user_set) == 1:
                v.set_vlan_number(get_a_vlan_number())
                v.userG = now_userG
                cat_vlan_set = [v]
            else:
                cat_vlan_set.extend(self.partition_by_k_means(v))
            # 论文里这步有一个合并集合的操作，将任意两个集合合并，如果满足流量条件就合并，如果不满足就不合并。
            # 目的可能是减少vlan，将一些小的vlan合并，这里现在没有写。
        for v in cat_vlan_set:
            v.userG = now_userG
            if now_userG not in self.total_vlan_dir:
                self.total_vlan_dir[now_userG] = {}
            self.total_vlan_dir[now_userG][v.vlan_number] = v
        return cat_vlan_set

    def calculate_spanning_tree(self, input_v):
        """
        计算vlan(input_v)的生成树以及对应的广播流量
        :param input_v:一个VlanTree的实例
        :return: span_tree:一个图，是输入input_v的生成树
                 b_plus:生成树的广播流量
        """
        v_span_tree = None
        min_cost = float('inf')
        a = 2.12
        user_num = len(input_v.user_set)
        vlanif_device = ''
        for core_device in self.get_vlanif_device_by_userG(input_v.user_set[0].userG):
            graph = nx.Graph()
            tmp_cost = 0
            for access_device in input_v.access_device_set:
                path = nx.reconstruct_path(access_device, core_device, self.g_path_set_predecessors)
                for i in range(len(path) - 1):
                    graph.add_edge(path[i], path[i+1], weight=self.topo[path[i]][path[i+1]]['current_cost'])
            for (_, _, link) in graph.edges.data('weight'):
                tmp_cost += link
            if tmp_cost < min_cost:
                v_span_tree = graph
                min_cost = tmp_cost
                vlanif_device = core_device
        return v_span_tree, vlanif_device, min_cost * user_num * a

    def partition_by_k_means(self, input_v):
        """
        根据KMeans算法对vlan(input_v)进行分割，分成若干个
        :param input_v:待分割的VlanTree实例
        :return: vlan_set:一个列表，列表中的元素为VlanTree的实例，是对输入vlan进行分割后的结果，但是返回的VlanTree里面只填充的用户节点信息
        """
        flag = True
        k = 2
        vlan_set = []
        temp_vlan_1_set = [copy.deepcopy(input_v)]
        temp_vlan_2_set = []
        temp_vlan_3_set = []
        while flag:
            flag = False
            for v in temp_vlan_1_set:
                temp_vlan_3_set.extend(self.k_means(v, k))
                for v_prime in temp_vlan_3_set:
                    v_prime.spanning_tree, v_prime.vlanif_device, b_plus_prime = self.calculate_spanning_tree(v_prime)
                    if b_plus_prime < \
                            min(self.b_plus_max,
                                (self.alpha + (1-self.alpha) * vlan_sum / self.vlan_limit) * self.b_plus_max):
                        v_prime.set_vlan_number(get_a_vlan_number())
                        vlan_set.append(v_prime)
                        self.increase_current_cost(v_prime)
                        self.g_path_set_predecessors, self.g_path_set_distances \
                            = nx.floyd_warshall_predecessor_and_distance(self.topo, weight='current_cost')
                    else:
                        flag = True
                        temp_vlan_2_set.append(v_prime)
                temp_vlan_3_set = []
            temp_vlan_1_set = temp_vlan_2_set
            temp_vlan_2_set = []
        return vlan_set

    def k_means(self, v, k):
        """
        KMeans算法，将vlan v分为k个部分
        :param v:
        :param k:
        :return: partition：一个列表，包含k个VlanTree实例
        """
        vlan_graph = self.make_user_graph(v)
        matrix = nx.adjacency_matrix(vlan_graph)  # 注：adjacency_matrix中有参数node_list，可以指定node的顺序，默认为G.nodes()的顺序
        kmeans = KMeans(n_clusters=k).fit(matrix)
        labels = kmeans.labels_.tolist()
        nodes = list(vlan_graph.nodes())
        partition = [Completion.VlanTree() for _ in range(k)]
        for i in range(k):
            for j in range(len(nodes)):
                if labels[j] == i:
                    partition[i].insert_user(v.find_user_by_name(nodes[j]))
        return partition

    def partition(self):
        """
        划分剩余的用户
        :return:
        """
        # self.delete_code_from_graph()
        self.sort_partition_user_set()
        now_userG = self.partition_user_set[0].userG
        now_userG_user_set = []
        for i in range(len(self.partition_user_set)):
            if now_userG == self.partition_user_set[i].userG:
                now_userG_user_set.append(self.partition_user_set[i])
            else:
                self.partition_one_user_userG(now_userG_user_set, now_userG)
                now_userG = self.partition_user_set[i].userG
                now_userG_user_set = [self.partition_user_set[i]]
        self.partition_one_user_userG(now_userG_user_set, now_userG)

    def get_vlanif_device_by_userG(self, userG):
        """
        这个部分还没写，需要DSL的信息
        :param userG:
        :return:
        """
        if userG in self.gateway:
            return self.gateway[userG]
        else:
            return self.gateway['gateway']

    def increase_current_cost(self, v):
        """
        增加vlan v路径上的current_cost值
        :param v: 一个VlanTree实例
        :return: 无
        """
        for (source, target) in v.spanning_tree.edges():
            self.topo[source][target]['pi'] += 1
            self.topo[source][target]['current_cost'] \
                = (1 + self.topo[source][target]['pi'] * self.beta) * self.topo[source][target]['basic_cost']

    def complete_topo_info(self):
        for userG in self.total_vlan_dir:
            for vlan in self.total_vlan_dir[userG]:
                spanning_tree = self.total_vlan_dir[userG][vlan].spanning_tree
                if 'vlanif' not in self.topo.nodes[self.total_vlan_dir[userG][vlan].vlanif_device]:
                    self.topo.nodes[self.total_vlan_dir[userG][vlan].vlanif_device]['vlanif'] = {}
                self.topo.nodes[self.total_vlan_dir[userG][vlan].vlanif_device]['vlanif'].update(
                    {self.total_vlan_dir[userG][vlan].vlan_number: 0})
                for node in spanning_tree.nodes():
                    if 'vlan' not in self.topo.nodes[node]:
                        self.topo.nodes[node]['vlan'] = []
                    self.topo.nodes[node]['vlan'].append(vlan)
                for edge in spanning_tree.edges():
                    if 'vlan' not in self.topo[edge[0]][edge[1]]:
                        self.topo[edge[0]][edge[1]]['vlan'] = []
                    self.topo[edge[0]][edge[1]]['vlan'].append(vlan)
                for user_info in self.total_vlan_dir[userG][vlan].user_set:
                    self.topo.nodes[user_info.name]['vlan'] = vlan
                    if 'vlan' not in self.topo[user_info.name][user_info.access]:
                        self.topo[user_info.name][user_info.access]['vlan'] = []
                    self.topo[user_info.name][user_info.access]['vlan'].append(vlan)

    def mark_access_device(self, device_name):
        self.topo.nodes[device_name]['layer'] = 'access'

    def print_user_info(self):
        for (node, node_dir) in self.topo.nodes().data():
            if node_dir['model'] == 'user':
                print("name: " + node + "  vlan: " + str(node_dir['vlan']))
