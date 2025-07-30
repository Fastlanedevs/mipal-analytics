/** @type {import('tailwindcss').Config} */
const animate = require("tailwindcss-animated");

module.exports = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          500: "#0ea5e9",
          600: "#0284c7",
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        chart: {
          1: "hsl(var(--chart-1))",
          2: "hsl(var(--chart-2))",
          3: "hsl(var(--chart-3))",
          4: "hsl(var(--chart-4))",
          5: "hsl(var(--chart-5))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },

      // Key frame
      // keyframe to animate scale and opacity
      keyframes: {
        "scale-opacity": {
          "0%": {
            opacity: "0",
            transform: "translateY(-40px)",
          },
          "100%": {
            opacity: "1",
          },
        },
        pulseScale: {
          "0%, 100%": {
            transform: "scale(1)",
            opacity: "1",
          },
          "50%": {
            transform: "scale(0.9)",
            opacity: ".9",
          },
        },
        bounce: {
          "0%, 100%": {
            transform: "translateY(-5%)",
            animationTimingFunction: "cubic-bezier(0.8, 0, 1, 1)",
          },
          "50%": {
            transform: "translateY(0)",
            animationTimingFunction: "cubic-bezier(0, 0, 0.2, 1)",
          },
        },
        "slide-down-fade": {
          "0%": { opacity: "0", transform: "translateY(-0.5rem)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-left-fade": {
          "0%": { opacity: "0", transform: "translateX(-1rem)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "fade-in-up": {
          "0%": {
            opacity: "0",
            transform: "translateY(10px)",
          },
          "100%": {
            opacity: "1",
            transform: "translateY(0)",
          },
        },
        expand: {
          "0%": {
            transform: "translateY(-20px)",
            maxHeight: "0",
            opacity: "0",
          },
          "100%": {
            transform: "translateY(0)",
            maxHeight: "500px",
            opacity: "1",
          },
        },
        collapse: {
          "0%": {
            transform: "translateY(0)",
            maxHeight: "500px",
            opacity: "1",
          },
          "100%": {
            transform: "translateY(-20px)",
            maxHeight: "0",
            opacity: "0",
          },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-100%)" },
        },
        "glare-text": {
          "0%": { backgroundPosition: "150% 0" },
          "100%": { backgroundPosition: "-150% 0" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },

      // animation
      animation: {
        "scale-opacity": "scale-opacity 1s ease-out",
        "ping-slow": "ping 5s cubic-bezier(0, 0, 0.2, 1) infinite",
        "pulse-scale": "pulseScale 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow": "spin 3s linear infinite",
        "bounce-gentle": "bounce 2s infinite",
        "slide-down-fade": "slide-down-fade 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
        "slide-left-fade": "slide-left-fade 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
        spin: "spin 0.6s linear infinite",
        "fade-in-up": "fade-in-up 0.5s ease-out",
        expand: "expand 0.3s ease-out",
        collapse: "collapse 0.3s ease-out",
        marquee: "marquee 5s linear",
        "glare-text": "glare-text 4s infinite linear",
        "glare-text-delayed": "glare-text 2s infinite linear 3s",
        blink: "blink 1s steps(5, start) infinite",
      },

      // boxShadow
      boxShadow: {
        card: "0px 0px 10px 0px rgba(0, 0, 0, 0.1)",
        // insetshadow
        "inset-shadow": "inset 0px 0px 10px 0px rgba(0, 0, 0, 0.1)",
        "file-upload-shadow": "0 4px 12px rgba(0,0,0,0.05)",
        "file-upload-shadow-dark": "0 0 8px hsl(var(--subtle-shadow))",
      },

      fontSize: {
        base: "1.125rem", // 18px
        lg: "1.25rem", // 20px
        xl: "1.5rem", // 24px
        "2xl": "1.75rem", // 28px
        "3xl": "2rem", // 32px
        // ... adjust other sizes as needed
      },

      typography: {
        lg: {
          css: {
            fontSize: "1.25rem",
            p: {
              fontSize: "1.25rem",
              lineHeight: "1.75",
            },
            li: {
              fontSize: "1.25rem",
            },
            code: {
              fontSize: "1.125rem",
            },
          },
        },
      },
    },
  },
  plugins: [
    require("tailwindcss-animated"),
    require("tailwind-scrollbar-hide"),
    require("@tailwindcss/typography"),
    function ({ addUtilities }) {
      addUtilities({
        ".scrollbar-hide": {
          /* IE and Edge */
          "-ms-overflow-style": "none",
          /* Firefox */
          "scrollbar-width": "none",
          /* Safari and Chrome */
          "&::-webkit-scrollbar": {
            display: "none",
          },
        },
      });
    },
    animate,
  ],
};
