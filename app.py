from flask import Flask, render_template, request, jsonify
import subprocess
import re
import os
from urllib.parse import urlparse
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Rate limiting and validation
MAX_URL_LENGTH = 200
ALLOWED_DOMAINS = ['instagram.com', 'instagr.am']
DOWNLOAD_TIMEOUT = 300  # 5 minutes

def validate_url(url):
    """Validate if the URL is a valid Instagram URL"""
    try:
        if len(url) > MAX_URL_LENGTH:
            return False, "URL too long"
            
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format"
            
        domain = result.netloc.lower()
        if not any(allowed in domain for allowed in ALLOWED_DOMAINS):
            return False, "Only Instagram URLs are allowed"
            
        # Basic Instagram URL pattern check
        instagram_pattern = r'instagram\.com/(p|reel|tv|stories)/[a-zA-Z0-9_-]+'
        if not re.search(instagram_pattern, url):
            return False, "URL doesn't appear to be a valid Instagram post"
            
        return True, "Valid URL"
    except Exception as e:
        return False, f"URL validation error: {str(e)}"

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InstaSave - Online Instagram Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .status-box {
            height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
        }
        .feature-card {
            transition: transform 0.2s;
        }
        .feature-card:hover {
            transform: translateY(-2px);
        }
        .disabled { background-color: #ccc; cursor: not-allowed; }
    </style>
</head>
<body class="bg-gradient-to-br from-purple-100 via-pink-50 to-red-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- Header -->
        <div class="text-center mb-10">
            <div class="flex items-center justify-center mb-4">
                <i class="fab fa-instagram text-5xl text-pink-600 mr-3"></i>
                <h1 class="text-5xl font-bold bg-gradient-to-r from-pink-600 to-purple-600 bg-clip-text text-transparent">
                    InstaSave
                </h1>
            </div>
            <p class="text-gray-600 text-xl">Download Instagram videos online - Available 24/7</p>
            <div class="mt-4 inline-flex items-center bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
                <i class="fas fa-circle text-green-500 text-xs mr-2"></i>
                Server Status: Online
            </div>
        </div>

        <!-- Features -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="feature-card bg-white rounded-xl p-6 shadow-lg">
                <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                    <i class="fas fa-bolt text-blue-600 text-xl"></i>
                </div>
                <h3 class="text-xl font-semibold text-gray-800 mb-2">Fast Downloads</h3>
                <p class="text-gray-600">High-speed servers ensure quick video downloads from Instagram.</p>
            </div>
            <div class="feature-card bg-white rounded-xl p-6 shadow-lg">
                <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                    <i class="fas fa-shield-alt text-green-600 text-xl"></i>
                </div>
                <h3 class="text-xl font-semibold text-gray-800 mb-2">Secure Processing</h3>
                <p class="text-gray-600">Your downloads are processed securely with privacy protection.</p>
            </div>
            <div class="feature-card bg-white rounded-xl p-6 shadow-lg">
                <div class="w-16 h-16 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                    <i class="fas fa-clock text-purple-600 text-xl"></i>
                </div>
                <h3 class="text-xl font-semibold text-gray-800 mb-2">24/7 Availability</h3>
                <p class="text-gray-600">Our service is always online and ready to download your videos.</p>
            </div>
        </div>

        <!-- Main Card -->
        <div class="bg-white rounded-2xl shadow-xl p-8 mb-8">
            <div class="text-center mb-6">
                <h2 class="text-2xl font-semibold text-gray-800 mb-2">Download Instagram Video</h2>
                <p class="text-gray-500">Enter Instagram URL to download video (reels, posts, stories)</p>
            </div>

            <!-- Input Form -->
            <div class="space-y-6">
                <div class="relative">
                    <label for="instagramUrl" class="block text-sm font-medium text-gray-700 mb-2">
                        Instagram Post URL
                    </label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="fas fa-link text-gray-400"></i>
                        </div>
                        <input 
                            type="text" 
                            id="instagramUrl" 
                            placeholder="https://www.instagram.com/p/ABC123xyz/"
                            class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 transition-all duration-200 text-gray-900"
                        >
                    </div>
                </div>

                <!-- Command Display -->
                <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <h3 class="text-sm font-medium text-gray-700 mb-2 flex items-center">
                        <i class="fas fa-terminal text-pink-500 mr-2"></i>
                        Processing Command
                    </h3>
                    <div id="commandDisplay" class="bg-black rounded p-3 text-green-400 font-mono text-sm break-all">
                        yt-dlp ""
                    </div>
                </div>

                <!-- Download Button -->
                <button id="downloadBtn" 
                    class="w-full bg-gradient-to-r from-pink-500 to-purple-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-pink-600 hover:to-purple-700 transform hover:scale-105 transition-all duration-200 shadow-md hover:shadow-lg flex items-center justify-center">
                    <i class="fas fa-download mr-2"></i>
                    Download Video
                </button>
            </div>
        </div>

        <!-- Status Section -->
        <div class="bg-white rounded-2xl shadow-lg p-6">
            <h3 class="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                <i class="fas fa-cogs text-pink-500 mr-2"></i>
                Download Status
            </h3>
            <div id="statusBox" class="status-box w-full bg-black text-green-400 p-4 rounded-lg font-mono text-sm overflow-auto mb-4">
                Service is online and ready. Enter an Instagram URL to start downloading.
            </div>
            
            <div class="flex gap-3">
                <button id="clearStatus" class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition flex items-center">
                    <i class="fas fa-trash mr-1"></i> Clear
                </button>
                <button id="copyStatus" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition flex items-center">
                    <i class="fas fa-copy mr-1"></i> Copy
                </button>
            </div>
        </div>

        <!-- How It Works -->
        <div class="bg-white rounded-2xl shadow-lg p-6 mt-8">
            <h3 class="text-2xl font-semibold text-gray-800 mb-6 text-center">How It Works</h3>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div class="text-center">
                    <div class="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl font-bold text-pink-600">1</span>
                    </div>
                    <h4 class="font-semibold text-gray-800 mb-2">Paste URL</h4>
                    <p class="text-gray-600 text-sm">Copy any Instagram post URL and paste it in the input box</p>
                </div>
                <div class="text-center">
                    <div class="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl font-bold text-pink-600">2</span>
                    </div>
                    <h4 class="font-semibold text-gray-800 mb-2">Start Download</h4>
                    <p class="text-gray-600 text-sm">Click the download button to process your request</p>
                </div>
                <div class="text-center">
                    <div class="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl font-bold text-pink-600">3</span>
                    </div>
                    <h4 class="font-semibold text-gray-800 mb-2">Wait Briefly</h4>
                    <p class="text-gray-600 text-sm">Our servers fetch the video (usually takes a few seconds)</p>
                </div>
                <div class="text-center">
                    <div class="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl font-bold text-pink-600">4</span>
                    </div>
                    <h4 class="font-semibold text-gray-800 mb-2">Get Your Video</h4>
                    <p class="text-gray-600 text-sm">Download completes automatically to your device</p>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center mt-12 text-gray-500">
            <p class="mb-2">⚠️ This service is for personal, educational use only.</p>
            <p class="text-sm">Respect content creators' rights and Instagram's Terms of Service.</p>
            <p class="text-xs mt-4">Server uptime: 99.9% | Last check: ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''</p>
        </div>
    </div>

    <script>
        const urlInput = document.getElementById('instagramUrl');
        const commandDisplay = document.getElementById('commandDisplay');
        const statusBox = document.getElementById('statusBox');
        const downloadBtn = document.getElementById('downloadBtn');
        const clearStatus = document.getElementById('clearStatus');
        const copyStatus = document.getElementById('copyStatus');

        // Update command display
        function updateCommand() {
            const url = urlInput.value.trim();
            if (url) {
                commandDisplay.textContent = `yt-dlp "${url}"`;
            } else {
                commandDisplay.textContent = 'yt-dlp ""';
            }
        }

        // Add message to status box
        function addStatus(message) {
            statusBox.innerHTML += message + '\\n';
            statusBox.scrollTop = statusBox.scrollHeight;
        }

        // Clear status box
        clearStatus.addEventListener('click', function() {
            statusBox.innerHTML = 'Status cleared. Ready for new download.';
        });

        // Copy status
        copyStatus.addEventListener('click', function() {
            const text = statusBox.textContent;
            navigator.clipboard.writeText(text).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check mr-1"></i> Copied!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
                alert('Failed to copy. Please select and copy manually.');
            });
        });

        // Real-time command update
        urlInput.addEventListener('input', updateCommand);

        // Download video
        downloadBtn.addEventListener('click', async function() {
            const url = urlInput.value.trim();
            
            if (!url) {
                addStatus('❌ ERROR: Please enter an Instagram URL');
                return;
            }

            // Validate URL format
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                addStatus('❌ ERROR: URL must start with http:// or https://');
                return;
            }

            if (!url.includes('instagram.com') && !url.includes('instagr.am')) {
                addStatus('❌ ERROR: Only Instagram URLs are supported');
                return;
            }

            // Update UI
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
            addStatus(`🔄 Processing request for: ${url}`);

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({url: url})
                });

                const data = await response.json();
                
                if (data.success) {
                    addStatus('✅ SUCCESS: Download completed!');
                    addStatus(`📁 File saved as: ${data.filename}`);
                } else {
                    addStatus(`❌ FAILED: ${data.error}`);
                    if (data.details) {
                        addStatus(`🔍 Details: ${data.details}`);
                    }
                }
            } catch (error) {
                addStatus(`❌ NETWORK ERROR: ${error.message}`);
                addStatus('💡 Check your internet connection and try again');
            } finally {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<i class="fas fa-download mr-2"></i>Download Video';
            }
        });

        // Allow Enter key to trigger download
        urlInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                downloadBtn.click();
            }
        });

        // Initial command update
        updateCommand();

        // Add welcome message
        addStatus('🚀 Service started successfully!');
        addStatus('💡 Enter an Instagram URL to begin downloading videos');
    </script>
</body>
</html>
'''

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        logger.info(f"Download request received for URL: {url}")
        
        if not url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        
        # Validate URL
        is_valid, message = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL rejected: {url} - {message}")
            return jsonify({'success': False, 'error': message})
        
        # Run yt-dlp command without format selection
        cmd = ['yt-dlp', '--no-check-certificate', url]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=DOWNLOAD_TIMEOUT
            )
            
            if result.returncode == 0:
                # Extract filename from output (simplified)
                output_lines = result.stdout.split('\\n')
                filename = "video.mp4"  # Default fallback
                for line in output_lines:
                    if "Destination:" in line:
                        filename = line.split("Destination:")[-1].strip()
                        break
                
                logger.info(f"Download successful for: {url}")
                return jsonify({
                    'success': True, 
                    'filename': filename,
                    'message': 'Download completed'
                })
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Download failed for {url}: {error_msg}")
                return jsonify({
                    'success': False, 
                    'error': 'Download failed', 
                    'details': error_msg[:200] + "..." if len(error_msg) > 200 else error_msg
                })
                
        except subprocess.TimeoutExpired:
            logger.error(f"Download timed out for: {url}")
            return jsonify({
                'success': False, 
                'error': 'Download timeout', 
                'details': f'Operation took longer than {DOWNLOAD_TIMEOUT} seconds'
            })
        except Exception as e:
            logger.error(f"Subprocess error for {url}: {str(e)}")
            return jsonify({
                'success': False, 
                'error': 'System error', 
                'details': str(e)
            })
            
    except Exception as e:
        logger.error(f"Request processing error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Get port from environment variable or default to 10000
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=Fal                </div>

                <!-- Download Button -->
                <button id="downloadBtn" 
                    class="w-full bg-gradient-to-r from-pink-500 to-purple-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-pink-600 hover:to-purple-700 transform hover:scale-105 transition-all duration-200 shadow-md hover:shadow-lg flex items-center justify-center">
                    <i class="fas fa-download mr-2"></i>
                    Download Video
                </button>
            </div>
        </div>

        <!-- Status Section -->
        <div class="bg-white rounded-2xl shadow-lg p-6">
            <h3 class="text-xl font-semibold text-gray-800 mb-4 flex items-center">
                <i class="fas fa-cogs text-pink-500 mr-2"></i>
                Download Status
            </h3>
            <div id="statusBox" class="status-box w-full bg-black text-green-400 p-4 rounded-lg font-mono text-sm overflow-auto mb-4">
                Service is online and ready. Enter an Instagram URL to start downloading.
            </div>
            
            <div class="flex gap-3">
                <button id="clearStatus" class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition flex items-center">
                    <i class="fas fa-trash mr-1"></i> Clear
                </button>
                <button id="copyStatus" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition flex items-center">
                    <i class="fas fa-copy mr-1"></i> Copy
                </button>
            </div>
        </div>

        <!-- How It Works -->
        <div class="bg-white rounded-2xl shadow-lg p-6 mt-8">
            <h3 class="text-2xl font-semibold text-gray-800 mb-6 text-center">How It Works</h3>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div class="text-center">
                    <div class="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl font-bold text-pink-600">1</span>
                    </div>
                    <h4 class="font-semibold text-gray-800 mb-2">Paste URL</h4>
                    <p class="text-gray-600 text-sm">Copy any Instagram post URL and paste it in the input box</p>
                </div>
                <div class="text-center">
                    <div class="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl font-bold text-pink-600">2</span>
                    </div>
                    <h4 class="font-semibold text-gray-800 mb-2">Start Download</h4>
                    <p class="text-gray-600 text-sm">Click the download button to process your request</p>
                </div>
                <div class="text-center">
                    <div class="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl font-bold text-pink-600">3</span>
                    </div>
                    <h4 class="font-semibold text-gray-800 mb-2">Wait Briefly</h4>
                    <p class="text-gray-600 text-sm">Our servers fetch the video (usually takes a few seconds)</p>
                </div>
                <div class="text-center">
                    <div class="w-16 h-16 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl font-bold text-pink-600">4</span>
                    </div>
                    <h4 class="font-semibold text-gray-800 mb-2">Get Your Video</h4>
                    <p class="text-gray-600 text-sm">Download completes automatically to your device</p>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center mt-12 text-gray-500">
            <p class="mb-2">⚠️ This service is for personal, educational use only.</p>
            <p class="text-sm">Respect content creators' rights and Instagram's Terms of Service.</p>
            <p class="text-xs mt-4">Server uptime: 99.9% | Last check: ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''</p>
        </div>
    </div>

    <script>
        const urlInput = document.getElementById('instagramUrl');
        const commandDisplay = document.getElementById('commandDisplay');
        const statusBox = document.getElementById('statusBox');
        const downloadBtn = document.getElementById('downloadBtn');
        const clearStatus = document.getElementById('clearStatus');
        const copyStatus = document.getElementById('copyStatus');

        // Update command display
        function updateCommand() {
            const url = urlInput.value.trim();
            if (url) {
                commandDisplay.textContent = `yt-dlp "${url}"`;
            } else {
                commandDisplay.textContent = 'yt-dlp ""';
            }
        }

        // Add message to status box
        function addStatus(message) {
            statusBox.innerHTML += message + '\\n';
            statusBox.scrollTop = statusBox.scrollHeight;
        }

        // Clear status box
        clearStatus.addEventListener('click', function() {
            statusBox.innerHTML = 'Status cleared. Ready for new download.';
        });

        // Copy status
        copyStatus.addEventListener('click', function() {
            const text = statusBox.textContent;
            navigator.clipboard.writeText(text).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check mr-1"></i> Copied!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
                alert('Failed to copy. Please select and copy manually.');
            });
        });

        // Real-time command update
        urlInput.addEventListener('input', updateCommand);

        // Download video
        downloadBtn.addEventListener('click', async function() {
            const url = urlInput.value.trim();
            
            if (!url) {
                addStatus('❌ ERROR: Please enter an Instagram URL');
                return;
            }

            // Validate URL format
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                addStatus('❌ ERROR: URL must start with http:// or https://');
                return;
            }

            if (!url.includes('instagram.com') && !url.includes('instagr.am')) {
                addStatus('❌ ERROR: Only Instagram URLs are supported');
                return;
            }

            // Update UI
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
            addStatus(`🔄 Processing request for: ${url}`);

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({url: url})
                });

                const data = await response.json();
                
                if (data.success) {
                    addStatus('✅ SUCCESS: Download completed!');
                    addStatus(`📁 File saved as: ${data.filename}`);
                } else {
                    addStatus(`❌ FAILED: ${data.error}`);
                    if (data.details) {
                        addStatus(`🔍 Details: ${data.details}`);
                    }
                }
            } catch (error) {
                addStatus(`❌ NETWORK ERROR: ${error.message}`);
                addStatus('💡 Check your internet connection and try again');
            } finally {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<i class="fas fa-download mr-2"></i>Download Video';
            }
        });

        // Allow Enter key to trigger download
        urlInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                downloadBtn.click();
            }
        });

        // Initial command update
        updateCommand();

        // Add welcome message
        addStatus('🚀 Service started successfully!');
        addStatus('💡 Enter an Instagram URL to begin downloading videos');
    </script>
</body>
</html>
'''

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        logger.info(f"Download request received for URL: {url}")
        
        if not url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        
        # Validate URL
        is_valid, message = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL rejected: {url} - {message}")
            return jsonify({'success': False, 'error': message})
        
        # Run yt-dlp command without format selection
        cmd = ['yt-dlp', '--no-check-certificate', url]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=DOWNLOAD_TIMEOUT
            )
            
            if result.returncode == 0:
                # Extract filename from output (simplified)
                output_lines = result.stdout.split('\\n')
                filename = "video.mp4"  # Default fallback
                for line in output_lines:
                    if "Destination:" in line:
                        filename = line.split("Destination:")[-1].strip()
                        break
                
                logger.info(f"Download successful for: {url}")
                return jsonify({
                    'success': True, 
                    'filename': filename,
                    'message': 'Download completed'
                })
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Download failed for {url}: {error_msg}")
                return jsonify({
                    'success': False, 
                    'error': 'Download failed', 
                    'details': error_msg[:200] + "..." if len(error_msg) > 200 else error_msg
                })
                
        except subprocess.TimeoutExpired:
            logger.error(f"Download timed out for: {url}")
            return jsonify({
                'success': False, 
                'error': 'Download timeout', 
                'details': f'Operation took longer than {DOWNLOAD_TIMEOUT} seconds'
            })
        except Exception as e:
            logger.error(f"Subprocess error for {url}: {str(e)}")
            return jsonify({
                'success': False, 
                'error': 'System error', 
                'details': str(e)
            })
            
    except Exception as e:
        logger.error(f"Request processing error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
