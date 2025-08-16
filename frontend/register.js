document.getElementById('register-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const userId = document.getElementById('user_id').value.trim();
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const fullName = document.getElementById('full_name').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    
    // Clear previous messages
    document.getElementById('error-message').style.display = 'none';
    document.getElementById('success-message').style.display = 'none';
    
    // Validation
    if (!validateForm(userId, username, email, password, confirmPassword)) {
        return;
    }
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                username: username,
                email: email,
                full_name: fullName,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess('Registration successful! Redirecting to login...');
            setTimeout(() => {
                window.location.href = '/login.html';
            }, 2000);
        } else {
            showError(data.detail || 'Registration failed. Please try again.');
        }
    } catch (error) {
        showError('Error during registration: ' + error.message);
    }
});

function validateForm(userId, username, email, password, confirmPassword) {
    // User ID validation
    if (!userId || userId.length < 3) {
        showError('User ID must be at least 3 characters long');
        return false;
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(userId)) {
        showError('User ID can only contain letters, numbers, hyphens, and underscores');
        return false;
    }
    
    // Username validation
    if (!username || username.length < 3) {
        showError('Username must be at least 3 characters long');
        return false;
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
        showError('Username can only contain letters, numbers, hyphens, and underscores');
        return false;
    }
    
    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showError('Please enter a valid email address');
        return false;
    }
    
    // Password validation
    if (password.length < 6) {
        showError('Password must be at least 6 characters long');
        return false;
    }
    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
        showError('Password must contain at least one lowercase letter, one uppercase letter, and one number');
        return false;
    }
    
    // Confirm password validation
    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return false;
    }
    
    return true;
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    document.getElementById('success-message').style.display = 'none';
}

function showSuccess(message) {
    const successDiv = document.getElementById('success-message');
    successDiv.textContent = message;
    successDiv.style.display = 'block';
    document.getElementById('error-message').style.display = 'none';
}

// Real-time validation
document.getElementById('user_id').addEventListener('input', function() {
    const userId = this.value.trim();
    if (userId && !/^[a-zA-Z0-9_-]+$/.test(userId)) {
        this.setCustomValidity('User ID can only contain letters, numbers, hyphens, and underscores');
    } else {
        this.setCustomValidity('');
    }
});

document.getElementById('email').addEventListener('input', function() {
    const email = this.value.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (email && !emailRegex.test(email)) {
        this.setCustomValidity('Please enter a valid email address');
    } else {
        this.setCustomValidity('');
    }
});

document.getElementById('confirm_password').addEventListener('input', function() {
    const password = document.getElementById('password').value;
    const confirmPassword = this.value;
    if (confirmPassword && password !== confirmPassword) {
        this.setCustomValidity('Passwords do not match');
    } else {
        this.setCustomValidity('');
    }
});
