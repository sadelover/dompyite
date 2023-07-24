
from siteinterface.mod_care import bp_care
from flask import request, jsonify, json
from siteinterface.BEOPDataAccess import BEOPDataAccess

@bp_care.route('/equipCareSearch', methods=["POST"])
def equip_CareSearch():

    result = {'status':True, 'msg':'ok', 'data':None, 'total': -1, 'flag': True}
    try:
        data = request.get_json()
        if 'projectId' not in data:
            raise Exception('请求中项目Id信息不存在')
        if 'status' not in data:
            raise Exception('请求中不存在status字段')
        if 'startTime' not in data:
            raise Exception('请求中不存在startTime字段')
        if 'endTime' not in data:
            raise Exception('请求中不存在endTime字段')
        if 'targetPage' not in data:
            raise Exception('请求中不存在目标页面字段')
        if 'pageSize' not in data:
            raise Exception('需要获取的页面大小信息不存在')

        projectId = int(data.get('projectId'))
        status = data.get('status')
        startTime = data.get('startTime')
        endTime = data.get('endTime')
        targetPage = int(data.get('targetPage'))
        pageSize = int(data.get('pageSize'))

        data = []
        flag = False
        total = 0
        data, total, flag = BEOPDataAccess.getInstance().equipCareList(projectId, status,startTime,endTime, pageSize, targetPage)
        result['data'] = data
        result['total'] = total
        result['flag'] = flag

    except Exception as e:
        print('interface equipCareSearch error:' + e.__str__())
        result['msg'] = e.__str__()
        result['status'] = False

    return json.dumps(result, ensure_ascii=False)