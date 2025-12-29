// Camera utility functions
export async function checkVideoReadyState(video, statusCallback) {
    return new Promise((resolve, reject) => {
        let isResolved = false;
        let checkCount = 0;
        const maxChecks = 50; // About 5 seconds at 100ms intervals
        
        // Log initial state
        console.log('Initial video state:', {
            videoElement: video ? 'exists' : 'missing',
            srcObject: video?.srcObject ? 'set' : 'not set',
            readyState: video?.readyState,
            paused: video?.paused,
            width: video?.videoWidth,
            height: video?.videoHeight
        });

        const timeoutId = setTimeout(() => {
            if (!isResolved) {
                console.error('Video ready state check timeout');
                reject(new Error('Camera không phản hồi sau 15 giây'));
            }
        }, 15000);

        function checkState() {
            if (!video || isResolved) return;

            const state = {
                hasVideo: !!video,
                hasStream: !!video.srcObject,
                readyState: video.readyState,
                paused: video.paused,
                width: video.videoWidth,
                height: video.videoHeight,
                played: video.played.length > 0,
                error: video.error
            };

            checkCount++;
            console.log(`Check ${checkCount}/${maxChecks}:`, state);

            // Success condition
            if (state.width > 0 && 
                state.height > 0 && 
                !state.paused && 
                state.readyState >= 2 &&
                state.played) {
                
                console.log('✅ Video is ready:', state);
                clearTimeout(timeoutId);
                isResolved = true;
                statusCallback?.('Camera đã sẵn sàng', false);
                resolve(true);
                return;
            }

            // Handle specific issues
            if (state.error) {
                console.error('Video error:', state.error);
                clearTimeout(timeoutId);
                isResolved = true;
                reject(new Error(`Lỗi camera: ${state.error.message}`));
                return;
            }

            if (checkCount >= maxChecks) {
                console.error('Max check attempts reached');
                clearTimeout(timeoutId);
                isResolved = true;
                reject(new Error('Không thể khởi tạo camera sau nhiều lần thử'));
                return;
            }

            // Update status with more detail
            const status = !state.hasStream ? 'Đang kết nối camera...' :
                          !state.width ? 'Đang khởi tạo video...' :
                          state.paused ? 'Đang chờ camera hoạt động...' :
                          'Đang kiểm tra camera...';
            
            statusCallback?.(status, true);

            // Continue checking
            setTimeout(checkState, 100);
        }

        // Set up event listeners
        const events = ['loadedmetadata', 'loadeddata', 'canplay', 'playing'];
        events.forEach(event => {
            video.addEventListener(event, () => {
                console.log(`Event triggered: ${event}`);
                checkState();
            }, { once: true });
        });

        // Handle errors
        video.onerror = (e) => {
            console.error('Video error event:', e);
            if (!isResolved) {
                clearTimeout(timeoutId);
                isResolved = true;
                reject(new Error(`Lỗi camera: ${video.error?.message || 'Không xác định'}`));
            }
        };

        // Start checking
        checkState();

        // Try to play the video
        video.play().catch(error => {
            console.warn('Auto-play failed:', error);
            if (!isResolved) {
                // Create manual play button
                const playButton = document.createElement('button');
                playButton.textContent = 'Bấm để bật camera';
                playButton.className = 'bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded shadow';
                playButton.onclick = async () => {
                    try {
                        await video.play();
                        playButton.remove();
                    } catch (e) {
                        console.error('Manual play failed:', e);
                        statusCallback?.('Không thể khởi động camera: ' + e.message, false);
                    }
                };

                // Show the button
                const container = video.parentElement;
                if (container) {
                    container.appendChild(playButton);
                    statusCallback?.('Vui lòng bấm nút để bật camera', false);
                }
            }
        });
    });
}
