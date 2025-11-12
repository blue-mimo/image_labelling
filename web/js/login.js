import { userPool, setAuthToken, setCognitoUser } from './auth.js';
import { showApp } from './mainApp.js';
import { loadImages } from './imageList.js';

export function showLogin() {
    document.getElementById('app').innerHTML = `
        <div style="max-width: 400px; margin: 100px auto; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            <h2 style="color: white; margin-top: 0;">Image Labeling - Login</h2>
            <form id="loginForm">
                <div style="margin: 15px 0;">
                    <label style="color: white; font-size: 14px;">Email:</label><br>
                    <input type="email" id="email" required style="width: 100%; padding: 10px; margin: 8px 0; background: rgba(255,255,255,0.9); border: none; border-radius: 6px; box-sizing: border-box;">
                </div>
                <div style="margin: 15px 0;">
                    <label style="color: white; font-size: 14px;">Password:</label><br>
                    <input type="password" id="password" required style="width: 100%; padding: 10px; margin: 8px 0; background: rgba(255,255,255,0.9); border: none; border-radius: 6px; box-sizing: border-box;">
                </div>
                <button type="submit" style="width: 100%; padding: 12px; background: white; color: #667eea; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; margin-top: 10px;">Login</button>
            </form>
            <div id="loginError" style="color: #ffe0e0; margin-top: 15px; font-size: 14px;"></div>
        </div>
    `;
    document.getElementById('loginForm').addEventListener('submit', login);
}

function login(event) {
    event.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    const authenticationData = { Username: email, Password: password };
    const authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails(authenticationData);
    const userData = { Username: email, Pool: userPool };
    const cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);

    cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: (result) => {
            setAuthToken(result.getIdToken().getJwtToken());
            setCognitoUser(cognitoUser);
            showApp();
            loadImages();
        },
        onFailure: (err) => {
            document.getElementById('loginError').textContent = err.message;
        },
        newPasswordRequired: () => {
            setCognitoUser(cognitoUser);
            showNewPasswordForm();
        }
    });
}

function showNewPasswordForm() {
    document.getElementById('app').innerHTML = `
        <div style="max-width: 400px; margin: 100px auto; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            <h2 style="color: white; margin-top: 0;">Set New Password</h2>
            <p style="color: rgba(255,255,255,0.9);">Please set a new password for your account.</p>
            <form id="newPasswordForm">
                <div style="margin: 15px 0;">
                    <label style="color: white; font-size: 14px;">New Password:</label><br>
                    <input type="password" id="newPassword" required style="width: 100%; padding: 10px; margin: 8px 0; background: rgba(255,255,255,0.9); border: none; border-radius: 6px; box-sizing: border-box;">
                </div>
                <button type="submit" style="width: 100%; padding: 12px; background: white; color: #667eea; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; margin-top: 10px;">Set Password</button>
            </form>
            <div id="passwordError" style="color: #ffe0e0; margin-top: 15px; font-size: 14px;"></div>
        </div>
    `;
    document.getElementById('newPasswordForm').addEventListener('submit', setNewPassword);
}

async function setNewPassword(event) {
    event.preventDefault();
    const newPassword = document.getElementById('newPassword').value;
    const { cognitoUser } = await import('./auth.js');

    cognitoUser.completeNewPasswordChallenge(newPassword, {}, {
        onSuccess: (result) => {
            setAuthToken(result.getIdToken().getJwtToken());
            showApp();
            loadImages();
        },
        onFailure: (err) => {
            document.getElementById('passwordError').textContent = err.message;
        }
    });
}
