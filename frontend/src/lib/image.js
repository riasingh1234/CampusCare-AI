// Checks a file before it is uploaded to Azure Blob Storage. The server checks again (type from the file's real bytes).
export const ACCEPTED_FILES = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
export const MAX_FILE_BYTES = 5 * 1024 * 1024;
export const MAX_FILES_PER_FORM = 3;

export function validateAttachment(file) {
  if (!ACCEPTED_FILES.includes(file.type)) return 'Upload a JPG, PNG or WebP image, or a PDF.';
  if (file.size > MAX_FILE_BYTES) return 'Each file must be under 5 MB.';
  if (file.size === 0) return 'That file is empty.';
  return null;
}

export const isImage = (typeOrFile) => (typeof typeOrFile === 'string' ? typeOrFile : typeOrFile.type).startsWith('image/');
