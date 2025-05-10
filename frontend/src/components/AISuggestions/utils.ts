export const truncateAndClean = (text: string, maxLength = 100): string => {
  if (!text) return "";
  const cleanedLines = text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0);
  const joinedText = cleanedLines.join(' ');
  if (joinedText.length <= maxLength) {
    return joinedText;
  }
  return joinedText.substring(0, maxLength).trimEnd() + '...';
}; 