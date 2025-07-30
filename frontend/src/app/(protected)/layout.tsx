"use client";
import Layout from "@/components/common/Layout";
import Sidebar from "@/components/common/Sidebar";
import { Container } from "@/components/ui/container";
import { usePathname } from "next/navigation";
import { ArtifactPanel } from "@/app/(protected)/chat/components/ArtifactPanel";
import { ReferencePanel } from "@/app/(protected)/chat/components/ReferencePanel";
import { useSelector, useDispatch } from "react-redux";
import { setIsArtifactPanelOpen } from "@/store/slices/artifactsSlice";
import { setIsReferencePanelOpen } from "@/store/slices/referencesSlice";
import { RootState } from "@/store/store";
import { useEffect } from "react";
import { useTranslations } from "next-intl";
export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations("chat");
  const pathname = usePathname();
  const isChat = pathname?.includes("/chat");
  const isAnalytics = pathname?.includes("/chat/analytics");
  const isAnalyticsChat = pathname?.includes("/chat/analytics");
  const isDashboard = pathname?.includes("/dashboard");
  const dispatch = useDispatch();
  const { artifacts, isArtifactPanelOpen } = useSelector(
    (state: RootState) => state.artifacts
  );
  const { references, isReferencePanelOpen } = useSelector(
    (state: RootState) => state.references
  );

  useEffect(() => {
    if (!isChat && isArtifactPanelOpen) {
      dispatch(setIsArtifactPanelOpen(false));
    }
    if (!isChat && isReferencePanelOpen) {
      dispatch(setIsReferencePanelOpen(false));
    }
  }, [pathname]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 relative h-full overflow-hidden flex">
        <Container className={isChat ? "flex-1" : "w-full"}>
          <div className="h-full py-0 md:py-0 overflow-y-auto flex flex-col justify-between">
            <Layout
              childrenClassName={
                isChat
                  ? "flex flex-col justify-between"
                  : isDashboard
                    ? "!max-w-[98%]"
                    : ""
              }
            >
              {children}
              {isChat && !isAnalyticsChat && (
                <div className="text-xs text-muted-foreground text-center pb-2 px-[6px]">
                  {t("disclaimer")}
                </div>
              )}
            </Layout>
          </div>
        </Container>
        {isChat && !isAnalytics && (
          <ArtifactPanel
            artifacts={artifacts}
            isOpen={isArtifactPanelOpen}
            onClose={() => dispatch(setIsArtifactPanelOpen(false))}
          />
        )}
        <ReferencePanel
          references={references}
          isOpen={isReferencePanelOpen}
          onClose={() => dispatch(setIsReferencePanelOpen(false))}
        />
      </main>
    </div>
  );
}
