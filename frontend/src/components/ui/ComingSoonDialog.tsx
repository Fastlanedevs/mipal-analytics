"use client";

import * as React from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Sparkles, X } from "lucide-react";
import { LEMCAL_URL } from "@/constants";
import { useTranslations } from "next-intl";
interface ComingSoonDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ComingSoonDialog({ isOpen, onClose }: ComingSoonDialogProps) {
  const t = useTranslations("pals");
  return (
    <AlertDialog open={isOpen} onOpenChange={onClose}>
      <AlertDialogContent className="sm:max-w-md">
        <X
          className="absolute top-2.5 right-2.5 w-6 h-6 cursor-pointer p-1 hover:bg-accent-foreground/80 rounded-lg hover:text-background"
          onClick={onClose}
        />
        <AlertDialogHeader className="flex flex-col items-center justify-center text-center">
          <div className="flex items-center justify-center w-12 h-12 mb-4 rounded-full bg-primary/10">
            <Sparkles className="w-6 h-6 text-primary" />
          </div>
          <AlertDialogTitle className="text-xl">
            {t("comingSoon")}
          </AlertDialogTitle>
          <AlertDialogDescription className="mt-2">
            {t("comingSoonDescription")}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex justify-center sm:justify-center">
          <AlertDialogAction
            onClick={() => {
              window.open(LEMCAL_URL, "_blank");
              onClose();
            }}
          >
            {t("contactUs")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
