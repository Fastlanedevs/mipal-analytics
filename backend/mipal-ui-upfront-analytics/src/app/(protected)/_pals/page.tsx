"use client";

import { useGetPalsQuery } from "@/store/services/palApi";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Pal } from "@/store/types";
import { useRouter } from "next/navigation";
import { useAppDispatch } from "@/store/hooks";
import { setChatCreationDetails } from "@/store/slices/chatCreationSlice";
import { v4 as uuidv4 } from "uuid";
import { PalEnum, palIconMap } from "./PalConstants";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { useState } from "react";
import { ComingSoonDialog } from "@/components/ui/ComingSoonDialog";
import { Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { clearModel } from "@/store/slices/chatSlice";
import { setModel } from "@/store/slices/chatSlice";

export default function PalsPage() {
  const t = useTranslations("pals");
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { data: pals, isLoading, error, refetch } = useGetPalsQuery();
  const [isComingSoonOpen, setIsComingSoonOpen] = useState(false);

  const capitalizeFirstLetter = (str: string) => {
    return str.charAt(0).toUpperCase() + str.slice(1);
  };

  const handlePalClick = (pal: Pal) => {
    if (!pal.is_active) return;

    if (pal.type === "ENTERPRISE_PLAN") {
      setIsComingSoonOpen(true);
      return;
    }

    const chatId = uuidv4();

    const isAnalyticsPal = pal.pal_enum === PalEnum.ANALYST_PAL;

    dispatch(
      setChatCreationDetails({
        chatTitle: "",
        model: pal.pal_enum,
        initialMessage: isAnalyticsPal
          ? ""
          : t("initialMessage", { palName: pal.name }),
      })
    );

    if (!isAnalyticsPal) {
      dispatch(setModel(pal.pal_enum));
    } else {
      dispatch(clearModel());
    }

    router.push(
      isAnalyticsPal ? `/chat/analytics/${chatId}` : `/chat/${chatId}`
    );
  };

  // Separate pals into free and enterprise
  const freePals = pals?.filter((pal) => pal.type === "FREE_PLAN") || [];
  const enterprisePals =
    pals?.filter((pal) => pal.type === "ENTERPRISE_PLAN") || [];

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <p className="text-lg text-muted-foreground">{t("errorLoadingPals")}</p>
        <button
          onClick={() => refetch()}
          className="text-sm text-primary hover:underline"
        >
          {t("tryAgain")}
        </button>
      </div>
    );
  }

  // Render a section of pals
  const renderPalSection = (
    palsList: Pal[],
    title: string,
    description: string,
    isEnterprise = false
  ) => {
    if (palsList.length === 0) return null;

    return (
      <div className="w-full max-w-7xl">
        {isEnterprise && (
          <div className="space-y-3 mb-8">
            <div className="flex items-center gap-2">
              <h2 className="text-2xl font-bold tracking-tight sm:text-4xl flex items-center gap-4">
                {title}
              </h2>
              <div className="flex items-center justify-center p-1 rounded-full bg-primary/10">
                <Sparkles className="w-4 h-4 text-primary" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground sm:text-base">
              {description}
            </p>
          </div>
        )}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {palsList.map((pal) => {
            const iconData = palIconMap[pal.pal_enum];
            const IconComponent = iconData.icon;

            return (
              <Card
                key={pal.id}
                className={cn(
                  "transition-all duration-200",
                  !pal.is_active && "opacity-60 cursor-not-allowed",
                  pal.is_active &&
                    "cursor-pointer hover:scale-[101%] hover:shadow-md active:scale-[100%] active:shadow-sm"
                )}
                onClick={() => handlePalClick(pal)}
              >
                <CardHeader>
                  <div className="flex items-center gap-4">
                    <div className={cn("p-2 rounded-lg", iconData.color)}>
                      <IconComponent className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="flex items-start gap-2">
                        <CardTitle className="text-sm sm:text-base">
                          {pal.name}
                        </CardTitle>
                        <Badge
                          variant={
                            pal.type === "FREE_PLAN" ? "secondary" : "default"
                          }
                          className="text-xs"
                        >
                          {pal.type === "FREE_PLAN" ? "Free" : "Enterprise"}
                        </Badge>
                      </div>
                      {/* <CardDescription className="text-xs sm:text-sm mt-1">
                        {pal.suggestions.length} suggestions available
                      </CardDescription> */}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {capitalizeFirstLetter(pal.description)}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
      <div className="flex flex-col items-start justify-center py-8 space-y-8">
        <PageHeader
          title="MI PALs"
          description="Choose your AI assistant to help you with your tasks"
          isLoading={isLoading}
        />

        <div className="w-full space-y-12">
          {renderPalSection(freePals, "", "")}

          {enterprisePals.length > 0 &&
            renderPalSection(
              enterprisePals,
              "Enterprise PALs",
              "Premium assistants available with enterprise subscription",
              true
            )}
        </div>
      </div>

      <ComingSoonDialog
        isOpen={isComingSoonOpen}
        onClose={() => setIsComingSoonOpen(false)}
      />
    </div>
  );
}
