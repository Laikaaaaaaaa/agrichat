// Lớp quản lý video element và hiển thị
export class VideoDisplay {
    constructor(videoElement) {
        this.video = videoElement;
        this.configure();
        console.log('🎬 Khởi tạo VideoDisplay');
    }

    configure() {
        if (!this.video) return;

        console.log('Configuring video element...');

        try {
            // Essential attributes for mobile
            this.video.setAttribute('autoplay', '');
            this.video.setAttribute('playsinline', '');
            this.video.setAttribute('muted', '');
            this.video.muted = true;
            
            // Additional attributes for better compatibility
            this.video.setAttribute('webkit-playsinline', ''); // iOS Safari
            this.video.setAttribute('x5-playsinline', ''); // QQ Browser
            this.video.setAttribute('x5-video-player-type', 'h5'); // X5 Engine
            this.video.setAttribute('x5-video-player-fullscreen', 'true');
            this.video.setAttribute('playsInline', ''); // React Native

            // Reset any transforms
            this.video.style.transform = 'none';

            // Force layout recalculation
            this.video.offsetHeight;

            console.log('✅ Video element configured successfully');
            console.log('Current video attributes:', {
                autoplay: this.video.autoplay,
                muted: this.video.muted,
                playsinline: this.video.getAttribute('playsinline'),
                style: this.video.style.cssText
            });
        } catch (error) {
            console.error('❌ Error configuring video:', error);
            throw error;
        }
    }

    getVideoState() {
        if (!this.video) return { error: 'No video element' };
        
        return {
            width: this.video.videoWidth,
            height: this.video.videoHeight,
            readyState: this.video.readyState,
            readyStateText: [
                'HAVE_NOTHING',
                'HAVE_METADATA',
                'HAVE_CURRENT_DATA',
                'HAVE_FUTURE_DATA',
                'HAVE_ENOUGH_DATA'
            ][this.video.readyState] || 'UNKNOWN',
            paused: this.video.paused,
            played: this.video.played.length > 0,
            hasStream: !!this.video.srcObject,
            streamActive: this.video.srcObject instanceof MediaStream ? 
                this.video.srcObject.active : false,
            streamTracks: this.video.srcObject instanceof MediaStream ? 
                this.video.srcObject.getTracks().map(t => ({
                    kind: t.kind,
                    enabled: t.enabled,
                    readyState: t.readyState
                })) : []
        };
    }

    async setStream(stream) {
        if (!this.video) {
            throw new Error('Không tìm thấy video element');
        }

        console.log('📥 Setting new stream to video element');
        
        try {
            // Reset video element
            if (this.video.srcObject) {
                console.log('Stopping old stream...');
                const oldStream = this.video.srcObject;
                this.video.srcObject = null;
                oldStream.getTracks().forEach(track => {
                    try {
                        track.stop();
                    } catch (e) {
                        console.warn('Error stopping track:', e);
                    }
                });
            }

            // Reset video element
            this.video.removeAttribute('src');
            this.video.load();
            
            // Configure video for mobile
            this.configure();
            
            // Set new stream
            console.log('Setting new stream:', stream);
            this.video.srcObject = stream;
            
            // Log initial state
            console.log('Initial video state:', this.getVideoState());

            // Wait for video to be ready
            console.log('Waiting for video to be ready...');
            await this.waitForVideo();
            
            // Log final state
            console.log('Final video state:', this.getVideoState());
            return true;
        } catch (error) {
            console.error('❌ Error setting stream:', error);
            console.error('Final video state:', this.getVideoState());
            throw error;
        }
    }

    async waitForVideo() {
        if (!this.video) throw new Error('Không tìm thấy video element');

        return new Promise((resolve, reject) => {
            let checkCount = 0;
            const maxChecks = 100; // 10 seconds at 100ms intervals

            const timeoutId = setTimeout(() => {
                const finalState = this.getVideoState();
                console.error('Video timeout. Final state:', finalState);
                reject(new Error(`Hết thời gian chờ video. Trạng thái: ${JSON.stringify(finalState)}`));
            }, 10000);

            const checkVideo = () => {
                checkCount++;
                const state = this.getVideoState();
                console.log(`Video check ${checkCount}:`, state);

                // Always try to play if paused
                if (state.paused && this.video.srcObject) {
                    console.log('Attempting to play video...');
                    this.video.play().catch(e => console.warn('Play attempt failed:', e));
                }

                if (state.width > 0 && state.height > 0 && state.readyState >= 2) {
                    console.log('✅ Video ready with size:', state.width, 'x', state.height);
                    clearTimeout(timeoutId);
                    if (state.paused) {
                        this.video.play()
                            .then(() => {
                                console.log('✅ Video playing successfully');
                                resolve();
                            })
                            .catch(error => {
                                console.warn('⚠️ Autoplay blocked:', error);
                                // Show play button
                                this.showPlayButton(document.getElementById('camera-status') || document.body);
                                resolve(); // Still resolve as user can click play
                            });
                    } else {
                        console.log('✅ Video already playing');
                        resolve();
                    }
                } else if (checkCount >= maxChecks) {
                    console.error('❌ Max checks reached. Video state:', state);
                    reject(new Error(`Không thể khởi tạo video sau ${maxChecks} lần thử`));
                } else {
                    setTimeout(checkVideo, 100);
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

    getVideoElement() {
        return this.video;
    }

    showPlayButton(container) {
        const button = document.createElement('button');
        button.textContent = 'Bấm để bật camera';
        button.className = 'bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded';
        button.onclick = () => this.video.play();
        container.appendChild(button);
    }

    getVideoSize() {
        return {
            width: this.video.videoWidth,
            height: this.video.videoHeight
        };
    }

    isReady() {
        return this.video &&
               this.video.readyState >= 2 &&
               this.video.videoWidth > 0 &&
               this.video.videoHeight > 0;
    }
}
