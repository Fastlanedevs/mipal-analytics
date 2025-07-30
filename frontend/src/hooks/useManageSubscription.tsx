import { toast } from "@/hooks/use-toast";
import { useGetSubscriptionQuery } from "@/store/services/userApi";
import { useCreatePortalSessionMutation } from "@/store/services/stripeApi";

export default function useManageSubscription() {
  const { data: subscription, isLoading: isLoadingSubscription } =
    useGetSubscriptionQuery();
  const [createPortalSession, { isLoading }] = useCreatePortalSessionMutation();

  const handleManageSubscription = async () => {
    try {
      const { url } = await createPortalSession({
        customer_id: subscription?.stripe_customer_id as string,
        return_url: `${process.env.NEXT_PUBLIC_APP_URL}/settings/plans`,
      }).unwrap();

      if (url) {
        window.location.href = url;
      }
    } catch (error) {
      console.error("Failed to create portal session:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description:
          "Failed to access subscription management. Please try again later.",
      });
    }
  };

  return {
    handleManageSubscription,
    isLoading: isLoadingSubscription || isLoading,
  };
}
