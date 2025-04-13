from datetime import datetime, timedelta
from models import RepaymentRecord, LoanApplication, db
from notification_service import NotificationService


class RepaymentService:
    def __init__(self):
        self.notification_service = NotificationService()

    def generate_repayment_plan(self, loan_application):
        """生成还款计划"""
        loan_amount = loan_application.loan_amount
        loan_term = loan_application.loan_term
        annual_interest_rate = 0.06  # 假设年利率为6%
        monthly_interest_rate = annual_interest_rate / 12

        # 计算等额本息每月还款额
        monthly_payment = (loan_amount * monthly_interest_rate * (1 + monthly_interest_rate) ** loan_term) / \
                         ((1 + monthly_interest_rate) ** loan_term - 1)

        # 生成还款计划
        repayment_plan = []
        remaining_principal = loan_amount
        current_date = datetime.now()

        for month in range(1, loan_term + 1):
            # 计算每月利息
            monthly_interest = remaining_principal * monthly_interest_rate
            # 计算每月本金
            monthly_principal = monthly_payment - monthly_interest
            # 更新剩余本金
            remaining_principal -= monthly_principal

            # 计算还款日期（每月1号）
            due_date = current_date.replace(day=1) + timedelta(days=30 * month)
            if due_date.day != 1:
                due_date = due_date.replace(day=1) + timedelta(days=30)

            repayment_record = RepaymentRecord(
                loan_id=loan_application.id,
                amount=round(monthly_payment, 2),
                due_date=due_date,
                status='pending'
            )
            repayment_plan.append(repayment_record)

        return repayment_plan

    def save_repayment_plan(self, loan_application, repayment_plan):
        """保存还款计划"""
        try:
            for record in repayment_plan:
                db.session.add(record)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

    def process_payment(self, repayment_record_id, payment_amount, payment_date=None):
        """处理还款"""
        if payment_date is None:
            payment_date = datetime.now()

        repayment_record = RepaymentRecord.query.get(repayment_record_id)
        if not repayment_record:
            return False, "还款记录不存在"

        if repayment_record.status != 'pending':
            return False, "该笔还款已处理"

        if payment_amount < repayment_record.amount:
            return False, "还款金额不足"

        # 计算是否逾期
        is_overdue = payment_date > repayment_record.due_date
        if is_overdue:
            # 计算逾期天数
            overdue_days = (payment_date - repayment_record.due_date).days
            # 计算逾期费用（假设每天0.05%）
            repayment_record.late_fee = round(repayment_record.amount * 0.0005 * overdue_days, 2)

        repayment_record.status = 'paid'
        repayment_record.payment_date = payment_date

        try:
            db.session.commit()
            return True, "还款成功"
        except Exception as e:
            db.session.rollback()
            return False, f"还款处理失败: {str(e)}"

    def check_upcoming_payments(self):
        """检查即将到期的还款"""
        upcoming_date = datetime.now() + timedelta(days=7)
        upcoming_payments = RepaymentRecord.query.filter(
            RepaymentRecord.status == 'pending',
            RepaymentRecord.due_date <= upcoming_date,
            RepaymentRecord.due_date > datetime.now()
        ).all()

        for payment in upcoming_payments:
            loan = LoanApplication.query.get(payment.loan_id)
            user = loan.user
            self.notification_service.notify_upcoming_payment(user, payment)

    def check_overdue_payments(self):
        """检查逾期还款"""
        overdue_payments = RepaymentRecord.query.filter(
            RepaymentRecord.status == 'pending',
            RepaymentRecord.due_date < datetime.now()
        ).all()

        for payment in overdue_payments:
            loan = LoanApplication.query.get(payment.loan_id)
            user = loan.user
            self.notification_service.notify_overdue_payment(user, payment)

    def get_repayment_summary(self, loan_id):
        """获取还款汇总信息"""
        records = RepaymentRecord.query.filter_by(loan_id=loan_id).all()
        
        total_amount = sum(r.amount for r in records)
        paid_amount = sum(r.amount for r in records if r.status == 'paid')
        pending_amount = sum(r.amount for r in records if r.status == 'pending')
        overdue_amount = sum(r.amount for r in records if r.status == 'overdue')
        late_fee = sum(r.late_fee for r in records)
        
        return {
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'pending_amount': pending_amount,
            'overdue_amount': overdue_amount,
            'late_fee': late_fee,
            'completion_rate': round(paid_amount / total_amount * 100, 2) if total_amount > 0 else 0
        }

    def get_repayment_history(self, loan_id):
        """获取还款历史记录"""
        return RepaymentRecord.query.filter_by(loan_id=loan_id)\
            .order_by(RepaymentRecord.due_date)\
            .all() 