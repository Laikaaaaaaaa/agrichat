// Lớp xử lý chụp và xử lý ảnh
export class PhotoCapture {
    constructor(videoElement) {
        this.video = videoElement;
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        console.log('📸 Khởi tạo PhotoCapture');
    }

    async capture(options = {}) {
        console.log('📸 PhotoCapture.capture() called');
        console.log('🔍 Video element:', this.video);
        console.log('🔍 Video ready state:', this.video?.readyState);
        console.log('🔍 Video dimensions:', this.video?.videoWidth, 'x', this.video?.videoHeight);
        
        if (!this.video || this.video.readyState !== this.video.HAVE_ENOUGH_DATA) {
            console.error('❌ Video not ready for capture');
            console.log('🔍 HAVE_ENOUGH_DATA constant:', this.video?.HAVE_ENOUGH_DATA);
            throw new Error('Video chưa sẵn sàng để chụp');
        }

        console.log('✅ Video is ready, starting capture process');

        // Set canvas size to match video
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        console.log('📐 Canvas size set to:', this.canvas.width, 'x', this.canvas.height);

        // Apply any effects before capture
        if (options.mirror) {
            console.log('🔄 Applying mirror effect');
            this.ctx.scale(-1, 1);
            this.ctx.translate(-this.canvas.width, 0);
        }

        // Draw the video frame to canvas
        console.log('🎨 Drawing video frame to canvas');
        this.ctx.drawImage(this.video, 0, 0);

        // Reset transform
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);

        // Apply post-processing effects
        if (options.brightness) {
            this.adjustBrightness(options.brightness);
        }
        if (options.contrast) {
            this.adjustContrast(options.contrast);
        }
        if (options.saturation) {
            this.adjustSaturation(options.saturation);
        }

        // Convert to blob
        console.log('🔄 Converting canvas to blob...');
        const blob = await new Promise(resolve => {
            this.canvas.toBlob(resolve, 'image/jpeg', options.quality || 0.95);
        });
        
        console.log('📦 Blob created:', blob);
        console.log('📦 Blob size:', blob?.size, 'bytes');

        console.log('🔄 Converting blob to data URL...');
        const dataUrl = await this.blobToDataUrl(blob);
        console.log('📝 Data URL created, length:', dataUrl?.length);

        const result = {
            blob,
            dataUrl,
            width: this.canvas.width,
            height: this.canvas.height
        };
        
        console.log('✅ PhotoCapture.capture() completed successfully');
        console.log('📦 Returning result:', result);
        return result;
    }

    adjustBrightness(value) {
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        
        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.min(255, data[i] + value);     // Red
            data[i + 1] = Math.min(255, data[i + 1] + value); // Green
            data[i + 2] = Math.min(255, data[i + 2] + value); // Blue
        }
        
        this.ctx.putImageData(imageData, 0, 0);
    }

    adjustContrast(value) {
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        const factor = (259 * (value + 255)) / (255 * (259 - value));
        
        for (let i = 0; i < data.length; i += 4) {
            data[i] = factor * (data[i] - 128) + 128;     // Red
            data[i + 1] = factor * (data[i + 1] - 128) + 128; // Green
            data[i + 2] = factor * (data[i + 2] - 128) + 128; // Blue
        }
        
        this.ctx.putImageData(imageData, 0, 0);
    }

    adjustSaturation(value) {
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        
        for (let i = 0; i < data.length; i += 4) {
            const gray = (data[i] + data[i + 1] + data[i + 2]) / 3;
            data[i] = gray + (data[i] - gray) * value;     // Red
            data[i + 1] = gray + (data[i + 1] - gray) * value; // Green
            data[i + 2] = gray + (data[i + 2] - gray) * value; // Blue
        }
        
        this.ctx.putImageData(imageData, 0, 0);
    }

    async blobToDataUrl(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    getImageFilters() {
        return {
            normal: (imageData) => imageData,
            grayscale: this.grayscaleFilter.bind(this),
            sepia: this.sepiaFilter.bind(this),
            invert: this.invertFilter.bind(this),
            blur: this.blurFilter.bind(this)
        };
    }

    grayscaleFilter(imageData) {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            const avg = (data[i] + data[i + 1] + data[i + 2]) / 3;
            data[i] = avg;     // Red
            data[i + 1] = avg; // Green
            data[i + 2] = avg; // Blue
        }
        return imageData;
    }

    sepiaFilter(imageData) {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];
            data[i] = Math.min(255, (r * 0.393) + (g * 0.769) + (b * 0.189));
            data[i + 1] = Math.min(255, (r * 0.349) + (g * 0.686) + (b * 0.168));
            data[i + 2] = Math.min(255, (r * 0.272) + (g * 0.534) + (b * 0.131));
        }
        return imageData;
    }

    invertFilter(imageData) {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            data[i] = 255 - data[i];         // Red
            data[i + 1] = 255 - data[i + 1]; // Green
            data[i + 2] = 255 - data[i + 2]; // Blue
        }
        return imageData;
    }

    blurFilter(imageData, radius = 1) {
        // Simple box blur implementation
        const width = imageData.width;
        const height = imageData.height;
        const data = imageData.data;
        const output = new Uint8ClampedArray(data);
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                let r = 0, g = 0, b = 0, a = 0;
                let count = 0;
                
                for (let dy = -radius; dy <= radius; dy++) {
                    for (let dx = -radius; dx <= radius; dx++) {
                        const px = x + dx;
                        const py = y + dy;
                        
                        if (px >= 0 && px < width && py >= 0 && py < height) {
                            const i = (py * width + px) * 4;
                            r += data[i];
                            g += data[i + 1];
                            b += data[i + 2];
                            a += data[i + 3];
                            count++;
                        }
                    }
                }
                
                const i = (y * width + x) * 4;
                output[i] = r / count;
                output[i + 1] = g / count;
                output[i + 2] = b / count;
                output[i + 3] = a / count;
            }
        }
        
        imageData.data.set(output);
        return imageData;
    }
}
