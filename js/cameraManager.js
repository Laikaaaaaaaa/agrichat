// Lớp quản lý chính cho camera
import { CameraDevice } from './cameraDevice.js';
import { VideoDisplay } from './videoDisplay.js';
import { PhotoCapture } from './photoCapture.js';
import { FlashController } from './flashController.js';

export class CameraManager {
    constructor() {
        console.log('🎥 Khởi tạo CameraManager...');
        this.initializeComponents();
        this.bindEvents();
    }

    initializeComponents() {
        // Tìm các elements
        this.modal = document.getElementById('camera-modal');
        this.video = document.getElementById('camera-preview');
        this.cameraSelect = document.getElementById('camera-select');
        this.takePhotoBtn = document.getElementById('take-photo');
        this.closeBtn = document.getElementById('close-camera');
        this.flashBtn = document.getElementById('flash-toggle');
        this.switchBtn = document.getElementById('switch-camera');
        
        // Kiểm tra kỹ hơn các elements
        console.log('Elements found:', {
            modal: !!this.modal,
            video: !!this.video,
            takePhotoBtn: !!this.takePhotoBtn,
            closeBtn: !!this.closeBtn,
            flashBtn: !!this.flashBtn,
            switchBtn: !!this.switchBtn
        });
        
        if (!this.modal || !this.video || !this.takePhotoBtn) {
            const missing = [];
            if (!this.modal) missing.push('camera-modal');
            if (!this.video) missing.push('camera-preview');
            if (!this.takePhotoBtn) missing.push('take-photo');
            throw new Error('Không tìm thấy các elements: ' + missing.join(', '));
        }

        // Khởi tạo các components
        this.device = new CameraDevice();
        this.display = new VideoDisplay(this.video);
        this.photoCapture = new PhotoCapture(this.video);
        this.flashController = null; // Sẽ được khởi tạo khi có stream

        // Trạng thái
        this.isInitialized = false;
        this.isInitializing = false;
    }

    bindEvents() {
        console.log('🔗 Binding camera events...');
        console.log('🔍 takePhotoBtn found:', !!this.takePhotoBtn);
        console.log('🔍 takePhotoBtn element:', this.takePhotoBtn);
        
        if (this.takePhotoBtn) {
            this.takePhotoBtn.onclick = (e) => {
                e.preventDefault();
                console.log('🔥 Take photo button clicked - calling takePhoto()');
                this.takePhoto();
            };
            console.log('✅ Take photo button event bound');
        } else {
            console.error('❌ Take photo button not found during event binding');
        }
        if (this.closeBtn) {
            this.closeBtn.onclick = (e) => {
                e.preventDefault();
                this.close();
            };
        }
        if (this.flashBtn) {
            this.flashBtn.onclick = (e) => {
                e.preventDefault();
                this.toggleFlash();
            };
        }
        if (this.switchBtn) {
            this.switchBtn.onclick = (e) => {
                e.preventDefault();
                this.switchCamera();
            };
        }
        if (this.cameraSelect) {
            this.cameraSelect.onchange = (e) => {
                e.preventDefault();
                this.onCameraChange();
            };
        }

        // Xử lý khi tab ẩn
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) this.close();
        });
    }

    updateStatus(message, isLoading = true) {
        const statusEl = document.getElementById('camera-status');
        if (!statusEl) return;

        statusEl.innerHTML = `
            <div class="flex items-center justify-center gap-2">
                ${isLoading ? '<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>' : ''}
                <span>${message}</span>
            </div>
        `;
        console.log('[Camera Status]', message);
    }

    async initialize() {
        if (this.isInitializing) {
            throw new Error('Camera đang được khởi tạo');
        }
        if (this.isInitialized) {
            return true;
        }

        this.isInitializing = true;
        this.updateStatus('Đang khởi tạo camera...');

        try {
            // Kiểm tra hỗ trợ và quyền truy cập
            await this.device.checkSupport();
            await this.device.getPermission();

            // Lấy danh sách camera
            const cameras = await this.device.getCameras();
            this.updateCameraList(cameras);

            // Thiết lập và bắt đầu stream camera đầu tiên
            const firstCamera = cameras[0];
            this.device.setCurrentDeviceId(firstCamera.deviceId);
            
            // Bắt đầu stream video
            const stream = await this.device.startStream(firstCamera.deviceId);
            await this.display.setStream(stream);
            
            // Khởi tạo flash controller sau khi có stream
            this.flashController = new FlashController(stream);

            this.isInitialized = true;
            this.updateStatus('Camera đã sẵn sàng', false);
            return true;

        } catch (error) {
            console.error('Lỗi khởi tạo camera:', error);
            this.updateStatus('Lỗi: ' + error.message, false);
            throw error;
        } finally {
            this.isInitializing = false;
        }
    }

    async startCamera(deviceId = null) {
        this.updateStatus('Đang kết nối camera...');

        try {
            // Lấy stream với các constraints khác nhau
            const constraints = [
                {
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                {}, // Default constraints
            ];

            let stream;
            let error;

            for (const constraint of constraints) {
                try {
                    stream = await this.device.startStream(deviceId, constraint);
                    if (stream) break;
                } catch (e) {
                    error = e;
                    await new Promise(r => setTimeout(r, 500));
                }
            }

            if (!stream) {
                throw error || new Error('Không thể kết nối camera');
            }

            // Thiết lập video
            await this.display.setStream(stream);

            // Khởi tạo flash controller
            this.flashController = new FlashController(stream);
            if (this.flashBtn) {
                this.flashBtn.disabled = !this.flashController.isSupported();
            }

            // Cập nhật UI
            this.updateStatus('Camera đã sẵn sàng', false);
            if (this.takePhotoBtn) {
                this.takePhotoBtn.disabled = false;
            }

            return true;

        } catch (error) {
            console.error('Lỗi khởi động camera:', error);
            this.updateStatus('Lỗi: ' + error.message, false);
            throw error;
        }
    }

    updateCameraList(cameras) {
        if (!this.cameraSelect) return;

        this.cameraSelect.innerHTML = '';
        
        // Thêm option mặc định
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.text = 'Chọn camera...';
        defaultOption.disabled = true;
        defaultOption.selected = !this.device.getCurrentDeviceId();
        this.cameraSelect.appendChild(defaultOption);

        // Thêm các cameras
        cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera.deviceId;
            option.text = camera.label || `Camera ${cameras.indexOf(camera) + 1}`;
            option.selected = camera.deviceId === this.device.getCurrentDeviceId();
            this.cameraSelect.appendChild(option);
        });

        this.cameraSelect.disabled = false;
    }

    async switchCamera() {
        if (!this.device.cameras || this.device.cameras.length < 2) {
            console.warn('Không có camera khác');
            return;
        }

        const currentIndex = this.device.cameras.findIndex(
            cam => cam.deviceId === this.device.getCurrentDeviceId()
        );
        const nextIndex = (currentIndex + 1) % this.device.cameras.length;
        const nextCamera = this.device.cameras[nextIndex];

        try {
            await this.startCamera(nextCamera.deviceId);
            this.device.setCurrentDeviceId(nextCamera.deviceId);
            if (this.cameraSelect) {
                this.cameraSelect.value = nextCamera.deviceId;
            }
        } catch (error) {
            console.error('Lỗi chuyển camera:', error);
            this.updateStatus('Không thể chuyển camera: ' + error.message, false);
        }
    }

    async onCameraChange() {
        if (!this.cameraSelect) return;
        
        const deviceId = this.cameraSelect.value;
        if (!deviceId) return;

        try {
            await this.startCamera(deviceId);
            this.device.setCurrentDeviceId(deviceId);
        } catch (error) {
            console.error('Lỗi đổi camera:', error);
            this.updateStatus('Không thể đổi camera: ' + error.message, false);
            this.cameraSelect.value = this.device.getCurrentDeviceId();
        }
    }

    async toggleFlash() {
        if (!this.flashController) return;

        try {
            const isOn = await this.flashController.toggleFlash();
            if (this.flashBtn) {
                this.flashBtn.classList.toggle('active', isOn);
            }
        } catch (error) {
            console.error('Lỗi điều khiển flash:', error);
            this.updateStatus('Không thể điều khiển flash: ' + error.message, false);
        }
    }

    async takePhoto() {
        console.log('� takePhoto() method called!');
        console.log('🔍 Display ready?', this.display?.isReady());
        console.log('🔍 PhotoCapture exists?', !!this.photoCapture);
        
        if (!this.display.isReady()) {
            console.error('❌ Camera not ready - display not ready');
            this.updateStatus('Camera chưa sẵn sàng', false);
            return;
        }

        console.log('📸 Starting photo capture process...');
        this.updateStatus('Đang chụp ảnh...', true);

        try {
            console.log('🔍 Getting camera device info...');
            console.log('🔍 Device:', this.device);
            console.log('🔍 Current device ID:', this.device?.getCurrentDeviceId());
            
            const isFrontCamera = this.device.isFrontCamera(
                this.device.getCurrentDeviceId()
            );
            console.log('🔍 Is front camera:', isFrontCamera);
            
            console.log('🔍 Video element state:', {
                videoWidth: this.video?.videoWidth,
                videoHeight: this.video?.videoHeight,
                readyState: this.video?.readyState,
                srcObject: !!this.video?.srcObject
            });
            
            console.log('🔍 PhotoCapture exists:', !!this.photoCapture);
            console.log('📸 Starting photo capture...');
            
            const photo = await this.photoCapture.capture({
                mirror: isFrontCamera,
                quality: 0.95
            });
            
            console.log('✅ Photo captured successfully!');
            console.log('📊 Photo details:', {
                hasBlob: !!photo.blob,
                hasDataUrl: !!photo.dataUrl,
                dataUrlLength: photo.dataUrl?.length,
                width: photo.width,
                height: photo.height
            });
            
            this.updateStatus('Đã chụp ảnh thành công!', false);
            
            console.log('🚀 Emitting photoTaken event...');
            this._emitPhotoTaken(photo.dataUrl);

            // Đóng camera và quay lại khung chat
            setTimeout(() => {
                this.close();
                console.log('Camera closed after photo');
            }, 500);

            return photo;

        } catch (error) {
            console.error('Lỗi chụp ảnh:', error);
            this.updateStatus('Lỗi chụp ảnh: ' + error.message, false);
            throw error;
        }
    }

    _emitPhotoTaken(photoData) {
        console.log('🚀 _emitPhotoTaken called!');
        console.log('📊 PhotoData type:', typeof photoData);
        console.log('📊 PhotoData length:', photoData?.length || 'unknown');
        console.log('📊 PhotoData starts with:', photoData?.substring ? photoData.substring(0, 50) : 'not a string');
        
        console.log('🔥 Creating and dispatching photoTaken event...');
        const event = new CustomEvent('photoTaken', {
            detail: { photoData }
        });
        
        console.log('📤 Dispatching event to document...');
        document.dispatchEvent(event);
        console.log('✅ PhotoTaken event dispatched successfully');
    }

    async open() {
        console.log('🚀 CameraManager.open() called!');
        console.log('🔍 Is initialized?', this.isInitialized);
        console.log('🔍 Modal exists?', !!this.modal);
        
        if (!this.isInitialized) {
            console.log('⏳ Initializing camera first...');
            await this.initialize();
            console.log('✅ Camera initialized');
        }
        
        if (this.modal) {
            console.log('📱 Showing camera modal...');
            this.modal.classList.remove('hidden');
            console.log('✅ Camera modal shown');
        } else {
            console.error('❌ Camera modal not found!');
        }
        
        document.body.style.overflow = 'hidden';
        
        console.log('📷 Starting camera...');
        await this.startCamera();
        console.log('✅ Camera started and ready');
    }

    close() {
        console.log('Closing camera...');
        this.device.stopStream();
        if (this.modal) {
            this.modal.classList.add('hidden');
            document.body.style.overflow = '';
            console.log('Camera modal hidden');
        }
        
        // Đảm bảo khung chat hiển thị
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.classList.remove('hidden');
            console.log('Chat container shown');
        }
    }
}
