// Reglas espejo de las del backend (app/services/user_service.py), para que
// el error aparezca al tipear y no recién tras un viaje al servidor. La
// validación real sigue siendo la del backend: esto es solo para que la
// experiencia no se sienta a destiempo. Compartido por las pantallas de
// registro y recuperación de contraseña, que validan lo mismo.
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function isValidName(value) {
  return Boolean(value && value.trim());
}

export function isValidEmail(value) {
  return EMAIL_RE.test(value.trim());
}

export function isValidPassword(value) {
  if (value.length < 8 || value.length > 72) return false;
  return /[a-zA-Z]/.test(value) && /[0-9]/.test(value);
}
