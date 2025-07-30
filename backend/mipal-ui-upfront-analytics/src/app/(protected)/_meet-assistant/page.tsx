"use client";
import React from "react";
import GoogleCalendarIcon from "@/assets/svg/GoogleCalendarIcon";
import MicrosoftIcon from "@/assets/svg/MicrosoftIcon";
import {
  useGetSpecificIntegrationQuery,
  INTEGRATION_TYPES,
} from "@/store/services/integrationApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

const Page = () => {
  const { data: googleIntegration, isLoading: googleIntegrationLoading } =
    useGetSpecificIntegrationQuery(INTEGRATION_TYPES.GOOGLE_CALENDAR);
  const { data: microsoftIntegration, isLoading: microsoftIntegrationLoading } =
    useGetSpecificIntegrationQuery(INTEGRATION_TYPES.MICROSOFT_CALENDER);

  const hasGoogleIntegration = googleIntegration?.is_active;
  const hasMicrosoftIntegration = microsoftIntegration?.is_active;

  const handleConnect = async () => {
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || window.location.origin;
    window.location.href = `${appUrl}/integration`;
  };

  const calendarButtons = (
    <>
      <button
        onClick={() => handleConnect()}
        disabled={hasGoogleIntegration}
        className={`flex items-center justify-center px-4 py-2.5 gap-2 bg-card border border-border text-card-foreground rounded-lg transition-all shadow-sm
          ${
            hasGoogleIntegration || googleIntegrationLoading
              ? "opacity-50 cursor-not-allowed"
              : "hover:bg-secondary hover:shadow"
          }`}
      >
        {googleIntegrationLoading && <LoadingSpinner size={16} />}
        <GoogleCalendarIcon className="w-5 h-5" />
        {!googleIntegrationLoading
          ? hasGoogleIntegration
            ? "Connected Google Calendar"
            : "Connect Google Calendar"
          : "Checking Google Calendar"}
      </button>
      <button
        onClick={() => handleConnect()}
        disabled={hasMicrosoftIntegration}
        className={`flex items-center justify-center px-4 py-2.5 gap-2 bg-card border border-border text-card-foreground rounded-lg transition-all shadow-sm
          ${
            hasMicrosoftIntegration || microsoftIntegrationLoading
              ? "opacity-50 cursor-not-allowed"
              : "hover:bg-secondary hover:shadow"
          }`}
      >
        {microsoftIntegrationLoading && <LoadingSpinner size={16} />}
        <MicrosoftIcon className="w-5 h-5" />
        {!microsoftIntegrationLoading
          ? hasMicrosoftIntegration
            ? "Connected"
            : "Connect"
          : "Checking"}
        {" Microsoft Calendar"}
      </button>
    </>
  );

  return (
    <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8 py-8">
      {/* Calendar Integration Section */}
      <PageHeader
        title="Connect Calendar"
        description="Integrate your preferred calendar service"
        className="mb-8"
        actions={calendarButtons}
      />

      {/* Meetings Section */}
      <PageHeader
        title="All Meetings"
        description="View and manage your upcoming meetings"
        className="mb-8"
        actions={
          <button className="flex items-center justify-center px-4 py-2.5 bg-card border border-border text-card-foreground hover:bg-secondary rounded-lg transition-all shadow-sm hover:shadow">
            <svg
              className="w-5 h-5 mr-2"
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
            Sync Meetings
          </button>
        }
      />

      {/* Meeting Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((_, index) => (
          <div
            key={index}
            className="bg-card border border-border rounded-xl p-6 hover:shadow-md transition-all group active:shadow-none hover:scale-[101%] active:scale-100 cursor-pointer"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-medium text-card-foreground group-hover:text-primary transition-colors flex flex-row items-center gap-2">
                  Meeting {index + 1} <GoogleCalendarIcon className="w-5 h-5" />
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Today, 2:00 PM - 3:00 PM
                </p>
              </div>
              <span className="bg-primary/10 text-primary text-xs font-medium px-2.5 py-1 rounded-full">
                Upcoming
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex -space-x-3">
                {[1, 2, 3].map((_, i) => (
                  <div
                    key={i}
                    className="w-8 h-8 rounded-full bg-muted border-2 border-background ring-2 ring-border"
                  />
                ))}
              </div>
              <span className="text-sm text-muted-foreground">+2 more</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Page;
