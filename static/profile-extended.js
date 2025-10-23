// ==================== PHOTOS FUNCTIONALITY ====================

async function loadPhotos() {
  try {
    const response = await fetch('/api/profile/photos');
    const data = await response.json();
    
    if (data.success) {
      displayPhotos(data.photos);
      updatePhotosCount(data.photos.length);
    }
  } catch (error) {
    console.error('Error loading photos:', error);
  }
}

function displayPhotos(photos) {
  const container = document.getElementById('photos-grid');
  if (!container) return;
  
  if (photos.length === 0) {
    container.innerHTML = `
      <div class="col-span-full text-center py-8 text-gray-500">
        <i class="fas fa-images text-4xl mb-3 opacity-50"></i>
        <p>Chưa có ảnh nào</p>
        <button onclick="openUploadPhotoModal()" class="mt-3 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
          <i class="fas fa-upload"></i> Tải ảnh lên
        </button>
      </div>
    `;
    return;
  }
  
  container.innerHTML = photos.map(photo => `
    <div class="relative group cursor-pointer rounded-lg overflow-hidden shadow hover:shadow-lg transition-all" onclick="openPhotoModal(${photo.id})">
      <img src="${photo.photo_url}" alt="${photo.caption || 'Photo'}" class="w-full h-40 object-cover">
      <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all flex items-center justify-center">
        <div class="opacity-0 group-hover:opacity-100 text-white text-sm space-x-3">
          <span><i class="fas fa-heart"></i> ${photo.likes_count}</span>
          <span><i class="fas fa-comment"></i> ${photo.comments_count}</span>
        </div>
      </div>
      ${photo.photo_type === 'cover' ? '<div class="absolute top-2 left-2 bg-green-600 text-white text-xs px-2 py-1 rounded">Ảnh bìa</div>' : ''}
      ${photo.photo_type === 'profile' ? '<div class="absolute top-2 left-2 bg-blue-600 text-white text-xs px-2 py-1 rounded">Ảnh đại diện</div>' : ''}
    </div>
  `).join('');
}

async function openPhotoModal(photoId) {
  try {
    const response = await fetch('/api/profile/photos');
    const data = await response.json();
    
    if (data.success) {
      const photo = data.photos.find(p => p.id === photoId);
      if (photo) {
        displayPhotoModal(photo);
      }
    }
  } catch (error) {
    console.error('Error loading photo:', error);
  }
}

function displayPhotoModal(photo) {
  const modal = document.getElementById('photo-detail-modal') || createPhotoModal();
  
  const date = new Date(photo.created_at);
  const formattedDate = date.toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
  
  const avatar = photo.user_avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(photo.user_name)}&background=16a34a&color=fff&size=40`;
  const likeButtonClass = photo.user_liked ? 'text-red-600' : 'text-gray-600';
  
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4" onclick="if(event.target === this) closePhotoModal()">
      <div class="bg-white rounded-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col md:flex-row" onclick="event.stopPropagation()">
        
        <!-- Left: Image -->
        <div class="md:w-2/3 bg-black flex items-center justify-center p-4">
          <img src="${photo.photo_url}" alt="${photo.caption || 'Photo'}" class="max-w-full max-h-[80vh] object-contain">
        </div>
        
        <!-- Right: Info & Comments -->
        <div class="md:w-1/3 flex flex-col max-h-[90vh]">
          <!-- Header -->
          <div class="p-4 border-b border-gray-200 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <img src="${avatar}" alt="${photo.user_name}" class="w-10 h-10 rounded-full">
              <div>
                <h3 class="font-semibold">${photo.user_name}</h3>
                <p class="text-xs text-gray-500">${formattedDate}</p>
              </div>
            </div>
            <button onclick="closePhotoModal()" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times text-xl"></i>
            </button>
          </div>
          
          <!-- Caption -->
          ${photo.caption ? `
            <div class="p-4 border-b border-gray-200">
              <p class="text-gray-800">${photo.caption}</p>
            </div>
          ` : ''}
          
          <!-- Stats -->
          <div class="p-4 border-b border-gray-200 flex gap-4 text-sm text-gray-600">
            <span><i class="fas fa-heart text-red-600"></i> <span id="photo-likes-count">${photo.likes_count}</span> lượt thích</span>
            <span><i class="fas fa-comment text-blue-600"></i> <span id="photo-comments-count">${photo.comments_count}</span> bình luận</span>
          </div>
          
          <!-- Comments Section -->
          <div id="photo-comments-section" class="flex-1 overflow-y-auto p-4 space-y-3">
            <div class="flex justify-center py-4">
              <div class="loading-spinner"></div>
            </div>
          </div>
          
          <!-- Actions -->
          <div class="p-4 border-t border-gray-200">
            <div class="flex gap-4 mb-3">
              <button onclick="togglePhotoLike(${photo.id})" id="photo-like-btn" class="flex items-center gap-2 ${likeButtonClass} hover:text-red-600 transition-colors">
                <i class="fas fa-heart"></i>
                <span>Thích</span>
              </button>
              <button onclick="focusPhotoComment()" class="flex items-center gap-2 text-gray-600 hover:text-blue-600 transition-colors">
                <i class="fas fa-comment"></i>
                <span>Bình luận</span>
              </button>
              <button class="flex items-center gap-2 text-gray-600 hover:text-green-600 transition-colors">
                <i class="fas fa-share"></i>
                <span>Chia sẻ</span>
              </button>
            </div>
            
            <!-- Comment Input -->
            <form onsubmit="submitPhotoComment(event, ${photo.id})" class="flex gap-2">
              <input type="text" id="photo-comment-input" placeholder="Viết bình luận..." class="flex-1 px-3 py-2 border border-gray-300 rounded-full focus:outline-none focus:border-green-600" required>
              <button type="submit" class="px-4 py-2 bg-green-600 text-white rounded-full hover:bg-green-700">
                <i class="fas fa-paper-plane"></i>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  `;
  
  modal.style.display = 'block';
  document.body.style.overflow = 'hidden';
  
  // Load comments
  loadPhotoComments(photo.id);
}

function createPhotoModal() {
  const modal = document.createElement('div');
  modal.id = 'photo-detail-modal';
  document.body.appendChild(modal);
  return modal;
}

function closePhotoModal() {
  const modal = document.getElementById('photo-detail-modal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }
}

async function loadPhotoComments(photoId) {
  try {
    const response = await fetch(`/api/profile/photos/${photoId}/comments`);
    const data = await response.json();
    
    if (data.success) {
      displayPhotoComments(data.comments, photoId);
    }
  } catch (error) {
    console.error('Error loading comments:', error);
  }
}

function displayPhotoComments(comments, photoId) {
  const container = document.getElementById('photo-comments-section');
  if (!container) return;
  
  if (comments.length === 0) {
    container.innerHTML = '<p class="text-gray-500 text-center text-sm">Chưa có bình luận nào</p>';
    return;
  }
  
  container.innerHTML = comments.map(comment => {
    const avatar = comment.user_avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(comment.user_name)}&background=16a34a&color=fff&size=32`;
    const date = new Date(comment.created_at);
    const timeAgo = getTimeAgo(date);
    
    return `
      <div class="flex gap-3">
        <img src="${avatar}" alt="${comment.user_name}" class="w-8 h-8 rounded-full flex-shrink-0">
        <div class="flex-1 bg-gray-100 rounded-lg p-3">
          <div class="flex items-center justify-between mb-1">
            <span class="font-semibold text-sm">${comment.user_name}</span>
            <span class="text-xs text-gray-500">${timeAgo}</span>
          </div>
          <p class="text-sm text-gray-800">${comment.content}</p>
        </div>
      </div>
    `;
  }).join('');
}

async function togglePhotoLike(photoId) {
  try {
    const response = await fetch(`/api/profile/photos/${photoId}/like`, {
      method: 'POST'
    });
    
    const data = await response.json();
    
    if (data.success) {
      document.getElementById('photo-likes-count').textContent = data.likes_count;
      
      const likeBtn = document.getElementById('photo-like-btn');
      if (data.action === 'liked') {
        likeBtn.classList.remove('text-gray-600');
        likeBtn.classList.add('text-red-600');
      } else {
        likeBtn.classList.remove('text-red-600');
        likeBtn.classList.add('text-gray-600');
      }
    }
  } catch (error) {
    console.error('Error toggling like:', error);
  }
}

async function submitPhotoComment(event, photoId) {
  event.preventDefault();
  
  const input = document.getElementById('photo-comment-input');
  const content = input.value.trim();
  
  if (!content) return;
  
  try {
    const response = await fetch(`/api/profile/photos/${photoId}/comments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content })
    });
    
    const data = await response.json();
    
    if (data.success) {
      input.value = '';
      document.getElementById('photo-comments-count').textContent = data.comments_count;
      loadPhotoComments(photoId);
    } else {
      alert(data.message || 'Không thể gửi bình luận');
    }
  } catch (error) {
    console.error('Error submitting comment:', error);
    alert('Lỗi kết nối. Vui lòng thử lại.');
  }
}

function focusPhotoComment() {
  document.getElementById('photo-comment-input')?.focus();
}

function updatePhotosCount(count) {
  const el = document.getElementById('photos-count');
  if (el) el.textContent = count;
}

// ==================== FRIENDS FUNCTIONALITY ====================

async function loadFriends() {
  try {
    // Use profileUserId from profile.html (the user whose profile is being viewed)
    const userId = typeof profileUserId !== 'undefined' ? profileUserId : null;
    
    if (!userId) {
      console.error('profileUserId is not defined');
      return;
    }
    
    const response = await fetch(`/api/profile/friends?user_id=${userId}`);
    const data = await response.json();
    
    if (data.success) {
      displayFriends(data.friends);
      updateFriendsCount(data.count);
    }
  } catch (error) {
    console.error('Error loading friends:', error);
  }
}

function displayFriends(friends) {
  const container = document.getElementById('friends-grid');
  if (!container) return;
  
  if (friends.length === 0) {
    container.innerHTML = '<p class="text-gray-500 text-center col-span-full">Chưa có bạn bè nào</p>';
    return;
  }
  
  container.innerHTML = friends.map(friend => {
    const avatar = friend.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(friend.name)}&background=16a34a&color=fff&size=80`;
    
    return `
      <div class="bg-white rounded-lg overflow-hidden shadow hover:shadow-md transition-all">
        <a href="/profile/${friend.id}">
          <img src="${avatar}" alt="${friend.name}" class="w-full h-32 object-cover hover:opacity-90 transition-opacity">
        </a>
        <div class="p-3">
          <a href="/profile/${friend.id}" class="hover:underline">
            <h4 class="font-semibold text-sm truncate">${friend.name}</h4>
          </a>
          <p class="text-xs text-gray-500 truncate">${friend.email}</p>
          <a href="/profile/${friend.id}" class="block w-full mt-2 px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-xs font-medium text-center">
            Xem trang cá nhân
          </a>
        </div>
      </div>
    `;
  }).join('');
}

function updateFriendsCount(count) {
  const els = document.querySelectorAll('.friends-count');
  els.forEach(el => el.textContent = count);
}

// Helper function for time ago
function switchTab(tabName) {
  // Hide all sections
  document.getElementById('posts-section')?.classList.add('hidden');
  document.getElementById('photos-section')?.classList.add('hidden');
  document.getElementById('friends-section')?.classList.add('hidden');
  document.getElementById('intro-section')?.classList.add('hidden');
  
  // Show selected section
  document.getElementById(`${tabName}-section`)?.classList.remove('hidden');
  
  // Load data if needed
  if (tabName === 'photos') {
    loadPhotos();
  } else if (tabName === 'friends') {
    loadFriends();
  }
  
  // Update tab styles
  document.querySelectorAll('.profile-tab').forEach(tab => {
    tab.classList.remove('border-green-600', 'text-green-600', 'border-b-4', '-mb-px');
    tab.classList.add('text-gray-600');
  });
  
  const activeTab = event.target;
  activeTab.classList.remove('text-gray-600');
  activeTab.classList.add('border-green-600', 'text-green-600', 'border-b-4', '-mb-px');
}

// Helper function for time ago
function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  
  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + ' năm trước';
  
  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + ' tháng trước';
  
  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + ' ngày trước';
  
  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + ' giờ trước';
  
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + ' phút trước';
  
  return 'Vừa xong';
}
