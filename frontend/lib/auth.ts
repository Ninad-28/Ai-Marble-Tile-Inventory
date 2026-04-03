export const setToken = (token: string) =>
  localStorage.setItem("token", token);

export const getToken = () =>
  typeof window !== "undefined" ? localStorage.getItem("token") : null;

export const removeToken = () => localStorage.removeItem("token");

export const isLoggedIn = () => !!getToken();