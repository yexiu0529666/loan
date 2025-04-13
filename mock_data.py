import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
import os
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Number of samples
num_samples = 2000

# Seed for reproducibility
np.random.seed(42)


def generate_training_data(num_samples=num_samples):
    """生成用于训练风险评估模型的模拟数据"""
    np.random.seed(42)

    # 数值特征
    age = np.random.normal(35, 10, num_samples).clip(18, 70).astype(int)
    employment_years = np.random.poisson(5, num_samples).clip(0, 30).astype(int)
    annual_income = np.random.lognormal(11, 0.4, num_samples).clip(200000, 2000000).astype(int)
    monthly_income = annual_income / 12
    savings_balance = np.random.lognormal(8, 0.8, num_samples).clip(1000, 500000).astype(int)
    total_assets = np.random.lognormal(11, 0.8, num_samples).clip(50000, 5000000).astype(int)
    total_liabilities = np.random.lognormal(10, 0.8, num_samples).clip(10000, 1000000).astype(int)
    credit_cards = np.random.poisson(2, num_samples).clip(0, 8).astype(int)
    existing_loans = np.random.lognormal(9, 0.6, num_samples).clip(0, 500000).astype(int)
    monthly_payment = np.random.lognormal(6, 0.5, num_samples).clip(500, 5000).astype(int)
    loan_amount = np.random.lognormal(9.5, 0.7, num_samples).clip(10000, 1000000)
    loan_term = np.random.choice([3,6,12, 24, 36], num_samples)
    dependents = np.random.poisson(1, num_samples).clip(0, 5).astype(int)

    # 确保总资产 >= 储蓄
    total_assets = np.maximum(total_assets, savings_balance)

    # 分类特征
    marital_status = np.random.choice(['single', 'married', 'divorced', 'widowed'],
                                     num_samples, p=[0.3, 0.5, 0.15, 0.05])
    education = np.random.choice(['high_school', 'college', 'bachelor', 'master', 'phd'],
                                num_samples, p=[0.2, 0.3, 0.3, 0.15, 0.05])
    employment_status = np.random.choice(['employed', 'self_employed', 'unemployed', 'retired'],
                                        num_samples, p=[0.6, 0.2, 0.1, 0.1])
    home_ownership = np.random.choice(['own', 'mortgage', 'rent', 'other'],
                                     num_samples, p=[0.2, 0.4, 0.3, 0.1])
    loan_purpose = np.random.choice(['business', 'education', 'home', 'car', 'debt_consolidation', 'other'],
                                   num_samples, p=[0.2, 0.1, 0.2, 0.2, 0.2, 0.1])
    previous_default = np.random.choice(['yes', 'no'], num_samples, p=[0.15, 0.85])

    # 计算衍生特征
    debt_to_income = monthly_payment / (monthly_income + 1e-6)
    new_loan_monthly_payment = loan_amount / loan_term
    new_loan_payment_ratio = new_loan_monthly_payment / monthly_income

    new_loan_payment_ratio_binned = np.zeros(num_samples)
    new_loan_payment_ratio_binned[(new_loan_payment_ratio > 0.1) & (new_loan_payment_ratio <= 0.5)] = 1
    new_loan_payment_ratio_binned[(new_loan_payment_ratio > 0.5) & (new_loan_payment_ratio <= 1)] = 2
    new_loan_payment_ratio_binned[(new_loan_payment_ratio > 1) & (new_loan_payment_ratio <= 2)] = 3
    new_loan_payment_ratio_binned[(new_loan_payment_ratio > 2) & (new_loan_payment_ratio <= 5)] = 4
    new_loan_payment_ratio_binned[(new_loan_payment_ratio > 5) & (new_loan_payment_ratio <= 10)] = 5
    new_loan_payment_ratio_binned[new_loan_payment_ratio > 10] = 6

    ratio_times_debt = new_loan_payment_ratio * debt_to_income

    # 贷款批准逻辑
    penalty = 1 / (1 + np.exp(-15 * (new_loan_payment_ratio - 0.3)))
    risk_score = (
                         0.1 * (annual_income / 2000000) +
                         0.1 * (previous_default == 'no').astype(float) +
                         0.15 * (1 - debt_to_income.clip(0, 1)) +
                         0.65 * (1 - penalty)
                 ) * 100
    loan_approved = (risk_score < 30).astype(int)

    # 添加噪声
    flip = np.random.choice([0, 1], num_samples, p=[0.9, 0.1])
    loan_approved = np.where(flip, 1 - loan_approved, loan_approved)

    # 创建数据框
    data = {
        'age': age,
        'employment_years': employment_years,
        'annual_income': annual_income,
        'monthly_income': monthly_income,
        'savings_balance': savings_balance,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'credit_cards': credit_cards,
        'existing_loans': existing_loans,
        'monthly_payment': monthly_payment,
        'loan_amount': loan_amount,
        'loan_term': loan_term,
        'dependents': dependents,
        'marital_status': marital_status,
        'education': education,
        'employment_status': employment_status,
        'home_ownership': home_ownership,
        'loan_purpose': loan_purpose,
        'previous_default': previous_default,
        'debt_to_income': debt_to_income,
        'new_loan_payment_ratio': new_loan_payment_ratio,
        'new_loan_payment_ratio_binned': new_loan_payment_ratio_binned,
        'ratio_times_debt': ratio_times_debt,
        'risk_score': risk_score,
        'loan_approved': loan_approved
    }

    df = pd.DataFrame(data)
    df.to_csv('loan_data.csv', index=False)
    print(f"生成了 {num_samples} 条模拟贷款数据，保存到 loan_data.csv")

    return df

def generate_sample_application():
    """生成一个样本贷款申请数据"""
    # 生成基本特征
    age = np.random.randint(18, 70)
    annual_income = int(np.random.lognormal(11, 0.4))
    monthly_income = annual_income / 12
    employment_years = min(max(int(np.random.poisson(5)), 0), 40)

    # 生成分类特征
    education = np.random.choice(['high_school', 'college', 'bachelor', 'master', 'phd'],
                                p=[0.2, 0.3, 0.3, 0.15, 0.05])
    employment_status = np.random.choice(['employed', 'self_employed', 'unemployed', 'retired'],
                                        p=[0.6, 0.2, 0.1, 0.1])
    marital_status = np.random.choice(['single', 'married', 'divorced', 'widowed'],
                                     p=[0.3, 0.5, 0.15, 0.05])
    home_ownership = np.random.choice(['own', 'mortgage', 'rent', 'other'],
                                     p=[0.2, 0.4, 0.3, 0.1])
    loan_purpose = np.random.choice(['business', 'education', 'home', 'car', 'debt_consolidation', 'other'],
                                   p=[0.2, 0.1, 0.2, 0.2, 0.2, 0.1])
    previous_default = np.random.choice(['yes', 'no'], p=[0.15, 0.85])

    # 生成数值特征
    dependents = min(max(int(np.random.poisson(1)), 0), 5)
    loan_amount = int(np.random.lognormal(8, 0.5))  # 类似 Bill 表
    loan_term = np.random.choice([12, 24, 36, 48, 60])
    monthly_payment = int(np.random.lognormal(6, 0.5))
    credit_cards = min(max(int(np.random.poisson(2)), 0), 8)
    existing_loans = int(np.random.lognormal(9, 0.6))
    savings_balance = int(np.random.lognormal(8, 0.8))
    total_assets = int(np.random.lognormal(11, 0.8))
    total_liabilities = int(np.random.lognormal(10, 0.8))

    # 确保总资产 >= 储蓄
    total_assets = max(total_assets, savings_balance)

    # 生成信用评分（模型可能用，但不影响批准）
    credit_score = int(min(max(np.random.normal(650, 80), 300), 850))

    # 返回样本数据
    return {
        'age': age,
        'annual_income': annual_income,
        'monthly_income': monthly_income,
        'employment_years': employment_years,
        'education': education,
        'employment_status': employment_status,
        'marital_status': marital_status,
        'home_ownership': home_ownership,
        'dependents': dependents,
        'loan_amount': loan_amount,
        'loan_term': loan_term,
        'monthly_payment': monthly_payment,
        'credit_cards': credit_cards,
        'existing_loans': existing_loans,
        'loan_purpose': loan_purpose,
        'previous_default': previous_default,
        'savings_balance': savings_balance,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'credit_score': credit_score
    }

if __name__ == "__main__":
    # 生成训练数据
    df = generate_training_data()

