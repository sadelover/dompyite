from flask import Flask, app

if __name__ == '__MAIN__':
    app = Flask(__name__)
    app.run(host="127.0.0.1",port=5008,debug=True)
