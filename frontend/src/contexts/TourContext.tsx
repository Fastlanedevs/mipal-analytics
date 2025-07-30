import {
  createContext,
  useContext,
  useState,
  ReactNode,
  useEffect,
  useMemo,
} from "react";
import Joyride, { CallBackProps, STATUS, Step } from "react-joyride";
import {
  useGetTourGuideQuery,
  useUpdateTourGuideMutation,
} from "@/store/services/userApi";
import {
  useGetUserProfileQuery,
  useGetUserSettingsQuery,
} from "@/store/services/userApi";
import { useTranslations } from "next-intl";

// Define available tours in the application
export type TourName =
  | "analytics"
  | "knowledgePal"
  | "integration"
  | "dashboard"
  | "home"
  | "search";

// Tour context type
type TourContextType = {
  startTour: (tourName: TourName) => void;
  endTour: () => void;
  currentTour: TourName | null;
  isTourActive: boolean;
};

// Create context with default values
const TourContext = createContext<TourContextType>({
  startTour: () => {},
  endTour: () => {},
  currentTour: null,
  isTourActive: false,
});

// Helper function to create tours with translations
const createTourConfig = (t: any): Record<TourName, Step[]> => ({
  analytics: [
    {
      target: ".analytics-tour-start",
      content: t("tourGuide.analytics.welcome"),
      disableBeacon: true,
      placement: "center",
    },
    {
      target: ".analytics-add-database",
      content: t("tourGuide.analytics.addDatabase"),
      disableBeacon: true,
    },
    {
      target: ".analytics-query-input",
      content: t("tourGuide.analytics.queryInput"),
      disableBeacon: true,
    },
    {
      target: ".analytics-visualization",
      content: t("tourGuide.analytics.visualization"),
      disableBeacon: true,
    },
  ],
  knowledgePal: [
    {
      target: ".knowledge-pal-tour-start",
      content: t("tourGuide.knowledgePal.intro"),
      disableBeacon: true,
    },
  ],
  integration: [
    {
      target: ".integration-tour-start",
      content: t("tourGuide.integration.welcome"),
      disableBeacon: true,
      placement: "center",
      spotlightPadding: 0,
    },
    {
      target: ".integration-list",
      content: t("tourGuide.integration.browseList"),
      disableBeacon: true,
      spotlightPadding: 15,
      placement: "bottom",
    },
    {
      target: ".integration-status",
      content: t("tourGuide.integration.statusView"),
      disableBeacon: true,
      spotlightPadding: 0,
      placement: "center",
    },
  ],
  dashboard: [
    {
      target: ".dashboard-tour-start",
      content: t("tourGuide.dashboard.welcome"),
      disableBeacon: true,
      placement: "center",
    },
    {
      target: ".dashboard-dropdown",
      content: t("tourGuide.dashboard.selectDashboard"),
      disableBeacon: true,
    },
    {
      target: ".dashboard-edit",
      content: t("tourGuide.dashboard.editDashboard"),
      disableBeacon: true,
    },
    {
      target: ".dashboard-save",
      content: t("tourGuide.dashboard.saveDashboard"),
      disableBeacon: true,
    },
  ],
  home: [
    {
      target: ".home-tour-start",
      content: t("tourGuide.home.welcome"),
      disableBeacon: true,
      placement: "center",
    },
    {
      target: ".chat-input",
      content: t("tourGuide.home.chatInput"),
      disableBeacon: false,
    },
    {
      target: ".file-upload-input",
      content: t("tourGuide.home.fileUpload"),
      disableBeacon: false,
    },
    {
      target: ".search-input",
      content: t("tourGuide.home.searchInput"),
      disableBeacon: true,
    },
    {
      target: ".web-search-input",
      content: t("tourGuide.home.webSearch"),
      disableBeacon: true,
    },
    {
      target: ".features-pals",
      content: t("tourGuide.home.featuresPals"),
      disableBeacon: true,
    },
  ],
  search: [
    {
      target: ".search-input",
      content: t("tourGuide.search.searchInput"),
      disableBeacon: true,
      placement: "center",
    },
    {
      target: ".web-search-input",
      content: t("tourGuide.search.webSearch"),
      disableBeacon: true,
    },
  ],
});

export const TourProvider = ({ children }: { children: ReactNode }) => {
  const t = useTranslations();
  const [currentTour, setCurrentTour] = useState<TourName | null>(null);
  const [run, setRun] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  // Add local state to track completed tours
  const [localCompletedTours, setLocalCompletedTours] = useState<Set<TourName>>(
    new Set()
  );

  // Create tour config with translations
  const tourConfig = createTourConfig(t);

  // Get tour guide state from API
  const { data: tourGuideState } = useGetTourGuideQuery();
  const { data: userProfile } = useGetUserProfileQuery({});
  const { data: userSettings } = useGetUserSettingsQuery({});
  const [updateTourGuide] = useUpdateTourGuideMutation();

  // Memoize the locale object to prevent infinite re-renders
  const localeMessages = useMemo(
    () => ({
      back: t("tourGuide.buttons.back"),
      close: t("tourGuide.buttons.close"),
      last: t("tourGuide.buttons.end"),
      next: t("tourGuide.buttons.next"),
      skip: t("tourGuide.buttons.skip"),
      // Add explicit nextLabelWithProgress that uses the format consistently
      nextLabelWithProgress: `{step} / {steps} - ${t("tourGuide.buttons.next")}`,
    }),
    [t, userSettings?.language]
  );

  // Check if user can see tours - must have both conditions true
  const canShowTour =
    userProfile?.joined_org === true && userProfile?.organisation != null;

  const startTour = (tourName: TourName) => {
    // Check both API state and local state
    if (!canShowTour || localCompletedTours.has(tourName)) {
      setRun(false);
      setCurrentTour(null);
      return;
    }

    // Only start tour if tourGuideState is loaded and the tour hasn't been completed
    const tourKey = `${tourName}_tour` as keyof typeof tourGuideState;
    const directKey = tourName as keyof typeof tourGuideState;

    // Check if the tour has been completed based on the tour name
    let isCompleted = false;
    if (
      tourName === "search" ||
      tourName === "home" ||
      tourName === "dashboard"
    ) {
      isCompleted = tourGuideState?.[directKey] ?? false;
    } else if (tourName === "integration") {
      isCompleted = tourGuideState?.integrations_tour ?? false;
    } else {
      isCompleted = tourGuideState?.[tourKey] ?? false;
    }

    if (tourGuideState && !isCompleted) {
      setCurrentTour(tourName);
      setSteps(tourConfig[tourName]);
      setRun(true);
    } else {
      setRun(false);
      setCurrentTour(null);
    }
  };

  const endTour = async () => {
    if (currentTour) {
      // Add to local completed tours immediately
      setLocalCompletedTours(
        (prev) => new Set(Array.from(prev).concat(currentTour))
      );

      if (tourGuideState) {
        // Create update data with only the current tour's state
        const updateData: Partial<typeof tourGuideState> = {};

        // Set only the current tour's state to true
        if (
          currentTour === "search" ||
          currentTour === "home" ||
          currentTour === "dashboard"
        ) {
          updateData[currentTour] = true;
        } else if (currentTour === "knowledgePal") {
          updateData.knowledge_pal_tour = true;
        } else if (currentTour === "integration") {
          updateData.integrations_tour = true;
        } else {
          updateData[`${currentTour}_tour`] = true;
        }

        try {
          await updateTourGuide(updateData);
        } catch (error) {
          console.error(`Failed to update tour ${currentTour} state:`, error);
        }
      }
    }
    setRun(false);
    setCurrentTour(null);
  };

  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status, type, step } = data;
    const finishedStatuses: string[] = [STATUS.FINISHED, STATUS.SKIPPED];

    if (finishedStatuses.includes(status)) {
      endTour();
    }
  };

  return (
    <TourContext.Provider
      value={{
        startTour,
        endTour,
        currentTour,
        isTourActive: run && canShowTour,
      }}
    >
      {/* Only render Joyride if both conditions are met */}
      {canShowTour && run && (
        <Joyride
          key={userSettings?.language || "en"}
          callback={handleJoyrideCallback}
          continuous
          hideCloseButton
          run={run}
          scrollToFirstStep
          showProgress
          showSkipButton
          steps={steps}
          spotlightClicks
          disableOverlayClose
          disableScrolling={false}
          locale={localeMessages}
          styles={{
            buttonNext: {
              backgroundColor: "rgba(31, 41, 55, 1)",
              color: "#ffffff",
              fontSize: "14px",
            },
            buttonBack: {
              color: "#6b7280",
              fontSize: "14px",
            },
          }}
        />
      )}
      {children}
    </TourContext.Provider>
  );
};

export const useTour = () => useContext(TourContext);
