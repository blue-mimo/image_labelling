import { showLogin } from './login.js';
import { showApp } from './mainApp.js';
import { loadImages } from './imageList.js';

export let authToken = null;
export let cognitoUser = null;
export let userPool = null;

export function initAuth(poolData) {
    userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);
}

export function setAuthToken(token) {
    authToken = token;
}

export function setCognitoUser(user) {
    cognitoUser = user;
}

export function checkAuth() {
    cognitoUser = userPool.getCurrentUser();
    if (cognitoUser) {
        cognitoUser.getSession((err, session) => {
            if (err || !session.isValid()) {
                showLogin();
            } else {
                authToken = session.getIdToken().getJwtToken();
                showApp();
                loadImages();
            }
        });
    } else {
        showLogin();
    }
}

export function logout() {
    if (cognitoUser) cognitoUser.signOut();
    authToken = null;
    cognitoUser = null;
    showLogin();
}

export function setupFetchInterceptor() {
    const originalFetch = window.fetch;
    window.fetch = async function (...args) {
        const response = await originalFetch(...args);
        if (response.status === 401) {
            const text = await response.clone().text();
            if (text.includes('expired') || text.includes('Unauthorized')) {
                alert('Your session has expired. Please log in again.');
                logout();
            }
        }
        return response;
    };
}
