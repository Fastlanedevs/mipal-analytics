"use client";

import { Button } from "@/components/ui/button";
import { CreditCard } from "lucide-react";
import { usePathname } from "next/navigation";
import { useGetSubscriptionQuery } from "@/store/services/userApi";
import useManageSubscription from "@/hooks/useManageSubscription";
import { useTranslations } from "next-intl";

export default function ManageSubscription() {
  const pathname = usePathname();
  const { data: subscription } = useGetSubscriptionQuery();
  const { handleManageSubscription } = useManageSubscription();
  const t = useTranslations("settings.navigation");

  // If user doesn't have a stripe_customer_id, don't show the button
  if (!subscription?.stripe_customer_id) {
    return null;
  }

  return (
    <Button
      variant="ghost"
      className={`justify-start flex-shrink-0 md:w-full ${
        pathname === "/settings/subscription"
          ? "bg-primary-foreground dark:bg-foreground dark:text-background"
          : "dark:hover:bg-foreground dark:hover:text-background"
      }`}
      onClick={handleManageSubscription}
    >
      <CreditCard className="w-4 h-4 mr-2" />
      {t("subscription")}
    </Button>
  );
}
