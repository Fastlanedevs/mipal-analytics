import React from "react";

const MicrosoftIcon = ({
  width = 26,
  height = 26,
  className,
}: {
  width?: number;
  height?: number;
  className?: string;
}) => {
  return (
    <svg
      className={className}
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M11.4062 11.4062H2V2H11.4062V11.4062Z" fill="#F25022" />
      <path d="M21.7812 11.4062H12.375V2H21.7812V11.4062Z" fill="#7FBA00" />
      <path d="M11.4062 21.7812H2V12.375H11.4062V21.7812Z" fill="#00A4EF" />
      <path
        d="M21.7812 21.7812H12.375V12.375H21.7812V21.7812Z"
        fill="#FFB900"
      />
    </svg>
  );
};

export default MicrosoftIcon;
