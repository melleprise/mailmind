import axios from 'axios';

interface ApiErrorResponse {
  message?: string;
  error?: string;
}

export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data as ApiErrorResponse | any | undefined;
    return responseData?.error || responseData?.message || error.message || 'An API error occurred';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
};