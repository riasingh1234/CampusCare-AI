export const isEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());

export function validatePassword(p) {
  if (p.length < 8) return 'Use at least 8 characters.';
  if (!/[A-Za-z]/.test(p) || !/\d/.test(p)) return 'Include at least one letter and one number.';
  return null;
}

export function validateComplaint({ title, description, categoryId, location }) {
  const e = {};
  if (title.trim().length < 5) e.title = 'Enter a title of at least 5 characters.';
  else if (title.length > 100) e.title = 'Keep the title under 100 characters.';
  if (description.trim().length < 20) e.description = 'Describe the problem in at least 20 characters.';
  else if (description.length > 1000) e.description = 'Keep the description under 1000 characters.';
  if (!categoryId) e.categoryId = 'Choose a category.';
  if (!location) e.location = 'Choose where the problem is.';
  return e;
}
