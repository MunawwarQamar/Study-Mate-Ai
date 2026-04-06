var loginForm = document.getElementById('login-form');
var registerForm = document.getElementById('register-form');

var formTitle = document.getElementById('form-title');
var loginTab = document.getElementById('login-tab');
var registerTab = document.getElementById('register-tab');

function showRegister() {
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';

    formTitle.innerText = "Register";

    loginTab.classList.remove('active-tab');
    loginTab.classList.add('inactive-tab');

    registerTab.classList.remove('inactive-tab');
    registerTab.classList.add('active-tab');
}

function showLogin() {
    registerForm.style.display = 'none';
    loginForm.style.display = 'block';

    formTitle.innerText = "Login";

    registerTab.classList.remove('active-tab');
    registerTab.classList.add('inactive-tab');

    loginTab.classList.remove('inactive-tab');
    loginTab.classList.add('active-tab');
}