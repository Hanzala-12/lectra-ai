/**
 * Signup form rules. These mirror src/auth_utils.py (the server is the source
 * of truth and re-checks everything); they exist so users get instant feedback.
 */

export const USERNAME_RE = /^[A-Za-z][A-Za-z0-9_.]{2,19}$/;
export const EMAIL_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;
export const NAME_RE = /^\p{L}+([ .'-]\p{L}+)*\.?$/u;

export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

const COMMON_PASSWORDS = new Set([
  'password', 'password1', 'password1!', 'password123', 'passw0rd', 'p@ssw0rd',
  'p@ssword1', 'qwerty123', 'qwerty123!', 'qwertyuiop', 'letmein123', 'welcome1',
  'welcome123', 'admin123', 'admin@123', 'iloveyou1', 'abc12345', 'abcd1234',
  'abc123456', '12345678', '123456789', '1234567890', '11111111', '000000000',
  'changeme', 'changeme1', 'lectra123', 'lectraai1', 'pakistan1', 'student123',
]);

export function validateUsername(value: string): string | null {
  const u = value.trim();
  if (!u) return 'Username is required.';
  if (u.length < 3) return 'Username must be at least 3 characters.';
  if (u.length > 20) return 'Username must be at most 20 characters.';
  if (!/^[A-Za-z]/.test(u)) return 'Username must start with a letter (not a number).';
  if (!USERNAME_RE.test(u)) return 'Only letters, numbers, underscores and dots are allowed.';
  if (u.endsWith('.') || u.includes('..')) return 'Username cannot end with a dot or contain two dots in a row.';
  return null;
}

export function validateName(value: string): string | null {
  const n = value.trim();
  if (!n) return null; // optional
  if (n.length < 2) return 'Name must be at least 2 characters.';
  if (n.length > 60) return 'Name must be at most 60 characters.';
  if (!NAME_RE.test(n)) return 'Name can only contain letters, spaces, hyphens and apostrophes.';
  return null;
}

export function validateEmail(value: string): string | null {
  const e = value.trim();
  if (!e) return null; // optional
  if (e.length > 254 || !EMAIL_RE.test(e) || e.includes('..')) {
    return 'Enter a valid email address (e.g. name@example.com).';
  }
  return null;
}

export type PasswordCheck = { id: string; label: string; ok: boolean };

/** Each rule individually, for the live checklist under the password field. */
export function passwordChecks(password: string, username = ''): PasswordCheck[] {
  const u = username.trim().toLowerCase();
  return [
    { id: 'len', label: `At least ${PASSWORD_MIN} characters`, ok: password.length >= PASSWORD_MIN },
    { id: 'upper', label: 'An uppercase letter (A-Z)', ok: /[A-Z]/.test(password) },
    { id: 'lower', label: 'A lowercase letter (a-z)', ok: /[a-z]/.test(password) },
    { id: 'digit', label: 'A number (0-9)', ok: /\d/.test(password) },
    { id: 'special', label: 'A special character (! @ # $ %)', ok: /[^A-Za-z0-9\s]/.test(password) },
    {
      id: 'clean',
      label: 'No spaces, no username, nothing too common',
      ok:
        password.length > 0 &&
        !/\s/.test(password) &&
        !/(.)\1{2,}/.test(password) &&
        !COMMON_PASSWORDS.has(password.toLowerCase()) &&
        !(u.length >= 3 && password.toLowerCase().includes(u)),
    },
  ];
}

export function validatePassword(password: string, username = ''): string | null {
  if (!password) return 'Password is required.';
  if (password.length > PASSWORD_MAX) return `Password must be at most ${PASSWORD_MAX} characters.`;
  if (password.length < PASSWORD_MIN) return `Password must be at least ${PASSWORD_MIN} characters.`;
  if (/\s/.test(password)) return 'Password cannot contain spaces.';
  if (!/[A-Z]/.test(password)) return 'Password needs at least one uppercase letter.';
  if (!/[a-z]/.test(password)) return 'Password needs at least one lowercase letter.';
  if (!/\d/.test(password)) return 'Password needs at least one number.';
  if (!/[^A-Za-z0-9]/.test(password)) return 'Password needs at least one special character (e.g. ! @ # $ %).';
  if (/(.)\1{2,}/.test(password)) return 'Password cannot repeat the same character three times in a row.';
  if (COMMON_PASSWORDS.has(password.toLowerCase())) return 'That password is too common - choose something less guessable.';
  const u = username.trim().toLowerCase();
  if (u.length >= 3 && password.toLowerCase().includes(u)) return 'Password cannot contain your username.';
  return null;
}

export function validateConfirm(password: string, confirm: string): string | null {
  if (!confirm) return 'Please confirm your password.';
  if (confirm !== password) return 'Passwords do not match.';
  return null;
}

export type Strength = { score: 0 | 1 | 2 | 3 | 4; label: string };

/** 0-4 score for the strength bar. A password that fails any rule never scores above 1 (Weak). */
export function passwordStrength(password: string, username = ''): Strength {
  if (!password) return { score: 0, label: '' };
  const passed = passwordChecks(password, username).filter((c) => c.ok).length;
  const valid = validatePassword(password, username) === null;
  let score = Math.min(passed, 6) / 6 * 3; // 0..3 from the rules
  if (valid && password.length >= 12) score += 1; // long + valid = strongest
  const s = (valid ? Math.max(Math.round(score), 3) : Math.min(Math.round(score), 1)) as 0 | 1 | 2 | 3 | 4;
  const labels = ['Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'];
  return { score: s, label: labels[s] };
}
