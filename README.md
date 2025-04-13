# 银行小微快贷系统

这是一个基于Flask的银行小微快贷系统，支持用户贷款申请、征信报告上传、风险评估、贷款审批和还款管理等功能。

## 功能特点

- 用户管理
  - 用户注册和登录
  - 角色权限控制（普通用户、客户经理、行长）
  
- 贷款申请
  - 在线提交贷款申请
  - 上传征信报告
  - 自动风险评估
  
- 贷款审批
  - 客户经理初审
  - 行长终审
  - 多级审批流程
  
- 还款管理
  - 自动生成还款计划
  - 还款提醒
  - 逾期管理
  
- 通知系统
  - 系统内通知
  - 邮件通知
  - 还款提醒

## 系统要求

- Python 3.8+
- SQLite
- 其他依赖见 requirements.txt

## 安装步骤

1. 克隆项目
```bash
git clone [项目地址]
cd [项目目录]
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
创建 `.env` 文件并设置以下变量：
```
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_password
```

5. 初始化数据库
```bash
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

6. 运行应用
```bash
python app.py
```

## 使用说明

### 普通用户

1. 注册账号并登录
2. 提交贷款申请
3. 上传征信报告
4. 查看申请进度
5. 接收通知提醒
6. 按时还款

### 客户经理

1. 登录系统
2. 查看待审核申请
3. 审核申请材料
4. 提交审核意见

### 行长

1. 登录系统
2. 查看待审批申请
3. 进行最终审批
4. 查看风险报告

## 项目结构

```
loan/
├── app.py                 # 主应用文件
├── models.py              # 数据模型
├── risk_model.py          # 风险评估模型
├── credit_report_service.py # 征信报告服务
├── repayment_service.py   # 还款服务
├── notification_service.py # 通知服务
├── requirements.txt       # 项目依赖
├── README.md             # 项目说明
├── uploads/              # 文件上传目录
│   └── credit_reports/   # 征信报告存储
└── templates/            # HTML模板
```

## 注意事项

1. 请确保征信报告文件格式正确
2. 定期检查还款提醒功能
3. 注意保护用户隐私数据
4. 定期备份数据库

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。

## 许可证

MIT License 