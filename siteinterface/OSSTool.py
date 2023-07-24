# -*- coding: UTF-8 -*-
import oss2
import logging
import re
import os


OSS_CONFIG = {
    "region": "http://oss-cn-shanghai.aliyuncs.com",
    "bucketName": "dom-soft-release"
}


class OSSTool:
    def __init__(self):
        self.region = OSS_CONFIG.get("region")
        self.bucketName = OSS_CONFIG.get("bucketName")

    def gen_bucket(self):
        try:
            auth = oss2.Auth(self.accessKeyId, self.accessKeySecret)
            bucket = oss2.Bucket(auth, self.region, self.bucketName)
            return bucket
        except Exception as e:
            logging.error("ERROR in OSSTool.gen_bucket: %s" % e.__str__())
            return None

    """
    ossFilePath: 除bucketName之外的文件路径部分
    示例：oss://dom-soft-release/update/update.txt，此处ossFilePath 为 update/update.txt
    """
    def download(self, ossFilePath, localFilePath):
        bucket = self.gen_bucket()
        if not bucket:
            return False

        if not self.file_exists(ossFilePath):
            strLog = "OSSTool::{file} doesn't exist".format(file=ossFilePath)
            logging.error(strLog)
            print(strLog)
            return False

        try:
            bucket.get_object_to_file(ossFilePath, localFilePath)
            return True
        except Exception as e:
            logging.error("ERROR in OSSTool.download: %s" % e.__str__())
            return False

    """
    ossPath: {folderName}/{fileName}
    """
    def upload(self, opTargetPath, ossPath):
        try:
            bucket = self.gen_bucket()
            with open(opTargetPath, "rb") as fileobj:
                fileobj.seek(0, os.SEEK_SET)
                bucket.put_object(ossPath, fileobj)
            return True
        except Exception as e:
            logging.error("ERROR in OSSTool.upload: %s" % e.__str__())
            return False

    def file_exists(self, ossFilePath):
        bucket = self.gen_bucket()
        if not bucket:
            return False
        try:
            bExists = bucket.object_exists(ossFilePath)
            return bExists
        except Exception as e:
            logging.error("ERROR in OSSTool.file_exists: %s" % e.__str__())
            return False

    def iterate_files(self, strKey):
        bucket = self.gen_bucket()
        fileNameList = []
        for obj in oss2.ObjectIteratorV2(bucket, delimiter="/", prefix="{strKey}/".format(strKey=strKey)):
            if obj.is_prefix():
                continue

            strFileName = obj.key.replace(strKey, "")
            strFileName = strFileName.replace("/", "")

            if strFileName not in fileNameList:
                if len(strFileName):
                    fileNameList.append(strFileName)
        return fileNameList

    def calculate_length(self, strKey):
        bucket = self.gen_bucket()
        length = 0
        for obj in oss2.ObjectIteratorV2(bucket, prefix="{key}/".format(key=strKey)):
            length += obj.size
        return length

    def delete_files(self, filePathList):
        try:
            bucket = self.gen_bucket()
            bucket.batch_delete_objects(filePathList)
            return True
        except:
            return False

if __name__ == "__main__":
    OSSTool().delete_files(["static/images/fdd/62a995ab14d45559b735c3a2.png", "static/images/fdd/62a9963414d45559b29951b5.png"])


