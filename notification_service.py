from datetime import datetime
from models import Notification, db
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class NotificationService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.example.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.email_enabled = bool(self.smtp_username and self.smtp_password)

    def create_notification(self, user_id, title, content, notification_type):
        """创建系统通知"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                content=content,
                type=notification_type,
                is_read=False
            )
            db.session.add(notification)
            db.session.commit()
            return notification
        except Exception as e:
            print(f"创建通知失败: {str(e)}")
            return None

    def send_email_notification(self, to_email, subject, content):
        """发送邮件通知"""
        if not self.email_enabled:
            print("邮件通知未启用：SMTP 配置缺失")
            return False

        msg = MIMEMultipart()
        msg['From'] = self.smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(content, 'html'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"发送邮件失败: {str(e)}")
            return False

    def notify_loan_application_submitted(self, user, loan_application):
        """通知贷款申请已提交"""
        try:
            title = "贷款申请已提交"
            content = f"您的贷款申请（金额：{loan_application.amount}元）已成功提交，请等待审核。"
            
            # 创建系统通知
            notification = self.create_notification(user.id, title, content, "application")
            if not notification:
                print("创建系统通知失败")
                return False
            
            # 如果启用了邮件通知，发送邮件
            if self.email_enabled and user.email:
                email_content = f"""
                <html>
                    <body>
                        <h2>贷款申请已提交</h2>
                        <p>尊敬的{user.username}：</p>
                        <p>您的贷款申请已成功提交，详情如下：</p>
                        <ul>
                            <li>申请金额：{loan_application.amount}元</li>
                            <li>贷款期限：{loan_application.term}个月</li>
                            <li>申请时间：{loan_application.created_at.strftime('%Y-%m-%d %H:%M:%S')}</li>
                        </ul>
                        <p>请等待审核结果，我们会通过系统通知您最新进展。</p>
                    </body>
                </html>
                """
                self.send_email_notification(user.email, title, email_content)
            
            return True
        except Exception as e:
            print(f"发送贷款申请通知失败: {str(e)}")
            return False

    def notify_loan_status_update(self, user, loan_application):
        """通知贷款状态更新"""
        status_messages = {
            "manager_review": "客户经理正在审核您的贷款申请",
            "president_review": "行长正在审核您的贷款申请",
            "approved": "恭喜！您的贷款申请已通过审核",
            "rejected": "很抱歉，您的贷款申请未通过审核"
        }
        
        title = "贷款申请状态更新"
        content = status_messages.get(loan_application.status, "贷款申请状态已更新")
        self.create_notification(user.id, title, content, "application")
        
        # 发送邮件通知
        email_content = f"""
        <html>
            <body>
                <h2>贷款申请状态更新</h2>
                <p>尊敬的{user.username}：</p>
                <p>{content}</p>
                <p>申请详情：</p>
                <ul>
                    <li>申请金额：{loan_application.loan_amount}元</li>
                    <li>贷款期限：{loan_application.loan_term}个月</li>
                    <li>当前状态：{loan_application.status}</li>
                </ul>
            </body>
        </html>
        """
        self.send_email_notification(user.email, title, email_content)

    def notify_upcoming_payment(self, user, repayment_record):
        """通知即将到期的还款"""
        title = "还款提醒"
        content = f"您有一笔{repayment_record.amount}元的还款将于{repayment_record.due_date.strftime('%Y-%m-%d')}到期，请及时还款。"
        self.create_notification(user.id, title, content, "repayment")
        
        # 发送邮件通知
        email_content = f"""
        <html>
            <body>
                <h2>还款提醒</h2>
                <p>尊敬的{user.username}：</p>
                <p>您有一笔还款即将到期，详情如下：</p>
                <ul>
                    <li>还款金额：{repayment_record.amount}元</li>
                    <li>到期日期：{repayment_record.due_date.strftime('%Y-%m-%d')}</li>
                </ul>
                <p>请确保在到期日前完成还款，以免产生逾期费用。</p>
            </body>
        </html>
        """
        self.send_email_notification(user.email, title, email_content)

    def notify_overdue_payment(self, user, repayment_record):
        """通知逾期还款"""
        title = "还款逾期提醒"
        content = f"您有一笔{repayment_record.amount}元的还款已逾期，请尽快还款以避免产生更多费用。"
        self.create_notification(user.id, title, content, "repayment")
        
        # 发送邮件通知
        email_content = f"""
        <html>
            <body>
                <h2>还款逾期提醒</h2>
                <p>尊敬的{user.username}：</p>
                <p>您有一笔还款已逾期，详情如下：</p>
                <ul>
                    <li>还款金额：{repayment_record.amount}元</li>
                    <li>到期日期：{repayment_record.due_date.strftime('%Y-%m-%d')}</li>
                    <li>逾期天数：{(datetime.now() - repayment_record.due_date).days}天</li>
                </ul>
                <p>请尽快完成还款，逾期将产生额外费用并影响您的信用记录。</p>
            </body>
        </html>
        """
        self.send_email_notification(user.email, title, email_content)

    def get_unread_notifications(self, user_id):
        """获取用户未读通知"""
        return Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).order_by(Notification.created_at.desc()).all()

    def mark_notification_as_read(self, notification_id):
        """标记通知为已读"""
        notification = Notification.query.get(notification_id)
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        return False 