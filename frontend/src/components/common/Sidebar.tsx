"use client";
import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Sidebar as ShadcnSidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
} from "@/components/ui/sidebar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  ChevronLeft,
  MessageCircleMore,
  Search,
  Blocks,
  History,
  Users,
  Settings,
  LogOut,
  Pin,
  PanelRight,
  Calendar,
  Ellipsis,
  ChartBar,
  CirclePlus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { usePathname, useRouter } from "next/navigation";
import { DesktopLogo, MobileLogo } from "@/assets/svg/MILogo";
import {
  useGetUserProfileQuery,
  useGetUserSettingsQuery,
  useUpdateUserSettingsMutation,
} from "@/store/services/userApi";
import { signOut } from "next-auth/react";
import { useGetOrganizationQuery } from "@/store/services/organizationApi";
import { useUser } from "@/store/hooks/useUser";
import { Theme, useTheme } from "@/contexts/ThemeContext";
import { toast } from "@/hooks/use-toast";
import { v4 as uuidv4 } from "uuid";
import { useDispatch } from "react-redux";
import { resetSelectedFiles } from "@/store/slices/fileSearchSlice";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ThemeSelector } from "@/components/ThemeSelector";
import { resetAnalytics } from "@/store/slices/analyticsSlice";
import { useTranslations } from "next-intl";
import RenderCreditsInfo from "../pricing/RenderCreditsInfo";
import { clearSuggestions } from "@/store/slices/intentsSlice";
import { resetToInitialChatState } from "@/store/slices/chatSlice";
import { removeArtifacts } from "@/store/slices/artifactsSlice";

// Add this array of avatar background colors
const AVATAR_COLORS = [
  "bg-blue-500",
  "bg-green-500",
  "bg-purple-500",
  "bg-pink-500",
  "bg-indigo-500",
  "bg-red-500",
  "bg-yellow-500",
  "bg-teal-500",
];

// Add this function to get a consistent color based on username
const getAvatarColor = (name: string) => {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
};

export default function Sidebar() {
  const t = useTranslations("sidebar");
  const dispatch = useDispatch();
  const router = useRouter();
  const pathname = usePathname() || "";

  const { data: userSettings } = useGetUserSettingsQuery({});
  const [updateUserSettings] = useUpdateUserSettingsMutation();
  const [isOpen, setIsOpen] = useState(false);
  const [isPinned, setIsPinned] = useState(
    userSettings?.pinned_sidebar || false
  );
  const [isMobileOrTablet, setIsMobileOrTablet] = useState(false);
  const [popoverOpen, setPopoverOpen] = useState(false);

  const {
    data: userProfile,
    isLoading: isUserLoading,
    error: userError,
  } = useGetUserProfileQuery({});

  const menuItems = [
    { icon: MessageCircleMore, label: t("newChat"), path: "/home" },
    { icon: ChartBar, label: t("biDashboard"), path: "/dashboard" },
    // { icon: Search, label: t("search"), path: "/search" },
    { icon: Blocks, label: t("integration"), path: "/integration" },
    { icon: History, label: t("history"), path: "/history" },
    // { icon: Users, label: t("pals"), path: "/pals" },
    // { icon: CalendarFold, label: "Meet Assistant", path: "/meet-assistant" },
    // {
    //   icon: Calendar,
    //   label: t("productionDashboard"),
    //   path: "/production-dashboard",
    // },
  ];

  if (userError) {
    // Type guard to check if error is a FetchBaseQueryError
    // basically the condition is userError.status === 401 && userError.data.error === "INVALID_TOKEN"
    if (
      "status" in userError &&
      "data" in userError &&
      userError.status === 401 &&
      typeof userError.data === "object" &&
      userError.data &&
      "error" in userError.data &&
      userError.data.error === "INVALID_TOKEN"
    ) {
      // TODO: Uncomment this when the issue is fixed at the backend
      console.log("🚀 ~ userError:", userError);
      // signOut({ callbackUrl: "/auth" });
      // toast({
      //   title: t("invalidToken"),
      //   description: t("pleaseLogInAgain"),
      // });
    }
  }

  const {
    data: organization,
    isLoading: isOrgLoading,
    error: orgError,
  } = useGetOrganizationQuery(userProfile?.organisation?.id || "", {
    skip: !userProfile?.organisation?.id,
  });

  // if (
  //   !userProfile?.organisation?.id &&
  //   !pathname.includes("/settings/profile")
  // ) {
  //   router.push("/settings/profile");
  // }

  const { user } = useUser();

  const { theme, setTheme } = useTheme();

  // Add useEffect to handle organization API error
  useEffect(() => {
    if (!user?.user_id) {
      console.error("User API error, signing out:", userError);

      // TODO: Uncomment this when the issue is fixed at the backend
      // signOut({ callbackUrl: "/auth" });
      // toast({
      //   title: t("userAPIError"),
      //   description: t("pleaseTryAgainLater"),
      //   variant: "destructive",
      // });
    }
  }, [userError]);

  useEffect(() => {
    const checkScreenSize = () => {
      // if pathname includes /chat/analytics, then set isMobileOrTablet to false
      const analyticsPath = pathname?.includes("/chat/analytics");
      const isMobileDevice =
        window.innerWidth < 1024 ||
        /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

      setIsMobileOrTablet(isMobileDevice || analyticsPath);
    };

    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);
    return () => window.removeEventListener("resize", checkScreenSize);
  }, [pathname]);

  useEffect(() => {
    // update pinned sidebar
    setIsPinned(!!userSettings?.pinned_sidebar);
    // update theme
    if (userSettings?.theme && theme !== userSettings.theme) {
      setTheme(userSettings.theme as Theme);
    }
  }, [userSettings]);

  useEffect(() => {
    if (isMobileOrTablet) {
      // setIsOpen(false);
      // setIsPinned(false);
      togglePin(false);
    }
  }, [isMobileOrTablet]);

  useEffect(() => {
    const handleEdgeHover = (e: MouseEvent) => {
      if (!isMobileOrTablet && !isPinned && e.clientX <= 20) {
        setIsOpen(true);
      }
    };

    document.addEventListener("mousemove", handleEdgeHover);
    return () => document.removeEventListener("mousemove", handleEdgeHover);
  }, [isMobileOrTablet, isPinned]);

  const handleMouseEnter = () => {
    if (!isMobileOrTablet && !isPinned) {
      setIsOpen(true);
    }
  };

  const handleMouseLeave = () => {
    if (!isMobileOrTablet && !isPinned && !popoverOpen) {
      setIsOpen(false);
    }
  };

  const togglePin = async (value?: boolean) => {
    const newPinnedState = value ?? !isPinned;
    setIsPinned(newPinnedState);
    setIsOpen(newPinnedState);

    // update user settings with the new state
    await updateUserSettings({
      ...userSettings,
      pinned_sidebar: newPinnedState,
    });
  };

  // const isAuthPageOrNoOrg = pathname?.includes("/auth") || !user?.joined_org;

  const isAuthPageOrNoOrg = pathname?.includes("/auth");

  if (isAuthPageOrNoOrg) return null;

  if (isUserLoading || isOrgLoading) return <div />;

  const avatarColor = userProfile?.name
    ? getAvatarColor(userProfile.name)
    : "bg-gray-500";

  const handleNewChat = () => {
    const newId = uuidv4();

    // // Reset states first
    // dispatch(resetToInitialChatState());
    dispatch(resetAnalytics());
    // dispatch(removeArtifacts());

    // // Set chat creation details
    // dispatch(
    //   setChatCreationDetails({
    //     initialMessage: "",
    //     chatTitle: "",
    //     attachments: [],
    //     web_search: false,
    //     files: [],
    //   })
    // );

    // Set active conversation
    // dispatch(setActiveConversation(newId));

    // Navigate after a short delay to ensure states are updated
    setTimeout(() => {
      if (pathname?.includes("/chat/analytics")) {
        router.push(`/chat/analytics/${newId}`);
      } else {
        dispatch(resetSelectedFiles());
        router.push(`/chat/${newId}`);
      }
    }, 200);
  };

  return (
    <div
      className={cn(
        "inset-y-0 left-0 z-40 flex flex-col justify-center",
        !isMobileOrTablet && isPinned ? "" : "fixed"
      )}
    >
      {/* Add a spacer div that pushes content when sidebar is pinned */}
      <div
        className={cn(
          "transition-all duration-300",
          !isMobileOrTablet && isPinned ? "w-64" : "w-0"
        )}
      />

      {/* Always visible Avatar and menu button when sidebar is closed */}
      {!isOpen && !isPinned && !isMobileOrTablet && (
        <div className="fixed bottom-4 left-4 z-50 flex flex-col gap-2 ">
          <Avatar
            className="w-10 h-10 cursor-pointer"
            onClick={() => setIsOpen(true)}
            onMouseEnter={handleMouseEnter}
          >
            {userProfile?.image_url ? (
              <AvatarImage
                src={userProfile.image_url}
                alt={userProfile.name || t("user")}
              />
            ) : (
              <AvatarFallback className={`text-white ${avatarColor}`}>
                {userProfile?.name
                  ? userProfile.name.charAt(0).toUpperCase()
                  : "U"}
              </AvatarFallback>
            )}
          </Avatar>
          <Button
            variant="ghost"
            size="icon"
            onMouseEnter={handleMouseEnter}
            onClick={() => setIsOpen(true)}
            // className="rounded-full bg-background border hover:bg-subtle-hover"
          >
            <PanelRight className="h-4 w-4 rotate-180" />
          </Button>
        </div>
      )}

      {isMobileOrTablet && !isOpen && !isPinned && (
        <div className="fixed top-9 left-4 -translate-y-1/2 z-50 cursor-pointer">
          <Button
            variant="ghost"
            size="icon"
            onMouseEnter={handleMouseEnter}
            onClick={() => setIsOpen(true)}
          >
            <PanelRight className="h-5 w-5 rotate-180" />
          </Button>
        </div>
      )}

      {/* 
      Show the new chat button if there are messages in the Analytics chat and the path is /chat/analytics 
      Currently, we are showing the new chat button on the /chat/analytics page, not on the /chat page.
      TO DO: To show the new chat button on the /chat page, we need to update the functionality of the chat page because the chat is being initialized when the user moves to the /chat page even if there is not message in the chat. Initializeing of chat creates a new conversation. In such situations, empty chat will be shown in the history.
      */}
      {!isOpen && !isPinned && pathname.includes("/chat/analytics") && (
        // check if there are messages in the chat
        <div
          className={cn(
            "fixed top-[4.5rem] left-4 -translate-y-1/2 z-50 cursor-pointer",
            isMobileOrTablet && !isOpen && !isPinned ? "top-[4.5rem]" : "top-9"
          )}
        >
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={handleNewChat}>
                  <CirclePlus className="h-5 w-5 rotate-180" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={8}>
                <p>
                  {pathname?.includes("/chat/analytics")
                    ? t("newAnalyticsChat")
                    : t("newChat")}
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      )}

      {/* Remove or comment out the old mobile/tablet toggle buttons */}
      {/* {isMobileOrTablet && !isOpen && !isPinned && (
        <div className="fixed top-9 left-4 -translate-y-1/2 z-50 cursor-pointer">
          ...
        </div>
      )} */}

      <ShadcnSidebar
        className={cn(
          "fixed left-0 z-40 bg-background",
          "w-64 transition-transform duration-300",
          !isOpen && !isPinned && "-translate-x-full",
          isPinned
            ? "shadow-none h-screen rounded-none border-r"
            : // Added the pathname condition to behave normally on desktop
              isMobileOrTablet && window.innerWidth < 1024
              ? "top-5 bottom-5 h-auto py-safe shadow-md rounded-r-3xl border"
              : "top-1/2 -translate-y-1/2 shadow-md h-[98vh] rounded-r-3xl border"
        )}
        onMouseLeave={handleMouseLeave}
        style={
          // Added the pathname condition to behave normally on desktop
          isMobileOrTablet && window.innerWidth < 1024
            ? {
                paddingTop: "max(env(safe-area-inset-top), 1rem)",
                paddingBottom: "max(env(safe-area-inset-bottom), 1rem)",
              }
            : {}
        }
      >
        <SidebarHeader className="flex flex-row justify-between">
          {/* <div className="w-20 h-20"> */}
          {isMobileOrTablet ? (
            <MobileLogo height={16} />
          ) : (
            <DesktopLogo height={20} width={24} />
          )}
          {/* </div> */}
          <div className="flex items-center">
            {/* Add pin button */}
            {!isMobileOrTablet && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => togglePin()}
                className={cn(
                  "hover:bg-subtle-hover group/pin ",
                  isPinned && "bg-subtle-hover"
                )}
              >
                <Pin
                  className={cn(
                    "w-4 h-4 group-hover/pin:scale-[1.1] transition-all",
                    isPinned && "rotate-45"
                  )}
                  fill={isPinned ? "currentColor" : "none"}
                />
              </Button>
            )}
            {/* Only show close button if not pinned */}
            {!isPinned && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsOpen(false)}
                className="hover:bg-subtle-hover group/close"
              >
                <ChevronLeft className="w-5 h-5 group-hover/close:scale-[1.1] transition-all" />
              </Button>
            )}
          </div>
        </SidebarHeader>

        <SidebarContent>
          <nav className="flex-grow">
            <ul className="p-4 space-y-2">
              {menuItems.map((item, index) => (
                <li key={index} className="group">
                  <Button
                    variant="ghost"
                    className={cn(
                      "w-full justify-start overflow-hidden",
                      "hover:bg-accent dark:text-subtle-fg border",
                      pathname === item.path
                        ? "text-primary font-bold"
                        : "border-transparent"
                    )}
                    onClick={() => {
                      if (item.path === "/home") {
                        const newChatId = uuidv4();
                        dispatch(resetToInitialChatState());
                        dispatch(removeArtifacts());
                        dispatch(clearSuggestions());
                        dispatch(resetAnalytics());
                        router.push(`/chat/analytics/${newChatId}`);
                      } else {
                        router.push(item.path);
                      }
                      if (isMobileOrTablet) setIsOpen(false);
                    }}
                  >
                    <item.icon className="w-5 h-5 mr-2" />
                    <div className="text-left overflow-hidden">
                      <div
                        className={cn(
                          "relative ",
                          item.label.length > 18 &&
                            "group-hover:animate-marquee"
                        )}
                      >
                        <span className="inline-block whitespace-nowrap">
                          {item.label}
                        </span>
                      </div>
                    </div>
                  </Button>
                </li>
              ))}
            </ul>
          </nav>
        </SidebarContent>

        <SidebarFooter>
          <div className="flex items-center w-full">
            <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
              <PopoverTrigger asChild>
                <div
                  // variant="ghost"
                  className="flex-2 justify-between hover:bg-subtle-hover dark:text-subtle-fg flex items-center gap-2 truncate cursor-pointer font-medium text-sm mb-1 line-clamp-1 text-foreground px-4 w-full"
                >
                  <div className="flex items-center gap-2 w-[60%]">
                    <Avatar className="w-8 h-8 ">
                      {userProfile?.image_url ? (
                        <AvatarImage
                          src={userProfile.image_url}
                          alt={userProfile.name || t("user")}
                        />
                      ) : (
                        <AvatarFallback className={`text-white ${avatarColor}`}>
                          {userProfile?.name
                            ? userProfile.name.charAt(0).toUpperCase()
                            : "U"}
                        </AvatarFallback>
                      )}
                    </Avatar>
                    <span className="truncate flex-1 text-left">
                      {userProfile?.name || t("user")}
                    </span>
                  </div>
                  <span className="flex items-center gap-1">
                    <Ellipsis className="w-4 h-4 ml-auto mr-1 mt-[3px]" />
                    {/* Theme toggle outside of Popover trigger */}
                    <ThemeSelector simplified />
                  </span>
                </div>
              </PopoverTrigger>
              <PopoverContent
                className="w-60 p-4 overflow-hidden ml-0 rounded-md"
                sideOffset={5}
                align="end"
              >
                <div className="flex flex-col space-y-4">
                  {/* User info */}
                  <div className="flex items-center space-x-4">
                    <Avatar className="w-10 h-10">
                      {userProfile?.image_url ? (
                        <AvatarImage
                          src={userProfile.image_url}
                          alt={userProfile.name || t("user")}
                        />
                      ) : (
                        <AvatarFallback className={`text-white ${avatarColor}`}>
                          {userProfile?.name
                            ? userProfile.name.charAt(0).toUpperCase()
                            : "U"}
                        </AvatarFallback>
                      )}
                    </Avatar>
                    <div className="flex flex-col  truncate">
                      <p className="text-sm font-medium">
                        {userProfile?.name || t("unnamedUser")}
                      </p>
                      <p className="text-xs text-muted-foreground text-wrap">
                        {userProfile?.email}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {organization?.name || t("noOrganization")}
                      </p>
                    </div>
                  </div>

                  {/* Credits info - remove px-4 since PopoverContent already has padding */}

                  <div className="p-2 rounded-md shadow-inner border">
                    <RenderCreditsInfo
                      popoverOpen={popoverOpen}
                      setPopoverOpen={setPopoverOpen}
                      isOpen={isOpen}
                      setIsOpen={setIsOpen}
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col space-y-2">
                    <Button
                      variant="ghost"
                      className={cn(
                        "justify-start w-full hover:bg-accent border",
                        pathname === "/settings/profile"
                          ? "text-primary font-bold"
                          : "border-transparent"
                      )}
                      onClick={() => {
                        setPopoverOpen(false);
                        setIsOpen(false);
                        router.push("/settings/profile");
                      }}
                    >
                      <Settings className="w-4 h-4 mr-2" />
                      {t("settings")}
                    </Button>

                    <Button
                      variant="ghost"
                      className="justify-start w-full text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => {
                        setPopoverOpen(false);
                        setIsOpen(false);
                        signOut({ callbackUrl: "/auth" });
                      }}
                    >
                      <LogOut className="w-4 h-4 mr-2" />
                      {t("logout")}
                    </Button>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </SidebarFooter>
      </ShadcnSidebar>
    </div>
  );
}
