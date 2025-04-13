from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from models import db, User, LoanApplication, RepaymentRecord, Notification, Bill
from risk_assessment import RiskAssessmentService
from notification_service import NotificationService
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from decimal import Decimal
import math
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loan.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

# 配置日志
if not os.path.exists('logs'):
    os.makedirs('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('应用启动')

# 初始化 Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'  # 使用强会话保护
login_manager.login_message = '请先登录'
login_manager.login_message_category = 'info'

# 初始化数据库
db.init_app(app)

# 创建调度器
scheduler = BackgroundScheduler()

def check_upcoming_bills():
    """检查即将到期的账单并发送通知"""
    with app.app_context():
        # 获取3天后到期的账单
        three_days_later = datetime.utcnow().date() + timedelta(days=3)
        upcoming_bills = Bill.query.filter(
            Bill.status == 'pending',
            Bill.due_date >= three_days_later,
            Bill.due_date < three_days_later + timedelta(days=1)
        ).all()

        for bill in upcoming_bills:
            # 检查是否已经发送过通知
            existing_notification = Notification.query.filter_by(
                user_id=bill.loan.user_id,
                content=f"请于 {bill.due_date.strftime('%Y-%m-%d')} 前还款 {bill.amount:.2f} 元。"
            ).first()
            
            if not existing_notification:
                # 创建新通知
                notification = Notification(
                    user_id=bill.loan.user_id,
                    title="还款提醒",
                    content=f"请于 {bill.due_date.strftime('%Y-%m-%d')} 前还款 {bill.amount:.2f} 元。",
                    type='repayment_reminder',
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
        
        try:
            db.session.commit()
            app.logger.info("成功提交还款提醒通知")
        except Exception as e:
            app.logger.error(f"提交还款提醒通知失败: {str(e)}")
            db.session.rollback()

def update_overdue_bills():
    """更新逾期账单状态"""
    with app.app_context():
        overdue_bills = Bill.query.filter(
            Bill.status == 'pending',
            Bill.due_date < datetime.utcnow().date()
        ).all()
        
        for bill in overdue_bills:
            bill.status = 'overdue'

            # 创建逾期通知
            notification = Notification(
                user_id=bill.loan.user_id,
                title="账单逾期提醒",
                content=f"您的账单已逾期，请尽快还款 {bill.amount:.2f} 元。",
                type='overdue_reminder',
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notification)
        
        try:
            db.session.commit()
            app.logger.info("成功提交逾期提醒通知")
        except Exception as e:
            app.logger.error(f"提交逾期提醒通知失败: {str(e)}")
            db.session.rollback()

# 添加定时任务，每分钟执行一次
scheduler.add_job(check_upcoming_bills, 'interval', seconds=10)
scheduler.add_job(update_overdue_bills, 'interval', seconds=10)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 创建数据库表
with app.app_context():
    db.create_all()
    
    # 启动调度器
    if not scheduler.running:
        scheduler.start()

# 用户认证装饰器
def login_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 角色检查装饰器
def role_required(roles):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('您没有权限访问此页面', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

# 初始化风险评估服务和通知服务
risk_service = RiskAssessmentService()
notification_service = NotificationService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = 'user'  # 默认角色为用户

        if User.query.filter_by(username=username).first():
            flash('用户名已存在，请选择其他用户名', 'error')
            return redirect(url_for('register'))

        user = User(
            username=username,
            password=generate_password_hash(password),
            email=email,
            phone=phone,
            role=role
        )
        db.session.add(user)
        db.session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.verify_password(password):
            login_user(user, remember=True)  # 添加 remember=True 保持登录状态
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误！', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'user':
        # 获取用户的贷款申请
        loans = LoanApplication.query.filter_by(user_id=current_user.id).all()
        # 获取用户的通知
        notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.id.desc()).all()
        return render_template('user_dashboard.html', user=current_user, loans=loans, notifications=notifications)
    elif current_user.role == 'manager':
        return redirect(url_for('manager_dashboard'))
    elif current_user.role == 'president':
        return redirect(url_for('president_dashboard'))
    else:
        flash('未知的用户角色', 'danger')
        return redirect(url_for('login'))

@app.route('/assess_risk', methods=['POST'])
def assess_risk():
    try:
        # 获取申请数据
        data = request.get_json()
        
        # 进行风险评估
        assessment = risk_service.assess_loan_application(data)
        
        return jsonify(assessment)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/apply_loan', methods=['GET', 'POST'])
@login_required
def apply_loan():
    if request.method == 'POST':
        try:
            app.logger.info("开始处理贷款申请")
            
            # 获取表单数据
            data = {
                'age': int(request.form.get('age')),
                'employment_years': int(request.form.get('work_experience')),
                'annual_income': float(request.form.get('annual_income')),
                'monthly_income': float(request.form.get('monthly_income')),
                'savings_balance': float(request.form.get('savings_balance')),
                'total_assets': float(request.form.get('total_assets')),
                'total_liabilities': float(request.form.get('total_liabilities')),
                'credit_cards': int(request.form.get('credit_cards')),
                'existing_loans': float(request.form.get('existing_loans')),
                'monthly_payment': float(request.form.get('monthly_debt')),
                'loan_amount': float(request.form.get('loan_amount')),
                'loan_term': int(request.form.get('loan_term')),
                'dependents': int(request.form.get('dependents')),
                'employment_status': request.form.get('employment_status'),
                'marital_status': request.form.get('marital_status'),
                'education': request.form.get('education'),
                'home_ownership': request.form.get('home_ownership'),
                'loan_purpose': request.form.get('purpose'),
                'previous_default': request.form.get('previous_default')
            }
            
            app.logger.debug(f"表单数据: {data}")
            
            # 进行风险评估
            risk_assessment = risk_service.assess_loan_application(data)
            
            app.logger.debug(f"风险评估结果: {risk_assessment}")
            
            # 计算利率
            interest_rate = calculate_credit_score(data)
            
            # 计算月利率
            monthly_rate = interest_rate / 12
            
            # 计算月还款额（等额本息）
            loan_amount = float(data['loan_amount'])
            loan_term = int(data['loan_term'])
            monthly_payment = (loan_amount * monthly_rate * (1 + monthly_rate) ** loan_term) / ((1 + monthly_rate) ** loan_term - 1)
            
            # 计算总利息
            total_interest = monthly_payment * loan_term - loan_amount
            
            app.logger.debug(f"利率: {interest_rate}, 月还款: {monthly_payment}, 总利息: {total_interest}")
            
            # 创建贷款申请
            loan = LoanApplication(
                user_id=current_user.id,
                username=current_user.username,
                amount=loan_amount,
                term=loan_term,
                interest_rate=interest_rate,
                monthly_payment=monthly_payment,
                total_interest=total_interest,
                purpose=data['loan_purpose'],
                status='pending',
                created_at=datetime.now(),
                risk_score=risk_assessment.get('risk_score', 0),
                risk_level=risk_assessment.get('risk_level', 'medium'),

                employment_years=data['employment_years'],
                age=data['age'],
                annual_income=data['annual_income'],
                monthly_income=data['monthly_income'],
                savings_balance=data['savings_balance'],
                total_assets=data['total_assets'],
                total_liabilities=data['total_liabilities'],
                credit_cards=data['credit_cards'],
                his_existing_loans=data['existing_loans'],
                his_monthly_debt=data['monthly_payment'],
                dependents=data['dependents'],
                employment_status=data['employment_status'],
                marital_status=data['marital_status'],
                education=data['education'],
                home_ownership=data['home_ownership'],
                previous_default=data['previous_default'],
                recommendation=risk_assessment.get('recommendation', {}).get('recommendation', '暂无建议')
            )
            
            app.logger.debug(f"创建贷款申请对象: {loan}")
            
            # 保存到数据库
            db.session.add(loan)
            
            # 创建通知
            notification = Notification(
                user_id=current_user.id,
                title="贷款申请提交成功",
                content=f"您的贷款申请（金额：{loan_amount}元）已提交成功，请等待审核。",
                type='loan_application',
                is_read=False,
                created_at=datetime.now()
            )
            db.session.add(notification)
            
            # 提交事务
            db.session.commit()
            
            app.logger.info("贷款申请提交成功")
            flash('贷款申请提交成功！', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            app.logger.error(f"贷款申请处理失败: {str(e)}", exc_info=True)
            db.session.rollback()
            flash('贷款申请处理失败，请稍后重试', 'danger')
            return redirect(url_for('apply_loan'))
            
    # GET 请求显示申请表单
    return render_template('apply_loan.html')

@app.route('/init_db')
def init_db():
    try:
        # 删除所有表
        db.drop_all()
        # 创建所有表
        db.create_all()
        
        # 创建测试用户
        test_user = User(
            username='test',
            password=generate_password_hash('123456'),
            email='test@example.com',
            phone='13800138000',
            role='user'
        )
        db.session.add(test_user)
        
        # 创建客户经理账号
        manager = User.query.filter_by(username='manager').first()
        if not manager:
            manager = User(
                username='manager',
                password=generate_password_hash('manager123'),
                email='manager@bank.com',
                phone='13800138001',
                role='manager'
            )
            db.session.add(manager)
            app.logger.info("客户经理账号已创建")
        
        # 创建行长账号
        president = User.query.filter_by(username='president').first()
        if not president:
            president = User(
                username='president',
                password=generate_password_hash('president123'),
                email='president@bank.com',
                phone='13800138002',
                role='president'
            )
            db.session.add(president)
            app.logger.info("行长账号已创建")
        
        
        db.session.commit()
        
        return '数据库初始化成功！<br>' + \
               '测试用户：用户名 test，密码 123456<br>' + \
               '客户经理：用户名 manager，密码 manager123<br>' + \
               '行长：用户名 president，密码 president123'
    except Exception as e:
        return f'数据库初始化失败：{str(e)}'

@app.route('/calculate_interest', methods=['POST'])
@login_required
def calculate_interest():
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = {
            'loan_amount': '贷款金额',
            'loan_term': '贷款期限'
        }

        for field, label in required_fields.items():
            if field not in data:
                return jsonify({'error': f'缺少必需字段: {label}'}), 400

        # 验证数值字段
        numeric_fields = {
            'loan_amount': {'min': 1000, 'max': 1000000, 'label': '贷款金额'},
            'loan_term': {'min': 1, 'max': 60, 'label': '贷款期限'}
        }

        for field, limits in numeric_fields.items():
            try:
                value = float(data[field])
                if 'min' in limits and value < limits['min']:
                    return jsonify({'error': f'{limits["label"]}不能小于{limits["min"]}'}), 400
                if 'max' in limits and value > limits['max']:
                    return jsonify({'error': f'{limits["label"]}不能大于{limits["max"]}'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': f'{limits["label"]}必须是有效的数字'}), 400

        # 计算利率
        interest_rate = calculate_credit_score(data)
        
        # 计算月利率
        monthly_rate = interest_rate / 12
        
        # 计算月还款额（等额本息）
        loan_amount = float(data['loan_amount'])
        loan_term = int(data['loan_term'])
        monthly_payment = (loan_amount * monthly_rate * (1 + monthly_rate) ** loan_term) / ((1 + monthly_rate) ** loan_term - 1)
        
        # 计算总利息
        total_interest = monthly_payment * loan_term - loan_amount
        
        return jsonify({
            'interest_rate': interest_rate,
            'monthly_payment': monthly_payment,
            'total_interest': total_interest,
            'total_payment': loan_amount + total_interest
        })
    except Exception as e:
        return jsonify({'error': f'计算失败: {str(e)}'}), 400

def calculate_credit_score(data):
    """根据贷款额度和期限计算利率"""
    try:
        # 获取贷款额度和期限
        loan_amount = float(data['loan_amount'])
        loan_term = int(data['loan_term'])
        
        # 基础利率
        base_rate = 0.05  # 5%
        
        # 根据贷款额度调整利率
        if loan_amount <= 50000:
            amount_factor = 0.0  # 小额贷款不调整利率
        elif loan_amount <= 100000:
            amount_factor = 0.01  # 增加1%
        elif loan_amount <= 200000:
            amount_factor = 0.02  # 增加2%
        else:
            amount_factor = 0.03  # 增加3%
        
        # 根据贷款期限调整利率
        if loan_term <= 12:
            term_factor = 0.0  # 短期贷款不调整利率
        elif loan_term <= 24:
            term_factor = 0.01  # 增加1%
        elif loan_term <= 36:
            term_factor = 0.02  # 增加2%
        else:
            term_factor = 0.03  # 增加3%
        
        # 计算最终利率
        interest_rate = base_rate + amount_factor + term_factor
        
        # 确保利率在合理范围内
        interest_rate = max(0.05, min(0.15, interest_rate))
        
        app.logger.info(f'贷款额度: {loan_amount}, 期限: {loan_term}, 计算得到的利率: {interest_rate}')
        
        # 返回利率（而不是信用评分）
        return interest_rate
        
    except Exception as e:
        app.logger.error(f'计算利率时发生错误: {str(e)}', exc_info=True)
        # 如果计算出错，返回一个默认的利率
        return 0.08  # 8%

@app.route('/repayment_records')
@login_required
def repayment_records():
    """显示用户的还款记录"""
    try:
        # 获取当前用户的所有贷款申请
        loans = LoanApplication.query.filter_by(user_id=current_user.id).all()
        
        # 获取所有还款记录
        records = []
        for loan in loans:
            loan_records = RepaymentRecord.query.filter_by(loan_id=loan.id).all()
            for record in loan_records:
                records.append({
                    'loan_id': loan.id,
                    'amount': record.amount,
                    'payment_date': record.payment_date,
                    'status': record.status,
                    'loan_amount': loan.amount,
                    'application_date': loan.application_date
                })
        
        # 按还款日期排序
        records.sort(key=lambda x: x['payment_date'], reverse=True)
        
        return render_template('repayment_records.html', records=records)
    except Exception as e:
        app.logger.error(f"获取还款记录失败: {str(e)}")
        flash('获取还款记录失败，请稍后重试', 'danger')
        return redirect(url_for('dashboard'))

def generate_bills(loan):
    """生成贷款账单"""
    amount = float(loan.amount)
    term = loan.term
    monthly_rate = float(loan.interest_rate) / 12
    monthly_payment = float(loan.monthly_payment)
    
    remaining_principal = amount
    current_date = datetime.utcnow()
    
    for period in range(1, term + 1):
        # 计算利息
        interest = remaining_principal * monthly_rate
        
        # 计算本金
        principal = monthly_payment - interest
        
        # 更新剩余本金
        remaining_principal -= principal
        
        # 设置还款日期为每月1号
        if period == 1:
            # 第一个月的还款日期是下个月1号
            if current_date.day > 1:
                # 如果当前日期大于1号，还款日期是下个月1号
                due_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
            else:
                # 如果当前日期小于等于1号，还款日期是本月1号
                due_date = current_date.replace(day=1)
        else:
            # 后续月份的还款日期是每月1号
            due_date = (current_date.replace(day=1) + timedelta(days=32 * period)).replace(day=1)
        
        # 创建账单
        bill = Bill(
            loan_id=loan.id,
            period=period,
            due_date=due_date,
            amount=round(monthly_payment, 2),
            principal=round(principal, 2),
            interest=round(interest, 2),
            remaining_principal=round(remaining_principal if remaining_principal > 0 else 0, 2),
            status='pending'
        )
        
        db.session.add(bill)
    
    db.session.commit()

@app.route('/review_loan/<int:loan_id>', methods=['GET', 'POST'])
@login_required
@role_required(['president'])
def president_review_loan(loan_id):
    loan = LoanApplication.query.get_or_404(loan_id)
    user = User.query.get(loan.user_id)
    
    if request.method == 'POST':
        decision = request.form.get('decision')

        
        if decision in ['approve', 'reject']:
            # 更新贷款状态
            loan.status = 'approved' if decision == 'approve' else 'rejected'
            loan.approved_at = datetime.utcnow()
            loan.approved_by = current_user.id
            
            # 创建通知
            notification = Notification(
                user_id=loan.user_id,
                title='贷款申请审核结果',
                content=f'您的贷款申请（ID: {loan.id}）已被{"批准" if decision == "approve" else "拒绝"}。',
                type='loan_review'
            )
            db.session.add(notification)
            
            # 如果批准，生成还款计划
            if decision == 'approve':
                generate_bills(loan)
            
            db.session.commit()
            flash('贷款申请已审核完成！', 'success')
            return redirect(url_for('president_dashboard'))
        else:
            flash('无效的审核决定！', 'danger')
    
    return render_template('president_review.html', loan=loan, user=user)

@app.route('/loan_detail/<int:loan_id>')
@login_required
def loan_detail(loan_id):
    loan = LoanApplication.query.get_or_404(loan_id)
    user = User.query.get(loan.user_id)
    
    # 检查权限：只有申请人、经理和行长可以查看
    if current_user.role not in ['manager', 'president'] and current_user.id != loan.user_id:
        flash('您没有权限查看此贷款详情', 'danger')
        return redirect(url_for('dashboard'))
    
    # 获取所有账单并按期数排序
    bills = Bill.query.filter_by(loan_id=loan.id).order_by(Bill.period).all()
    
    # 检查是否有逾期账单

    
    return render_template('loan_detail.html', 
                         loan=loan, 
                         user=user, 
                         bills=bills,
                         current_user=current_user)

@app.route('/manager_dashboard')
@login_required
@role_required(['manager'])
def manager_dashboard():
    try:
        app.logger.info("开始获取贷款列表")
        # 获取所有待审核的贷款申请
        pending_loans = LoanApplication.query.all()
        
        # 获取每个贷款申请的用户信息
        loans_with_users = []
        for loan in pending_loans:
            app.logger.debug(f"处理贷款 ID: {loan.id}, 用户 ID: {loan.user_id}")
            user = loan.applicant
            app.logger.debug(f"用户信息: {user.username if user else 'None'}")
            loans_with_users.append({
                'loan': loan,
                'user': user
            })
        
        app.logger.info(f"准备渲染模板，共 {len(loans_with_users)} 个贷款申请")
        return render_template('manager_dashboard.html', loans=loans_with_users, user=current_user)
    except Exception as e:
        app.logger.error(f"获取待审核贷款失败: {str(e)}", exc_info=True)
        flash('获取待审核贷款失败，请稍后重试', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/debug/loans')
@login_required
@role_required(['manager'])
def debug_loans():
    """调试路由：查看所有贷款申请"""
    try:
        all_loans = LoanApplication.query.all()
        loans_info = []
        for loan in all_loans:
            loans_info.append({
                'id': loan.id,
                'user_id': loan.user_id,
                'username': loan.applicant.username if loan.applicant else 'Unknown',
                'amount': loan.amount,
                'term': loan.term,
                'status': loan.status,
                'created_at': loan.created_at
            })
        return jsonify(loans_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/president_dashboard')
@login_required
@role_required(['president'])
def president_dashboard():
    try:
        # 获取所有待审核的贷款申请
        pending_loans = LoanApplication.query.all()
        
        # 获取每个贷款申请的用户信息
        loans_with_users = []
        for loan in pending_loans:
            user = User.query.get(loan.user_id)
            loans_with_users.append({
                'loan': loan,
                'user': user
            })
        
        return render_template('president_dashboard.html', 
                             pending_loans=loans_with_users,
                             user=current_user)
    except Exception as e:
        app.logger.error(f"获取行长仪表板数据失败: {str(e)}", exc_info=True)
        flash('获取数据失败，请稍后重试', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/repay_bill', methods=['POST'])
@login_required
def repay_bill():
    """处理账单还款"""
    try:
        bill_id = request.form.get('bill_id')
        
        if not bill_id:
            flash('账单ID不能为空', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        
        # 获取账单
        bill = Bill.query.get(bill_id)
        if not bill:
            flash('账单不存在', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        
        # 检查账单是否属于当前用户
        if bill.loan.user_id != current_user.id:
            flash('无权操作此账单', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        
        # 检查账单状态
        if bill.status != 'pending' and bill.status != 'overdue':
            flash('账单状态不正确', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        
        # 更新账单状态
        bill.status = 'paid'
        bill.updated_at = datetime.utcnow()
        bill.paid_at = datetime.utcnow()
        
        # 创建还款记录
        repayment = RepaymentRecord(
            loan_id=bill.loan_id,
            amount=bill.amount,
            due_date=bill.due_date,
            payment_date=datetime.utcnow(),
            status='paid'
        )
        
        db.session.add(repayment)
        db.session.commit()
        
        flash('还款成功', 'success')
        return redirect(url_for('loan_detail', loan_id=bill.loan_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'还款失败: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

@app.route('/manager_review_loan/<int:loan_id>', methods=['GET', 'POST'])
@login_required
@role_required(['manager'])
def manager_review_loan(loan_id):
    """经理评估贷款"""
    loan = LoanApplication.query.get_or_404(loan_id)
    user = User.query.get(loan.user_id)
    
    if request.method == 'POST':
        decision = request.form.get('decision')
        
        if decision == 'recommend_approve':
            loan.status = 'recommend_approve'
            loan.assessed_at = datetime.utcnow()
            loan.assessor_id = current_user.id
            flash('贷款申请已通过，等待行长审核', 'success')
        else:
            loan.status = 'recommend_reject'
            loan.assessed_at = datetime.utcnow()
            loan.assessor_id = current_user.id
            flash('贷款申请已拒绝', 'success')
        
        db.session.commit()
        return redirect(url_for('manager_dashboard'))
    
    return render_template('review_loan.html', loan=loan, user=user)

@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    # 检查通知是否属于当前用户
    if notification.user_id != current_user.id:
        flash('无权操作此通知', 'danger')
        return redirect(url_for('dashboard'))
    
    notification.is_read = True
    db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/send_collection_notice/<int:bill_id>', methods=['POST'])
@login_required
@role_required(['manager'])
def send_collection_notice(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    loan = LoanApplication.query.get(bill.loan_id)
    
    # 创建催收通知
    notification = Notification(
        user_id=loan.user_id,
        title='催收提醒',
        content=f'您的第 {bill.period} 期账单已逾期，请尽快还款。逾期金额：{bill.amount}元，逾期天数：{(datetime.utcnow() - bill.due_date).days}天。',
        type='collection'
    )
    
    db.session.add(notification)
    db.session.commit()
    
    flash('催收通知已发送', 'success')
    return redirect(url_for('loan_detail', loan_id=loan.id))

if __name__ == '__main__':
    with app.app_context():
        # 初始化数据库
        db.create_all()
        
        # 启动调度器
        if not scheduler.running:
            scheduler.start()
        
        # 运行应用程序
        app.run(host='0.0.0.0', port=5000, debug=True)