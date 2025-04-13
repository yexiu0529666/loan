from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Password:
    """密码处理类"""
    def __init__(self, password):
        self.hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.hash, password)
    
    def __repr__(self):
        return self.hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Flask-Login 所需的属性
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def verify_password(self, password):
        return check_password_hash(self.password, password)
    
    # 作为申请人的贷款申请
    submitted_applications = db.relationship(
        'LoanApplication',
        primaryjoin='User.id==LoanApplication.user_id',
        backref='applicant',
        lazy=True
    )
    
    # 作为审批人的贷款申请
    reviewed_applications = db.relationship(
        'LoanApplication',
        primaryjoin='User.id==LoanApplication.approved_by',
        backref='approver',
        lazy=True
    )
    
    # 通知关系
    received_notifications = db.relationship('Notification', back_populates='recipient')
    
    def __repr__(self):
        return f'<User {self.username}>'

class CreditReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_valid = db.Column(db.Boolean, default=False)
    validation_comment = db.Column(db.Text)

class LoanApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(80))
    amount = db.Column(db.Float, nullable=False)
    term = db.Column(db.Integer, nullable=False)  # 贷款期限（月）
    interest_rate = db.Column(db.Float, nullable=False)  # 年利率
    monthly_payment = db.Column(db.Float, nullable=False)  # 月还款额
    total_interest = db.Column(db.Float, nullable=False)  # 总利息
    purpose = db.Column(db.String(200))  # 贷款用途
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    risk_score = db.Column(db.Float)  # 风险评分
    risk_level = db.Column(db.String(20))  # 风险等级
    credit_report_id = db.Column(db.Integer, db.ForeignKey('credit_report.id'))

    employment_years = db.Column(db.Integer)
    age = db.Column(db.Integer)
    annual_income = db.Column(db.Float, nullable=False)
    monthly_income = db.Column(db.Float, nullable=False)
    savings_balance = db.Column(db.Float, nullable=False)
    total_assets = db.Column(db.Float, nullable=False)
    total_liabilities = db.Column(db.Float, nullable=False)
    credit_cards = db.Column(db.Integer)
    his_existing_loans = db.Column(db.Float, nullable=False) # 历史贷款
    his_monthly_debt = db.Column(db.Float, nullable=False)  # 历史月还贷额
    dependents = db.Column(db.Integer)
    employment_status = db.Column(db.String(20))
    marital_status = db.Column(db.String(20))
    education = db.Column(db.String(20))
    home_ownership = db.Column(db.String(20))
    previous_default = db.Column(db.String(20))
    recommendation = db.Column(db.String(80))  # 模型建议


    # 定义与还款记录的关系
    repayment_records = db.relationship('RepaymentRecord', backref='loan', lazy=True)
    
    def __repr__(self):
        return f'<LoanApplication {self.id}>'

class RepaymentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loan_application.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    payment_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False)  # pending, paid, overdue
    late_fee = db.Column(db.Float, default=0.0)

class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type = db.Column(db.String(50), nullable=True, default=None)
    
    # 使用 back_populates 来明确关系
    recipient = db.relationship('User', back_populates='received_notifications')
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class Bill(db.Model):
    __tablename__ = 'bills'
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan_application.id'), nullable=False)
    period = db.Column(db.Integer, nullable=False)  # 第几期
    due_date = db.Column(db.DateTime, nullable=False)  # 还款日期
    amount = db.Column(db.Float, nullable=False)  # 还款金额
    principal = db.Column(db.Float, nullable=False)  # 本金
    interest = db.Column(db.Float, nullable=False)  # 利息
    remaining_principal = db.Column(db.Float, nullable=False)  # 剩余本金
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, paid, overdue
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = db.Column(db.DateTime, default=None)  # 还款时间

    # 添加与 LoanApplication 的关系
    loan = db.relationship('LoanApplication', backref=db.backref('bills', lazy=True))

    def __repr__(self):
        return f'<Bill {self.id}>'

    def is_overdue(self):
        """检查账单是否逾期"""
        if self.status == 'paid':
            return False
        return datetime.utcnow().date() > self.due_date.date()
    
    def get_status_display(self):
        """获取账单状态的显示文本"""
        if self.status == 'paid':
            return '已还款'
        elif self.is_overdue():
            return '已逾期'
        else:
            return '待还款'