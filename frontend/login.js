document.getElementById('login-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    
    // Clear previous messages
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
    
    // Basic validation
    if (!username || !password) {
        showError('Please fill in all fields');
        return;
    }
    
    if (username.length < 3) {
        showError('User ID must be at least 3 characters long');
        return;
    }
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({ username, password })
        });

        if (response.ok) {
            const data = await response.json();
            showSuccess('Login successful! Redirecting...');
            setTimeout(() => {
                window.location.href = '/chat.html';
            }, 1500);
        } else {
            const errorData = await response.json();
            showError(errorData.detail || 'Login failed. Please check your credentials.');
        }
    } catch (error) {
        showError('Error during login: ' + error.message);
    }
});

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    } else {
        alert(message);
    }
}

function showSuccess(message) {
    const successDiv = document.getElementById('success-message');
    if (successDiv) {
        successDiv.textContent = message;
        successDiv.style.display = 'block';
    } else {
        alert(message);
    }
}

// Real-time validation
document.getElementById('username').addEventListener('input', function() {
    const username = this.value.trim();
    if (username && username.length < 3) {
        this.setCustomValidity('User ID must be at least 3 characters long');
    } else {
        this.setCustomValidity('');
    }
});
