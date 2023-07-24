# -*- coding: utf-8 -*-

from flask_mail import Mail, Message
import logging
from flask import current_app
from siteinterface import app
import csv
import ftplib
from ftplib import FTP

class SiteTool:
    @classmethod
    def send_email(cls, subject, recipients, html, attachment_list=None):
        print('send_email #1')
        rt = False
        if not current_app:
            app_ctx = app.app_context()
            app_ctx.push()
        print('send_email #2')
        try:
            if not isinstance(recipients, (list,)):
                recipients = recipients.split(';')

            print('send_email #3')
            sender = app.config.get('MAIL_DEFAULT_SENDER')
            msg = Message(subject=subject, recipients=recipients, charset='utf-8', html=html, sender=sender)

            print('send_email #4')
            if attachment_list:
                print('send_email add attachments')
                for attachment_item in attachment_list:
                    msg.attach(filename=attachment_item.get('filename', 'attachment'),
                               content_type=attachment_item.get('content_type ', 'text/html'),
                               data=attachment_item.get('data').encode('utf-8'))
            print('send_email #4AA')
            mm = Mail(app)

            print('send_email #4BB')
            mm.send(msg)
            print('Mail Sent Once to %s:'%(str(recipients)))
            logging.error('Mail Sent Once to %s:'%(str(recipients)))
            rt = True
        except Exception as e:
            print('send_email error:' + e.__str__())
            logging.error('send_email error:' + e.__str__())
        print('send_email #5')
        return rt


    @classmethod
    def upload_file_to_ftp(cls, serverPath, filename):
        ftp = FTP()
        ftp.set_debuglevel(0)
        # 打开调试级别2，显示详细信息;0为关闭调试信息
        ftp.connect(app.config['FTP_SERVER_ADDR'], int(app.config['FTP_SERVER_PORT']))
        # ftp.connect('114.215.172.232',6621)
        # 连接
        ftp.login(app.config['FTP_SERVER_USER'], app.config['FTP_SERVER_PWD'])
        # ftp.login('guest','rnbtech')

        ftp.cwd(serverPath)


        bufsize = 1024
        # 设置缓冲块大小
        file_handler = open(filename, 'rb')
        # 以读模式在本地打开文件
        ftp.storbinary('STOR %s' % filename, file_handler, bufsize)
        # 上传文件
        ftp.set_debuglevel(0)
        file_handler.close()
        ftp.quit()

    @classmethod
    def download_file_from_ftp(cls, serverPath, filename):
        ftp = FTP()
        ftp.set_debuglevel(0)
        # 打开调试级别2，显示详细信息;0为关闭调试信息
        ftp.connect(app.config['FTP_SERVER_ADDR'], int(app.config['FTP_SERVER_PORT']))
        # ftp.connect('114.215.172.232',6621)
        # 连接
        ftp.login(app.config['FTP_SERVER_USER'], app.config['FTP_SERVER_PWD'])
        # ftp.login('guest','rnbtech')

        ftp.cwd(serverPath)

        bufsize = 1024
        # 设置缓冲块大小写
        ftp.nlst()
        file_handler = open(filename, 'wb')
        # 以模式在本地写创建文件
        ftp.retrbinary('RETR %s' % filename, file_handler.write, bufsize)
        # 写入文件
        ftp.set_debuglevel(0)
        file_handler.close()
        ftp.quit()