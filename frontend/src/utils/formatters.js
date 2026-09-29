/**
 * Format integer amount to Vietnamese currency string.
 * Example: 1290000 -> "1.290.000đ"
 */
export function formatCurrency(amount) {
  if (amount === null || amount === undefined) return 'N/A';
  return `${amount.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') }đ`;
}

/**
 * Format date string to Vietnamese friendly format.
 */
export function formatDate(dateString) {
  if (!dateString) return 'Chưa cập nhật';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;
  
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Format short date for chart X-axis.
 */
export function formatChartDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;
  
  return `${date.getDate()}/${date.getMonth() + 1} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}
