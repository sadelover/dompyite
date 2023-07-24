# -*- coding: utf-8 -*-
import subprocess
import re
import requests
import json
from siteinterface.commonUtils import find_ip_list, is_ip, get_network_segment


# 为路由节点命名
def name_router_nodes(nodeList):
    for idx, node in enumerate(nodeList):
        node["networkName"] = "网络{n}".format(n=idx+1)

# 为路由和服务器节点赋值deviceName
def assign_name_for_router_nodes(nodeList):
    routerIdx = 0
    for node in nodeList:
        if node["device"] == "router":
            if node["remark"] == "可能为外网":
                deviceName = "路由器{n}(可能为外网)\n{ip}".format(n=routerIdx+1, ip=node.get("ip", ""))
            elif node.get("legal", True) == False:
                deviceName = "路由器{n}\n(非自控系统服务器内网路由)\n{ip}".format(n=routerIdx + 1, ip=node.get("ip", ""))
            else:
                deviceName = "路由器{n}\n{ip}".format(n=routerIdx + 1, ip=node.get("ip", ""))
            node["name"] = deviceName
            routerIdx += 1


# 对所有网络节点按IP排序
def sort_node_via_ip(nodeList):
    for i in range(len(nodeList)):
        for j in range(len(nodeList)-i-1):
            if not is_ip(nodeList[j]["ip"]) and is_ip(nodeList[j+1]["ip"]):
                nodeList[j], nodeList[j + 1] = nodeList[j + 1], nodeList[j]
            elif is_ip(nodeList[j]["ip"]) and is_ip(nodeList[j+1]["ip"]):
                front = nodeList[j]["ip"].split(".")
                back = nodeList[j+1]["ip"].split(".")

                nFront = int(front[0]) * 1000000000 + int(front[1]) * 1000000 + int(front[2]) * 1000 + int(front[3])
                nBack = int(back[0]) * 1000000000 + int(back[1]) * 1000000 + int(back[2]) * 1000 + int(back[3])

                if nFront > nBack:
                    nodeList[j], nodeList[j+1] = nodeList[j+1], nodeList[j]

    for node in nodeList:
        subNodeList = node.get("subnetwork", [])
        if len(subNodeList):
            sort_node_via_ip(subNodeList)


def is_the_node_with_ip(dNode, strIp):
    if dNode.get("ip", None) == strIp:
        return True
    return False

def find_node_with_same_network_segment(nodeList, strIp):
    for dNode in nodeList:
        if is_same_network_segment(dNode, strIp):
            return dNode
    return None

def find_node_with_same_ip_and_port(nodeList, strIp, nPort):
    for dNode in nodeList:
        if dNode.get("ip") == strIp and dNode.get("port") == nPort:
            return dNode
    return None

def find_node_with_same_ip(nodeList, strIp):
    for dNode in nodeList:
        if dNode.get("ip") == strIp:
            return dNode
    return None


def is_same_network_segment(dNode, strIp):
    nodeSegment = dNode.get("segment", None)
    if nodeSegment == None:
        return False

    tarSegment = get_network_segment(strIp)
    if tarSegment == None:
        return False

    if tarSegment == nodeSegment:
        return True
    return False


