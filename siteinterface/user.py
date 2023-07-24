# -*- coding: utf-8 -*-

"""
Routes and views for the flask application.
"""
from flask import request, jsonify
from siteinterface import  app
from siteinterface.BEOPDataAccess import BEOPDataAccess
from siteinterface.mod_fdd.utils import inspect_work_order
from siteinterface.RedisManager import RedisManager


def format_result(is_success, msg='', data=None):
    ''' 格式化输出结果 '''
    result = None
    if is_success:
        result = {"status": 'OK'}
    else:
        result = {"status": 'ERROR'}
    if msg:
        result['msg'] = msg
    if data != None:
        result['data'] = data
    return jsonify(result)

@app.route('/user/add', methods=['POST'])
def add_user():
    ''' 新增用户 '''
    data = request.get_json()
    result = BEOPDataAccess.getInstance().add_user(data)
    if result == -1:
      # 用户名存在
        return format_result(False, '用户名已经存在')
    if result['success']:
        return format_result(True, '添加用户成功', {
            'userid': result['userid']
        })
    else:
        return format_result(False, result.get("msg", ""))

@app.route('/user/del', methods=['POST'])
def del_user():
    ''' 删除用户 '''
    data = request.get_json()
    result = BEOPDataAccess.getInstance().delete_users(data['ids'])
    rtInspectWorkOrder = inspect_work_order()
    if result:
        return format_result(True, '删除用户成功。' + rtInspectWorkOrder.get("msg"))
    return format_result(False, '删除用户失败，请稍后重试。' + rtInspectWorkOrder.get("msg"))

@app.route('/user/modify/<userid>', methods=['POST'])
def modify_user(userid):
    ''' 修改用户 '''
    data = request.get_json()
    result = BEOPDataAccess.getInstance().modify_user(int(userid), data)
    if result:
        return format_result(True, '修改用户成功')
    return format_result(False, '修改用户失败，请稍后重试')

@app.route('/allusers/<userofrole>')
@app.route('/allusers')
def get_all_users(userofrole=""):
    try:
        userList = BEOPDataAccess.getInstance().get_all_users()
        if isinstance(userList,list) and len(userList)>0:
            userList.pop(0) #将cx账号从接口中去除，根用户没必要暴露
        authDict = RedisManager.get("FaultAuthInfo")
        if authDict:
            for user in userList:
                if user.get("username_zh", None) is None:
                    if authDict.get(user["username"], None):
                        if authDict.get(user["username"]).get("name_zh", None) is not None:
                            user["username_zh"] = authDict[user["username"]].get("name_zh")
                    else:
                        user["username_zh"] = ""

        if userofrole == "":
            return format_result(True, "", userList)

        res = []
        for item in userList:
            if item.get("userofrole") == userofrole:
                res.append(item)

        return format_result(True, "", res)
    except Exception as e:
        print(e.__str__())
        return format_result(False, '获取用户列表失败', [])

@app.route('/getUserOfRoleList')
def get_user_of_role_list():
    userList = BEOPDataAccess.getInstance().get_all_users()

    dAllInfo = {}
    for dUser in userList:
        userOfRole = dUser.get("userofrole", None)

        userNameEn = dUser.get("username", "")
        if userNameEn in ["cx"]:  # 屏蔽超级用户
            continue

        if userOfRole == None:
            continue

        if not isinstance(userOfRole, str):
            userOfRole = str(userOfRole)

        if userOfRole not in dAllInfo.keys():
            dAllInfo.update({userOfRole: []})

        dAllInfo[userOfRole].append(dict(nameEn=dUser.get("username", ""),
                                         nameCh=dUser.get("username_zh", ""),
                                         role=userOfRole,
                                         mobile=dUser.get("usermobile", ""),
                                         email=dUser.get("usermail", ""),
                                         id=dUser.get("id", ""),
                                         sex=dUser.get("usersex", "")))

    userOfRoleList = list(dAllInfo.keys())
    for i in range(len(userOfRoleList)):
        for j in range(len(userOfRoleList)-i-1):
            if userOfRoleList[j] > userOfRoleList[j+1]:
                userOfRoleList[j], userOfRoleList[j+1] = userOfRoleList[j+1], userOfRoleList[j]

    return jsonify(dict(err=0, msg="", data={"roleList": userOfRoleList, "allUsers": dAllInfo}))



