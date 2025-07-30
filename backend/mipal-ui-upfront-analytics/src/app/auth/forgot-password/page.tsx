"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MILogo from "@/assets/svg/MILogo";
import { useSession, signIn } from "next-auth/react";
import { Eye, EyeOff } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  useRequestPasswordResetMutation,
  useResetPasswordMutation,
} from "@/store/services/userApi";

export default function ForgotPasswordPage() {
  // States
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"email" | "verification">("email");

  // Hooks
  const router = useRouter();
  const { status } = useSession();
  const { toast } = useToast();
  const [requestPasswordReset] = useRequestPasswordResetMutation();
  const [resetPassword] = useResetPasswordMutation();

  // Prevent authenticated users from accessing this page
  useEffect(() => {
    if (status === "authenticated") {
      router.push("/");
    }
  }, [status, router]);

  // Only show the page content if the user is unauthenticated
  if (status === "loading" || status === "authenticated") {
    return null;
  }

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await requestPasswordReset({ email }).unwrap();
      setStep("verification");
      toast({
        title: "OTP Sent",
        description: "A verification code has been sent to your email.",
        variant: "default",
      });
    } catch (error: any) {
      console.error("Reset password request error:", error);

      // Handle different error formats
      if (error.data) {
        setError(
          error.data.detail ||
            error.data.message ||
            "An unexpected error occurred"
        );
      } else if (error.message) {
        setError(error.message);
      } else {
        setError("Failed to send verification code. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    // Validate passwords match
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      setIsLoading(false);
      return;
    }

    try {
      await resetPassword({
        email,
        otp,
        new_password: newPassword,
      }).unwrap();

      toast({
        title: "Password Reset Successful",
        description: "Your password has been reset. Logging you in...",
        variant: "default",
      });

      // Log the user in
      const signInResult = await signIn("credentials", {
        email,
        password: newPassword,
        redirect: false,
      });

      if (signInResult?.error) {
        throw new Error(signInResult.error);
      }

      // Redirect to dashboard on successful login
      router.push("/");
    } catch (error: any) {
      console.error("Reset password error:", error);

      // Handle different error formats
      if (error.data) {
        setError(
          error.data.detail ||
            error.data.message ||
            "An unexpected error occurred"
        );
      } else if (error.message) {
        setError(error.message);
      } else {
        setError("Failed to reset password. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-md p-6">
        <CardHeader className="space-y-1 p-0 mb-6">
          <div className="flex justify-between items-center mb-8">
            <MILogo />
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => router.push("/auth")}
            >
              Back to login
            </Button>
          </div>
          <CardTitle className="text-3xl font-normal">
            {step === "email" ? "Reset Password" : "Verify & Set New Password"}
          </CardTitle>
          <p className="text-sm text-gray-600 mt-2">
            {step === "email"
              ? "Enter your email address and we'll send you a verification code."
              : "Enter the verification code sent to your email and set a new password."}
          </p>
        </CardHeader>

        <CardContent className="space-y-4 p-0">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
              {error}
            </div>
          )}

          {step === "email" ? (
            <form onSubmit={handleRequestReset} className="space-y-4">
              <Input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Sending..." : "Send Verification Code"}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleResetPassword} className="space-y-4">
              <Input
                type="text"
                placeholder="Verification code"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                required
              />

              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="New password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
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

              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                  className="pr-[37px]"
                />
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1"
                  onClick={() => setStep("email")}
                >
                  Back
                </Button>
                <Button type="submit" className="flex-1" disabled={isLoading}>
                  {isLoading ? "Resetting..." : "Reset Password"}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
