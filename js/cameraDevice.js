// Lớp quản lý thiết bị camera cơ bản
export class CameraDevice {
    constructor() {
        this.stream = null;
        this.currentDeviceId = null;
        this.cameras = [];
        console.log('🎥 Khởi tạo CameraDevice');
    }

    async checkSupport() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Trình duyệt không hỗ trợ camera');
        }
        return true;
    }

    async getPermission() {
        try {
            // Check permissions API first
            try {
                const result = await navigator.permissions.query({ name: 'camera' });
                if (result.state === 'denied') {
                    throw new Error('Quyền truy cập camera bị từ chối');
                }
            } catch (e) {
                console.log('Permissions API không được hỗ trợ, thử với getUserMedia');
            }

            // Try to get camera access
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            stream.getTracks().forEach(track => track.stop());
            return true;
        } catch (error) {
            console.error('Lỗi truy cập camera:', error);
            throw new Error('Vui lòng cấp quyền camera và làm mới trang');
        }
    }

    async getCameras() {
        const devices = await navigator.mediaDevices.enumerateDevices();
        this.cameras = devices.filter(device => device.kind === 'videoinput');
        
        if (this.cameras.length === 0) {
            throw new Error('Không tìm thấy camera');
        }

        return this.cameras;
    }

    async startStream(deviceId = null, constraints = {}) {
        // Stop any existing stream
        await this.stopStream();

        // Build video constraints
        const videoConstraints = {
            deviceId: deviceId ? { exact: deviceId } : undefined,
            ...constraints
        };

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: videoConstraints,
                audio: false
            });
            return this.stream;
        } catch (error) {
            console.error('Lỗi khởi tạo stream:', error);
            throw error;
        }
    }

    async stopStream() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    getCurrentDeviceId() {
        return this.currentDeviceId;
    }

    setCurrentDeviceId(deviceId) {
        this.currentDeviceId = deviceId;
    }

    getStream() {
        return this.stream;
    }

    isFrontCamera(deviceId) {
        const camera = this.cameras.find(c => c.deviceId === deviceId);
        return camera && (
            camera.label.toLowerCase().includes('front') ||
            camera.label.toLowerCase().includes('trước') ||
            camera.label.toLowerCase().includes('selfie')
        );
    }
}
