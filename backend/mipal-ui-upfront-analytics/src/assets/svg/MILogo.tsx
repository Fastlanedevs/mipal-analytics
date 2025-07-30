"use client";

import { useTheme } from "@/contexts/ThemeContext";
import { useMediaQuery } from "react-responsive";

interface MILogoProps {
  className?: string;
}

const MILogo = ({ className }: MILogoProps) => {
  const isMobile = useMediaQuery({ maxWidth: 768 });

  return isMobile ? <MobileLogo /> : <DesktopLogo />;
};

export default MILogo;

export const MobileLogo = ({
  height = 10,
  width = 8,
  showBeta = false,
  className,
}: {
  height?: number;
  width?: number;
  showBeta?: boolean;
  className?: string;
}) => {
  const { theme } = useTheme();
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 60 60"
      className={`w-${width} h-${height} ${className}`}
    >
      <style>{`
        .text { font-family: Arial, sans-serif; font-weight: bold; }
        .beta { font-family: Arial, sans-serif; font-size: 12px; }
      `}</style>
      <rect
        x="5"
        y="0"
        width="50"
        height="50"
        rx="10"
        fill={isDark ? "#ffffff" : "#000000"}
      />
      <text
        x="13"
        y="36"
        className="text"
        fontSize="30"
        fill={isDark ? "#000000" : "#ffffff"}
      >
        MI
      </text>
      {/* {showBeta && (
        <text
          x="13"
          y="65"
          style={{
            fontSize: "16px",
          }}
          className="beta"
          fill={isDark ? "#0ea5e9" : "blue"}
          // fill={!isDark ? "#000000" : "#ffffff"}
        >
          Beta
        </text>
      )} */}
    </svg>
  );
};

export const DesktopLogo = ({
  height = 20,
  width = 32,
}: {
  height?: number;
  width?: number;
}) => {
  const { theme } = useTheme();
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 160 100"
      className={`w-${width} h-${height}`}
    >
      <style>{`
        .text { font-family: Arial, sans-serif; font-weight: bold; }
        .beta { font-family: Arial, sans-serif; font-size: 12px; }
      `}</style>
      <rect
        x="10"
        y="25"
        width="50"
        height="50"
        rx="10"
        fill={isDark ? "#ffffff" : "#000000"}
      />
      <text
        x="18"
        y="62"
        className="text"
        fontSize="30"
        fill={isDark ? "#000000" : "#ffffff"}
      >
        MI
      </text>
      <text
        x="70"
        y="62"
        className="text"
        fontSize="30"
        fill={isDark ? "#ffffff" : "#000000"}
      >
        PAL
      </text>
      {/* <text
        x="135"
        y="40"
        className="beta"
        fill={isDark ? "#0ea5e9" : "blue"}
        // fill={isDark ? "#ffffff" : "#000000"}
      >
        Beta
      </text> */}
    </svg>
  );
};
