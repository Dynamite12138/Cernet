#!/usr/bin/env python 
# -*- coding:utf-8 -*-
"""
使用PLY编写的词法与语法
输入：策略文件*2
输出：
用户信息集合
隔离用户集合
网关集合
ACL偏好集合
"""
import IPy
import regex
from UNIT import User

# read files
with open(r'./policy_admin.txt', 'r') as file1:
    admin_policy = file1.read()
with open(r'./policy_user.txt', 'r') as file2:
    user_policy = file2.read()


# get gateway dict
def gateway_set(a):
    gateway_dict = {'gateway': []}
    # global gateway
    n = regex.findall(r"-gateway (.*)", a)
    gateway_id = regex.findall(r'[a-zA-Z_][a-zA-Z_0-9]*', str(n))
    for i in gateway_id:
        gateway_dict.setdefault('gateway').append(i)
    # group gateway
    m_key = regex.findall(r"-(.*) gateway", a)
    m_value = regex.findall(r' gateway (.*)', a)
    i = 0
    while i < len(m_key):
        m_true_value = regex.findall(r'[a-zA-Z_][a-zA-Z_0-9]*', str(m_value[i]))
        new = {m_key[i]: []}
        gateway_dict.update(new)
        for j in m_true_value:
            gateway_dict.setdefault(m_key[i]).append(j)
        i += 1
    return gateway_dict


GLOBAL_num = 1


# get user info
# 将用户对象封装在一个字典内，key为用户名，value为对象
def user_info(a):
    q = regex.findall(r'define (.*)}', a)
    users = {}
    users_temp = []
    flag = 1
    global GLOBAL_num
    for i in range(len(q)):
        group_id = regex.findall(r'([a-zA-Z_][a-zA-Z_0-9]*) {', q[i])
        user_info_list = regex.findall(r'user-.*?;', q[i])
        for j in range(len(user_info_list)):
            user_name = regex.findall(r'user-([a-zA-Z_][a-zA-Z_0-9\-]*)', user_info_list[j])
            users_temp.append(user_name[0])
            # 判断用户名是否重复
            if len(users_temp) == len(set(users_temp)):
                # user_ip = regex.findall(
                #     r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/\d+|\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                #     user_info_list[j])

                user_vlan = regex.findall(r'vlan-(\d+)', user_info_list[j])
                user_num = regex.findall(r'num-(\d+)', user_info_list[j])
                username = user_name[0]
                users[username] = User()
                users[username].name = user_name[0]
                users[username].userG = group_id[0]
                # if user_ip:
                #     if r'/' in user_ip[0]:
                #         user_ip1 = regex.findall(
                #             r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                #             user_ip[0])
                #         # print(user_ip1)
                #         user_ip2 = regex.findall(r'/(\d+)', user_ip[0])
                #         # print(int(user_ip2[0]))
                #         users[username].ip = IP(IPy.IP(user_ip1[0]), int(user_ip2[0]))
                #     else:
                #         users[username].ip = IP(IPy.IP(user_ip[0]), 24)
                #         # if user_num:
                #         #     GLOBAL_num = -1  # 出现定义错误
                #         users[username].num = 1
                if user_vlan:
                    users[username].vlan = int(user_vlan[0])
                # if user_num:
                #     if user_ip:
                #         if r'/' not in user_ip[0]:
                #             GLOBAL_num = -1
                #             users[username].num = 1
                #     users[username].num = int(user_num[0])
            else:
                flag = 0
                break
        else:
            continue
        break

    if flag == 0:
        return None
    elif flag == 1:
        return users
