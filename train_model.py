import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle
import os
from mock_data import generate_training_data

def train_and_evaluate_model():
    """训练并评估风险评估模型"""
    # 生成训练数据
    print("正在生成训练数据...")
    df = generate_training_data(num_samples=10000)
    
    # 准备特征
    print("正在准备特征...")
    categorical_features = ['education', 'employment_status', 'marital_status', 
                          'home_ownership', 'loan_purpose', 'previous_default']
    
    # 对分类特征进行独热编码
    X = pd.get_dummies(df.drop(['risk_score', 'loan_approved'], axis=1), 
                      columns=categorical_features)
    
    # 保存特征名称
    feature_names = X.columns.tolist()
    print(f"特征名称: {feature_names}")
    
    # 准备目标变量
    y = df['loan_approved']

    sample_weights = np.ones(len(y))
    sample_weights[df['new_loan_payment_ratio'] > 0.5] *= 2
    
    # 分割训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 标准化特征
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 训练随机森林模型
    print("正在训练模型...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_split=20,
        min_samples_leaf=10,
        max_features='sqrt',
        random_state=42
    )
    model.fit(X_train_scaled, y_train)
    
    # 评估模型
    train_score = model.score(X_train_scaled, y_train)
    test_score = model.score(X_test_scaled, y_test)
    print(f"模型训练集准确率: {train_score:.4f}")
    print(f"模型测试集准确率: {test_score:.4f}")
    
    # 保存特征名称
    model.feature_names_in_ = X.columns
    
    # 保存模型和标准化器
    print("正在保存模型...")
    with open('risk_assessment_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    with open('risk_assessment_scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    
    print("模型和标准化器已保存")
    
    return model, scaler, feature_names

if __name__ == "__main__":
    # 训练模型
    model, scaler, feature_names = train_and_evaluate_model() 