import os
from datetime import datetime
from werkzeug.utils import secure_filename
from models import CreditReport, db
import PyPDF2
import re

class CreditReportService:
    def __init__(self):
        self.upload_folder = 'uploads/credit_reports'
        self.allowed_extensions = {'pdf'}
        self._ensure_upload_folder()

    def _ensure_upload_folder(self):
        """确保上传文件夹存在"""
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

    def allowed_file(self, filename):
        """检查文件类型是否允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def save_credit_report(self, file, user_id):
        """保存征信报告文件"""
        if not file or not self.allowed_file(file.filename):
            return None, "不支持的文件类型"

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{user_id}_{timestamp}_{filename}"
        file_path = os.path.join(self.upload_folder, unique_filename)

        try:
            file.save(file_path)
            return file_path, None
        except Exception as e:
            return None, f"文件保存失败: {str(e)}"

    def create_credit_report_record(self, user_id, file_path):
        """创建征信报告记录"""
        credit_report = CreditReport(
            user_id=user_id,
            file_path=file_path,
            upload_date=datetime.now(),
            is_valid=False
        )
        db.session.add(credit_report)
        db.session.commit()
        return credit_report

    def validate_credit_report(self, file_path):
        """验证征信报告的有效性"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # 检查PDF是否加密
                if pdf_reader.is_encrypted:
                    return False, "征信报告文件已加密，无法读取"
                
                # 提取文本内容
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                # 检查关键信息
                required_fields = [
                    "个人基本信息",
                    "信贷交易信息",
                    "公共信息",
                    "查询记录"
                ]
                
                missing_fields = [field for field in required_fields if field not in text]
                if missing_fields:
                    return False, f"征信报告缺少必要字段: {', '.join(missing_fields)}"
                
                # 检查报告日期
                date_pattern = r"报告日期：(\d{4}年\d{1,2}月\d{1,2}日)"
                date_match = re.search(date_pattern, text)
                if not date_match:
                    return False, "无法找到报告日期"
                
                report_date = datetime.strptime(date_match.group(1), "%Y年%m月%d日")
                if (datetime.now() - report_date).days > 30:
                    return False, "征信报告已超过30天，请上传最新报告"
                
                return True, "征信报告验证通过"
                
        except Exception as e:
            return False, f"征信报告验证失败: {str(e)}"

    def update_credit_report_status(self, credit_report_id, is_valid, validation_comment):
        """更新征信报告状态"""
        credit_report = CreditReport.query.get(credit_report_id)
        if credit_report:
            credit_report.is_valid = is_valid
            credit_report.validation_comment = validation_comment
            db.session.commit()
            return True
        return False

    def get_user_credit_reports(self, user_id):
        """获取用户的征信报告列表"""
        return CreditReport.query.filter_by(user_id=user_id)\
            .order_by(CreditReport.upload_date.desc())\
            .all()

    def delete_credit_report(self, credit_report_id):
        """删除征信报告"""
        credit_report = CreditReport.query.get(credit_report_id)
        if credit_report:
            try:
                # 删除文件
                if os.path.exists(credit_report.file_path):
                    os.remove(credit_report.file_path)
                
                # 删除数据库记录
                db.session.delete(credit_report)
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
                return False
        return False 