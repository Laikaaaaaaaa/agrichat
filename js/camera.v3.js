// Enhanced Camera Manager Class
export class CameraManager {
    constructor() {
        // Initialize state
        this.isComponentsInitialized = false;
        this.isInitialized = false;
        this.isInitializing = false;
        this.stream = null;
        this.currentDeviceId = null;
        this.cameras = [];
        
        console.log('🎥 Creating CameraManager instance');
        
        // Bind methods to preserve this context
        this.initialize = this.initialize.bind(this);
        this.initializeComponents = this.initializeComponents.bind(this);
        this.bindEvents = this.bindEvents.bind(this);
        this.open = this.open.bind(this);
        this.close = this.close.bind(this);
        this.takePhoto = this.takePhoto.bind(this);
        this.switchCamera = this.switchCamera.bind(this);
        this.onCameraChange = this.onCameraChange.bind(this);
        this.processSelectedImage = this.processSelectedImage.bind(this);
        
        // Wait for DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', this.initializeComponents);
        } else {
            this.initializeComponents();
        }
    }

    initializeComponents() {
        if (this.isComponentsInitialized) {
            console.log('⚠️ Components already initialized');
            return;
        }
        
        console.log('🔍 Finding camera components...');
        
        // Find UI elements
        this.modal = document.getElementById('camera-modal');
        this.video = document.getElementById('camera-preview');
        this.cameraSelect = document.getElementById('camera-select');
        this.takePhotoBtn = document.getElementById('take-photo');
        this.closeBtn = document.getElementById('close-camera');
        this.flashBtn = document.getElementById('flash-toggle');
        this.switchBtn = document.getElementById('switch-camera');
        this.imageInput = document.getElementById('image-input');
        this.uploadImageOption = document.getElementById('upload-image-option');

        // Validate required elements
        if (!this.modal || !this.video || !this.cameraSelect || 
            !this.takePhotoBtn || !this.closeBtn || !this.flashBtn || !this.switchBtn ||
            !this.imageInput || !this.uploadImageOption) {
            console.error('❌ Missing required elements:', {
                modal: !!this.modal,
                video: !!this.video,
                cameraSelect: !!this.cameraSelect,
                takePhotoBtn: !!this.takePhotoBtn,
                closeBtn: !!this.closeBtn,
                flashBtn: !!this.flashBtn,
                switchBtn: !!this.switchBtn,
                imageInput: !!this.imageInput,
                uploadImageOption: !!this.uploadImageOption
            });
            throw new Error('Camera UI elements not found');
        }

        // Setup initial state
        this.video.muted = true;
        this.video.playsInline = true;
        this.video.autoplay = true;
        
        // Bind events
        this.bindEvents();
        
        this.isComponentsInitialized = true;
        console.log('✅ Camera components initialized');
        
        if (!this.modal || !this.video) {
            console.error('[ERROR] Không tìm thấy các elements cần thiết:');
            console.error('[ERROR] - modal:', !this.modal ? 'missing' : 'ok');
            console.error('[ERROR] - video:', !this.video ? 'missing' : 'ok');
            throw new Error('Không tìm thấy các elements cần thiết cho camera');
        }

        // Create status element if not exists
        if (!document.getElementById('camera-status')) {
            const statusDiv = document.createElement('div');
            statusDiv.id = 'camera-status';
            statusDiv.className = 'text-center mt-2';
            this.video.parentElement?.appendChild(statusDiv);
        }

        // Initialize state
        this.stream = null;
        this.currentDeviceId = null;
        this.cameras = [];
        this.isInitialized = false;
        this.isInitializing = false;
        this.retryCount = 0;
        this.maxRetries = 3;

        console.log('✅ Components initialized');
    }

    setupErrorHandling() {
        // Handle unhandled rejections
        window.addEventListener('unhandledrejection', event => {
            console.error('Unhandled promise rejection:', event.reason);
            this.updateStatus('Lỗi không xác định: ' + event.reason.message, false);
        });

        // Handle errors
        window.addEventListener('error', event => {
            console.error('Global error:', event.error);
            this.updateStatus('Lỗi: ' + event.error?.message || 'Không xác định', false);
        });
    }

    bindEvents() {
        console.log('🔄 Binding camera events...');

        // Handle file upload
        if (this.imageInput && this.uploadImageOption) {
            this.uploadImageOption.addEventListener('click', () => {
                console.log('📤 Upload image clicked');
                this.imageInput.click();
                // Hide camera menu if exists
                const cameraMenu = document.getElementById('camera-menu');
                if (cameraMenu) {
                    cameraMenu.classList.add('hidden');
                }
            });

            this.imageInput.addEventListener('change', async (event) => {
                if (event.target.files && event.target.files[0]) {
                    const file = event.target.files[0];
                    console.log('📁 File selected:', file.name);
                    
                    if (file.type.startsWith('image/')) {
                        try {
                            this.updateStatus('Đang xử lý ảnh...', true);
                            const img = await this.createImageFromFile(file);
                            await this.processSelectedImage(img);
                        } catch (error) {
                            console.error('❌ Error processing image:', error);
                            this.updateStatus('Không thể xử lý ảnh. ' + error.message, false, 'error');
                        }
                    } else {
                        console.error('❌ Invalid file type:', file.type);
                        this.updateStatus('Vui lòng chọn một tập tin hình ảnh hợp lệ.', false, 'error');
                    }
                    event.target.value = ''; // Reset input
                }
            });
        }
        
        // Take Photo
        this.takePhotoBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('📸 Take photo clicked');
            try {
                await this.takePhoto();
            } catch (error) {
                console.error('❌ Error taking photo:', error);
                this.updateStatus(error.message, false, 'error');
            }
        });

        // Close Camera
        this.closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('🚪 Close clicked');
            this.close();
        });

        // Flash Toggle
        this.flashBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('💡 Flash clicked');
            this.toggleFlash();
        });

        // Switch Camera
        this.switchBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('🔄 Switch camera clicked');
            try {
                await this.switchCamera();
            } catch (error) {
                console.error('❌ Error switching camera:', error);
                this.updateStatus(error.message, false, 'error');
            }
        });

        // Camera Select
        this.cameraSelect.addEventListener('change', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('📹 Camera selected:', e.target.value);
            try {
                await this.onCameraChange();
            } catch (error) {
                console.error('❌ Error changing camera:', error);
                this.updateStatus(error.message, false, 'error');
            }
        });

        // Handle visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log('📱 Page hidden, closing camera');
                this.close();
            }
        });

        // Handle orientation change
        window.addEventListener('orientationchange', () => {
            console.log('📱 Orientation changed, reinitializing video');
            this.reinitializeVideo();
        });

        console.log('✅ All events bound successfully');
    }

    updateStatus(message, isLoading = true, type = 'info') {
        const statusEl = document.getElementById('camera-status');
        if (!statusEl) return;

        // Log với màu sắc dựa vào type
        const logStyle = {
            info: 'color: #3b82f6', // blue
            error: 'color: #ef4444; font-weight: bold', // red
            warning: 'color: #f59e0b', // yellow
            success: 'color: #10b981' // green
        };

        console.log(
            `%c[Camera Status] ${message}`,
            logStyle[type] || logStyle.info
        );

        // Thêm device info vào log khi có lỗi
        if (type === 'error') {
            this.logDeviceInfo();
        }

        statusEl.innerHTML = `
            <div class="flex items-center justify-center gap-2">
                ${isLoading ? '<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>' : ''}
                <span class="${type === 'error' ? 'text-red-500' : type === 'warning' ? 'text-yellow-500' : type === 'success' ? 'text-green-500' : ''}">${message}</span>
            </div>
        `;
    }

    async checkSupport() {
        // Đảm bảo DOM đã sẵn sàng
        await this.domReadyPromise;
        
        console.group('📋 Camera Support Check');
        console.log('Checking camera support...');

        // Feature detection results
        const support = {
            mediaDevices: !!navigator.mediaDevices,
            getUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
            enumerateDevices: !!(navigator.mediaDevices && navigator.mediaDevices.enumerateDevices),
            secureContext: !!window.isSecureContext,
            https: window.location.protocol === 'https:',
            videoElement: !!this.video,
            srcObject: !!(this.video && 'srcObject' in this.video)
        };

        console.table(support);
        
        // Check basic API support
        if (!support.mediaDevices) {
            console.error('[ERROR] mediaDevices API không được hỗ trợ');
            console.error('[DEBUG] Navigator APIs:', Object.keys(navigator));
            throw new Error('Trình duyệt không hỗ trợ mediaDevices API. Vui lòng sử dụng trình duyệt hiện đại hơn.');
        }
        
        if (!support.getUserMedia) {
            console.error('[ERROR] getUserMedia không được hỗ trợ');
            console.error('[DEBUG] MediaDevices APIs:', Object.keys(navigator.mediaDevices));
            throw new Error('Trình duyệt không hỗ trợ getUserMedia. Vui lòng cập nhật trình duyệt.');
        }

        console.log('[DEBUG] ✓ Các API cơ bản đều được hỗ trợ');

        if (!support.enumerateDevices) {
            console.error('❌ enumerateDevices not supported');
            throw new Error('Trình duyệt không hỗ trợ enumerateDevices. Không thể liệt kê camera.');
        }

        // Check HTTPS (required for camera access on most browsers)
        if (window.location.protocol !== 'https:' && 
            window.location.hostname !== 'localhost' && 
            window.location.hostname !== '127.0.0.1') {
            console.warn('⚠️ Camera may not work without HTTPS');
        }

        // Check camera permission state if possible
        if (navigator.permissions && navigator.permissions.query) {
            try {
                const result = await navigator.permissions.query({ name: 'camera' });
                console.log('Camera permission state:', result.state);
                
                if (result.state === 'denied') {
                    throw new Error('Quyền truy cập camera đã bị từ chối. Vui lòng cấp quyền trong cài đặt trình duyệt');
                }
            } catch (error) {
                console.warn('Permission query not supported:', error);
            }
        }

            // Final check - verify camera access without stopping stream
        try {
            // Không cần test stream riêng - để dành cho startCamera
            console.log('✅ Basic camera support verified');
            return true;        } catch (error) {
            console.error('❌ Camera access error:', error);
            
            // Provide more specific error messages
            if (error.name === 'NotAllowedError') {
                throw new Error('Vui lòng cấp quyền camera và làm mới trang');
            } else if (error.name === 'NotFoundError') {
                throw new Error('Không tìm thấy thiết bị camera');
            } else if (error.name === 'NotReadableError') {
                throw new Error('Camera đang được sử dụng bởi ứng dụng khác');
            } else {
                throw new Error(`Lỗi camera: ${error.message}`);
            }
        }
    }

    // Log device and browser information
    logVideoState(context = '') {
        if (!this.video) {
            console.error('No video element to log state');
            return;
        }

        const readyStates = [
            'HAVE_NOTHING',
            'HAVE_METADATA',
            'HAVE_CURRENT_DATA',
            'HAVE_FUTURE_DATA',
            'HAVE_ENOUGH_DATA'
        ];

        const networkStates = [
            'NETWORK_EMPTY',
            'NETWORK_IDLE',
            'NETWORK_LOADING',
            'NETWORK_NO_SOURCE'
        ];

        const state = {
            context: context,
            timestamp: new Date().toISOString(),
            readyState: {
                code: this.video.readyState,
                description: readyStates[this.video.readyState]
            },
            networkState: {
                code: this.video.networkState,
                description: networkStates[this.video.networkState]
            },
            dimensions: {
                videoWidth: this.video.videoWidth,
                videoHeight: this.video.videoHeight,
                clientWidth: this.video.clientWidth,
                clientHeight: this.video.clientHeight,
                offsetWidth: this.video.offsetWidth,
                offsetHeight: this.video.offsetHeight
            },
            timing: {
                currentTime: this.video.currentTime,
                duration: this.video.duration
            },
            playback: {
                paused: this.video.paused,
                ended: this.video.ended,
                seeking: this.video.seeking,
                playbackRate: this.video.playbackRate
            },
            stream: {
                hasStream: !!this.video.srcObject,
                streamActive: this.video.srcObject instanceof MediaStream ? 
                    this.video.srcObject.active : false,
                tracks: this.video.srcObject instanceof MediaStream ?
                    this.video.srcObject.getTracks().map(t => ({
                        kind: t.kind,
                        label: t.label,
                        enabled: t.enabled,
                        readyState: t.readyState
                    })) : []
            },
            error: this.video.error ? {
                code: this.video.error.code,
                message: this.video.error.message
            } : null
        };

        console.group(`📺 Video State: ${context}`);
        Object.entries(state).forEach(([key, value]) => {
            if (key === 'context' || key === 'timestamp') {
                console.log(`${key}:`, value);
            } else {
                console.group(key);
                Object.entries(value).forEach(([k, v]) => {
                    console.log(`${k}:`, v);
                });
                console.groupEnd();
            }
        });
        console.groupEnd();
    }

    logDeviceInfo() {
        console.group('📱 Device & Browser Info');
        console.log('User Agent:', navigator.userAgent);
        console.log('Platform:', navigator.platform);
        console.log('Vendor:', navigator.vendor);
        console.log('Screen:', {
            width: window.screen.width,
            height: window.screen.height,
            pixelRatio: window.devicePixelRatio
        });
        console.log('Browser:', {
            language: navigator.language,
            hardwareConcurrency: navigator.hardwareConcurrency,
            onLine: navigator.onLine
        });
        if (this.stream) {
            const videoTrack = this.stream.getVideoTracks()[0];
            if (videoTrack) {
                console.log('Video Track:', {
                    label: videoTrack.label,
                    settings: videoTrack.getSettings(),
                    constraints: videoTrack.getConstraints()
                });
            }
        }
        console.groupEnd();
    }

    async initialize() {
        console.group('🎥 Camera Initialization');
        console.log('Starting camera initialization...');
        this.logDeviceInfo();

        // Reset state trước khi kiểm tra
        this.retryCount = 0;
        
        // Nếu đang khởi tạo, đợi tối đa 5 giây
        if (this.isInitializing) {
            console.warn('⚠️ Camera is already initializing, waiting...');
            let waitTime = 0;
            while (this.isInitializing && waitTime < 5000) {
                await new Promise(resolve => setTimeout(resolve, 100));
                waitTime += 100;
            }
            if (this.isInitializing) {
                this.isInitializing = false; // Reset flag nếu quá thời gian
                console.error('⌛ Camera initialization timeout');
                throw new Error('Khởi tạo camera quá thời gian. Vui lòng thử lại.');
            }
        }

        // Nếu đã khởi tạo và hoạt động, trả về true
        if (this.isInitialized && this.stream && this.stream.active) {
            console.log('✅ Camera already initialized and active');
            console.groupEnd();
            return true;
        }

        // Kiểm tra và đóng stream cũ nếu còn
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                try {
                    track.stop();
                } catch (e) {
                    console.warn('Error stopping track:', e);
                }
            });
        }

        // Reset state
        this.isInitializing = true;
        this.isInitialized = false;
        this.stream = null;
        
        // Update UI with percentage progress
        let progress = 0;
        const updateProgress = (stage, percent) => {
            progress = percent;
            this.updateStatus(`Đang khởi tạo camera (${Math.round(progress)}%)... ${stage}`, true);
        };
        
        if (this.video) {
            this.video.classList.add('loading');
        }

        try {
            updateProgress('Kiểm tra hỗ trợ', 10);
            console.log('1️⃣ Checking browser support...');
            await this.checkSupport();

            updateProgress('Yêu cầu quyền camera', 30);
            console.log('2️⃣ Getting camera permissions...');
            let initialStream;
            try {
                initialStream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    } 
                });
            } finally {
                if (initialStream) {
                    initialStream.getTracks().forEach(track => {
                        try { track.stop(); } catch (e) { console.warn(e); }
                    });
                }
            }

            updateProgress('Đang quét camera', 50);
            console.log('3️⃣ Enumerating cameras...');
            let enumStream;
            let devices = [];
            
            try {
                // Force device re-enumeration to get fresh labels
                enumStream = await navigator.mediaDevices.getUserMedia({ video: true });
                devices = await navigator.mediaDevices.enumerateDevices();
            } finally {
                if (enumStream) {
                    enumStream.getTracks().forEach(track => {
                        try { track.stop(); } catch (e) { console.warn(e); }
                    });
                }
            }
            
            this.cameras = devices.filter(device => device.kind === 'videoinput');
            console.log(`Found ${this.cameras.length} cameras:`, this.cameras);

            if (this.cameras.length === 0) {
                throw new Error('Không tìm thấy camera trên thiết bị');
            }

            // Sort cameras: built-in webcams first, then other cameras, DroidCam last
            this.cameras.sort((a, b) => {
                const labelA = (a.label || '').toLowerCase();
                const labelB = (b.label || '').toLowerCase();
                
                if (labelA.includes('droidcam')) return 1;
                if (labelB.includes('droidcam')) return -1;
                
                if (labelA.includes('built-in') || labelA.includes('integrated')) return -1;
                if (labelB.includes('built-in') || labelB.includes('integrated')) return 1;
                
                return 0;
            });

            console.log(`4️⃣ Found ${this.cameras.length} cameras:`, this.cameras);
            
            // Update UI
            this.updateCameraList();
            this.currentDeviceId = this.cameras[0].deviceId;

            // Configure video element
            console.log('5️⃣ Configuring video element...');
            await this.configureVideo();

            // Start camera stream
            console.log('6️⃣ Starting camera stream...');
            await this.startCamera(this.currentDeviceId);

            this.isInitialized = true;
            this.updateStatus('', false);
            if (this.video) {
                this.video.classList.remove('loading');
            }
            console.log('✅ Camera initialized successfully');
            return true;

        } catch (error) {
            console.error('❌ Camera initialization error:', error);
            this.updateStatus('Lỗi: ' + error.message, false);
            throw error;
        } finally {
            this.isInitializing = false;
        }
    }

    async configureVideo() {
        if (!this.video) {
            throw new Error('Video element not found');
        }

        console.log('Configuring video element...');

        // Clear any existing stream
        if (this.video.srcObject) {
            const oldStream = this.video.srcObject;
            if (oldStream instanceof MediaStream) {
                oldStream.getTracks().forEach(track => track.stop());
            }
            this.video.srcObject = null;
        }

        // Reset video element
        this.video.pause();
        this.video.currentTime = 0;
        this.video.load();

        // Essential attributes for mobile
        this.video.setAttribute('autoplay', '');
        this.video.setAttribute('playsinline', '');
        this.video.setAttribute('muted', '');
        this.video.muted = true; // Explicit mute

        // Additional attributes for better compatibility
        this.video.setAttribute('webkit-playsinline', '');
        this.video.setAttribute('x5-playsinline', '');
        this.video.setAttribute('x5-video-player-type', 'h5');
        this.video.setAttribute('x5-video-player-fullscreen', 'true');
        this.video.setAttribute('x5-video-orientation', 'portrait');
        this.video.setAttribute('x-webkit-airplay', 'allow');
        this.video.setAttribute('disablePictureInPicture', '');

        // iOS fullscreen hint
        this.video.setAttribute('playsinline', 'true');
        this.video.setAttribute('controls', 'false');

        // Style for proper display
        this.video.style.width = '100%';
        this.video.style.height = 'auto';
        this.video.style.transform = 'none';
        this.video.style.objectFit = 'contain';

        // Force layout recalculation
        this.video.offsetHeight;

        // Add event listeners for debugging
        const events = ['loadedmetadata', 'loadeddata', 'canplay', 'canplaythrough', 'play', 'playing'];
        events.forEach(event => {
            this.video.addEventListener(event, () => {
                console.log(`Video event: ${event}`);
                if (event === 'canplaythrough') {
                    this.updateStatus('', false);
                }
            }, { once: true });
        });

        // Add error listener
        this.video.addEventListener('error', (e) => {
            console.error('Video error:', this.video.error);
            this.updateStatus(`Lỗi video: ${this.video.error?.message || 'Không xác định'}`, false);
        });

        console.log('✅ Video element configured');
        return true;

        // Force layout recalculation
        this.video.offsetHeight;

        console.log('✅ Video configured');
    }

    logStreamDetails(stream, context = '') {
        console.group(`📹 Stream Details ${context}`);
        
        if (!stream) {
            console.error('❌ No stream provided');
            console.groupEnd();
            return;
        }

        const videoTracks = stream.getVideoTracks();
        console.log('Stream ID:', stream.id);
        console.log('Stream Active:', stream.active);
        console.log('Video Tracks:', videoTracks.length);

        videoTracks.forEach((track, index) => {
            console.group(`Video Track ${index + 1}`);
            console.log('Label:', track.label);
            console.log('ID:', track.id);
            console.log('Ready State:', track.readyState);
            console.log('Enabled:', track.enabled);
            console.log('Muted:', track.muted);
            
            const settings = track.getSettings();
            console.log('Settings:', {
                width: settings.width,
                height: settings.height,
                frameRate: settings.frameRate,
                facingMode: settings.facingMode,
                deviceId: settings.deviceId,
                aspectRatio: settings.aspectRatio
            });
            
            if (track.getCapabilities) {
                console.log('Capabilities:', track.getCapabilities());
            }
            
            console.log('Constraints:', track.getConstraints());
            console.groupEnd();
        });

        console.groupEnd();
    }

    async startCamera(deviceId = null) {
        console.group('🎥 Starting Camera');
        console.log('Device ID:', deviceId || 'default');

        if (!deviceId && this.currentDeviceId) {
            deviceId = this.currentDeviceId;
            console.log('Using current device ID:', deviceId);
        }

        this.updateStatus('Đang kết nối camera...', true, 'info');

        try {
            console.log('Stopping existing camera...');
            await this.stopCamera();

            // Reset video element
            if (this.video) {
                this.video.srcObject = null;
                this.video.load();
                await this.configureVideo();
            }

            // Mobile detection
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            
            // Prepare constraints based on device type
            const constraints = [];
            
            if (deviceId) {
                // If we have a specific device ID, try it first
                constraints.push({
                    video: {
                        deviceId: { exact: deviceId },
                        width: { ideal: isMobile ? 720 : 1280 },
                        height: { ideal: isMobile ? 1280 : 720 }
                    }
                });
            } else {
                // Try environment camera first on mobile
                if (isMobile) {
                    constraints.push({
                        video: {
                            facingMode: { ideal: 'environment' },
                            width: { ideal: 720 },
                            height: { ideal: 1280 }
                        }
                    });
                }
            }
            
            // Add fallback constraints
            constraints.push(
                {
                    video: {
                        deviceId: deviceId ? { exact: deviceId } : undefined,
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    }
                },
                {
                    video: deviceId ? { deviceId: { exact: deviceId } } : true
                }
            );

            console.group('📝 Trying Camera Constraints');
            let stream;
            let error;
            let successfulConstraints;

            for (let i = 0; i < constraints.length; i++) {
                try {
                    this.updateStatus(`Đang thử cấu hình camera (${i + 1}/${constraints.length})...`, true, 'info');
                    console.log(`🔄 Attempt ${i + 1}/${constraints.length}:`, constraints[i]);

                    // Log device permissions before trying
                    if (navigator.permissions) {
                        try {
                            const permission = await navigator.permissions.query({ name: 'camera' });
                            console.log('Camera permission state:', permission.state);
                        } catch (e) {
                            console.warn('Could not query camera permission:', e);
                        }
                    }

                    stream = await navigator.mediaDevices.getUserMedia(constraints[i]);
                    
                    // Verify stream has video tracks
                    const tracks = stream.getVideoTracks();
                    console.log(`Found ${tracks.length} video tracks`);
                    
                    if (tracks.length > 0) {
                        const track = tracks[0];
                        console.log('✅ Got working video track:', {
                            label: track.label,
                            id: track.id,
                            settings: track.getSettings(),
                            constraints: track.getConstraints()
                        });
                        successfulConstraints = constraints[i];
                        break;
                    } else {
                        console.warn('❌ No video tracks in stream');
                        throw new Error('Không tìm thấy camera track trong stream');
                    }
                } catch (e) {
                    console.warn(`❌ Failed with constraints ${i + 1}:`, e);
                    console.log('Error name:', e.name);
                    console.log('Error message:', e.message);
                    error = e;
                    await new Promise(r => setTimeout(r, 500));
                }
            }
            
            if (successfulConstraints) {
                console.log('✅ Successfully connected with constraints:', successfulConstraints);
            }
            console.groupEnd();

            if (!stream || stream.getVideoTracks().length === 0) {
                throw error || new Error('Không thể kết nối camera');
            }

            // Log stream details before setting
            this.logStreamDetails(stream, 'Before Setting');

            // Set stream to video
            this.stream = stream;
            this.video.srcObject = stream;

            console.log('Stream set to video element');
            console.log('Video element state:', {
                readyState: this.video.readyState,
                paused: this.video.paused,
                currentTime: this.video.currentTime,
                videoWidth: this.video.videoWidth,
                videoHeight: this.video.videoHeight,
                error: this.video.error
            });

            // Wait for video to be ready
            try {
                await this.waitForVideo();
                this.updateStatus('Camera đã sẵn sàng', false, 'success');
                if (this.takePhotoBtn) this.takePhotoBtn.disabled = false;

                // Log final stream state
                this.logStreamDetails(stream, 'After Setup');
                console.groupEnd(); // End startCamera group
                return true;
            } catch (error) {
                console.error('Video preparation error:', error);
                this.updateStatus(`Lỗi chuẩn bị video: ${error.message}`, false, 'error');
                throw error;
            }

        } catch (error) {
            console.error('❌ Error starting camera:', error);
            this.updateStatus('Lỗi: ' + error.message, false);
            throw error;
        }
    }

    async waitForVideo() {
        if (!this.video) throw new Error('Không tìm thấy video element');

        console.group('🎬 Video Ready Check');
        
        return new Promise((resolve, reject) => {
            // Theo dõi trạng thái video
            let isPlaying = false;
            let hasSize = false;
            let checkCount = 0;
            const maxChecks = 50; // Tối đa 50 lần kiểm tra
            const checkInterval = 100; // Kiểm tra mỗi 100ms
            
            // Thêm các event handlers
            const handlers = new Map();
            
            handlers.set('loadedmetadata', () => {
                console.log('📏 Video metadata loaded');
                this.logVideoState('Metadata loaded');
            });

            handlers.set('canplay', () => {
                console.log('▶️ Video can start playing');
                // Bắt đầu phát video
                this.video.play().catch(e => console.warn('Auto-play failed:', e));
            });

            handlers.set('playing', () => {
                console.log('🎬 Video started playing');
                isPlaying = true;
                checkReady();
            });

            // Kiểm tra kích thước riêng biệt
            const checkDimensions = () => {
                if (this.video.videoWidth > 0 && this.video.videoHeight > 0) {
                    console.log('📐 Video dimensions available:', {
                        width: this.video.videoWidth,
                        height: this.video.videoHeight
                    });
                    hasSize = true;
                    checkReady();
                }
            };

            // Kiểm tra mỗi 100ms cho đến khi có kích thước
            const dimensionsInterval = setInterval(checkDimensions, 100);

            const checkReady = () => {
                if (isPlaying && hasSize) {
                    cleanup();
                    console.log('✅ Video fully ready');
                    this.logVideoState('Final state');
                    console.groupEnd();
                    resolve();
                }
            };

            // Cleanup function
            const cleanup = () => {
                clearInterval(dimensionsInterval);
                clearTimeout(timeoutId);
                handlers.forEach((handler, event) => {
                    this.video.removeEventListener(event, handler);
                });
            };

            // Add all event listeners
            handlers.forEach((handler, event) => {
                this.video.addEventListener(event, handler);
            });

            // Error handling
            this.video.addEventListener('error', (error) => {
                cleanup();
                console.error('❌ Video error:', error);
                this.logVideoState('Error state');
                console.groupEnd();
                reject(new Error(`Lỗi video: ${this.video.error?.message || 'Không xác định'}`));
            });

            // Timeout
            const timeoutId = setTimeout(() => {
                cleanup();
                console.warn('⚠️ Video initialization timeout');
                this.logVideoState('Timeout state');
                console.groupEnd();
                
                // Không reject ngay - thử tiếp tục chờ
                console.log('Continuing to wait for video...');
            }, 5000);

            const checkVideo = () => {
                checkCount++;
                
                // Get detailed state
                const state = {
                    width: this.video.videoWidth,
                    height: this.video.videoHeight,
                    readyState: this.video.readyState,
                    readyStateText: [
                        'HAVE_NOTHING',
                        'HAVE_METADATA',
                        'HAVE_CURRENT_DATA',
                        'HAVE_FUTURE_DATA',
                        'HAVE_ENOUGH_DATA'
                    ][this.video.readyState],
                    paused: this.video.paused,
                    ended: this.video.ended,
                    seeking: this.video.seeking,
                    error: this.video.error,
                    networkState: this.video.networkState,
                    hasStream: !!this.video.srcObject,
                    streamActive: this.video.srcObject instanceof MediaStream ? 
                        this.video.srcObject.active : false
                };

                // Log with colors based on state
                const stateColor = state.readyState >= 2 ? 'color: #10b981' : 'color: #f59e0b';
                console.log(
                    `%cVideo check ${checkCount}/${maxChecks}:`,
                    stateColor,
                    state
                );

                // Log any errors
                if (state.error) {
                    console.error('Video Error:', {
                        code: state.error.code,
                        message: state.error.message,
                        name: state.error.name
                    });
                }

                // Try to play if paused
                if (state.paused && state.hasStream && state.readyState >= 2) {
                    console.log('Attempting to play paused video...');
                    this.video.play()
                        .then(() => console.log('✅ Video playback started'))
                        .catch(err => {
                            console.error('❌ Video play error:', err);
                            this.updateStatus(`Lỗi phát video: ${err.message}`, false, 'error');
                        });
                }

                // Check if video is ready
                if (state.width > 0 && state.height > 0 && state.readyState >= 2) {
                    console.log('✅ Video is ready:', state);
                    clearTimeout(timeoutId);
                    console.groupEnd();
                    resolve();
                } else if (checkCount >= maxChecks) {
                    console.error(`❌ Video not ready after ${maxChecks} checks:`, state);
                    clearTimeout(timeoutId);
                    console.groupEnd();
                    reject(new Error(`Video không sẵn sàng sau ${maxChecks} lần kiểm tra. Trạng thái: ${state.readyStateText}`));
                } else {
                    setTimeout(checkVideo, checkInterval);
                }
            };

            ['loadedmetadata', 'loadeddata', 'canplay'].forEach(event => {
                this.video.addEventListener(event, () => {
                    console.log(`Video event: ${event}`);
                    checkVideo();
                }, { once: true });
            });

            checkVideo();
        });
    }

    async stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
            this.video.load();
        }
    }

    updateCameraList() {
        if (!this.cameraSelect) return;

        this.cameraSelect.innerHTML = '';
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.text = 'Chọn camera...';
        defaultOption.disabled = true;
        defaultOption.selected = !this.currentDeviceId;
        this.cameraSelect.appendChild(defaultOption);

        // Filter out DroidCam if there are other cameras available
        let availableCameras = this.cameras;
        if (this.cameras.length > 1) {
            availableCameras = this.cameras.filter(camera => !camera.label.toLowerCase().includes('droidcam'));
        }

        availableCameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera.deviceId;
            option.text = camera.label || `Camera ${this.cameras.indexOf(camera) + 1}`;
            option.selected = camera.deviceId === this.currentDeviceId;
            this.cameraSelect.appendChild(option);
        });

        this.cameraSelect.disabled = false;
    }

    async switchCamera() {
        if (!this.cameras || this.cameras.length < 2) {
            console.warn('No other cameras available');
            return;
        }

        const currentIndex = this.cameras.findIndex(cam => cam.deviceId === this.currentDeviceId);
        const nextIndex = (currentIndex + 1) % this.cameras.length;
        const nextCamera = this.cameras[nextIndex];

        try {
            await this.startCamera(nextCamera.deviceId);
            this.currentDeviceId = nextCamera.deviceId;
            if (this.cameraSelect) {
                this.cameraSelect.value = nextCamera.deviceId;
            }
        } catch (error) {
            console.error('Failed to switch camera:', error);
            this.updateStatus('Không thể chuyển camera: ' + error.message, false);
        }
    }

    async onCameraChange() {
        if (!this.cameraSelect) return;
        const deviceId = this.cameraSelect.value;
        if (!deviceId) return;

        try {
            await this.startCamera(deviceId);
            this.currentDeviceId = deviceId;
        } catch (error) {
            console.error('Failed to change camera:', error);
            this.updateStatus('Không thể đổi camera: ' + error.message, false);
            this.cameraSelect.value = this.currentDeviceId;
        }
    }

    async takePhoto() {
        console.log('Taking photo...');
        
        if (!this.video || !this.stream) {
            console.error('Camera not ready:', { video: !!this.video, stream: !!this.stream });
            throw new Error('Camera chưa sẵn sàng');
        }

        if (this.video.readyState !== this.video.HAVE_ENOUGH_DATA) {
            console.warn('Video not ready yet, state:', this.video.readyState);
            throw new Error('Video chưa sẵn sàng để chụp');
        }

        // Add flash effect
        const flashOverlay = document.createElement('div');
        flashOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: white;
            opacity: 0;
            z-index: 9999;
            pointer-events: none;
            transition: opacity 0.1s ease-out;
        `;
        document.body.appendChild(flashOverlay);

        // Flash animation
        flashOverlay.style.opacity = '1';
        setTimeout(() => {
            flashOverlay.style.opacity = '0';
            setTimeout(() => flashOverlay.remove(), 300);
        }, 100);

        try {
            const canvas = document.createElement('canvas');
            canvas.width = this.video.videoWidth;
            canvas.height = this.video.videoHeight;
            
            console.log('Capturing photo with dimensions:', {
                width: canvas.width,
                height: canvas.height
            });
            
            const ctx = canvas.getContext('2d');
            
            // Apply mirror effect if using front camera
            const videoTrack = this.stream.getVideoTracks()[0];
            const isFrontCamera = videoTrack.label.toLowerCase().includes('front') || 
                                videoTrack.label.toLowerCase().includes('user') ||
                                videoTrack.label.toLowerCase().includes('selfie');
            
            if (isFrontCamera) {
                ctx.scale(-1, 1);
                ctx.translate(-canvas.width, 0);
            }
            
            ctx.drawImage(this.video, 0, 0);
            
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.95);
            });

            console.log('Photo captured, converting to base64...');

            const reader = new FileReader();
            const photoData = await new Promise((resolve, reject) => {
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });

            console.log('Photo ready, emitting event...');
            this._emitPhotoTaken(photoData);
            return photoData;
        } catch (error) {
            console.error('Error taking photo:', error);
            throw new Error('Lỗi khi chụp ảnh: ' + error.message);
        }
    }

    _emitPhotoTaken(photoData) {
        const event = new CustomEvent('photoTaken', {
            detail: { photoData }
        });
        document.dispatchEvent(event);
    }

    async open() {
        console.group('📸 Opening Camera');
        try {
            // Check if modal exists
            if (!this.modal) {
                throw new Error('Không tìm thấy camera modal trong DOM');
            }

            // Check video element
            if (!this.video) {
                throw new Error('Không tìm thấy video element trong DOM');
            }

            console.log('Modal found:', this.modal);
            console.log('Video element found:', this.video);
            
            // Try to initialize if needed
            if (!this.isInitialized) {
                console.log('Camera not initialized, initializing...');
                try {
                    await this.initialize();
                } catch (error) {
                    console.error('❌ Initialization failed:', error);
                    this.updateStatus(`Lỗi khởi tạo: ${error.message}`, false, 'error');
                    throw error;
                }
            }

            // Show modal
            console.log('Showing camera modal...');
            this.modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';

            // Start camera stream
            console.log('Starting camera stream...');
            try {
                await this.startCamera();
                console.log('✅ Camera opened successfully');
                this.updateStatus('Camera đã sẵn sàng', false, 'success');
            } catch (error) {
                console.error('❌ Failed to start camera:', error);
                this.updateStatus(`Không thể khởi động camera: ${error.message}`, false, 'error');
                throw error;
            }
        } catch (error) {
            console.error('❌ Error opening camera:', error);
            this.updateStatus(`Lỗi mở camera: ${error.message}`, false, 'error');
            throw error;
        } finally {
            console.groupEnd();
        }
    }

    close() {
        this.stopCamera();
        if (this.modal) {
            this.modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }

    async reinitializeVideo() {
        if (!this.stream || !this.video) return;

        console.log('Reinitializing video...');
        const currentDeviceId = this.currentDeviceId;

        try {
            await this.stopCamera();
            await new Promise(resolve => setTimeout(resolve, 500));
            await this.startCamera(currentDeviceId);
        } catch (error) {
            console.error('Error reinitializing video:', error);
            this.updateStatus('Lỗi khởi tạo lại camera: ' + error.message, false);
        }
    }

    createImageFromFile(file) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = () => reject(new Error('Không thể tải ảnh'));
            img.src = URL.createObjectURL(file);
        });
    }

    processSelectedImage(img) {
        console.log('Processing selected image...');
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas dimensions to match image, maintaining aspect ratio
        const maxDimension = 1280;
        let width = img.width;
        let height = img.height;
        
        if (width > height && width > maxDimension) {
            height = Math.round(height * (maxDimension / width));
            width = maxDimension;
        } else if (height > maxDimension) {
            width = Math.round(width * (maxDimension / height));
            height = maxDimension;
        }
        
        canvas.width = width;
        canvas.height = height;
        
        // Draw and process image
        ctx.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob((blob) => {
            // Create a data URL from the blob
            const reader = new FileReader();
            reader.onload = () => {
                const imageData = reader.result;
                
                // Emit the photo taken event
                this._emitPhotoTaken(imageData);
                
                // Clean up
                URL.revokeObjectURL(img.src);
            };
            reader.onerror = () => {
                console.error('Error reading processed image');
                this.updateStatus('Lỗi xử lý ảnh', false, 'error');
                URL.revokeObjectURL(img.src);
            };
            reader.readAsDataURL(blob);
            
            this.updateStatus('Đã xử lý ảnh thành công!', false, 'success');
        }, 'image/jpeg', 0.95);
    }
}
