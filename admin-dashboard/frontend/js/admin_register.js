document.getElementById('admin-register-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const full_name = document.getElementById('full_name').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value;
    const confirm_password = document.getElementById('confirm_password').value;

    const messageDiv = document.getElementById('message');
    messageDiv.textContent = '';

    if (password !== confirm_password) {
        messageDiv.textContent = 'Passwords do not match.';
        messageDiv.style.color = 'red';
        return;
    }

    try {
        const response = await fetch('/api/admin/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                email,
                full_name,
                phone,
                password
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            messageDiv.textContent = 'Registration successful. You can now log in.';
            messageDiv.style.color = 'green';
            document.getElementById('admin-register-form').reset();
        } else {
            messageDiv.textContent = data.message || 'Registration failed.';
            messageDiv.style.color = 'red';
        }
    } catch (error) {
        messageDiv.textContent = 'An error occurred. Please try again later.';
        messageDiv.style.color = 'red';
    }
});
