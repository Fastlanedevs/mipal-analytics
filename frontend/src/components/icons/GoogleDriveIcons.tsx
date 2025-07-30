import React from "react";

interface GoogleDriveIconProps {
  className?: string;
}

export const GoogleDocsIcon: React.FC<GoogleDriveIconProps> = ({
  className = "w-4 h-4",
}) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="32"
    height="32"
    viewBox="0 0 81 111.372"
    id="google-docs"
  >
    <path
      fill="#4285f4"
      d="M50.623 0H7.591A7.786 7.786 0 0 0 0 7.6v96.182a7.786 7.786 0 0 0 7.6 7.6h65.8a7.786 7.786 0 0 0 7.6-7.6v-73.4L63.284 17.716Z"
    ></path>
    <path
      fill="#f1f1f1"
      d="M20.247 80.996h40.5v-5.061h-40.5v5.061Zm0 10.126h30.372v-5.061H20.247Zm0-35.437v5.061h40.5v-5.062Zm0 15.186h40.5V65.81h-40.5v5.061Z"
    ></path>
    <path
      fill="#a1c2fa"
      d="M50.623 0v22.781a7.782 7.782 0 0 0 7.591 7.591h22.781Z"
    ></path>
  </svg>
);

export const GoogleSheetsIcon: React.FC<GoogleDriveIconProps> = ({
  className = "w-4 h-4",
}) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="32"
    height="32"
    viewBox="0 0 512 512"
    id="sheets"
  >
    <path
      fill="#28b446"
      d="M441.412 140.235v338.781c0 18.219-14.778 32.983-32.983 32.983H103.572c-18.219 0-32.983-14.764-32.983-32.983V32.983C70.588 14.764 85.352 0 103.572 0h197.605l140.235 140.235z"
    ></path>
    <path
      fill="#219b38"
      d="m320.31 137.188 121.102 49.891v-46.844l-68.661-20.273z"
    ></path>
    <path
      fill="#6ace7c"
      d="M441.412 140.235H334.16c-18.22 0-32.983-14.764-32.983-32.983V0l140.235 140.235z"
    ></path>
    <path
      fill="#fff"
      d="M337.115 254.946H174.876c-5.82 0-10.536 4.717-10.536 10.536v141.169c0 5.818 4.716 10.536 10.536 10.536h162.239c5.82 0 10.536-4.717 10.536-10.536V265.482c0-5.818-4.716-10.536-10.536-10.536zm-151.703 67.736h60.048v26.773h-60.048v-26.773zm81.119 0h60.048v26.773h-60.048v-26.773zm60.049-21.071h-60.048v-25.593h60.048v25.593zm-81.12-25.593v25.592h-60.048v-25.592h60.048zm-60.048 94.508h60.048v25.592h-60.048v-25.592zm81.119 25.591v-25.592h60.048v25.592h-60.048z"
    ></path>
  </svg>
);

export const GoogleSlidesIcon: React.FC<GoogleDriveIconProps> = ({
  className = "w-4 h-4",
}) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" id="slide">
    <path
      fill="#f5ba15"
      d="M25 8v18.5c0 .831-.669 1.5-1.5 1.5h-16c-.831 0-1.5-.669-1.5-1.5v-22C6 3.67 6.669 3 7.5 3H20"
    ></path>
    <path fill="#fadc87" d="M20 3v3.5c0 .831.669 1.5 1.5 1.5H25z"></path>
    <path fill="#fff" d="M10 12h8v8h-8z"></path>
    <path fill="#fff" d="M19 15V21h-6V23h8v-8h-2zm-2 1L13.998 19H17V16z"></path>
  </svg>
);

export const GoogleDrawingsIcon: React.FC<GoogleDriveIconProps> = ({
  className = "w-4 h-4",
}) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <title>Google Drawings</title>
    <g>
      <path
        d="M14.5 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V7.5L14.5 2Z"
        stroke="#DB4437"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M14 2V8H20"
        stroke="#DB4437"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M8 13L12 17L16 13"
        stroke="#DB4437"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </g>
  </svg>
);

export const GooglePDFIcon: React.FC<GoogleDriveIconProps> = ({
  className = "w-4 h-4",
}) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="32"
    height="32"
    viewBox="0 0 81 111.372"
    id="google-pdf"
  >
    <path
      fill="#D93838"
      d="M50.623 0H7.591A7.786 7.786 0 0 0 0 7.6v96.182a7.786 7.786 0 0 0 7.6 7.6h65.8a7.786 7.786 0 0 0 7.6-7.6v-73.4L63.284 17.716Z"
    ></path>
    <path
      fill="#f1f1f1"
      d="M20.247 80.996h40.5v-5.061h-40.5v5.061Zm0 10.126h30.372v-5.061H20.247Zm0-35.437v5.061h40.5v-5.062Zm0 15.186h40.5V65.81h-40.5v5.061Z"
    ></path>
    <path
      fill="#ffa199"
      d="M50.623 0v22.781a7.782 7.782 0 0 0 7.591 7.591h22.781Z"
    ></path>
  </svg>
);
