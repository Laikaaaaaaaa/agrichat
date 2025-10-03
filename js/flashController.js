// Lớp quản lý flash và ánh sáng
export class FlashController {
    constructor(stream) {
        this.stream = stream;
        this.isFlashSupported = false;
        this.isFlashOn = false;
        this.checkFlashSupport();
        console.log('💡 Khởi tạo FlashController');
    }

    async checkFlashSupport() {
        if (!this.stream) return false;

        const track = this.stream.getVideoTracks()[0];
        if (!track) return false;

        try {
            const capabilities = track.getCapabilities();
            this.isFlashSupported = capabilities.torch || 
                                  (capabilities.fillLightMode && 
                                   capabilities.fillLightMode.includes('flash'));
            
            console.log('Flash support:', this.isFlashSupported);
            return this.isFlashSupported;
        } catch (error) {
            console.warn('Không thể kiểm tra flash:', error);
            return false;
        }
    }

    async toggleFlash() {
        if (!this.isFlashSupported) {
            throw new Error('Thiết bị không hỗ trợ flash');
        }

        const track = this.stream.getVideoTracks()[0];
        if (!track) {
            throw new Error('Không tìm thấy video track');
        }

        try {
            const capabilities = track.getCapabilities();
            const settings = track.getSettings();

            // Try torch mode first
            if (capabilities.torch) {
                this.isFlashOn = !this.isFlashOn;
                await track.applyConstraints({
                    advanced: [{ torch: this.isFlashOn }]
                });
            }
            // Fall back to fill light mode
            else if (capabilities.fillLightMode && 
                     capabilities.fillLightMode.includes('flash')) {
                this.isFlashOn = !this.isFlashOn;
                await track.applyConstraints({
                    advanced: [{ 
                        fillLightMode: this.isFlashOn ? 'flash' : 'none'
                    }]
                });
            }
            
            return this.isFlashOn;
        } catch (error) {
            console.error('Lỗi điều khiển flash:', error);
            throw error;
        }
    }

    async setFlash(enabled) {
        if (enabled === this.isFlashOn) return;
        await this.toggleFlash();
    }

    isSupported() {
        return this.isFlashSupported;
    }

    isEnabled() {
        return this.isFlashOn;
    }

    updateStream(stream) {
        this.stream = stream;
        this.checkFlashSupport();
        if (this.isFlashOn) {
            this.setFlash(true).catch(console.error);
        }
    }
}
