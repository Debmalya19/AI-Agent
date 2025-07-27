document.getElementById('login-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

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
            alert('Login successful: ' + data.message);
            // Redirect to chat page after successful login
            window.location.href = '/chat.html';
        } else {
            const errorData = await response.json();
            alert('Login failed: ' + errorData.detail);
        }
    } catch (error) {
        alert('Error during login: ' + error.message);
    }
});
