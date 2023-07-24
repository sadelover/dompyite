

import numpy as np
import matplotlib.pyplot as plt
from sklearn import tree
from sklearn.linear_model import LinearRegression
from sklearn import svm
from sklearn import neighbors
from sklearn import ensemble
from sklearn import ensemble
from sklearn import ensemble
from sklearn import ensemble
from sklearn.tree import ExtraTreeRegressor
from sklearn.metrics import r2_score
from sklearn.externals import joblib
import os
from siteinterface.BEOPDataAccess import BEOPDataAccess
import pandas as pd
import logging

class DomRegression():

    def __init__(self, strModelName):
        self.x_train = None
        self.y_train = None

        self.x_test = None
        self.y_test = None
        self.best_model = None
        self.model_name = strModelName
        pass

    # 生成数据
    def gen_data(self, x1, x2):
        y = np.sin(x1) * 1 / 2 + np.cos(x2) * 1 / 2 + 0.1 * x1
        return y

    def set_train_data(self, x_train, y_train, x_test, y_test):
        self.x_train = x_train
        self.y_train = y_train

        self.x_test = x_test
        self.y_test = y_test

    def load_data(self):
        x1_train = np.linspace(0, 50, 500)
        x2_train = np.linspace(-10, 10, 500)
        data_train = np.array(
            [[x1, x2, self.gen_data(x1, x2) + np.random.random(1) - 0.5] for x1, x2 in zip(x1_train, x2_train)])
        x1_test = np.linspace(0, 50, 100) + np.random.random(100) * 0.5
        x2_test = np.linspace(-10, 10, 100) + 0.02 * np.random.random(100)
        data_test = np.array([[x1, x2, self.gen_data(x1, x2)] for x1, x2 in zip(x1_test, x2_test)])

        # train的前两列是x，后一列是y，这里的y有随机噪声
        self.x_train, self.y_train = data_train[:, :2], data_train[:, 2]
        self.x_test, self.y_test = data_test[:, :2], data_test[:, 2]  # 同上，但这里的y没有噪声

    # 回归部分
    def try_different_method(self, model, bFigured=False):
        model.fit(self.x_train, self.y_train)
        score = model.score(self.x_test, self.y_test)
        result = model.predict(self.x_test)
        if bFigured:
            plt.figure()
            plt.plot(np.arange(len(result)), self.y_test, "go-", label="True value")
            plt.plot(np.arange(len(result)), result, "ro-", label="Predict value")
            plt.title("method:{method}---score:{score}")
            plt.legend(loc="best")
            plt.show()
        return r2_score(self.y_test, result)

    def save_model(self):
        if self.best_model is None:
            return False
        # 保存模型
        strModelDataPath = os.getcwd() + '\\siteinterface\\static\\model_data'
        if not os.path.exists(strModelDataPath):
            os.makedirs(strModelDataPath)
        strFilePath = os.path.join(strModelDataPath, self.model_name + '.pkl')
        joblib.dump(self.best_model, strFilePath)
        return True

    def load_model(self, ):
        strModelDataPath = os.getcwd() + '\\siteinterface\\static\\model_data'
        if not os.path.exists(strModelDataPath):
            os.makedirs(strModelDataPath)
        strFilePath = os.path.join(strModelDataPath, self.model_name + '.pkl')

        if os.path.exists(strFilePath):
            self.best_model = joblib.load(strFilePath)
            return True

        return False

    def predict_data(self, x_list):
        result = self.best_model.predict(x_list)
        try:
            return result.tolist()
        except:
            return list(result)

    def train_best_model(self, strModelTypeName):
        fBestScore = 0
        scoreAllMap = {}
        # 方法选择
        # 1.决策树回归
        model_decision_tree_regression = tree.DecisionTreeRegressor()
        fScore = self.try_different_method(model_decision_tree_regression)
        scoreAllMap['DicisionTree'] = fScore
        if fScore > fBestScore:
            self.best_model = model_decision_tree_regression

        if strModelTypeName == 'DicisionTree':
            self.best_model = model_decision_tree_regression
            self.save_model()
            return scoreAllMap

        # 2.线性回归
        model_linear_regression = LinearRegression()
        fScore = self.try_different_method(model_linear_regression, )
        scoreAllMap['Linear'] = fScore
        if fScore > fBestScore:
            self.best_model = model_linear_regression

        if strModelTypeName == 'Linear':
            self.best_model = model_linear_regression
            self.save_model()
            return scoreAllMap

        # 3.SVM回归
        model_svm = svm.SVR()
        fScore = self.try_different_method(model_svm, )
        scoreAllMap["SVR"] = fScore
        if fScore > fBestScore:
            self.best_model = model_svm

        if strModelTypeName == 'SVR':
            self.best_model = model_svm
            self.save_model()
            return scoreAllMap

        # 4.kNN回归
        model_k_neighbor = neighbors.KNeighborsRegressor()
        fScore = self.try_different_method(model_k_neighbor, )
        scoreAllMap["KNeighbors"] = fScore
        if fScore > fBestScore:
            self.best_model = model_k_neighbor

        if strModelTypeName == 'KNeighbors':
            self.best_model = model_k_neighbor
            self.save_model()
            return scoreAllMap

        # 5.随机森林回归
        model_random_forest_regressor = ensemble.RandomForestRegressor(n_estimators=20)  # 使用20个决策树
        fScore = self.try_different_method(model_random_forest_regressor, )
        scoreAllMap["RandomForest"] = fScore
        if fScore > fBestScore:
            self.best_model = model_random_forest_regressor

        if strModelTypeName == 'RandomForest':
            self.best_model = model_random_forest_regressor
            self.save_model()
            return scoreAllMap

        # 6.Adaboost回归
        model_adaboost_regressor = ensemble.AdaBoostRegressor(n_estimators=50)  # 这里使用50个决策树
        fScore = self.try_different_method(model_adaboost_regressor, )
        scoreAllMap["AdaBoost"] = fScore
        if fScore > fBestScore:
            self.best_model = model_adaboost_regressor

        if strModelTypeName == 'AdaBoost':
            self.best_model = model_adaboost_regressor
            self.save_model()
            return scoreAllMap

        # 7.GBRT回归
        model_gradient_boosting_regressor = ensemble.GradientBoostingRegressor(n_estimators=100)  # 这里使用100个决策树
        fScore = self.try_different_method(model_gradient_boosting_regressor, )
        scoreAllMap["GradientBoosting"] = fScore
        if fScore > fBestScore:
            self.best_model = model_gradient_boosting_regressor

        if strModelTypeName == 'GradientBoosting':
            self.best_model = model_gradient_boosting_regressor
            self.save_model()
            return scoreAllMap

        # 8.Bagging回归
        model_bagging_regressor = ensemble.BaggingRegressor()
        fScore = self.try_different_method(model_bagging_regressor, )
        scoreAllMap["Bagging"] = fScore
        if fScore > fBestScore:
            self.best_model = model_bagging_regressor

        if strModelTypeName == 'Bagging':
            self.best_model = model_bagging_regressor
            self.save_model()
            return scoreAllMap

        # 9.ExtraTree极端随机数回归
        model_extra_tree_regressor = ExtraTreeRegressor()
        fScore = self.try_different_method(model_extra_tree_regressor, )
        scoreAllMap["EntraTree"] = fScore
        if fScore > fBestScore:
            self.best_model = model_extra_tree_regressor

        if strModelTypeName == 'EntraTree':
            self.best_model = model_extra_tree_regressor
            self.save_model()
            return scoreAllMap

        self.save_model()
        return scoreAllMap

    # 每N个数间隔取一个作为测试集
    def split_list_to_train_test(self, fXList, validatePercent=15):
        fXTrainList = []
        fXTestList = []
        if validatePercent<=0:
            validatePercent = 10.0

        bAllTest = False
        if validatePercent>=100.0:
            bAllTest = True
        nIndexTest = int(100.0/validatePercent)-1

        for iIndex in range(len(fXList)):
            if bAllTest:
                fXTestList.append(fXList[iIndex])
            elif nIndexTest>0 and iIndex % nIndexTest == 0:
                fXTestList.append(fXList[iIndex])
            #所有样本都加入训练集
            fXTrainList.append(fXList[iIndex])
        return np.array(fXTrainList), np.array(fXTestList)

    def model_gen_by_values(self, x_values, y_values, strModelTypeName, validatePercent=15):
        x_train, x_test = self.split_list_to_train_test(x_values, validatePercent)
        y_train, y_test = self.split_list_to_train_test(y_values, validatePercent)
        self.set_train_data(x_train, y_train, x_test, y_test)
        allScoreMap = self.train_best_model(strModelTypeName)
        print(allScoreMap)
        return allScoreMap

    def get_data_list_by_point_name(self, strPointNameListX, strPointNameListY, strTimeFrom, strTimeTo,
                                    strTimeFormat):
        strPointNameListAll = strPointNameListX.copy()
        strPointNameListAll.extend(strPointNameListY)
        AllHistoryData = BEOPDataAccess.getInstance().get_history_data_padded(strPointNameListAll, strTimeFrom, strTimeTo, strTimeFormat)
        AllHistoryData = AllHistoryData.get('map')
        x_train = []
        y_train = []
        x_test = []
        y_test = []

        nDataCount = 0
        for pp in strPointNameListAll:
            ppDataList = AllHistoryData.get(pp, [])
            if ppDataList is None or len(ppDataList) == 0:
                print('ERROR in point data is empty:%s' % (pp))
                return [],[]
            nDataCount = len(ppDataList)

        x_all_data = []
        y_all_data = []
        for iIndex in range(nDataCount):
            XGroup = []
            for pp in strPointNameListX:
                floatValue = AllHistoryData[pp][iIndex]
                try:
                    floatValue = float(AllHistoryData[pp][iIndex])
                except:
                    pass
                XGroup.append(floatValue)
            x_all_data.append(XGroup)
            YGroup = []
            for pp in strPointNameListY:
                floatValue = AllHistoryData[pp][iIndex]
                try:
                    floatValue = float(AllHistoryData[pp][iIndex])
                except:
                    pass
                YGroup.append(floatValue)
            y_all_data.append(YGroup)

        return x_all_data, y_all_data

    # XList, YList均为一维数组
    def relation_analysis(self, XList, YList):

        data = pd.DataFrame({'X': XList,
                             'Y': YList})
        print(data.corr())  # 计算所有的变量的两两相关性
        return data['X'].corr(data['Y'])  # 只计算选择的两个变量的相关性
