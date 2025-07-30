import {
  BarChart,
  BookOpen,
  Leaf,
  Square,
  ShoppingCart,
  File,
  ChartCandlestick,
} from "lucide-react";
import { LucideIcon } from "lucide-react";

export enum PalEnum {
  ANALYST_PAL = "ANALYST_PAL",
  KNOWLEDGE_PAL = "KNOWLEDGE_PAL",
  SUSTAINABILITY_PAL = "SUSTAINABILITY_PAL",
  ORDER_PROCESSING = "ORDER_PROCESSING",
  RFP_PAL = "RFP_PAL",
  MARKET_ANALYSER = "MARKET_ANALYSER",
}

export const palIconMap: Record<string, { icon: LucideIcon; color: string }> = {
  ANALYST_PAL: { icon: BarChart, color: "text-blue-500" },
  KNOWLEDGE_PAL: { icon: BookOpen, color: "text-green-500" },
  SUSTAINABILITY_PAL: { icon: Leaf, color: "text-purple-500" },
  ORDER_PROCESSING: { icon: ShoppingCart, color: "text-yellow-500" },
  RFP_PAL: { icon: File, color: "text-red-500" },
  MARKET_ANALYSER: { icon: ChartCandlestick, color: "text-orange-500" },
  DEFAULT_PAL: { icon: Square, color: "text-gray-500" },
};
