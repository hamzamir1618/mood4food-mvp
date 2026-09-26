/**
 * Light or dark, and who decides.
 *
 * The system setting is the default; a reader who chooses overrides it, and that choice is
 * remembered. The choice lives on <html data-theme>, which index.html sets before the first
 * paint so the page never flashes white on its way to dark.
 */

const KEY = 'mood4food-theme';

/** What the reader chose last time, or null if they never did. */
export function storedTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    return saved === 'dark' || saved === 'light' ? saved : null;
  } catch {
    return null; // private windows and blocked storage: fall back to the system setting
  }
}

export function systemTheme() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function currentTheme() {
  return document.documentElement.dataset.theme || storedTheme() || systemTheme();
}

/** Applies a theme and remembers it. */
export function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* the page still looks right for this visit */
  }
  return theme;
}
