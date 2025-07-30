"use client";

import { cn } from "@/lib/utils";

const MobileLogo = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 60 60"
    className="w-16 h-16"
  >
    <style>{`
      .text { font-family: Arial, sans-serif; font-weight: bold; }
      .mi { fill: #ffffff; }
      @keyframes fadeInOut {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
      }
      .animate-text {
        animation: fadeInOut 2s ease-in-out infinite;
      }
      @keyframes typing {
        0% {
          stroke-dashoffset: 100;
          opacity: 1;
        }
        80% {
          stroke-dashoffset: 20;
          opacity: 1;
        }
        100% {
          stroke-dashoffset: 0;
          opacity: 0;
        }
      }
      .typing-text {
        stroke: #ffffff;
        stroke-width: 1px;
        stroke-dasharray: 100;
        fill: transparent;
        animation: typing 3s linear forwards;
      }
      .fill-after {
        fill: #ffffff;
        opacity: 0;
        animation: fadeIn 0.5s linear 2s forwards;
      }
      @keyframes fadeIn {
        to {
          opacity: 1;
        }
      }
    `}</style>
    <rect
      x="5"
      y="5"
      width="50"
      height="50"
      rx="10"
      className="animate-text"
      fill="#000000"
    />
    <text x="12" y="42" className="typing-text" fontSize="30" textLength="36">
      MI
    </text>
    <text x="12" y="42" className="fill-after" fontSize="30" textLength="36">
      MI
    </text>
  </svg>
);

export default function LoadingScreen() {
  return (
    <div className="fixed inset-0 bg-white dark:bg-input z-[100000] flex items-center justify-center">
      <div className="relative flex items-center justify-center">
        {/* Pulsing background */}
        <div className="absolute inset-0 animate-ping-slow rounded-full bg-purple-100 opacity-75 w-32 h-32 -left-1/2 -top-1/2" />
        <div
          className="absolute inset-0 rounded-full bg-blue-200 opacity-50 w-32 h-32 animate-ping -left-1/2 -top-1/2"
          style={{ animationDuration: "2500ms" }}
        />
        {/* Logo with bounce animation */}
        <div className={cn("relative z-10")}>
          <MobileLogo />
        </div>
      </div>
    </div>
  );
}
