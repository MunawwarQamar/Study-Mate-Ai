var loginForm = document.getElementById('login-form');
var registerForm = document.getElementById('register-form');

function showRegister() {
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
}

function showLogin() {
    registerForm.style.display = 'none';
    loginForm.style.display = 'block';
}