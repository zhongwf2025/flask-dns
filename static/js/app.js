/* DNS管理系统 - 前端通用脚本 */

// 通用AJAX请求函数
function apiRequest(url, method, data) {
    return fetch(url, {
        method: method || 'POST',
        headers: {'Content-Type': 'application/json'},
        body: data ? JSON.stringify(data) : undefined
    }).then(function(response) {
        return response.json();
    });
}

// 确认对话框
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// 显示提示信息
function showToast(message, type) {
    var toast = document.createElement('div');
    toast.className = 'alert alert-' + (type || 'info');
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '200px';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s';
        setTimeout(function() {
            document.body.removeChild(toast);
        }, 500);
    }, 3000);
}

// 格式化时间
function formatTime(timestamp) {
    if (!timestamp) return '-';
    var d = new Date(timestamp * 1000);
    return d.getFullYear() + '-' +
        String(d.getMonth() + 1).padStart(2, '0') + '-' +
        String(d.getDate()).padStart(2, '0') + ' ' +
        String(d.getHours()).padStart(2, '0') + ':' +
        String(d.getMinutes()).padStart(2, '0') + ':' +
        String(d.getSeconds()).padStart(2, '0');
}

// 格式化数字
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return String(num);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 自动关闭提示消息
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(function() {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 500);
        }, 5000);
    });
});
