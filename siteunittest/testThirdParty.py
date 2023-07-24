import unittest
from test import *
from siteinterface.BEOPDataAccess import *
from datetime import datetime
import requests

# 测试下面class中的所有test
class TestList(unittest.TestCase):

    # @classmethod
    # def setUpClass(cls):
    #     print("Begin ")
    #
    # @classmethod
    # def tearDownClass(cls):
    #     print("End ")
    #
    # def setUp(self):
    #     print('setUp...')
    #
    # def tearDown(self):
    #     print('tearDown...')
    @unittest.skip('skip is ok ')
    def sample(self):
        self.assertEqual(3, add(1, 2))
        self.assertNotEqual(3, add(2, 2))
        # self.assertEqual(a, b) a == b
        # self.assertNotEqual(a, b) a != b
        # self.assertTrue(x)  bool(x) is True
        # self.assertFalse(x)  bool(x) is False
        # self.assertIsNone(x)  x is None
        # self.assertIsNotNone(x)  x is not None
        # self.assertIn(a, b)  a in b
        # self.assertNotIn(a, b)  a not in b

    def test_third_party_upload(self):
        pointList = ["SHDT#XJWC#HVC#Outdoor1#t","SHDT#XJWC#HVC#Outdoor1#rh","SHDT#XJWC#HVC#CH01#status_sp"]
        valueList = ["34.5","90.0455","0"]
        thirdPartyName = "abas"

        headers = {'content-type': 'application/json'}

        strServerURL = '127.0.0.1:5000'

        post_data = dict(pointList=pointList, valueList=valueList, thirdPartyName=thirdPartyName, timeNow= datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        r = requests.post('http://%s/thirdParty/upload' % (strServerURL), data=json.dumps(post_data),
                          headers=headers, timeout=300)
        ret = BEOPDataAccess.getInstance().setThirdPartyRealtimeData(pointList, valueList, thirdPartyName)
        valueList = ret['msg']
        # check value
        for i in range(len(pointList)):
            retVal = BEOPDataAccess.getInstance().TestGetThirdPartyRealtimeData(pointList[i], thirdPartyName)
            try:
                retVal = float(retVal)
            except Exception:pass
            self.assertEqual(retVal, valueList[i])

        # check rewrite
        valueList = ["fdsa", "70.0045"]
        ret = BEOPDataAccess.getInstance().setThirdPartyRealtimeData(pointList, valueList, thirdPartyName)
        valueList = ret['msg']
        for i in range(len(pointList)):
            retVal = BEOPDataAccess.getInstance().TestGetThirdPartyRealtimeData(pointList[i], thirdPartyName)
            try:
                retVal = float(retVal)
            except Exception:pass
            self.assertEqual(retVal, valueList[i])


    def test_update_process_status(self):
        process = 'abas_process'

        BEOPDataAccess.getInstance().updateProcessStatus(process)
        timeTo = BEOPDataAccess.getInstance().TestGetProcessTime(process)
        timeNow = datetime.now()

        self.assertTrue((timeNow-timeTo).seconds < 20)


    def test_third_party_command(self):
        thirdPartyName = "abas"
        pointList = ["pointName1", "pointName2"]
        valueList = ["fdsafdsf", "90.00445"]
        #valueList = BEOPDataAccess.getInstance().setThirdPartyRealtimeData(pointList, valueList,[], thirdPartyName)

        #ret = BEOPDataAccess.getInstance().getAndClearThirdPartyOutputTable(None, thirdPartyName)
        #self.assertEqual(len(ret), len(pointList))

        #ret = BEOPDataAccess.getInstance().getThirdPartyInputTable(thirdPartyName)
        #self.assertEqual(len(ret), len(pointList))


if __name__ == '__main__':
    unittest.main(verbosity=2)

