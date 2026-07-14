// Base URL of the backend API. Override with VITE_API_URL in a .env file.
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// How many messages to load per page when scrolling back through history.
export const MESSAGE_PAGE_SIZE = 10;

// How many sessions to load per page in the sidebar.
export const SESSION_PAGE_SIZE = 10;
