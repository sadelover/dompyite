
from siteinterface.mod_deviceManage import bp_deviceManage
from flask import request, jsonify, json
from siteinterface.BEOPDataAccess import BEOPDataAccess

"""
查询巡检用户
设备搜索功能（支持设备名称，安装位置，负责人名称字段）：
    searchKey: 关键字
    pageSize: 获取的页面大小
    targetPage: 目标页
:return:dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,
            'status' = False or True，出错为False
            'flag' = False or True  True代表查询有结果，False代表查询关键词没有结果，此时返回的是设备第一页的信息
              'data' = 正常返回的是DB中符合搜索词的所有设备信息，否则是None，
              'total' = 总共满足条件的记录的数量，出错时为-1,如果为0，则)
"""
@bp_deviceManage.route('/searchArea', methods=["POST"])
def area_search():

    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1, 'flag': True}
    try:
        data = request.get_json()
        if 'projectId' not in data:
            raise Exception('请求中项目Id信息不存在')
        projectId = int(data.get('projectId'))
        if 'searchKey' not in data:
            raise Exception('请求中不存在搜索关键字字段')
        searchKey = data.get('searchKey').strip()
        if 'targetPage' not in data:
            raise Exception('请求中不存在目标页面字段')
        targetPage = int(data.get('targetPage'))
        if 'pageSize' not in data:
            raise Exception('需要获取的页面大小信息不存在')
        pageSize = int(data.get('pageSize'))
        data = []
        flag = False
        total = 0
        data, total, flag = BEOPDataAccess.getInstance().searchArea(projectId, searchKey, pageSize, targetPage)
        result['data'] = data
        result['total'] = total
        result['flag'] = flag

    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)


#添加巡检用户
"""
    设备添加功能：
        request中需要包含应添加的设备各字段（除id）信息，json格式
        pageSize：所需获取的当前页面大小
        设备各字段参见本文件头
    :return: dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,'status' = False or True，出错为False,
    'data' = 正常返回的是设备的id，否则是None， 'total' = 总共记录的数量，出错时为-1)
    """
@bp_deviceManage.route('/addArea', methods=["POST"])
def area_add():
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        print(data)

        if 'projId' not in data:
            raise Exception('请求中项目Id信息不存在')
        projId = data.get('projId')
        if 'areaName' not in data:
            raise Exception('巡检计划名称信息不存在')
        areaName = data.get('areaName').strip()
        description = data.get('description')

        strProjectId = str(projId)
        BEOPDataAccess.getInstance().addArea(areaName,description,strProjectId)

    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False
        result['data'] = None

    return json.dumps(result, ensure_ascii=False)


@bp_deviceManage.route('/deleteArea', methods=["POST"])
def area_delete():
    """
    设备删除功能：
        delArray: 应删除的设备id数组
        curPage: 当前页面中显示的设备list的page
        pageSize: 所需获取的页面大小
        设备删除后，返回DB中设备list当前page中所有设备信息，用以更新页面
    :return: dict('msg'= 信息字符串，出错的时候为出错信息，否则为ok,'status' = False or True，出错为False,
                  'data' = 正常返回的是DB中删除设备后的当前页的所有设备信息，否则是None，
                   'total' = 总共记录的数量，出错时为-1
                  )
    """
    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1}
    try:
        data = request.get_json()
        if 'delArray' not in data:
            raise Exception('所要删除的数据_id信息不存在')
        delArray = data['delArray']

        #删除且获取更新后的当前页面
        BEOPDataAccess.getInstance().delArea(delArray)
    except Exception as e:
        print('interface equipment error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False
        result['total']= 0

    return json.dumps(result, ensure_ascii=False)