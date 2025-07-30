"use client";
// import { redirect } from "next/navigation";
// import { getServerSession } from "next-auth";
// import { authOptions } from "@/lib/auth.config";
import { resetAnalytics } from "@/store/slices/analyticsSlice";
import { clearSuggestions } from "@/store/slices/intentsSlice";
import { resetToInitialChatState } from "@/store/slices/chatSlice";
import { removeArtifacts } from "@/store/slices/artifactsSlice";
import { useRouter } from "next/navigation";
import { v4 as uuidv4 } from "uuid";
import { useDispatch } from "react-redux";
import { useSession } from "next-auth/react";

export default function RootPage() {
  // const session = await getServerSession(authOptions);
  const session = useSession();
  const router = useRouter();
  const dispatch = useDispatch();
  if (!session.data) {
    // redirect("/auth");
    router.push("/auth");
  }

  const newChatId = uuidv4();
  dispatch(resetToInitialChatState());
  dispatch(removeArtifacts());
  dispatch(clearSuggestions());
  dispatch(resetAnalytics());
  router.push(`/chat/analytics/${newChatId}`);
  // redirect("/home");
}
