"use client";

import { useState, useEffect, useRef } from "react";
import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MobileLogo, DesktopLogo } from "@/assets/svg/MILogo";
import { useRouter, useSearchParams } from "next/navigation";
import { GoogleIcon } from "@/assets/svg/GoogleIcon";
import LoadingScreen from "@/components/common/LoadingScreen";
import {
  Eye,
  EyeOff,
  CheckCircle,
  LucideBookOpen,
  Brain,
  Lightbulb,
  Search,
  MessageSquare,
  Lock,
} from "lucide-react";
import MicrosoftIcon from "@/assets/svg/MicrosoftIcon";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useTranslations } from "next-intl";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [isVerifying, setIsVerifying] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    name: "",
    otp: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const callbackUrl = searchParams?.get("callbackUrl") || "/";
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [otpTimer, setOtpTimer] = useState(600); // 10 minutes in seconds
  const t = useTranslations("auth");

  useEffect(() => {
    if (callbackUrl) {
      try {
        if (process.env.NEXTAUTH_URL) {
          localStorage.setItem("loginCallbackUrl", process.env.NEXTAUTH_URL);
        }
      } catch (error) {
        console.error("Error storing callback URL:", error);
        localStorage.setItem("loginCallbackUrl", "/");
      }
    }
  }, [callbackUrl]);

  // OTP Timer effect
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (isVerifying && otpTimer > 0) {
      interval = setInterval(() => {
        setOtpTimer((prev) => prev - 1);
      }, 1000);
    } else if (isVerifying && otpTimer === 0) {
      // Timer expired, go back to signup form
      setIsVerifying(false);
      setOtpTimer(600); // Reset timer for next time
      setFormData((prev) => ({ ...prev, otp: "" })); // Clear OTP
      setError("OTP verification time expired. Please try signing up again.");
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isVerifying, otpTimer]);

  // Reset timer when entering OTP verification mode
  useEffect(() => {
    if (isVerifying) {
      setOtpTimer(600); // Reset to 10 minutes
    }
  }, [isVerifying]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.persist(); // Keep the event around for the timeout
    const { name, value } = e.target;

    // Update state without causing unnecessary re-renders
    setFormData({
      ...formData,
      [name]: value,
    });
  };

  const handleGoogleSignIn = async () => {
    try {
      setError(null);
      setIsLoading(true);
      setIsTransitioning(true);

      const baseUrl = process.env.NEXTAUTH_URL;

      const finalCallbackUrl = `${baseUrl}/`;

      await signIn("google", {
        redirect: true,
        callbackUrl: finalCallbackUrl,
        authorizationParams: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code",
        },
      });
    } catch (error) {
      console.error("Google Sign In Error:", error);
      setError(t("anUnexpectedErrorOccurredPleaseTryAgain"));
      setIsTransitioning(false);
      setIsLoading(false);
    }
  };

  const handleMicrosoftSignIn = async () => {
    try {
      setError(null);
      setIsLoading(true);
      setIsTransitioning(true);

      const baseUrl = process.env.NEXTAUTH_URL;

      const finalCallbackUrl = `${baseUrl}/`;

      await signIn("azure-ad", {
        redirect: true,
        callbackUrl: finalCallbackUrl,
      });
    } catch (error) {
      console.error("Microsoft Sign In Error:", error);
      setError(t("anUnexpectedErrorOccurredPleaseTryAgain"));
      setIsTransitioning(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const baseUrl = process.env.NEXTAUTH_URL;

      const finalCallbackUrl = `${baseUrl}/`;

      const result = await signIn("credentials", {
        email: formData.email,
        password: formData.password,
        name: formData.name,
        otp: formData.otp,
        isSignUp: (!isLogin).toString(),
        redirect: false,
        callbackUrl: finalCallbackUrl,
      });

      if (result?.error === "OTP_REQUIRED") {
        setIsVerifying(true);
        return;
      }

      if (result?.error) {
        setError(result.error);
        return;
      }

      if (result?.ok) {
        setIsTransitioning(true);
        router.push(finalCallbackUrl);
        router.refresh();
      }
    } catch (error) {
      console.error("Sign In Error:", error);
      setError(t("anUnexpectedErrorOccurredPleaseTryAgain"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = () => {
    router.push("/auth/forgot-password");
  };

  // Format timer display (MM:SS)
  const formatTimer = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

  // Auth form component to reuse in hero section
  const authFormCard = () => (
    <Card className="w-full p-4 md:p-6 shadow-2xl bg-white dark:bg-zinc-800">
      {error && (
        <div className="p-3 mb-4 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900 rounded-md bg-red-50 dark:bg-red-900/30">
          {error}
        </div>
      )}
      <CardHeader className="p-0 mb-4 md:mb-6 space-y-1">
        <div className="flex items-center justify-between mb-6 md:mb-8">
          <MobileLogo />
          {!isVerifying && (
            <Button
              variant="outline"
              className="rounded-full text-sm md:text-base"
              onClick={() => setIsLogin(!isLogin)}
            >
              {isLogin ? t("signUp") : t("logIn")}
            </Button>
          )}
        </div>
        <CardTitle className="text-2xl md:text-3xl font-normal text-gray-900 dark:text-gray-100">
          {isVerifying
            ? t("verifyEmail")
            : isLogin
              ? t("welcomeBack")
              : t("createAccount")}
        </CardTitle>
      </CardHeader>

      <CardContent className="p-0 space-y-3 md:space-y-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          {isVerifying ? (
            <div className="space-y-4">
              <Input
                // ref={otpInputRef}
                type="text"
                name="otp"
                placeholder={t("enterOTP")}
                value={formData.otp}
                onChange={handleChange}
                required
              />
              <div className="flex flex-col items-center justify-center space-y-4">
                <div className="text-sm text-gray-600 dark:text-gray-400 text-center">
                  <span>{t("timeRemaining")}</span>
                </div>
                {/* Circular Progress Timer */}
                <div className="relative flex items-center justify-center">
                  <svg
                    className="w-24 h-24 transform -rotate-90"
                    viewBox="0 0 100 100"
                  >
                    {/* Background circle */}
                    <circle
                      cx="50"
                      cy="50"
                      r="45"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                      className="text-background"
                    />
                    {/* Progress circle */}
                    <circle
                      cx="50"
                      cy="50"
                      r="45"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                      className="text-muted-foreground"
                      strokeDasharray={`${2 * Math.PI * 45}`}
                      strokeDashoffset={`${2 * Math.PI * 45 * ((600 - otpTimer) / 600)}`}
                      style={{
                        transition: "stroke-dashoffset 1s linear",
                      }}
                    />
                  </svg>
                  {/* Timer text in center */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-base font-mono font-semibold">
                      {formatTimer(otpTimer)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {!isLogin && (
                <Input
                  // ref={nameInputRef}
                  type="text"
                  name="name"
                  placeholder={t("name")}
                  value={formData.name}
                  onChange={handleChange}
                  required={!isLogin}
                />
              )}
              <Input
                // ref={emailInputRef}
                type="email"
                name="email"
                placeholder={t("email")}
                value={formData.email}
                onChange={handleChange}
                required
              />
              <div className="relative">
                <Input
                  // ref={passwordInputRef}
                  type={showPassword ? "text" : "password"}
                  name="password"
                  placeholder={t("password")}
                  value={formData.password}
                  onChange={handleChange}
                  required
                  minLength={8}
                  className="pr-[37px]"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-[1px] top-[1px] h-[34px] px-3 rounded-l-none bg-background"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h- w-[13px]" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </>
          )}

          {isLogin && !isVerifying && (
            <div className="text-right">
              <Button
                variant="link"
                className="p-0 h-auto text-sm text-blue-600 dark:text-blue-400"
                onClick={handleForgotPassword}
                type="button"
              >
                {t("forgotPassword")}
              </Button>
            </div>
          )}

          <Button
            type="submit"
            variant="outline"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading
              ? t("loading")
              : isVerifying
                ? t("verify")
                : isLogin
                  ? t("logIn")
                  : t("signUp")}
          </Button>
        </form>

        {!isVerifying && (
          <>
            <div className="flex items-center my-4">
              <div className="flex-grow h-px bg-gray-300 dark:bg-gray-700"></div>
              <span className="px-3 text-sm text-gray-500 dark:text-gray-400">
                {t("orContinueWith")}
              </span>
              <div className="flex-grow h-px bg-gray-300 dark:bg-gray-700"></div>
            </div>

            {/* <div className="grid grid-cols-2 gap-4"> */}
            <div className="grid gap-4">
              <Button
                type="button"
                variant="outline"
                className="flex items-center justify-center gap-2"
                onClick={handleGoogleSignIn}
                disabled={isLoading}
              >
                <GoogleIcon className="h-5 w-5" />
                Google
              </Button>
              {/* <Button
                type="button"
                variant="outline"
                className="flex items-center justify-center gap-2"
                onClick={handleMicrosoftSignIn}
                disabled={isLoading}
              >
                <MicrosoftIcon className="h-5 w-5" />
                Microsoft
              </Button> */}
            </div>

            {/* Terms acceptance message */}
            <div className="text-center text-xs text-gray-500 dark:text-gray-400 mt-4">
              {t("byContinuingYouAgreeToMIPALs")}{" "}
              <a
                href="/terms-of-service"
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                {t("termsOfService")}
              </a>
              <span className="mx-1">{t("and")}</span>
              <a
                href="/privacy-policy"
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                {t("privacyPolicy")}
              </a>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="flex flex-col min-h-screen justify-between">
      {isTransitioning && <LoadingScreen />}

      {/* Hero Section with Auth Card */}
      <section className="pt-8 pb-14 md:py-14 px-4 sm:px-6 flex-1 flex items-center">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-1 gap-12 items-center">
            {/* Left side - Hero text */}
            {/* <div className="flex flex-col space-y-6">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 dark:text-white leading-tight">
                {t("aiEcosystemToAccelerateYourBusinessProcess")}
              </h1>
              <p className="text-lg text-gray-600 dark:text-gray-300 max-w-lg">
                {t(
                  "miPALIntegratesWithYourEnterpriseDNAThroughSecureOnPremiseAIAssistanceTransformingKnowledgeSilosIntoCollectiveIntelligenceThatPowersCompetitiveEdgeAndBusinessExcellence"
                )}
              </p>
            </div> */}

            {/* Right side - Auth Card */}
            <div className="w-full max-w-md mx-auto md:ml-auto">
              {authFormCard()}
            </div>
          </div>
        </div>
      </section>

      {/* Footer Section */}
      <footer className="py-1 px-4 sm:px-6 dark:border-gray-800 bg-white dark:bg-zinc-900">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-8">
            {/* Company Info */}
            <div className="space-y-2">
              <div className="flex flex-col md:flex-row items-center gap-2">
                <MobileLogo />
                <p className="text-sm text-gray-600 dark:text-gray-400 text-center md:text-left">
                  {t(
                    "empoweringBusinessesWithIntelligentDataSolutionsAndActionableInsights"
                  )}
                </p>
              </div>
            </div>

            {/* Legal Links */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-2 text-center md:text-left">
                Legal
              </h3>
              <ul className="space-y-1 text-center md:text-left">
                <li>
                  <a
                    href="/privacy-policy"
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    {t("privacyPolicy")}
                  </a>
                </li>
                <li>
                  <a
                    href="/terms-of-service"
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    {t("termsOfService")}
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-800 mt-5 py-5">
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
              © {new Date().getFullYear()} {t("allRightsReserved")}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
