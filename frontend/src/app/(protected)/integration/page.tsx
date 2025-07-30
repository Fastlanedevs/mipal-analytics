"use client";
import React from "react";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useEffect, useState } from "react";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import {
  useGetIntegrationQuery,
  useDeleteIntegrationMutation,
} from "@/store/services/integrationApi";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MessageCircleIcon, MoreVertical, Database } from "lucide-react";
import {
  useStartSyncMutation,
  useGetSyncStatusQuery,
  isSyncInProgress,
  SYNC_STATUS,
} from "@/store/services/syncApi";
import LoadingScreen from "@/components/common/LoadingScreen";
import { PageHeader } from "@/components/common/PageHeader";

import {
  INTEGRATION_TYPES,
  IntegrationType,
  Integration,
} from "@/store/services/integrationApi";

import PostgresIcon from "@/assets/svg/PostgresIcon";
import { PostgresModal } from "@/components/modals/PostgresModal";
import { useTour } from "@/contexts/TourContext";
import { useGetTourGuideQuery } from "@/store/services/userApi";
import { useTranslations } from "next-intl";
import { useSession } from "next-auth/react";

interface IntegrationOption {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  isConnected?: boolean;
  lastSynced?: string;
  comingSoon?: boolean;
  count?: number; // Number of connected instances for PostgreSQL
  instances?: Integration[]; // List of connected PostgreSQL instances
  instanceId?: string; // ID of the specific PostgreSQL instance
}

interface IntegrationCategory {
  title: string;
  description: string;
  options: IntegrationOption[];
  icon?: React.ReactNode;
}

export default function IntegrationsPage() {
  const t = useTranslations("integration");
  const { toast } = useToast();
  const { status: sessionStatus } = useSession();
  const [isPostgresModalOpen, setIsPostgresModalOpen] = useState(false);
  const { startTour } = useTour();
  const { data: tourGuideState } = useGetTourGuideQuery();
  const [tourStarted, setTourStarted] = useState(false);
  const [pageReady, setPageReady] = useState(false);
  const [deleteIntegration, { isLoading: isDeleting }] =
    useDeleteIntegrationMutation();

  // Initialize the query with skip false when session is authenticated
  const {
    data: integrations,
    isLoading,
    error,
    refetch,
  } = useGetIntegrationQuery(undefined);

  const integrationTypeMap = INTEGRATION_TYPES;

  // Set page ready after data is loaded
  useEffect(() => {
    if (!isLoading && integrations) {
      setPageReady(true);
    }
  }, [isLoading, integrations]);

  // Start tour when page is ready and tour guide state is loaded
  useEffect(() => {
    if (pageReady && !tourStarted && tourGuideState) {
      // Add a small delay to ensure DOM is fully rendered
      const timer = setTimeout(() => {
        startTour("integration");
        setTourStarted(true);
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [pageReady, tourStarted, startTour, tourGuideState]);

  useEffect(() => {
    if (error) {
      console.error("Integration fetch error:", error);
      toast({
        title: t("error"),
        description: t("failedToLoadIntegrations"),
        variant: "destructive",
      });
    }
  }, [error]);

  const isIntegrationConnected = (type: IntegrationType) => {
    if (!integrations) return false;

    const backendType = INTEGRATION_TYPES[type as IntegrationType] || type;

    if (type === INTEGRATION_TYPES.POSTGRESQL) {
      // For PostgreSQL, return true if there are any active instances
      return integrations.some(
        (integration) =>
          integration.integration_type === backendType &&
          integration.is_active === true
      );
    }

    // For other integrations, maintain single instance behavior
    return integrations.some(
      (integration) =>
        integration.integration_type === backendType &&
        integration.is_active === true
    );
  };

  const getIntegrationInstanceId = (integration_type: string) => {
    return integrations?.find(
      (integration) => integration.integration_type === integration_type
    )?.integration_id;
  };

  const getPostgresInstances = () => {
    if (!integrations) return [];
    return integrations.filter(
      (integration) =>
        integration.integration_type === INTEGRATION_TYPES.POSTGRESQL &&
        integration.is_active === true
    );
  };

  const handleConnect = async (integrationId: string) => {
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || window.location.origin;

    if (integrationId.startsWith("google-")) {
      const service = integrationId.replace("google-", "");
      if (service === "CALENDAR") {
        toast({
          title: t("comingSoon"),
          description: t("googleCalendarIntegrationWillBeAvailableSoon"),
          variant: "default",
        });
      } else {
        window.location.href = `${appUrl}/api/integrations/google-workspace?service=${service}`;
      }
    } else if (integrationId.startsWith("microsoft-")) {
      // disabled for now
      // const service = integrationId.replace("microsoft-", "");
      // window.location.href = `${appUrl}/api/integrations/azure?service=${service}`;
      // Don't connect for Microsoft services as they're coming soon
      toast({
        title: t("comingSoon"),
        description: t("microsoftIntegrationsWillBeAvailableSoon"),
        variant: "default",
      });
    // Slack integration removed
    } else if (integrationId === "github") {
      window.location.href = `${appUrl}/api/integrations/github`;
    } else if (integrationId === "postgresql") {
      setIsPostgresModalOpen(true);
    }
  };

  const getIntegrationOptions = () => {
    const postgresInstances = getPostgresInstances();

    const integrationCategories = [
      // {
      //   title: "Google Workspace",
      //   description: t("connectWithGoogleServices"),
      //   icon: <GoogleIcon className="w-7 h-7" />,
      //   options: [
      //     {
      //       id: "google-" + integrationTypeMap.GOOGLE_DRIVE,
      //       name: "Google Drive",
      //       description: t("accessAndManageYourDriveFiles"),
      //       icon: <GoogleDriveIcon className="w-9 h-9" />,
      //       isConnected: isIntegrationConnected(
      //         integrationTypeMap.GOOGLE_DRIVE
      //       ),
      //       service: "drive",
      //       instanceId: getIntegrationInstanceId(
      //         integrationTypeMap.GOOGLE_DRIVE
      //       ),
      //     },
      //     {
      //       id: "google-" + integrationTypeMap.GOOGLE_GMAIL,
      //       name: "Gmail",
      //       description: t("accessAndManageYourEmails"),
      //       icon: <GmailIcon className="w-9 h-9" />,
      //       isConnected: isIntegrationConnected(
      //         integrationTypeMap.GOOGLE_GMAIL
      //       ),
      //       service: "gmail",
      //       instanceId: getIntegrationInstanceId(
      //         integrationTypeMap.GOOGLE_GMAIL
      //       ),
      //     },
      //     {
      //       id: "google-" + integrationTypeMap.GOOGLE_CALENDAR,
      //       name: "Google Calendar",
      //       description: t("manageYourCalendarAndEvents"),
      //       icon: <GoogleCalendarIcon className="w-9 h-9" />,
      //       isConnected: isIntegrationConnected(
      //         integrationTypeMap.GOOGLE_CALENDAR
      //       ),
      //       comingSoon: true,
      //       service: "calendar",
      //       instanceId: getIntegrationInstanceId(
      //         integrationTypeMap.GOOGLE_CALENDAR
      //       ),
      //     },
      //   ],
      // },
      {
        title: t("databases"),
        description: t("connectWithDatabaseSystems"),
        icon: <Database className="w-7 h-7" />,
        options: [
          {
            id: "postgresql",
            name: "PostgreSQL",
            description: t("connectToYourPostgreSQLDatabase"),
            icon: <PostgresIcon className="w-9 h-9" />,
            isConnected: false,
            lastSynced: "2024-03-19T10:30:00Z",
            instanceId: getIntegrationInstanceId(integrationTypeMap.POSTGRESQL),
          },
        ],
      },
      // {
      //   title: t("communication"),
      //   description: t("connectWithMessagingAndCollaborationPlatforms"),
      //   icon: <MessageCircleIcon className="w-7 h-7" />,
      //   options: [
      //     {
      //       id: "slack",
      //       name: "Slack",
      //       description: t("accessFilesFromSlackChatAndChannels"),
      //       icon: <SlackIcon className="w-9 h-9" />,
      //       isConnected: isIntegrationConnected(integrationTypeMap.SLACK_CHAT),
      //       lastSynced: "2024-03-19T10:30:00Z",
      //       instanceId: getIntegrationInstanceId(integrationTypeMap.SLACK_CHAT),
      //     },
      //     // {
      //     //   id: "github",
      //     //   name: "GitHub",
      //     //   description: "Access files from GitHub repositories",
      //     //   icon: <GithubIcon className="w-9 h-9" />,
      //     //   isConnected: isIntegrationConnected(
      //     //     integrationTypeMap.GITHUB
      //     //   ),
      //     //   lastSynced: "2024-03-19T10:30:00Z",
      //     // },
      //   ],
      // },
      // {
      //   title: "Microsoft 365",
      //   description: t("connectWithMicrosoftServices"),
      //   icon: <MicrosoftIcon className="w-7 h-7" />,
      //   options: [
      //     {
      //       id: "microsoft-" + integrationTypeMap.MICROSOFT_ONEDRIVE,
      //       name: "OneDrive",
      //       description: t("accessAndManageYourOneDriveFiles"),
      //       icon: <OneDriveIcon className="w-9 h-9" />,
      //       // disabled for now
      //       // isConnected: isIntegrationConnected(
      //       //   integrationTypeMap.MICROSOFT_ONEDRIVE
      //       // ),
      //       isConnected: false,
      //       comingSoon: true,
      //       lastSynced: "2024-03-19T10:30:00Z",
      //       instanceId: getIntegrationInstanceId(
      //         integrationTypeMap.MICROSOFT_ONEDRIVE
      //       ),
      //     },
      //     {
      //       id: "microsoft-" + integrationTypeMap.MICROSOFT_OUTLOOK,
      //       name: "Outlook",
      //       description: t("accessAndManageYourEmailsAndCalendar"),
      //       icon: <OutlookIcon className="w-9 h-9" />,
      //       // disabled for now
      //       // isConnected: isIntegrationConnected(
      //       //   integrationTypeMap.MICROSOFT_OUTLOOK
      //       // ),
      //       isConnected: false,
      //       comingSoon: true,
      //       lastSynced: "2024-03-19T10:30:00Z",
      //       instanceId: getIntegrationInstanceId(
      //         integrationTypeMap.MICROSOFT_OUTLOOK
      //       ),
      //     },
      //     // {
      //     //   id: "microsoft-sharepoint",
      //     //   name: "SharePoint",
      //     //   description: "Access and manage SharePoint documents",
      //     //   icon: <SharePointIcon className="w-9 h-9" />,
      //     //   isConnected: isIntegrationConnected(integrationTypeMap.MICROSOFT_SHAREPOINT),
      //     //   lastSynced: "2024-03-19T10:30:00Z",
      //     // },
      //     {
      //       id: "microsoft-" + integrationTypeMap.MICROSOFT_TEAMS,
      //       name: "Microsoft Teams",
      //       description: t("accessTeamsChatsChannelsAndFiles"),
      //       icon: <Teams className="w-9 h-9" />,
      //       // disabled for now
      //       // isConnected: isIntegrationConnected(integrationTypeMap.MICROSOFT_TEAMS),
      //       isConnected: false,
      //       comingSoon: true,
      //       lastSynced: "2024-03-19T10:30:00Z",
      //       instanceId: getIntegrationInstanceId(
      //         integrationTypeMap.MICROSOFT_TEAMS
      //       ),
      //     },
      //     {
      //       id: "microsoft-" + integrationTypeMap.MICROSOFT_CALENDER,
      //       name: "Microsoft Calendar",
      //       description: t("accessAndManageYourCalendar"),
      //       icon: <MicrosoftCalendar className="w-9 h-9" />,
      //       // disabled for now
      //       // isConnected: isIntegrationConnected(integrationTypeMap.MICROSOFT_CALENDER),
      //       isConnected: false,
      //       comingSoon: true,
      //       lastSynced: "2024-03-19T10:30:00Z",
      //       instanceId: getIntegrationInstanceId(
      //         integrationTypeMap.MICROSOFT_CALENDER
      //       ),
      //     },
      //   ],
      // },
    ];

    // Create separate PostgreSQL instances for connected integrations
    const connectedPostgresInstances = postgresInstances.map((instance) => ({
      id: `postgresql_${instance.integration_id}`,
      name: "PostgreSQL",
      description: `Database: ${
        instance?.integration_name || "Unnamed Database"
      }`,
      icon: <PostgresIcon className="w-9 h-9" />,
      isConnected: true,
      lastSynced: instance.last_sync || "2024-03-19T10:30:00Z",
      instanceId: instance.integration_id,
    }));

    return integrationCategories.reduce(
      (acc, category) => {
        // Check if any options in this category are unconnected
        const hasUnconnectedOptions = category.options.some(
          (integration) => !integration.isConnected
        );

        // Add connected integrations to connectedIntegrations
        category.options.forEach((integration) => {
          if (integration.isConnected) {
            acc.connectedIntegrations.push(integration);
          }
        });

        // Only add the category once if it has any unconnected options
        if (hasUnconnectedOptions) {
          acc.availableIntegrations.push(category);
        }

        return acc;
      },
      {
        connectedIntegrations: connectedPostgresInstances,
        availableIntegrations: [],
      } as {
        connectedIntegrations: IntegrationOption[];
        availableIntegrations: IntegrationCategory[];
      }
    );
  };

  const { connectedIntegrations, availableIntegrations } =
    getIntegrationOptions();

  const IntegrationCard = ({
    integration,
  }: {
    integration: IntegrationOption;
  }) => {
    const [startSync] = useStartSyncMutation();

    // Update integrationType logic to handle Google services
    const getIntegrationType = (integrationId: string) => {
      if (integrationId.startsWith("google-")) {
        // Extract the service type (e.g., 'google-drive' -> 'GOOGLE_DRIVE')
        const serviceType = integrationId.replace("google-", "").toUpperCase();
        return serviceType;
      } else if (integrationId.startsWith("microsoft-")) {
        const serviceType = integrationId
          .replace("microsoft-", "")
          .toUpperCase();
        return serviceType;
      } else if (integrationId.startsWith("postgresql_")) {
        return "POSTGRESQL";
      } else if (integrationId === "postgresql") {
        return "POSTGRESQL";
      }
      return integrationId;
    };

    const integrationType = getIntegrationType(integration.id);
    const { toast } = useToast();

    // Add state to control polling
    const [shouldPoll, setShouldPoll] = useState(false);

    const {
      data: syncStatus,
      refetch: refetchSyncStatus,
      isLoading: isSyncStatusLoading,
      isSuccess: isSyncStatusSuccess,
      isFetching,
    } = useGetSyncStatusQuery(integration.instanceId || "", {
      skip: !integration.instanceId,
      // Only poll when shouldPoll is true
      pollingInterval: shouldPoll ? 2000 : 0,
      refetchOnMountOrArgChange: true,
    });

    // Control polling based on sync status
    useEffect(() => {
      if (!syncStatus) {
        setShouldPoll(false);
        return;
      }

      if (
        syncStatus.last_sync_status === SYNC_STATUS.COMPLETED ||
        syncStatus.last_sync_status === SYNC_STATUS.FAILED
      ) {
        setShouldPoll(false);
      } else if (
        syncStatus.last_sync_status === SYNC_STATUS.STARTED ||
        syncStatus.last_sync_status === SYNC_STATUS.PROCESSING
      ) {
        setShouldPoll(true);
      }
    }, [syncStatus?.last_sync_status]);

    const handleSync = async (e: React.MouseEvent) => {
      e.stopPropagation();

      if (isSyncInProgress(syncStatus)) {
        return;
      }

      try {
        setShouldPoll(true);

        const instanceId = integration.instanceId;
        await startSync(`${instanceId}`).unwrap();
        // if (integration.id.startsWith("postgresql_")) {
        //   // For individual PostgreSQL instances
        // } else if (integration.id === "postgresql") {
        //   // For the main PostgreSQL card (when adding a new instance)
        //   await startSync(integrationType).unwrap();
        // } else {
        //   await startSync(integrationType).unwrap();
        // }

        toast({
          title: t("syncStarted"),
          description: t("synchronizationProcessHasBegunFor", {
            integration: integration.name,
          }),
          variant: "default",
        });
      } catch (error) {
        setShouldPoll(false);
        console.error("Sync error:", error);
        toast({
          title: t("syncFailed"),
          description: t("failedToStartSynchronizationFor", {
            integration: integration.name,
          }),
          variant: "destructive",
        });
      }
    };

    const handleDisconnect = async (e: React.MouseEvent) => {
      e.stopPropagation();
      try {
        await deleteIntegration(integration.instanceId || "").unwrap();
        toast({
          title: t("disconnectedSuccessfully"),
          description: t("integrationDisconnected", {
            integration: integration.name,
          }),
          variant: "default",
        });
      } catch (error) {
        console.error("Disconnect error:", error);
        toast({
          title: t("disconnectFailed"),
          description: t("failedToDisconnectIntegration", {
            integration: integration.name,
          }),
          variant: "destructive",
        });
      }
    };

    // Handle card click event
    const handleCardClick = () => {
      if (integration.comingSoon) {
        // If it's coming soon, show a toast instead of connecting
        toast({
          title: t("comingSoon"),
          description: t("comingSoonDescription", {
            integration: integration.name,
          }),
          variant: "default",
        });
      } else {
        // Otherwise, proceed with normal connection flow
        handleConnect(integration.id);
      }
    };

    return (
      <Card
        key={integration.id}
        className={`
          relative w-full transition-all max-w-72 hover:scale-[101%] cursor-pointer group hover:shadow-md shadow-none dark:shadow-none active:scale-100 active:shadow
          ${integration.isConnected ? "bg-green-500" : ""}
          ${integration.comingSoon ? "opacity-75" : ""}
        `}
        onClick={handleCardClick}
      >
        {integration.isConnected && (
          <div className="absolute top-3 right-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <button className="p-1 rounded-md hover:bg-green-100 dark:hover:bg-green-900">
                  <MoreVertical className="w-4 h-4 text-green-700 dark:text-white" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSync(e);
                  }}
                >
                  {t("syncNow")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-red-600 cursor-pointer focus:text-red-600"
                  onClick={handleDisconnect}
                >
                  {t("disconnect")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
        <CardHeader className="p-6">
          <div className="flex flex-col gap-4">
            <CardTitle
              className={`text-lg flex flex-row items-center gap-2 ${
                integration.isConnected ? "text-white" : ""
              }`}
            >
              {integration.name}
              {integration.count && integration.count > 0 && (
                <span className="ml-1 text-xs font-normal px-2 py-0.5 bg-white/20 text-white rounded">
                  {integration.count} connected
                </span>
              )}
              {integration.comingSoon && (
                <span className="ml-1 text-xs font-normal px-2 py-0.5 bg-amber-200 text-amber-800 dark:bg-amber-800 dark:text-amber-200 rounded">
                  {t("comingSoon")}
                </span>
              )}
              {!integration.isConnected && !integration.comingSoon && (
                <svg
                  className="w-4 h-4 mr-2 group-hover:block hidden opacity-80"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                  />
                </svg>
              )}
            </CardTitle>
            <div className="flex justify-center py-2 group-hover:animate-rotate-y">
              {integration.icon}
            </div>
            <p
              className={`text-sm ${
                integration.isConnected
                  ? "text-white/90"
                  : "text-muted-foreground"
              }`}
            >
              {integration.description}
            </p>
            {integration.isConnected && (
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                {isSyncStatusLoading && !syncStatus && !isFetching ? (
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size={12} className="dark:text-white" />
                    <span className="dark:text-white">
                      {t("loadingSyncStatus")}
                    </span>
                  </div>
                ) : syncStatus ? (
                  <div className="flex flex-col gap-1">
                    <span className="text-white">
                      {t("lastSynced")}:{" "}
                      {syncStatus.last_successful_sync
                        ? new Date(
                            syncStatus.last_successful_sync
                          ).toLocaleString()
                        : t("never")}
                    </span>
                    <span
                      className={`text-xs ${
                        syncStatus.last_sync_status === SYNC_STATUS.COMPLETED
                          ? "text-green-100"
                          : syncStatus.last_sync_status === SYNC_STATUS.FAILED
                            ? "text-red-200"
                            : "text-white/70"
                      }`}
                    >
                      {t("status")}: {syncStatus.last_sync_status}
                    </span>
                  </div>
                ) : (
                  <span className="text-white">{t("noSyncDataAvailable")}</span>
                )}
                <button
                  className={`px-3 py-1 text-primary hover:text-blue-700 bg-white dark:bg-accent rounded-md transition-colors ${
                    isSyncInProgress(syncStatus) ? "cursor-not-allowed" : ""
                  }`}
                  onClick={handleSync}
                  disabled={isSyncInProgress(syncStatus) || isSyncStatusLoading}
                  type="button"
                >
                  <div className="flex items-center gap-1">
                    {isSyncInProgress(syncStatus) ? (
                      <>
                        <LoadingSpinner size={12} className="dark:text-white" />
                        <span className="dark:text-white">{t("syncing")}</span>
                      </>
                    ) : (
                      <>
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                          />
                        </svg>
                        <span>{t("sync")}</span>
                      </>
                    )}
                  </div>
                </button>
              </div>
            )}
          </div>
        </CardHeader>
        {integration.comingSoon && (
          <div className="absolute inset-0 bg-black/5 dark:bg-black/20 flex items-center justify-center rounded-lg pointer-events-none">
            {/* Overlay content can be added here if needed */}
          </div>
        )}
      </Card>
    );
  };

  // if (error) {
  //   return (
  //     <Layout>
  //       <div className="container p-6 mx-auto text-center">
  //         <p className="text-red-600">
  //           Failed to load integrations. Please try again later.
  //         </p>
  //       </div>
  //     </Layout>
  //   );
  // }

  return (
    <div className="container p-6 mx-auto">
      <div className="max-w-6xl mx-auto">
        <div
          className="integration-tour-start integration-status"
          style={{ height: "1px" }}
        ></div>
        <PageHeader
          title={t("integrations")}
          description={t("connectYourFavoriteToolsToEnhanceYourWorkspace")}
          className="mb-8"
        />

        {isLoading ? (
          <LoadingScreen />
        ) : (
          <div className="space-y-12">
            {connectedIntegrations.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-6">
                  <div className="h-2.5 w-2.5 rounded-full bg-green-500"></div>
                  <h2 className="text-xl font-semibold">
                    {t("activeIntegrations")}
                  </h2>
                </div>
                <div className="flex flex-row flex-wrap gap-6">
                  {connectedIntegrations.map((integration) => (
                    <IntegrationCard
                      key={integration.id}
                      integration={integration}
                    />
                  ))}
                </div>
              </section>
            )}

            {availableIntegrations.length > 0 && (
              <div className="space-y-12 integration-list">
                {availableIntegrations.map((category) => {
                  const availableInCategory = category.options.filter(
                    (opt) => !opt.isConnected
                  );
                  if (availableInCategory.length === 0) return null;

                  // if any of the options in the category are connected
                  const isAnyConnected = availableInCategory.some(
                    (opt) => opt.isConnected
                  );

                  return (
                    <section key={category.title}>
                      <div className="flex items-center gap-2 mb-6">
                        {isAnyConnected && (
                          <div className="h-2.5 w-2.5 rounded-full bg-green-500"></div>
                        )}
                        <div className="flex flex-col gap-2">
                          <h2 className="text-xl font-semibold flex flex-row items-center gap-2">
                            {category?.icon}
                            {category.title}
                          </h2>
                          <p className="text-sm text-muted-foreground">
                            {category.description}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-row flex-wrap gap-6">
                        {availableInCategory.map((integration) => (
                          <IntegrationCard
                            key={integration.id}
                            integration={integration}
                          />
                        ))}
                      </div>
                    </section>
                  );
                })}
              </div>
            )}

            {connectedIntegrations.length === 0 &&
              availableIntegrations.length === 0 && (
                <div className="py-12 text-center">
                  <p className="text-muted-foreground">
                    {t("noIntegrationsAvailable")}
                  </p>
                </div>
              )}
          </div>
        )}

        <PostgresModal
          isOpen={isPostgresModalOpen}
          onClose={() => setIsPostgresModalOpen(false)}
        />
        <div className="integration-settings" style={{ height: "1px" }}></div>
      </div>
    </div>
  );
}
