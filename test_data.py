# 测试数据
from risk_assessment import RiskAssessmentService
import logging


# 配置日志
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 准备更完整的测试数据
data = {
    'age': 25,
    'employment_years': 3,
    'annual_income': 150000,
    'monthly_income': 15000,
    'savings_balance': 50000,
    'total_assets': 0,
    'total_liabilities': 0,
    'credit_cards': 0,
    'existing_loans': 0,
    'monthly_payment': 0,
    'loan_amount': 50000,
    'loan_term': 3,
    'dependents': 3,
    'employment_status': 'employed',
    'marital_status': 'single',
    'education': 'college',
    'home_ownership': 'rent',
    'loan_purpose': 'education',
    'previous_default': 'no'
}

# 初始化服务并评估
service = RiskAssessmentService()
print("\n开始风险评估...")
result = service.assess_loan_application(data)
print("\n评估结果:")
print(result)