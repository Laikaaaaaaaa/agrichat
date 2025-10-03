"""
Mode Manager - Quản lý các chế độ trả lời
"""

from .basic_mode import BasicMode
from .normal_mode import NormalMode
from .expert_mode import ExpertMode

class ModeManager:
    def __init__(self):
        self.modes = {
            'basic': BasicMode(),
            'normal': NormalMode(),
            'expert': ExpertMode()
        }
        self.current_mode = 'normal'  # Default mode
    
    def set_mode(self, mode_name):
        """Thiết lập chế độ hiện tại"""
        if mode_name in self.modes:
            self.current_mode = mode_name
            return True
        return False
    
    def get_current_mode(self):
        """Lấy chế độ hiện tại"""
        return self.modes[self.current_mode]
    
    def get_system_prompt(self):
        """Lấy system prompt cho chế độ hiện tại"""
        return self.modes[self.current_mode].get_system_prompt()
    
    def get_image_analysis_prompt(self):
        """Lấy image analysis prompt cho chế độ hiện tại"""
        return self.modes[self.current_mode].get_image_analysis_prompt()
    
    def get_mode_info(self, mode_name=None):
        """Lấy thông tin về chế độ"""
        mode = self.modes.get(mode_name or self.current_mode)
        if mode:
            return {
                'name': mode.name,
                'title': mode.title,
                'description': mode.description
            }
        return None
    
    def list_all_modes(self):
        """Liệt kê tất cả các chế độ có sẵn"""
        return [
            {
                'name': mode.name,
                'title': mode.title,
                'description': mode.description
            }
            for mode in self.modes.values()
        ]
