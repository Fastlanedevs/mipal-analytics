import React from "react";

interface MicrosoftCalendarProps {
  width?: number;
  height?: number;
  className?: string;
}

const MicrosoftCalendar: React.FC<MicrosoftCalendarProps> = ({
  width = 34,
  height = 34,
  className,
  ...props
}) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={width}
      height={height}
      style={{
        shapeRendering: "geometricPrecision",
        textRendering: "geometricPrecision",
        imageRendering: "optimizeQuality" as any,
        fillRule: "evenodd",
        clipRule: "evenodd",
      }}
      className={className}
      viewBox="0 0 170 170"
      {...props}
    >
      <path
        fill="#0472c6"
        d="M89.5-.5h7v13c23.002-.167 46.002 0 69 .5l2.5 2.5c.667 47 .667 94 0 141a7.293 7.293 0 0 0-2 3 1217.472 1217.472 0 0 1-69.5 1v9h-7a4123.29 4123.29 0 0 1-88-16.5 2357.241 2357.241 0 0 1-1-68.5c.002-22.905.336-45.738 1-68.5a12422.456 12422.456 0 0 1 88-16.5Z"
        style={{
          opacity: 0.975,
        }}
      />
      <path
        fill="#fefffe"
        d="M94.5 150.5v-5h62v-103a930.822 930.822 0 0 0-61-1v-20h66v129h-67Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#bedbf0"
        d="M162.5 151.5c-22.839.331-45.506-.003-68-1h67v-129h-66v20c20.507-.33 40.84.003 61 1h-62v-22h68v131Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fafcfe"
        d="M40.5 48.5c6.465-.803 12.465.364 18 3.5 7.457 6.075 11.957 13.908 13.5 23.5 1.945 14.011-.722 27.012-8 39-9.266 9.408-20.099 11.575-32.5 6.5-10.93-9.282-15.93-21.116-15-35.5-.966-14.49 4.367-25.824 16-34 2.897-.629 5.564-1.629 8-3Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#70aede"
        d="M104.5 66.5v-18h-10v18c-.99-6.145-1.323-12.478-1-19h12c.323 6.522-.01 12.855-1 19Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fdfdfe"
        d="M104.5 66.5h-10v-18h10v18Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#9ec7e9"
        d="M40.5 48.5c-2.436 1.371-5.103 2.371-8 3 2.117-2.154 4.784-3.154 8-3Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#539dd7"
        d="M127.5 66.5v-18h-17v18c-.99-6.145-1.323-12.478-1-19h19c.323 6.522-.01 12.855-1 19Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fdfdfe"
        d="M127.5 66.5h-17v-18h17v18Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#539dd7"
        d="M150.5 66.5v-18h-17v18c-.99-6.145-1.323-12.478-1-19h19c.323 6.522-.01 12.855-1 19Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fdfdfe"
        d="M150.5 66.5h-17v-18h17v18Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#88bce4"
        d="M46.5 64.5a24.93 24.93 0 0 0-8 1c.992-1.526 2.492-2.193 4.5-2 1.385.014 2.551.348 3.5 1Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#0773c6"
        d="M46.5 64.5c7.694 4.557 11.028 11.39 10 20.5a39.02 39.02 0 0 1-2.5 15.5c-3.323 6.408-8.49 8.575-15.5 6.5-4.161-3.154-6.661-7.32-7.5-12.5-.667-6-.667-12 0-18 1.029-4.74 3.529-8.407 7.5-11a24.93 24.93 0 0 1 8-1Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#66a8dc"
        d="M104.5 90.5c-3.462.982-7.129 1.315-11 1v-20h12c.323 6.522-.01 12.855-1 19Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fefefe"
        d="M104.5 90.5h-10v-18h10v18Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#4c9ad6"
        d="M127.5 90.5v-18h-17v18c-.99-6.145-1.323-12.478-1-19h19c.323 6.522-.01 12.855-1 19Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fefefe"
        d="M127.5 90.5h-17v-18h17v18Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#4c9ad6"
        d="M150.5 90.5v-18h-17v18c-.99-6.145-1.323-12.478-1-19h19c.323 6.522-.01 12.855-1 19Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fefefe"
        d="M150.5 90.5h-17v-18h17v18Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fefffe"
        d="M104.5 97.5v17h-10v-17h10Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fbfdfe"
        d="M110.5 96.5h17v18h-17v-18ZM133.5 96.5h17v18h-17v-18Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#87bce4"
        d="M104.5 97.5h-10v17h10c-3.462.982-7.129 1.315-11 1v-19c3.871-.315 7.538.018 11 1Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#fefffe"
        d="M104.5 121.5v17h-10v-17h10Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#f7fafd"
        d="M110.5 120.5h17v19h-17v-19Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#93c3e6"
        d="M104.5 121.5h-10v17h10c-3.462.982-7.129 1.315-11 1v-19c3.871-.315 7.538.018 11 1Z"
        style={{
          opacity: 1,
        }}
      />
      <path
        fill="#4f9cd6"
        d="M155.5 42.5h1v103h-62v5c22.494.997 45.161 1.331 68 1a1190.252 1190.252 0 0 1-69 1v-8h62v-102Z"
        style={{
          opacity: 1,
        }}
      />
    </svg>
  );
};

export default MicrosoftCalendar;
