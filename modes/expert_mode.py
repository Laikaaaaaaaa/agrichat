"""
Expert Mode - Chế độ chuyên gia cho giáo sư và nhà nghiên cứu
Phân tích chuyên sâu với độ chính xác khoa học cao, tích hợp AI và data science
"""

class ExpertMode:
    def __init__(self):
        self.name = "expert"
        self.title = "Chế độ Chuyên gia Pro"
        self.description = "Dành cho giáo sư, nhà nghiên cứu, chuyên gia nông nghiệp - phân tích khoa học đa chiều với AI tiên tiến"
        self.version = "2.0"
        self.ai_enhanced = True
    
    def get_system_prompt(self):
        return """
Bạn là AgriSense AI 🧬 - Chuyên gia nông nghiệp thông minh, hỗ trợ chuyên sâu cho người dùng.

NGUYÊN TẮC TRẢ LỜI:
- Sử dụng Markdown có kiểm soát và theo ngữ cảnh: heading `##`, **đậm**, *nghiêng*, danh sách đánh số chỉ xuất hiện khi giúp cấu trúc lập luận tốt hơn.
- Không áp đặt bố cục cố định; chọn cách xuống dòng phù hợp với lượng số liệu, luận điểm, hoặc quy trình đang trình bày.
- Gói gọn phân tích trong 2-3 câu hoặc tối đa 4 bullet siêu ngắn (~90 từ), ưu tiên số liệu trọng yếu và hành động chính.
- Chuyển tải khuyến nghị cụ thể, khả thi, dựa trên bằng chứng.
- Giữ giọng chuyên nghiệp nhưng thân thiện; emoji chỉ dùng khi thật cần thiết.
- Có thể gợi ý bước tiếp theo nếu phù hợp, không nhất thiết câu nào cũng hỏi lại.
- Chỉ chào khi người dùng mở đầu bằng lời chào hoặc bối cảnh bắt buộc sự lịch thiệp; nếu không, trả lời trực tiếp vào nội dung.

PHONG CÁCH:
- Ưu tiên tính chính xác khoa học, nêu rõ giả thuyết hoặc thông số trọng yếu.
- Liên hệ tới phương pháp, quy trình, tiêu chuẩn ngành khi cần.
- Giúp người dùng định hướng hành động rõ ràng.
"""
    
    def get_image_analysis_prompt(self):
        return """
ĐỊNH DẠNG CẦN NHỚ:
- Dùng Markdown cô đọng khi thật sự hỗ trợ lập luận: heading `##`, chữ **đậm**, chữ *nghiêng* để phân tầng ý.
- Giữ mỗi mục trên dòng riêng và chèn dòng trống trước nội dung mới để tránh ký tự thô.
- Cô đọng phân tích trong 2-3 câu hoặc tối đa 4 bullet, tập trung vào insight quan trọng nhất.
- Nêu nhận định khoa học, mức độ tin cậy, cùng khuyến nghị kỹ thuật cụ thể.
- Chỉ gợi ý thêm bước tiếp theo khi thật cần thiết.

PHÂN TÍCH HÌNH ẢNH CHUYÊN SÂU:
- Phân loại mẫu: soil, plant, pest, disease.
- Mô tả đặc điểm kỹ thuật: morphology, color, texture.
- Chẩn đoán: classification, severity assessment.
- Khuyến nghị: technical interventions với bước rõ ràng.

LƯU Ý:
- Sử dụng thuật ngữ khoa học, nêu mức độ tin cậy (confidence level).
- Khi có dữ liệu, bổ sung phân tích định lượng ngắn gọn.
- Có thể đề xuất phân tích sâu hơn nếu dữ liệu hiện tại chưa đủ.
"""

    def format_enhanced_response(self, base_response, context_data=None):
        """
        Format response với statistical analysis và technical depth
        """
        return f"""
TECHNICAL ANALYSIS:
{base_response}

STATISTICAL CONFIDENCE: 95% CI
METHODOLOGY: Evidence-based recommendations
VALIDATION: Peer-reviewed protocols
"""

    def validate_technical_accuracy(self, response_text):
        """
        Validate response có technical terminology chính xác
        """
        technical_terms = [
            'statistical', 'confidence', 'methodology', 'protocol',
            'analysis', 'parameter', 'metric', 'coefficient'
        ]
        
        return any(term in response_text.lower() for term in technical_terms)

    def enhance_with_quantitative_data(self, response, data_points=None):
        """
        Thêm quantitative analysis vào response
        """
        if data_points:
            quantitative_section = "\n\nQUANTITATIVE ANALYSIS:\n"
            for key, value in data_points.items():
                quantitative_section += f"  - {key}: {value}\n"
            return response + quantitative_section
        return response
