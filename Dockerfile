# 使用官方 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
#RUN pip install --no-cache-dir absl-py==2.2.2
#RUN pip install --no-cache-dir APScheduler==3.11.0
#RUN pip install --no-cache-dir astunparse==1.6.3
#RUN pip install --no-cache-dir blinker==1.9.0
#RUN pip install --no-cache-dir certifi==2025.1.31
#RUN pip install --no-cache-dir charset-normalizer==3.4.1
#RUN pip install --no-cache-dir click==8.1.8
#RUN pip install --no-cache-dir colorama==0.4.6
#RUN pip install --no-cache-dir Flask==2.0.1
#RUN pip install --no-cache-dir Flask-Login==0.6.3
#RUN pip install --no-cache-dir Flask-SQLAlchemy==2.5.1
#RUN pip install --no-cache-dir flatbuffers==25.2.10
#RUN pip install --no-cache-dir gast==0.6.0
#RUN pip install --no-cache-dir google-pasta==0.2.0
#RUN pip install --no-cache-dir greenlet==3.1.1
#RUN pip install --no-cache-dir grpcio==1.71.0
#RUN pip install --no-cache-dir gunicorn==20.1.0
#RUN pip install --no-cache-dir h5py==3.13.0
#RUN pip install --no-cache-dir idna==3.10
#RUN pip install --no-cache-dir itsdangerous==2.2.0
#RUN pip install --no-cache-dir Jinja2==3.1.6
#RUN pip install --no-cache-dir joblib==1.3.2
#RUN pip install --no-cache-dir keras==3.9.2
#RUN pip install --no-cache-dir libclang==18.1.1
#RUN pip install --no-cache-dir Markdown==3.7
#RUN pip install --no-cache-dir markdown-it-py==3.0.0
#RUN pip install --no-cache-dir MarkupSafe==3.0.2
#RUN pip install --no-cache-dir mdurl==0.1.2
#RUN pip install --no-cache-dir ml_dtypes==0.5.1
#RUN pip install --no-cache-dir model-selection==0.0.1
#RUN pip install --no-cache-dir namex==0.0.8
#RUN pip install --no-cache-dir numpy==1.26.4
#RUN pip install --no-cache-dir opt_einsum==3.4.0
#RUN pip install --no-cache-dir optree==0.15.0
#RUN pip install --no-cache-dir packaging==24.2
#RUN pip install --no-cache-dir pandas==2.2.1
#RUN pip install --no-cache-dir protobuf==5.29.4
#RUN pip install --no-cache-dir Pygments==2.19.1
#RUN pip install --no-cache-dir PyPDF2==2.0.0
#RUN pip install --no-cache-dir python-dateutil==2.9.0.post0
#RUN pip install --no-cache-dir python-dotenv==1.0.0
#RUN pip install --no-cache-dir pytz==2025.2
#RUN pip install --no-cache-dir requests==2.32.3
#RUN pip install --no-cache-dir rich==14.0.0
#RUN pip install --no-cache-dir scikit-learn==1.6.1
#RUN pip install --no-cache-dir scipy==1.15.2
#RUN pip install --no-cache-dir setuptools==78.1.0
#RUN pip install --no-cache-dir six==1.17.0
#RUN pip install --no-cache-dir SQLAlchemy==1.4.41
#RUN pip install --no-cache-dir tensorboard==2.18.0
#RUN pip install --no-cache-dir tensorboard-data-server==0.7.2
#RUN pip install --no-cache-dir tensorflow==2.18.1 -i https://pypi.tuna.tsinghua.edu.cn/simple
#RUN pip install --no-cache-dir termcolor==3.0.1
#RUN pip install --no-cache-dir threadpoolctl==3.6.0
#RUN pip install --no-cache-dir typing_extensions==4.13.1
#RUN pip install --no-cache-dir tzdata==2025.2
#RUN pip install --no-cache-dir tzlocal==5.3.1
#RUN pip install --no-cache-dir urllib3==2.3.0
#RUN pip install --no-cache-dir Werkzeug==2.0.1
#RUN pip install --no-cache-dir wheel==0.45.1
#RUN pip install --no-cache-dir wrapt==1.17.2


# 设置环境变量（可选）
ENV FLASK_ENV=production

# 暴露端口
EXPOSE 5000

# 运行 Flask 应用
CMD ["python", "app.py"]