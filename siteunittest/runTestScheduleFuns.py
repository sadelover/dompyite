import json
from siteinterface.BEOPDataAccess import BEOPDataAccess

if __name__=='__main__':
    bReadSuccess = False
    # new schedule
    BEOPDataAccess.getInstance().addSchedule('myTest', 'username',0,'point1')

    #read , confirm
    result = BEOPDataAccess.getInstance().getSchedule()
    id = 0
    strScheduleName=""
    isloop=0
    strPointDefine=""

    for day in result:
        if day.get("name") == "myTest" :
            bReadSuccess = True
            id = day.get("id")
            strScheduleName=day.get("name")
            isloop = day.get("isloop")
            strPointDefine = day.get("point")

    if not bReadSuccess:
        print('test failed: create failed')
    else:
        print('test addSchedule: create Success')

    #modify
    BEOPDataAccess.getInstance().editSchedule(id,strScheduleName,isloop,"point1,point3")
    # modify confirm
    result = BEOPDataAccess.getInstance().getSchedule()
    for day in result:
        if day.get("id") == id:
            if day.get("point") == "point1,point3":
                print('test editSchedule: edit Success')


    #enable
    BEOPDataAccess.getInstance().enableSchedule(1,id)

    #enable confirm
    result = BEOPDataAccess.getInstance().getSchedule()
    for day in result:
        if day.get("id") == id:
            if day.get("enable") == 1:
                print('test enableSchedule: enable Success')


    #schedule 内容定义创建: 周一到周五8:00-20:00, 周六周日不开
    data ={"id": id,"content":[{'id':id,'timeFrom':'8','timeTo':'20','value':'1,2','weekday':1},{'id':id,'timeFrom':'8','timeTo':'20','value':'1,2','weekday':2},{'id':id,'timeFrom':'8','timeTo':'20','value':'1,2','weekday':3},{'id':id,'timeFrom':'8','timeTo':'20','value':'1,2','weekday':4},{'id':id,'timeFrom':'8','timeTo':'20','value':'1,2','weekday':5}]}
    #data = json.loads(content)
    content=data.get("content")
    bSucces = BEOPDataAccess.getInstance().removeWeekDays(id);
    for day in content:
        BEOPDataAccess.getInstance().addWeekDays(day.get('weekday'), day.get('timeFrom'), day.get('timeTo'), day.get('value'), day.get('id'))

    #confirm
    result2 = BEOPDataAccess.getInstance().fromGrouopIdGetSecheduleTask(id)
    for week in result2:
       if week.get("groupid") == id:
           print('test editWeekDays: editWeekDays Success')
           break


    # delete
    BEOPDataAccess.getInstance().removeSchedule(id)
    # delete confirm
    bisDelete = True
    result = BEOPDataAccess.getInstance().getSchedule()
    for day in result:
        if day.get("id") == id:
            bisDelete= False

    result2 = BEOPDataAccess.getInstance().fromGrouopIdGetSecheduleTask(id)
    if  result2.__len__() == 0 and bisDelete:
        print("delete Schedule: removeSchedule Success")
    # BEOPDataAccess.getInstance().enableSchedule(enable, id)

    print('finish')