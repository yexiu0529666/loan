import os
import pickle

import numpy as np
import pandas as pd
import logging


class RiskAssessmentService:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = None
        
        # 设置日志记录器
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('\n%(asctime)s - %(name)s - %(levelname)s\n%(message)s\n')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        self.load_model()
    
    def load_model(self):
        """加载风险评估模型和标准化器"""
        try:
            model_path = 'risk_assessment_model.pkl'
            scaler_path = 'risk_assessment_scaler.pkl'
            
            self.logger.info(f"尝试加载模型文件: {model_path}")
            self.logger.info(f"尝试加载标准化器文件: {scaler_path}")
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                    self.logger.info("成功加载模型")
                    
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                    self.logger.info("成功加载标准化器")
                
                # 从模型中获取特征名称
                if hasattr(self.model, 'feature_names_in_'):
                    self.feature_names = self.model.feature_names_in_.tolist()
                    self.logger.info(f"从模型中获取特征名称: {self.feature_names}")
                else:
                    # 使用实际的特征名称
                    self.feature_names = [
                        'age', 'employment_years', 'annual_income', 'monthly_income',
                        'savings_balance', 'total_assets', 'total_liabilities',
                        'credit_cards', 'existing_loans', 'monthly_payment',
                        'loan_amount', 'loan_term', 'dependents', 'credit_score',
                        'marital_status_single', 'marital_status_married', 'marital_status_divorced', 'marital_status_widowed',
                        'education_high_school', 'education_college', 'education_bachelor', 'education_master', 'education_phd',
                        'employment_status_employed', 'employment_status_self_employed', 'employment_status_unemployed', 'employment_status_retired',
                        'home_ownership_own', 'home_ownership_rent', 'home_ownership_mortgage', 'home_ownership_other',
                        'loan_purpose_business', 'loan_purpose_education', 'loan_purpose_home', 'loan_purpose_car', 'loan_purpose_debt_consolidation', 'loan_purpose_other',
                        'previous_default_yes', 'previous_default_no'
                    ]
                    self.logger.info("使用默认特征名称列表")
                
                # 验证模型和标准化器
                if not hasattr(self.model, 'predict_proba'):
                    raise AttributeError("模型缺少 predict_proba 方法")
                if not hasattr(self.scaler, 'transform'):
                    raise AttributeError("标准化器缺少 transform 方法")
                
                self.logger.info("模型和标准化器验证成功")
            else:
                if not os.path.exists(model_path):
                    self.logger.error(f"模型文件不存在: {model_path}")
                if not os.path.exists(scaler_path):
                    self.logger.error(f"标准化器文件不存在: {scaler_path}")
                self.logger.warning("将使用默认风险评估方法")
                
        except Exception as e:
            self.logger.error(f"加载模型时出错: {str(e)}")
            self.model = None
            self.scaler = None
            self.feature_names = None

    def calculate_risk_score(self, data):
        """计算风险分数"""
        try:
            if self.model is not None and self.scaler is not None:
                # 准备特征数据
                features = self._prepare_features(data)
                
                # 将特征转换为 DataFrame，并确保列顺序正确
                df = pd.DataFrame([features])
                
                # 确保列顺序与训练时一致
                if hasattr(self.model, 'feature_names_in_'):
                    required_features = self.model.feature_names_in_.tolist()
                else:
                    required_features = self.feature_names
                
                self.logger.debug(f"模型期望的特征顺序: {required_features}")
                self.logger.debug(f"当前特征顺序: {df.columns.tolist()}")
                
                # 重新排序列
                df = df[required_features]
                
                # 标准化特征
                X = self.scaler.transform(df)
                
                # 预测风险概率
                risk_prob = self.model.predict_proba(X)[0][1]

                # 显式公式
                ratio = features['new_loan_payment_ratio']
                penalty = 1 / (1 + np.exp(-15 * (ratio - 0.3)))  # 更早、更强惩罚
                explicit_score = (
                                         0.1 * (features['annual_income'] / 2000000) +
                                         0.1 * features['previous_default_no'] +
                                         0.15 * (1 - min(max(features['debt_to_income'], 0), 1)) +
                                         0.65 * (1 - penalty)  # 反转penalty，增大权重
                                 ) * 100


                self.logger.info(f"使用模型计算的风险分数: {100-int(explicit_score)}")
                return int(explicit_score)
            else:
                risk_score = self._calculate_default_risk_score(data)
                self.logger.info(f"使用默认方法计算的风险分数: {risk_score}")
                return risk_score
        except Exception as e:
             self.logger.error(f"计算风险分数时出错: {str(e)}")
             return self._calculate_default_risk_score(data)

    def _prepare_features(self, data):
        """准备特征数据"""
        features = {}
        self.logger.debug(f"开始准备特征，输入数据: {data}")

        # 确保特征顺序与训练时一致
        if self.feature_names is None:
            self.logger.error("特征名称列表未初始化")
            return features

        # 数值特征
        numeric_features = [
            'age', 'employment_years', 'annual_income', 'monthly_income',
            'savings_balance', 'total_assets', 'total_liabilities',
            'credit_cards', 'existing_loans', 'monthly_payment',
            'loan_amount', 'loan_term', 'dependents', 'credit_score',
            'debt_to_income', 'new_loan_monthly_payment', 'new_loan_payment_ratio',
            'new_loan_payment_ratio_binned', 'ratio_times_debt'
        ]
        for feature in numeric_features:
            try:
                if feature == 'debt_to_income':
                    value = data.get('monthly_payment', 0) / (data.get('monthly_income', 1) + 1e-6)
                elif feature == 'new_loan_payment_ratio':
                    value = (data.get('loan_amount', 0) / data.get('loan_term', 1)) / (
                                data.get('monthly_income', 1) + 1e-6)
                elif feature == 'new_loan_payment_ratio_binned':
                    ratio = (data.get('loan_amount', 0) / data.get('loan_term', 1)) / (
                            data.get('monthly_income', 1) + 1e-6)
                    if ratio <= 0.1:
                        value = 0
                    elif ratio <= 0.5:
                        value = 1
                    elif ratio <= 1:
                        value = 2
                    elif ratio <= 2:
                        value = 3
                    elif ratio <= 5:
                        value = 4
                    elif ratio <= 10:
                        value = 5
                    else:
                        value = 6
                elif feature == 'ratio_times_debt':
                    ratio = (data.get('loan_amount', 0) / data.get('loan_term', 1)) / (
                            data.get('monthly_income', 1) + 1e-6)
                    debt = data.get('monthly_payment', 0) / (data.get('monthly_income', 1) + 1e-6)
                    value = ratio * debt
                else:
                    value = data.get(feature)
                self.logger.debug(f"处理数值特征 {feature}, 原始值: {value}")
                features[feature] = float(value) if value is not None else 0.0
                self.logger.debug(f"处理后的值: {features[feature]}")
            except Exception as e:
                self.logger.error(f"处理数值特征 {feature} 时出错: {str(e)}")
                features[feature] = 0.0


        # 分类特征及其可能值
        categorical_features = {
            'marital_status': ['single', 'married', 'divorced', 'widowed'],
            'education': ['high_school', 'college', 'bachelor', 'master', 'phd'],
            'employment_status': ['employed', 'self_employed', 'unemployed', 'retired'],
            'home_ownership': ['own', 'rent', 'mortgage', 'other'],
            'loan_purpose': ['business', 'education', 'home', 'car', 'debt_consolidation', 'other'],
            'previous_default': ['yes', 'no']
        }

        # 独热编码
        for feature, values in categorical_features.items():
            try:
                value = str(data.get(feature, 'unknown')).lower()
                self.logger.debug(f"处理分类特征 {feature}, 原始值: {value}")
                for v in values:
                    features[f"{feature}_{v}"] = 1 if value == v else 0
                    self.logger.debug(f"独热编码 {feature}_{v}: {features[f'{feature}_{v}']}")
            except Exception as e:
                self.logger.error(f"处理分类特征 {feature} 时出错: {str(e)}")
                for v in values:
                    features[f"{feature}_{v}"] = 0

        # 确保所有特征都存在，并按正确顺序排列
        ordered_features = {}
        for feature_name in self.feature_names:
            if feature_name in features:
                ordered_features[feature_name] = features[feature_name]
            else:
                self.logger.warning(f"特征 {feature_name} 不存在，使用默认值 0")
                ordered_features[feature_name] = 0.0

        self.logger.debug(f"特征准备完成，最终特征: {ordered_features}")
        return ordered_features
    
    def _calculate_default_credit_score(self, data):
        """使用默认方法计算信用分数"""
        score = 600  # 基础分
        
        # 根据月收入调整分数
        monthly_income = float(data.get('monthly_income', 0))
        if monthly_income >= 10000:
            score += 50
        elif monthly_income >= 5000:
            score += 30
        elif monthly_income >= 3000:
            score += 10
        
        # 根据负债比率调整分数
        monthly_debt = float(data.get('monthly_debt', 0))
        if monthly_income > 0:
            debt_ratio = monthly_debt / monthly_income
            if debt_ratio <= 0.3:
                score += 30
            elif debt_ratio <= 0.5:
                score += 10
            elif debt_ratio > 0.7:
                score -= 20
        
        # 根据资产状况调整分数
        total_assets = float(data.get('total_assets', 0))
        total_liabilities = float(data.get('total_liabilities', 0))
        if total_assets > total_liabilities:
            score += 20
        
        # 根据就业状况调整分数
        employment_status = data.get('employment_status', 'unknown')
        if employment_status == 'employed':
            score += 20
        elif employment_status == 'self_employed':
            score += 10
        
        # 确保分数在300-850之间
        score = max(300, min(850, score))
        
        return score
    
    def _calculate_default_risk_score(self, data):
        """使用默认方法计算风险分数"""
        score = 50  # 基础分
        
        # 根据贷款额度调整分数
        loan_amount = float(data.get('loan_amount', 0))
        if loan_amount <= 50000:
            score += 10
        elif loan_amount <= 100000:
            score += 5
        elif loan_amount > 200000:
            score -= 10
        
        # 根据贷款期限调整分数
        loan_term = int(data.get('loan_term', 12))
        if loan_term <= 12:
            score += 10
        elif loan_term <= 24:
            score += 5
        elif loan_term > 36:
            score -= 10
        
        # 根据月收入与月还款比例调整分数
        monthly_income = float(data.get('monthly_income', 0))
        monthly_payment = float(data.get('monthly_payment', 0))
        if monthly_income > 0:
            payment_ratio = monthly_payment / monthly_income
            if payment_ratio <= 0.3:
                score += 10
            elif payment_ratio <= 0.5:
                score += 5
            elif payment_ratio > 0.7:
                score -= 10
        
        # 确保分数在0-100之间
        score = max(0, min(100, score))
        
        return score
    
    def get_risk_level(self, risk_score):
        """根据风险分数确定风险等级"""
        if risk_score < 30:
            return '低风险'
        elif risk_score < 60:
            return '中风险'
        elif risk_score < 80:
            return '高风险'
        else:
            return '极高风险'
    
    def get_risk_recommendation(self, risk_score):
        """根据风险分数提供建议"""
        if risk_score < 30:
            return {
                'recommendation': '建议批准贷款',
                'suggestions': [
                    '可以适当提高贷款额度',
                    '可以考虑降低利率',
                    '可以延长贷款期限'
                ]
            }
        elif risk_score < 60:
            return {
                'recommendation': '建议谨慎批准贷款',
                'suggestions': [
                    '建议保持当前贷款额度',
                    '建议保持标准利率',
                    '建议保持标准贷款期限'
                ]
            }
        elif risk_score < 80:
            return {
                'recommendation': '建议拒绝贷款或增加担保',
                'suggestions': [
                    '建议降低贷款额度',
                    '建议提高利率',
                    '建议缩短贷款期限',
                    '建议增加担保要求'
                ]
            }
        else:
            return {
                'recommendation': '建议拒绝贷款',
                'suggestions': [
                    '风险过高，不建议批准贷款',
                    '建议客户改善财务状况后再申请'
                ]
            }
    
    def assess_loan_application(self, application_data):
        """评估贷款申请"""
        try:
            # 计算风险分数
            risk_score = 100 - self.calculate_risk_score(application_data)
            
            # 确定风险等级
            risk_level = self.get_risk_level(risk_score)
            
            # 获取建议
            recommendation = self.get_risk_recommendation(risk_score)
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'recommendation': recommendation
            }
        except Exception as e:
            self.logger.error(f"评估贷款申请时出错: {str(e)}")
            return {
                'risk_score': 50,  # 默认风险分数
                'risk_level': '中风险',
                'recommendation': {
                    'recommendation': '需要进一步评估',
                    'suggestions': ['系统评估出错，需要人工审核']
                }
            } 