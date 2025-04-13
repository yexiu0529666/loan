import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib
import os

class RiskAssessment:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.load_model()
        
    def load_model(self):
        model_path = 'models/risk_model.pkl'
        scaler_path = 'models/scaler.pkl'
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
        else:
            self.train_model()
            
    def train_model(self):
        # 这里可以添加模型训练逻辑
        pass

    def preprocess_data(self, app):
        numeric_features = [
            app.loan_amount,
            app.loan_term,
            app.annual_income,
            app.credit_score,
            app.debt_total
        ]
        scaled_features = self.scaler.transform([numeric_features])[0]
        occupation_onehot = [1 if app.occupation == i else 0 for i in range(3)]
        repayment_onehot = [1 if app.repayment_history == i else 0 for i in range(3)]
        return np.hstack((scaled_features, occupation_onehot, repayment_onehot))

    def assess_risk(self, app):
        input_data = self.preprocess_data(app)
        input_data = np.array([input_data])
        risk_score = self.model.predict(input_data, verbose=0)[0][0]
        return {
            'risk_score': float(risk_score),
            'suggestion': "通过" if risk_score < 0.5 else "拒绝",
            'risk_level': self._get_risk_level(risk_score),
            'risk_factors': self._analyze_risk_factors(app, risk_score)
        }

    def _get_risk_level(self, risk_score):
        if risk_score < 0.3:
            return "低风险"
        elif risk_score < 0.6:
            return "中风险"
        else:
            return "高风险"

    def _analyze_risk_factors(self, app, risk_score):
        factors = []
        if app.debt_total / app.annual_income > 0.5:
            factors.append("负债收入比过高")
        if app.credit_score < 600:
            factors.append("信用评分较低")
        if app.repayment_history == 2:  # 假设2表示有逾期记录
            factors.append("有还款逾期记录")
        return factors

    def predict_repayment_risk(self, loan, repayment_records):
        """预测还款风险"""
        if not repayment_records:
            return "无还款记录"
            
        # 计算逾期率
        overdue_count = sum(1 for r in repayment_records if r.status == 'overdue')
        overdue_rate = overdue_count / len(repayment_records)
        
        # 计算最近还款情况
        recent_records = sorted(repayment_records, key=lambda x: x.due_date, reverse=True)[:3]
        recent_overdue = sum(1 for r in recent_records if r.status == 'overdue')
        
        if overdue_rate > 0.3 or recent_overdue > 1:
            return "高风险"
        elif overdue_rate > 0.1 or recent_overdue > 0:
            return "中风险"
        else:
            return "低风险"

    def generate_early_warning(self, loan, repayment_records):
        """生成早期预警"""
        warnings = []
        
        # 检查即将到期的还款
        upcoming_payments = [r for r in repayment_records 
                           if r.status == 'pending' 
                           and r.due_date - datetime.now() < timedelta(days=7)]
        if upcoming_payments:
            warnings.append({
                'type': 'upcoming_payment',
                'message': f'有{len(upcoming_payments)}笔还款即将到期',
                'severity': 'info'
            })
            
        # 检查逾期情况
        overdue_payments = [r for r in repayment_records if r.status == 'overdue']
        if overdue_payments:
            warnings.append({
                'type': 'overdue',
                'message': f'有{len(overdue_payments)}笔还款已逾期',
                'severity': 'warning'
            })
            
        # 检查风险趋势
        risk_level = self.predict_repayment_risk(loan, repayment_records)
        if risk_level in ['高风险', '中风险']:
            warnings.append({
                'type': 'risk_trend',
                'message': f'还款风险等级：{risk_level}',
                'severity': 'warning' if risk_level == '高风险' else 'info'
            })
            
        return warnings