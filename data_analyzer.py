"""
data_analyzer.py - AI Data Analysis Module for AgriSense
Phân tích câu hỏi và tạo dữ liệu thông minh cho biểu đồ
"""
import re
import json
import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import google.generativeai as genai

@dataclass
class ChartData:
    """Cấu trúc dữ liệu cho biểu đồ"""
    chart_type: str  # 'bar', 'line', 'pie', 'doughnut', 'mixed'
    title: str
    subtitle: str
    labels: List[str]
    datasets: List[Dict[str, Any]]
    metrics: List[Dict[str, Any]]  # Các chỉ số bổ sung
    expert_data: Optional[Dict[str, Any]] = None

@dataclass
class AnalysisResult:
    """Kết quả phân tích câu hỏi"""
    category: str  # livestock, crops, weather, economics, etc.
    subcategory: str  # heo, gà, lúa, ngô, etc.
    chart_configs: List[ChartData]
    confidence: float  # Độ tin cậy của phân tích (0-1)
    keywords: List[str]
    time_period: Optional[str] = None  # '2024', 'last_year', 'monthly', etc.

class AgriDataAnalyzer:
    def __init__(self, gemini_api_key: str = None):
        """Khởi tạo AI Data Analyzer"""
        self.gemini_api_key = gemini_api_key
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Database mẫu - trong thực tế sẽ kết nối database thật
        self.data_sources = {
            'livestock': self._load_livestock_data(),      # Gia súc - 4 chân
            'poultry': self._load_poultry_data(),         # Gia cầm - 2 chân
            'animal_husbandry': self._load_livestock_data(),  # Chăn nuôi tổng hợp
            'crops': self._load_crops_data(),
            'economics': self._load_economics_data(),
            'weather': self._load_weather_data(),
            'fertilizer': self._load_fertilizer_data(),
            'irrigation': self._load_irrigation_data()
        }
        
        # Patterns để phân tích câu hỏi
        self.analysis_patterns = self._load_analysis_patterns()
    
    def analyze_question(self, question: str, use_ai: bool = True) -> AnalysisResult:
        """
        Phân tích câu hỏi và trả về cấu hình dữ liệu cho biểu đồ
        """
        print(f"🔍 Analyzing question: {question}")
        
        # Bước 1: Phân tích cơ bản với patterns
        basic_analysis = self._basic_pattern_analysis(question)
        
        # Bước 2: Sử dụng AI để phân tích sâu hơn (nếu có)
        if use_ai and self.gemini_api_key:
            ai_analysis = self._ai_enhanced_analysis(question, basic_analysis)
            analysis = ai_analysis
        else:
            analysis = basic_analysis
        
        # Bước 3: Tạo cấu hình biểu đồ dựa trên phân tích
        chart_configs = self._generate_chart_configs(analysis, question)
        
        return AnalysisResult(
            category=analysis['category'],
            subcategory=analysis['subcategory'],
            chart_configs=chart_configs,
            confidence=analysis['confidence'],
            keywords=analysis['keywords'],
            time_period=analysis.get('time_period')
        )
    
    def _basic_pattern_analysis(self, question: str) -> Dict[str, Any]:
        """Phân tích cơ bản bằng patterns"""
        question_lower = question.lower()
        
        analysis = {
            'category': 'general',
            'subcategory': 'overview',
            'keywords': [],
            'confidence': 0.5,
            'data_types': [],
            'time_period': None
        }
        
        # Phân tích category chính
        for category, patterns in self.analysis_patterns.items():
            score = 0
            matched_keywords = []
            
            for pattern in patterns['keywords']:
                if pattern in question_lower:
                    score += patterns['weights'].get(pattern, 1)
                    matched_keywords.append(pattern)
            
            if score > 0:
                analysis['category'] = category
                analysis['keywords'].extend(matched_keywords)
                analysis['confidence'] = min(score / 10, 1.0)
                
                # Tìm subcategory
                for subcat, sub_patterns in patterns['subcategories'].items():
                    if any(sp in question_lower for sp in sub_patterns):
                        analysis['subcategory'] = subcat
                        analysis['confidence'] += 0.2
                        break
                
                break
        
        # Phân tích loại dữ liệu cần thiết
        data_type_patterns = {
            'price': ['giá', 'chi phí', 'cost', 'price', 'thị trường'],
            'quantity': ['số lượng', 'đàn', 'diện tích', 'sản lượng', 'population'],
            'trend': ['xu hướng', 'biến động', 'thay đổi', 'trend', 'tăng', 'giảm'],
            'comparison': ['so sánh', 'compare', 'khác nhau', 'difference'],
            'distribution': ['phân bố', 'distribution', 'vùng', 'khu vực', 'region'],
            'performance': ['hiệu suất', 'năng suất', 'performance', 'productivity']
        }
        
        for data_type, patterns in data_type_patterns.items():
            if any(pattern in question_lower for pattern in patterns):
                analysis['data_types'].append(data_type)
        
        # Phân tích time period
        time_patterns = {
            'monthly': ['tháng', 'month', 'hàng tháng'],
            'yearly': ['năm', 'year', 'hàng năm'],
            'quarterly': ['quý', 'quarter'],
            'current': ['hiện tại', 'current', 'bây giờ'],
            'forecast': ['dự báo', 'forecast', 'tương lai']
        }
        
        for period, patterns in time_patterns.items():
            if any(pattern in question_lower for pattern in patterns):
                analysis['time_period'] = period
                break
        
        return analysis
    
    def _ai_enhanced_analysis(self, question: str, basic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Sử dụng AI để phân tích sâu hơn"""
        try:
            ai_prompt = f"""
Phân tích câu hỏi nông nghiệp sau và trả về JSON:

Câu hỏi: "{question}"

Phân tích cơ bản đã có: {json.dumps(basic_analysis, ensure_ascii=False)}

Hãy cải thiện phân tích này và trả về JSON với cấu trúc:
{{
    "category": "livestock/crops/economics/weather/fertilizer/irrigation",
    "subcategory": "heo/gà/bò/lúa/ngô/etc",
    "keywords": ["từ khóa chính"],
    "confidence": 0.8,
    "data_types": ["price", "quantity", "trend", "comparison", "distribution", "performance"],
    "time_period": "monthly/yearly/current/forecast",
    "specific_focus": "điều gì cần focus chính",
    "chart_suggestions": ["bar", "line", "pie", "mixed"],
    "data_requirements": {{
        "main_metric": "chỉ số chính cần hiển thị",
        "supporting_metrics": ["chỉ số phụ"],
        "geographical_scope": "toàn quốc/vùng miền/tỉnh thành",
        "time_scope": "1 năm/6 tháng/etc"
    }}
}}

Chỉ trả về JSON, không giải thích thêm.
"""
            
            response = self.model.generate_content(ai_prompt)
            ai_result = json.loads(response.text.strip())
            
            # Merge với basic analysis
            enhanced_analysis = basic_analysis.copy()
            enhanced_analysis.update(ai_result)
            enhanced_analysis['confidence'] = min(enhanced_analysis['confidence'] + 0.3, 1.0)
            
            print(f"✅ AI enhanced analysis: {enhanced_analysis['category']}/{enhanced_analysis['subcategory']}")
            return enhanced_analysis
            
        except Exception as e:
            print(f"⚠️ AI analysis failed: {e}, using basic analysis")
            return basic_analysis
    
    def _generate_chart_configs(self, analysis: Dict[str, Any], question: str) -> List[ChartData]:
        """Tạo cấu hình biểu đồ dựa trên phân tích"""
        category = analysis['category']
        subcategory = analysis['subcategory']
        data_types = analysis.get('data_types', [])
        
        print(f"📊 Generating charts for {category}/{subcategory} with data types: {data_types}")
        
        chart_configs = []
        
        # Lấy dữ liệu từ data source
        category_data = self.data_sources.get(category, {})
        specific_data = category_data.get(subcategory, category_data.get('default', {}))
        
        # Tạo biểu đồ chính
        main_chart = self._create_main_chart(analysis, specific_data, question)
        if main_chart:
            chart_configs.append(main_chart)
        
        # Tạo biểu đồ bổ sung dựa trên data_types
        for data_type in data_types:
            additional_chart = self._create_additional_chart(data_type, analysis, specific_data)
            if additional_chart:
                chart_configs.append(additional_chart)
        
        # Nếu không có biểu đồ nào, tạo biểu đồ mặc định
        if not chart_configs:
            default_chart = self._create_default_chart(analysis, specific_data)
            chart_configs.append(default_chart)
        
        print(f"✅ Generated {len(chart_configs)} chart configurations")
        return chart_configs
    
    def _create_main_chart(self, analysis: Dict[str, Any], data: Dict[str, Any], question: str) -> ChartData:
        """Tạo biểu đồ chính"""
        category = analysis['category']
        subcategory = analysis['subcategory']
        
        if category == 'livestock':  # Gia súc - 4 chân
            return self._create_livestock_main_chart(subcategory, data, question)
        elif category == 'poultry':  # Gia cầm - 2 chân
            return self._create_poultry_main_chart(subcategory, data, question)
        elif category == 'animal_husbandry':  # Chăn nuôi tổng hợp
            return self._create_animal_husbandry_chart(subcategory, data, question)
        elif category == 'crops':
            return self._create_crops_main_chart(subcategory, data, question)
        elif category == 'economics':
            return self._create_economics_main_chart(subcategory, data, question)
        else:
            return self._create_general_main_chart(analysis, data, question)
    
    def _create_livestock_main_chart(self, subcategory: str, data: Dict[str, Any], question: str) -> ChartData:
        """Tạo biểu đồ chính cho chăn nuôi"""
        
        # Nếu là câu hỏi tổng quan về gia súc, tạo biểu đồ phân bố các loài gia súc
        if subcategory == 'overview' or 'tỷ lệ' in question.lower() or 'phân bố' in question.lower():
            chart_type = 'doughnut'
            title = "Tỷ lệ gia súc tại Việt Nam"
            labels = ['Heo', 'Bò', 'Trâu', 'Dê', 'Cừu']
            # Dữ liệu thực tế về đàn gia súc Việt Nam (triệu con)
            values = [26.8, 5.2, 2.8, 1.5, 0.8]
            return ChartData(
                chart_type=chart_type,
                title=title,
                subtitle="Phân bố đàn gia súc theo loài (triệu con)",
                labels=labels,
                datasets=[{
                    'label': 'Số lượng (triệu con)',
                    'data': values,
                    'backgroundColor': ['#8b5cf6', '#10b981', '#3b82f6', '#f59e0b', '#ef4444'],
                    'borderColor': '#ffffff',
                    'borderWidth': 2
                }],
                metrics=[
                    {'label': 'Tổng đàn gia súc', 'value': '36.1 triệu con', 'change': '+2.1%', 'trend': 'positive'},
                    {'label': 'Gia súc chủ lực', 'value': 'Heo (74.2%)', 'change': 'Ổn định', 'trend': 'neutral'},
                    {'label': 'Tăng trưởng ngành', 'value': '3.5%/năm', 'change': '+0.8%', 'trend': 'positive'}
                ]
            )
        
        # Xác định loại biểu đồ phù hợp cho từng loài cụ thể
        if 'giá' in question.lower() or 'price' in question.lower():
            chart_type = 'line'
            title = f"Biến động giá {subcategory} 12 tháng"
            labels = [f"T{i}" for i in range(1, 13)]
            base_price = data.get('current_price', 50000)
            values = [base_price + random.randint(-5000, 5000) for _ in range(12)]
        elif 'số lượng' in question.lower() or 'đàn' in question.lower():
            chart_type = 'bar'
            title = f"Đàn {subcategory} theo vùng miền"
            labels = ['ĐBSCL', 'ĐB Bắc Bộ', 'Duyên hải Nam TB', 'Tây Nguyên', 'Bắc TB', 'Khác']
            total = data.get('total_population', 100)
            values = self._distribute_values(total, len(labels))
        else:
            chart_type = 'doughnut'
            title = f"Cơ cấu {subcategory} theo loại"
            labels = data.get('types', ['Loại 1', 'Loại 2', 'Loại 3'])
            values = self._distribute_values(100, len(labels))
        
        return ChartData(
            chart_type=chart_type,
            title=title,
            subtitle=f"Dữ liệu {subcategory} năm 2024",
            labels=labels,
            datasets=[{
                'label': title,
                'data': values,
                'backgroundColor': self._generate_colors(len(labels)),
                'borderColor': '#ffffff',
                'borderWidth': 2
            }],
            metrics=self._generate_livestock_metrics(subcategory, data)
        )
    
    def _create_additional_chart(self, data_type: str, analysis: Dict[str, Any], data: Dict[str, Any]) -> Optional[ChartData]:
        """Tạo biểu đồ bổ sung dựa trên loại dữ liệu"""
        category = analysis['category']
        subcategory = analysis['subcategory']
        
        if data_type == 'trend':
            return ChartData(
                chart_type='line',
                title=f"Xu hướng {subcategory} theo thời gian",
                subtitle="Dữ liệu 12 tháng qua",
                labels=[f"T{i}" for i in range(1, 13)],
                datasets=[{
                    'label': f'Xu hướng {subcategory}',
                    'data': self._generate_trend_data(),
                    'borderColor': '#10b981',
                    'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                    'fill': True,
                    'tension': 0.4
                }],
                metrics=[]
            )
        
        elif data_type == 'comparison':
            return ChartData(
                chart_type='bar',
                title=f"So sánh {subcategory} với năm trước",
                subtitle="Tỷ lệ thay đổi (%)",
                labels=['Q1', 'Q2', 'Q3', 'Q4'],
                datasets=[
                    {
                        'label': '2023',
                        'data': self._generate_comparison_data('2023'),
                        'backgroundColor': '#94a3b8'
                    },
                    {
                        'label': '2024',
                        'data': self._generate_comparison_data('2024'),
                        'backgroundColor': '#10b981'
                    }
                ],
                metrics=[]
            )
        
        elif data_type == 'performance':
            return ChartData(
                chart_type='mixed',
                title=f"Hiệu suất {subcategory}",
                subtitle="Các chỉ số hiệu suất chính",
                labels=['Q1', 'Q2', 'Q3', 'Q4'],
                datasets=[
                    {
                        'type': 'line',
                        'label': 'Hiệu suất (%)',
                        'data': [85, 88, 92, 89],
                        'borderColor': '#3b82f6',
                        'yAxisID': 'y'
                    },
                    {
                        'type': 'bar',
                        'label': 'Sản lượng',
                        'data': [100, 110, 115, 108],
                        'backgroundColor': '#10b981',
                        'yAxisID': 'y1'
                    }
                ],
                metrics=[]
            )
        
        return None
    
    def _generate_livestock_metrics(self, subcategory: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Tạo metrics cho chăn nuôi"""
        metrics = [
            {
                'label': f'Tổng đàn {subcategory}',
                'value': f"{data.get('total_population', 100)}M con",
                'change': '+2.3%',
                'trend': 'positive'
            },
            {
                'label': f'Giá {subcategory} hiện tại',
                'value': f"{data.get('current_price', 50000):,} VNĐ/kg",
                'change': '+1.5%',
                'trend': 'positive'
            },
            {
                'label': 'Tăng trọng TB',
                'value': f"{data.get('growth_rate', 750)}g/ngày",
                'change': '+3.1%',
                'trend': 'positive'
            }
        ]
        return metrics
    
    def _distribute_values(self, total: float, count: int) -> List[float]:
        """Phân bố giá trị ngẫu nhiên có tổng = total"""
        if count == 0:
            return []
        
        # Tạo tỷ lệ ngẫu nhiên
        ratios = [random.uniform(0.5, 2.0) for _ in range(count)]
        ratio_sum = sum(ratios)
        
        # Chuẩn hóa để tổng = total
        values = [(ratio / ratio_sum) * total for ratio in ratios]
        
        # Làm tròn và điều chỉnh
        values = [round(v, 1) for v in values]
        
        return values
    
    def _generate_colors(self, count: int) -> List[str]:
        """Tạo màu sắc cho biểu đồ"""
        base_colors = [
            '#10b981', '#3b82f6', '#f59e0b', '#ef4444', 
            '#8b5cf6', '#6b7280', '#14b8a6', '#f97316'
        ]
        
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])
        
        return colors
    
    def _generate_trend_data(self) -> List[float]:
        """Tạo dữ liệu xu hướng"""
        base = 100
        data = [base]
        
        for i in range(11):
            change = random.uniform(-5, 8)  # Xu hướng tăng nhẹ
            base += change
            data.append(round(base, 1))
        
        return data
    
    def _generate_comparison_data(self, year: str) -> List[float]:
        """Tạo dữ liệu so sánh"""
        if year == '2024':
            return [105, 112, 118, 115]  # Tăng so với 2023
        else:
            return [100, 103, 108, 106]  # Baseline 2023
    
    def _create_default_chart(self, analysis: Dict[str, Any], data: Dict[str, Any]) -> ChartData:
        """Tạo biểu đồ mặc định"""
        return ChartData(
            chart_type='bar',
            title=f"Tổng quan {analysis['subcategory']}",
            subtitle="Dữ liệu tổng hợp",
            labels=['Hiện tại', 'Mục tiêu', 'Trung bình ngành'],
            datasets=[{
                'label': 'Giá trị',
                'data': [85, 100, 90],
                'backgroundColor': ['#10b981', '#3b82f6', '#f59e0b']
            }],
            metrics=[
                {'label': 'Trạng thái', 'value': 'Tốt', 'change': '+5%', 'trend': 'positive'}
            ]
        )
    
    def _create_poultry_main_chart(self, subcategory: str, data: Dict[str, Any], question: str) -> ChartData:
        """Tạo biểu đồ chính cho gia cầm (2 chân, có cánh)"""
        
        # Nếu là câu hỏi tổng quan về gia cầm, tạo biểu đồ phân bố các loài gia cầm
        if subcategory == 'overview' or 'tỷ lệ' in question.lower() or 'phân bố' in question.lower():
            chart_type = 'doughnut'
            title = "Tỷ lệ gia cầm tại Việt Nam"
            labels = ['Gà', 'Vịt', 'Ngan', 'Ngỗng', 'Chim cút']
            # Dữ liệu thực tế về đàn gia cầm Việt Nam (triệu con)
            values = [347, 82, 15, 8, 25]
            return ChartData(
                chart_type=chart_type,
                title=title,
                subtitle="Phân bố đàn gia cầm theo loài (triệu con)",
                labels=labels,
                datasets=[{
                    'label': 'Số lượng (triệu con)',
                    'data': values,
                    'backgroundColor': ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'],
                    'borderColor': '#ffffff',
                    'borderWidth': 2
                }],
                metrics=[
                    {'label': 'Tổng đàn gia cầm', 'value': '477 triệu con', 'change': '+3.5%', 'trend': 'positive'},
                    {'label': 'Gia cầm chủ lực', 'value': 'Gà (72.7%)', 'change': '+2.1%', 'trend': 'positive'},
                    {'label': 'Sản lượng trứng', 'value': '16.8 tỷ quả', 'change': '+4.2%', 'trend': 'positive'}
                ]
            )
        
        # Xác định loại biểu đồ phù hợp cho từng loài cụ thể
        if 'giá' in question.lower() or 'price' in question.lower():
            chart_type = 'line'
            title = f"Biến động giá {subcategory} 12 tháng"
            labels = [f"T{i}" for i in range(1, 13)]
            base_price = data.get('current_price', 45000)
            values = [base_price + random.randint(-3000, 3000) for _ in range(12)]
        elif 'số lượng' in question.lower() or 'đàn' in question.lower():
            chart_type = 'bar'
            title = f"Đàn {subcategory} theo vùng miền"
            labels = ['ĐBSCL', 'ĐB Bắc Bộ', 'Duyên hải Nam TB', 'Tây Nguyên', 'Bắc TB', 'Khác']
            total = data.get('total_population', 100)
            values = self._distribute_values(total, len(labels))
        elif 'trứng' in question.lower() or 'egg' in question.lower():
            chart_type = 'doughnut'
            title = f"Năng suất trứng {subcategory}"
            labels = ['Xuất sắc (>90%)', 'Tốt (70-90%)', 'Trung bình (<70%)']
            values = [45, 35, 20]
        else:
            chart_type = 'doughnut'
            title = f"Cơ cấu {subcategory} theo mục đích"
            labels = data.get('types', ['Thịt', 'Đẻ', 'Giống'])
            values = self._distribute_values(100, len(labels))
        
        return ChartData(
            chart_type=chart_type,
            title=title,
            subtitle=f"Dữ liệu gia cầm {subcategory} năm 2024",
            labels=labels,
            datasets=[{
                'label': title,
                'data': values,
                'backgroundColor': self._generate_colors(len(labels)),
                'borderColor': '#ffffff',
                'borderWidth': 2
            }],
            metrics=self._generate_poultry_metrics(subcategory, data)
        )

    def _create_animal_husbandry_chart(self, subcategory: str, data: Dict[str, Any], question: str) -> ChartData:
        """Tạo biểu đồ cho chăn nuôi tổng hợp"""
        chart_type = 'bar'
        title = "Tổng quan chăn nuôi Việt Nam"
        labels = ['Gia súc (4 chân)', 'Gia cầm (2 chân)', 'Thủy sản', 'Khác']
        values = [35, 55, 8, 2]  # Tỷ lệ phần trăm
        
        return ChartData(
            chart_type=chart_type,
            title=title,
            subtitle="Cơ cấu chăn nuôi theo loại động vật",
            labels=labels,
            datasets=[{
                'label': 'Tỷ trọng (%)',
                'data': values,
                'backgroundColor': ['#8b5cf6', '#10b981', '#3b82f6', '#f59e0b']
            }],
            metrics=[
                {'label': 'Tổng đàn gia súc', 'value': '36M con', 'change': '+2.1%', 'trend': 'positive'},
                {'label': 'Tổng đàn gia cầm', 'value': '477M con', 'change': '+3.5%', 'trend': 'positive'},
                {'label': 'Tổng giá trị ngành', 'value': '267 nghìn tỷ VNĐ', 'change': '+4.2%', 'trend': 'positive'}
            ]
        )

    def _generate_poultry_metrics(self, subcategory: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Tạo metrics cho gia cầm"""
        metrics = [
            {
                'label': f'Tổng đàn {subcategory}',
                'value': f"{data.get('total_population', 100)}M con",
                'change': '+3.2%',
                'trend': 'positive'
            },
            {
                'label': f'Giá {subcategory} hiện tại',
                'value': f"{data.get('current_price', 45000):,} VNĐ/kg",
                'change': '+1.8%',
                'trend': 'positive'
            },
            {
                'label': 'Tăng trọng TB',
                'value': f"{data.get('growth_rate', 40)}g/ngày",
                'change': '+2.5%',
                'trend': 'positive'
            }
        ]
        
        # Thêm metric về trứng nếu có
        if 'eggs_per_year' in data:
            metrics.append({
                'label': 'Năng suất trứng',
                'value': f"{data['eggs_per_year']} quả/năm",
                'change': '+1.2%',
                'trend': 'positive'
            })
        
        return metrics
    
    # Data loading methods
    def _load_livestock_data(self) -> Dict[str, Any]:
        """Load dữ liệu gia súc (động vật 4 chân)"""
        return {
            'heo': {
                'total_population': 26.8,  # triệu con
                'current_price': 73500,    # VNĐ/kg sống
                'growth_rate': 750,        # gram/ngày
                'types': ['Heo nái', 'Heo thịt', 'Heo con'],
                'category': 'livestock',
                'legs': 4,
                'description': 'Động vật gia súc 4 chân, nguồn protein chính'
            },
            'bò': {
                'total_population': 5.2,
                'current_price': 92000,
                'growth_rate': 1000,
                'types': ['Bò thịt', 'Bò sữa', 'Bò giống'],
                'category': 'livestock',
                'legs': 4,
                'description': 'Động vật gia súc lớn, nguồn thịt và sữa'
            },
            'trâu': {
                'total_population': 2.8,
                'current_price': 85000,
                'growth_rate': 900,
                'types': ['Trâu thịt', 'Trâu cày', 'Trâu sữa'],
                'category': 'livestock',
                'legs': 4,
                'description': 'Động vật gia súc bản địa, chịu khô hạn tốt'
            },
            'dê': {
                'total_population': 1.5,
                'current_price': 78000,
                'growth_rate': 300,
                'types': ['Dê thịt', 'Dê sữa', 'Dê giống'],
                'category': 'livestock',
                'legs': 4,
                'description': 'Động vật gia súc nhỏ, thích nghi tốt với khí hậu khô'
            },
            'cừu': {
                'total_population': 0.8,
                'current_price': 82000,
                'growth_rate': 280,
                'types': ['Cừu thịt', 'Cừu len', 'Cừu giống'],
                'category': 'livestock',
                'legs': 4,
                'description': 'Động vật gia súc nhỏ, nguồn thịt và len'
            },
            'default': {
                'total_population': 10,
                'current_price': 75000,
                'growth_rate': 600,
                'types': ['Loại 1', 'Loại 2', 'Loại 3'],
                'category': 'livestock',
                'legs': 4,
                'description': 'Gia súc tổng quát'
            }
        }
    
    def _load_crops_data(self) -> Dict[str, Any]:
        """Load dữ liệu cây trồng"""
        return {
            'lúa': {
                'area': 7.42,  # triệu ha
                'yield': 5.89,  # tấn/ha
                'price': 7200,  # VNĐ/kg
                'production': 43.67  # triệu tấn
            },
            'ngô': {
                'area': 1.18,
                'yield': 4.72,
                'price': 5800,
                'production': 5.57
            },
            'cà phê': {
                'area': 0.7,
                'yield': 2.5,
                'price': 45000,
                'production': 1.75
            },
            'default': {
                'area': 1.0,
                'yield': 3.0,
                'price': 10000,
                'production': 3.0
            }
        }
    
    def _load_economics_data(self) -> Dict[str, Any]:
        """Load dữ liệu kinh tế"""
        return {
            'export': {
                'total_value': 53.2,  # tỷ USD
                'growth_rate': 8.5,   # %
                'main_products': ['Gạo', 'Cà phê', 'Cao su', 'Tiêu']
            },
            'import': {
                'total_value': 12.8,
                'growth_rate': 5.2,
                'main_products': ['Phân bón', 'Máy móc', 'Thuốc BVTV']
            }
        }
    
    def _load_weather_data(self) -> Dict[str, Any]:
        """Load dữ liệu thời tiết"""
        return {
            'temperature': {
                'average': 26.5,
                'min': 18.2,
                'max': 35.8,
                'monthly_data': [22, 24, 26, 28, 29, 30, 29, 28, 27, 25, 23, 21]
            },
            'rainfall': {
                'annual': 1800,
                'monthly_data': [45, 60, 80, 120, 180, 250, 280, 260, 200, 120, 80, 50]
            }
        }
    
    def _load_fertilizer_data(self) -> Dict[str, Any]:
        """Load dữ liệu phân bón"""
        return {
            'urea': {
                'price': 13200,
                'consumption': 2.5,  # triệu tấn
                'nitrogen_content': 46
            },
            'npk': {
                'price': 16500,
                'consumption': 1.8,
                'composition': [20, 20, 15]
            }
        }
    
    def _load_poultry_data(self) -> Dict[str, Any]:
        """Load dữ liệu gia cầm (động vật 2 chân, có cánh)"""
        return {
            'gà': {
                'total_population': 347,   # triệu con
                'current_price': 48000,    # VNĐ/kg sống
                'growth_rate': 45,         # gram/ngày
                'types': ['Gà thịt', 'Gà đẻ', 'Gà giống'],
                'category': 'poultry',
                'legs': 2,
                'eggs_per_year': 280,
                'description': 'Gia cầm phổ biến nhất, nguồn thịt và trứng chính'
            },
            'vịt': {
                'total_population': 82,
                'current_price': 42000,
                'growth_rate': 38,
                'types': ['Vịt thịt', 'Vịt đẻ', 'Vịt giống'],
                'category': 'poultry',
                'legs': 2,
                'eggs_per_year': 200,
                'description': 'Gia cầm nước, thích hợp với khí hậu ẩm ướt'
            },
            'ngan': {
                'total_population': 15,
                'current_price': 55000,
                'growth_rate': 65,
                'types': ['Ngan thịt', 'Ngan đẻ', 'Ngan giống'],
                'category': 'poultry',
                'legs': 2,
                'eggs_per_year': 180,
                'description': 'Gia cầm lớn, thịt thơm ngon'
            },
            'ngỗng': {
                'total_population': 8,
                'current_price': 72000,
                'growth_rate': 85,
                'types': ['Ngỗng thịt', 'Ngỗng lông', 'Ngỗng giống'],
                'category': 'poultry',
                'legs': 2,
                'eggs_per_year': 60,
                'description': 'Gia cầm lớn nhất, nguồn thịt và lông'
            },
            'chim_cút': {
                'total_population': 25,
                'current_price': 35000,
                'growth_rate': 15,
                'types': ['Cút thịt', 'Cút đẻ', 'Cút giống'],
                'category': 'poultry',
                'legs': 2,
                'eggs_per_year': 300,
                'description': 'Gia cầm nhỏ, trứng bổ dưỡng'
            },
            'default': {
                'total_population': 50,
                'current_price': 45000,
                'growth_rate': 40,
                'types': ['Loại 1', 'Loại 2', 'Loại 3'],
                'category': 'poultry',
                'legs': 2,
                'eggs_per_year': 200,
                'description': 'Gia cầm tổng quát'
            }
        }
    
    def _load_irrigation_data(self) -> Dict[str, Any]:
        """Load dữ liệu tưới tiêu"""
        return {
            'systems': {
                'sprinkler': {'efficiency': 85, 'cost': 15000000, 'description': 'Hệ thống tưới phun'},
                'drip': {'efficiency': 95, 'cost': 25000000, 'description': 'Hệ thống tưới nhỏ giọt'},
                'flood': {'efficiency': 60, 'cost': 5000000, 'description': 'Tưới tràn'},
                'furrow': {'efficiency': 70, 'cost': 8000000, 'description': 'Tưới rãnh'}
            },
            'water_usage': {
                'rice': 1500,  # m3/ha
                'corn': 800,
                'vegetables': 600,
                'fruit_trees': 1200
            },
            'regions': {
                'north': {'water_availability': 'sufficient', 'main_source': 'rivers'},
                'central': {'water_availability': 'moderate', 'main_source': 'reservoirs'},
                'south': {'water_availability': 'abundant', 'main_source': 'mekong_delta'}
            }
        }
    
    def _load_analysis_patterns(self) -> Dict[str, Any]:
        """Load patterns để phân tích câu hỏi"""
        return {
            'livestock': {  # GIA SÚC - Động vật 4 chân
                'keywords': ['heo', 'lợn', 'bò', 'trâu', 'dê', 'cừu', 'gia súc', 'thịt heo', 'thịt bò', 'sữa bò', 'sữa dê'],
                'weights': {
                    'heo': 3, 'lợn': 3, 'bò': 3, 'trâu': 3, 'dê': 3, 'cừu': 3,
                    'gia súc': 2, 'thịt heo': 2, 'thịt bò': 2, 'sữa': 2
                },
                'subcategories': {
                    'heo': ['heo', 'lợn', 'heo hơi', 'heo thịt', 'heo nái', 'heo con'],
                    'bò': ['bò', 'bò thịt', 'bò sữa', 'bê', 'nghé'],
                    'trâu': ['trâu', 'trâu thịt', 'trâu cày'],
                    'dê': ['dê', 'dê thịt', 'sữa dê', 'dê con'],
                    'cừu': ['cừu', 'cừu thịt', 'len cừu', 'cừu con']
                }
            },
            'poultry': {  # GIA CẦM - Động vật 2 chân, có cánh
                'keywords': ['gà', 'vịt', 'ngan', 'ngỗng', 'chim cút', 'gia cầm', 'thịt gà', 'thịt vịt', 'trứng gà', 'trứng vịt'],
                'weights': {
                    'gà': 3, 'vịt': 3, 'ngan': 3, 'ngỗng': 3, 'chim cút': 3,
                    'gia cầm': 2, 'trứng': 2, 'thịt gà': 2, 'thịt vịt': 2
                },
                'subcategories': {
                    'gà': ['gà', 'gà thịt', 'gà ta', 'gà công nghiệp', 'gà broiler', 'gà layer', 'trứng gà'],
                    'vịt': ['vịt', 'vịt thịt', 'vịt con', 'vịt siêu thịt', 'trứng vịt'],
                    'ngan': ['ngan', 'thịt ngan', 'trứng ngan'],
                    'ngỗng': ['ngỗng', 'thịt ngỗng', 'lông ngỗng'],
                    'chim_cút': ['chim cút', 'cút', 'trứng cút']
                }
            },
            'animal_husbandry': {  # CHĂN NUÔI TỔNG HỢP - Bao gồm cả gia súc và gia cầm
                'keywords': ['chăn nuôi', 'trang trại', 'đàn', 'nuôi', 'động vật', 'thức ăn chăn nuôi', 'chuồng trại', 'vaccine'],
                'weights': {
                    'chăn nuôi': 3, 'trang trại': 2, 'nuôi': 2, 'đàn': 2
                },
                'subcategories': {
                    'general': ['chăn nuôi', 'nuôi', 'trang trại'],
                    'feed': ['thức ăn', 'cám', 'cỏ', 'silage'],
                    'health': ['vaccine', 'thuốc thú y', 'bệnh', 'dịch'],
                    'facility': ['chuồng', 'trại', 'hệ thống']
                }
            },
            'crops': {
                'keywords': ['lúa', 'gạo', 'ngô', 'bắp', 'khoai', 'rau', 'cà phê', 'cao su', 'tiêu', 'điều', 'cây trồng', 'trồng trọt'],
                'weights': {
                    'lúa': 3, 'gạo': 3, 'ngô': 3, 'bắp': 3, 'cà phê': 3,
                    'cao su': 3, 'tiêu': 3, 'cây trồng': 2, 'trồng trọt': 2
                },
                'subcategories': {
                    'lúa': ['lúa', 'gạo', 'thóc', 'ruộng lúa'],
                    'ngô': ['ngô', 'bắp', 'bắp ngô', 'ngô ngọt'],
                    'cà phê': ['cà phê', 'cafe', 'coffee', 'robusta', 'arabica'],
                    'cao su': ['cao su', 'rubber', 'mủ cao su'],
                    'tiêu': ['tiêu', 'pepper', 'tiêu đen'],
                    'rau': ['rau', 'rau xanh', 'rau củ', 'cải', 'xà lách']
                }
            },
            'economics': {
                'keywords': ['giá', 'chi phí', 'lợi nhuận', 'doanh thu', 'thị trường', 'xuất khẩu', 'nhập khẩu', 'kinh tế'],
                'weights': {
                    'giá': 3, 'thị trường': 3, 'xuất khẩu': 3, 'kinh tế': 2
                },
                'subcategories': {
                    'price': ['giá', 'giá cả', 'cost', 'price'],
                    'export': ['xuất khẩu', 'export', 'bán ra nước ngoài'],
                    'import': ['nhập khẩu', 'import', 'mua từ nước ngoài'],
                    'market': ['thị trường', 'market', 'kinh doanh']
                }
            }
        }
    
    def _create_crops_main_chart(self, subcategory: str, data: Dict[str, Any], question: str) -> ChartData:
        """Tạo biểu đồ chính cho cây trồng"""
        if 'diện tích' in question.lower() or 'area' in question.lower():
            chart_type = 'bar'
            title = f"Diện tích trồng {subcategory} theo vùng"
            labels = ['ĐBSCL', 'ĐB Bắc Bộ', 'Duyên hải Nam TB', 'Tây Nguyên', 'Bắc TB']
            total_area = data.get('area', 5.0)
            values = self._distribute_values(total_area, len(labels))
        elif 'năng suất' in question.lower() or 'yield' in question.lower():
            chart_type = 'line'
            title = f"Năng suất {subcategory} theo tháng"
            labels = [f"T{i}" for i in range(1, 13)]
            base_yield = data.get('yield', 3.0)
            values = [base_yield + random.uniform(-0.5, 0.5) for _ in range(12)]
        else:
            chart_type = 'doughnut'
            title = f"Cơ cấu sản xuất {subcategory}"
            labels = ['Sản xuất thương phẩm', 'Tiêu dùng nội địa', 'Xuất khẩu']
            values = self._distribute_values(100, len(labels))
        
        return ChartData(
            chart_type=chart_type,
            title=title,
            subtitle=f"Dữ liệu {subcategory} năm 2024",
            labels=labels,
            datasets=[{
                'label': title,
                'data': values,
                'backgroundColor': self._generate_colors(len(labels)),
                'borderColor': '#ffffff',
                'borderWidth': 2
            }],
            metrics=self._generate_crops_metrics(subcategory, data)
        )
    
    def _generate_crops_metrics(self, subcategory: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Tạo metrics cho cây trồng"""
        metrics = [
            {
                'label': f'Diện tích {subcategory}',
                'value': f"{data.get('area', 5.0)} triệu ha",
                'change': '+1.8%',
                'trend': 'positive'
            },
            {
                'label': f'Năng suất {subcategory}',
                'value': f"{data.get('yield', 3.0)} tấn/ha",
                'change': '+2.5%',
                'trend': 'positive'
            },
            {
                'label': f'Giá {subcategory}',
                'value': f"{data.get('price', 10000):,} VNĐ/kg",
                'change': '+3.2%',
                'trend': 'positive'
            }
        ]
        return metrics
    
    def _create_economics_main_chart(self, subcategory: str, data: Dict[str, Any], question: str) -> ChartData:
        """Tạo biểu đồ chính cho kinh tế"""
        return ChartData(
            chart_type='line',
            title=f"Xu hướng {subcategory} nông sản",
            subtitle="12 tháng qua",
            labels=[f"T{i}" for i in range(1, 13)],
            datasets=[{
                'label': f'{subcategory} (tỷ USD)',
                'data': self._generate_trend_data(),
                'borderColor': '#10b981',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'fill': True
            }],
            metrics=[
                {'label': 'Tổng giá trị', 'value': '53.2 tỷ USD', 'change': '+8.5%', 'trend': 'positive'}
            ]
        )
    
    def _create_general_main_chart(self, analysis: Dict[str, Any], data: Dict[str, Any], question: str) -> ChartData:
        """Tạo biểu đồ tổng quát"""
        return ChartData(
            chart_type='bar',
            title="Tổng quan nông nghiệp Việt Nam",
            subtitle="Các chỉ số chính theo ngành",
            labels=['Gia súc (4 chân)', 'Gia cầm (2 chân)', 'Cây trồng', 'Thủy sản', 'Lâm nghiệp'],
            datasets=[{
                'label': 'Tỷ trọng GDP (%)',
                'data': [18, 25, 42, 12, 3],
                'backgroundColor': self._generate_colors(5)
            }],
            metrics=[
                {'label': 'Tổng GDP nông nghiệp', 'value': '14.8%', 'change': '+1.2%', 'trend': 'positive'},
                {'label': 'Kim ngạch xuất khẩu', 'value': '53.2 tỷ USD', 'change': '+8.5%', 'trend': 'positive'},
                {'label': 'Tăng trưởng ngành', 'value': '3.2%/năm', 'change': '+0.5%', 'trend': 'positive'}
            ]
        )

# Utility functions để sử dụng từ JavaScript
def analyze_agricultural_question(question: str, gemini_api_key: str = None) -> str:
    """
    Function chính để gọi từ JavaScript/Python backend
    Trả về JSON string chứa cấu hình biểu đồ
    """
    try:
        print(f"DEBUG: Starting analysis for: {question}")
        
        analyzer = AgriDataAnalyzer(gemini_api_key)
        print("DEBUG: AgriDataAnalyzer created")
        
        result = analyzer.analyze_question(question, use_ai=False)  # Disable AI for now to avoid errors
        print(f"DEBUG: Analysis complete: {result.category}")
        
        # Convert to JSON-serializable format
        output = {
            'success': True,
            'category': result.category,
            'subcategory': result.subcategory,
            'confidence': result.confidence,
            'keywords': result.keywords,
            'time_period': result.time_period,
            'charts': []
        }
        
        for chart in result.chart_configs:
            chart_dict = {
                'chart_type': chart.chart_type,
                'title': chart.title,
                'subtitle': chart.subtitle,
                'labels': chart.labels,
                'datasets': chart.datasets,
                'metrics': chart.metrics
            }
            if hasattr(chart, 'expert_data') and chart.expert_data:
                chart_dict['expert_data'] = chart.expert_data
            
            output['charts'].append(chart_dict)
        
        print(f"DEBUG: Generated {len(output['charts'])} charts")
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except Exception as e:
        print(f"DEBUG: Error in analyze_agricultural_question: {e}")
        import traceback
        traceback.print_exc()
        
        error_output = {
            'success': False,
            'error': str(e),
            'charts': []
        }
        return json.dumps(error_output, ensure_ascii=False)

# Test function
if __name__ == "__main__":
    # Test với một số câu hỏi phân loại chính xác
    test_questions = [
        "Tỷ lệ gia súc ở Việt Nam phân bố ra sao?",  # Gia súc (4 chân)
        "Giá heo hơi hiện tại như thế nào?",        # Gia súc - heo
        "Đàn bò sữa tại Việt Nam có bao nhiêu?",    # Gia súc - bò
        "Số lượng gà trong cả nước",                # Gia cầm - gà
        "Năng suất trứng vịt ở ĐBSCL",              # Gia cầm - vịt
        "Tổng quan chăn nuôi Việt Nam",             # Chăn nuôi tổng hợp
        "Sản lượng lúa năm nay tăng hay giảm?",     # Cây trồng
        "Xuất khẩu cà phê 6 tháng đầu năm"          # Kinh tế
    ]
    
    analyzer = AgriDataAnalyzer()
    
    for question in test_questions:
        print(f"\n🔍 Testing: {question}")
        result_json = analyze_agricultural_question(question)
        result = json.loads(result_json)
        print(f"✅ Category: {result['category']}/{result['subcategory']}")
        print(f"📊 Charts generated: {len(result['charts'])}")
        if result['charts']:
            print(f"📈 First chart: {result['charts'][0]['title']}")
            # Hiển thị category của data để kiểm tra
            if 'category' in result['charts'][0].get('datasets', [{}])[0]:
                print(f"🏷️  Data category: {result['charts'][0]['datasets'][0]['category']}")
    
    # Test riêng phân biệt gia súc vs gia cầm
    print("\n" + "="*50)
    print("🧪 KIỂM TRA PHÂN LOẠI GIA SÚC VS GIA CẦM")
    print("="*50)
    
    livestock_questions = ["heo", "bò", "dê", "cừu", "trâu"]
    poultry_questions = ["gà", "vịt", "ngan", "ngỗng", "chim cút"]
    
    print("\n🐄 GIA SÚC (4 chân):")
    for animal in livestock_questions:
        question = f"Giá {animal} hiện tại"
        result_json = analyze_agricultural_question(question)
        result = json.loads(result_json)
        print(f"  {animal}: {result['category']}")
    
    print("\n🐔 GIA CẦM (2 chân):")
    for animal in poultry_questions:
        question = f"Giá {animal} hiện tại"
        result_json = analyze_agricultural_question(question)
        result = json.loads(result_json)
        print(f"  {animal}: {result['category']}")
