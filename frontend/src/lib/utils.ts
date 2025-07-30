import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const formatDate = (dateString: string) => {
  // The backend sends date in format: 2025-05-15T04:19:28.522461
  // Parse date manually to avoid timezone issues
  let date;

  try {
    // Split the ISO string into parts
    const [datePart, timePart] = dateString.split("T");
    const [year, month, day] = datePart.split("-").map(Number);

    // Handle time part (may contain milliseconds)
    const timeComponents = timePart.split(".")[0].split(":").map(Number);
    const [hours, minutes, seconds] = timeComponents;

    // Create date using UTC constructor (months are 0-indexed in JS)
    date = new Date(Date.UTC(year, month - 1, day, hours, minutes, seconds));
  } catch (e) {
    // Fallback to direct parsing if format is different
    date = new Date(dateString);
  }

  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  // Less than a minute
  if (diffInSeconds < 60) {
    return "just now";
  }

  // Less than an hour
  if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes}m ago`;
  }

  // Less than a day
  if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours}h ago`;
  }

  // Less than a week
  if (diffInSeconds < 604800) {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days}d ago`;
  }

  // Format as date
  const options: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone, // Use local timezone
  };
  return date.toLocaleDateString("en-US", options);
};

export const formatDateWithTime = (dateString: string) => {
  // Handle dates in formats:
  // - 2025-05-14T12:04:06.929000Z (with Z timezone)
  // - 2025-05-15T09:27:19 (without timezone, assumed UTC)
  let date;

  try {
    if (dateString.includes("Z")) {
      // If it has Z timezone indicator, use direct parsing
      // The Z indicates UTC timezone, Date constructor will handle it properly
      date = new Date(dateString);
    } else {
      // For dates without timezone, parse manually and treat as UTC
      const [datePart, timePart] = dateString.split("T");
      const [year, month, day] = datePart.split("-").map(Number);

      // Handle time part
      const timeComponents = timePart.split(".")[0].split(":").map(Number);
      const [hours, minutes, seconds] = timeComponents;

      // Create date using UTC (since input is in UTC/00 timezone)
      date = new Date(
        Date.UTC(year, month - 1, day, hours, minutes, seconds || 0)
      );
    }

    // Check if date is valid
    if (isNaN(date.getTime())) {
      throw new Error("Invalid date");
    }
  } catch (e) {
    // Fallback handling if needed
    console.error("Error parsing date:", e);
    return "Invalid date";
  }

  // Format as DD/MM/YYYY, HH:MM in local timezone
  // Date methods automatically use the local timezone for these operations
  const day = date.getDate().toString().padStart(2, "0");
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const year = date.getFullYear();
  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");

  return `${day}/${month}/${year}, ${hours}:${minutes}`;
};

export const thinHorizontalScrollbar = (height = 2) => {
  return `[&::-webkit-scrollbar]:h-${height} [&::-webkit-scrollbar-track]:!bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 [&::-webkit-scrollbar-thumb]:rounded-full`;
};
