const TOKEN_KEY = "access_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn() {
  return Boolean(getToken());
}

export function logoutAndRedirect() {
  clearToken();

  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}