"use client";

import { ThemeSelector } from "@/components/ThemeSelector";
// import { useSession } from 'next-auth/react';
import Image from "next/image";
import { useState, useEffect } from "react";
import {
  useGetUserProfileQuery,
  useGetUserSettingsQuery,
  UserSettings,
  useUpdateUserProfileMutation,
  useUpdateUserSettingsMutation,
} from "@/store/services/userApi";
import { Pencil, X, Upload, Loader2 } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Save } from "lucide-react";
import { FormField } from "@/components/FormField";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { useUser } from "@/store/hooks/useUser";
import { signOut, useSession } from "next-auth/react";
import TokenSection from "@/components/pricing/TokenSection";
import { jwtDecode } from "jwt-decode";
import { redirect } from "next/navigation";
import CreateOrganizationForm from "@/components/organization/CreateOrganizationForm";
import OrganizationAdminView from "@/components/organization/OrganizationAdminView";
import { useTranslations } from "next-intl";
import { languages } from "@/constants";

interface DecodedToken {
  user_id: string;
  joined_org: boolean;
  role: string;
  org_id?: string;
  exp: number;
}

export default function ProfilePage() {
  // const { data: session } = useSession();
  const t = useTranslations("settings.profile");
  const tOrg = useTranslations("settings.organization.create");
  const { data: userProfile, refetch: refetchProfile } = useGetUserProfileQuery(
    {}
  );
  const { data: userSettings, refetch: refetchSettings } =
    useGetUserSettingsQuery({});

  const [updateProfile] = useUpdateUserProfileMutation();
  const [updateUserSettings] = useUpdateUserSettingsMutation();
  const { user } = useUser();

  // Edit states
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editedName, setEditedName] = useState(userProfile?.name || "");
  const [editedPhone, setEditedPhone] = useState(userProfile?.phone || "");
  const [editedPosition, setEditedPosition] = useState(
    userProfile?.job_role || ""
  );
  const [editedImage, setEditedImage] = useState<string | null>(null);
  const [isEditingOtherPreferences, setIsEditingOtherPreferences] =
    useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  // Add state for settings
  const [editedSettings, setEditedSettings] = useState({
    user_id: userProfile?.id || "",
    theme: userSettings?.theme || "dark",
    language: userSettings?.language || "en",
    timezone: userSettings?.timezone || "UTC",
    date_format: userSettings?.date_format || "DD/MM/YYYY",
    subscription_plan: userSettings?.subscription_plan || "free",
    pinned_sidebar: userSettings?.pinned_sidebar || false,
  } as UserSettings);

  // Update settings when userSettings data is fetched
  useEffect(() => {
    if (userSettings) {
      setEditedSettings({
        user_id: userProfile?.id || "",
        theme: userSettings.theme || "dark",
        language: userSettings.language || "en",
        timezone: userSettings.timezone || "UTC",
        date_format: userSettings.date_format || "DD/MM/YYYY",
        subscription_plan: userSettings.subscription_plan || "free",
        pinned_sidebar: userSettings.pinned_sidebar || false,
      });
    }
  }, [userSettings]);

  // Handle image upload
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file size (2MB = 2 * 1024 * 1024 bytes)
    const maxSize = 2 * 1024 * 1024; // 2MB

    if (file.size > maxSize) {
      toast({
        variant: "destructive",
        title: t("error"),
        description: t("imageSizeError"),
      });
      e.target.value = ""; // Reset the input
      return;
    }

    // Check file type
    const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      toast({
        variant: "destructive",
        title: t("error"),
        description: t("imageTypeFormatError"),
      });
      e.target.value = ""; // Reset the input
      return;
    }

    try {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        setEditedImage(base64String);
      };
      reader.readAsDataURL(file);
    } catch (error) {
      console.error("Failed to process image:", error);
      toast({
        variant: "destructive",
        title: t("error"),
        description: t("failedToProcessImage"),
      });
      e.target.value = ""; // Reset the input on error
    }
  };

  // Handle profile update
  const handleSaveChanges = async () => {
    setIsSaving(true);
    try {
      await updateProfile({
        name: editedName,
        phone: editedPhone,
        job_role: editedPosition,
        image_url: editedImage || userProfile?.image_url,
      }).unwrap();
      refetchProfile();
      setIsEditing(false);
      toast({
        title: t("success"),
        description: t("profileUpdatedSuccessfully"),
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: t("error"),
        description: t("failedToUpdateProfile"),
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Handle settings update
  const handleSaveSettings = async (settings?: UserSettings) => {
    setIsSavingSettings(true);
    try {
      await updateUserSettings(settings || editedSettings).unwrap();
      refetchSettings();
      setIsEditingOtherPreferences(false);

      // If language was changed, refresh the page
      if (settings?.language !== userSettings?.language) {
        window.location.reload();
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: t("error"),
        description: t("failedToUpdateProfile"),
      });
      console.error("Failed to update profile:", error);
    } finally {
      setIsSavingSettings(false);
    }
  };

  const { data: session } = useSession();

  let hasJoinedOrg = false;
  let userId = "";
  try {
    const decodedToken = jwtDecode(
      session?.user?.access_token || ""
    ) as DecodedToken;
    hasJoinedOrg = decodedToken.joined_org;
    userId = decodedToken.user_id;
  } catch (error) {
    console.error("Error decoding token:", error);
    redirect("/auth"); // Redirect to auth if token is invalid
  }

  if (!hasJoinedOrg) {
    return (
      <>
        <h1 className="text-2xl font-bold mb-6">
          {tOrg("createOrganization")}
        </h1>
        <CreateOrganizationForm userId={userId} />
      </>
    );
  }

  const maxWidthOfCards = "w-[450px]";

  return (
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">
      <div className="flex flex-row flex-wrap gap-4 justify-start px-auto">
        <TokenSection maxWidthOfCards={maxWidthOfCards} />

        {/* Theme Card */}
        <Card className={cn("rounded-2xl h-fit", maxWidthOfCards)}>
          <CardHeader>
            <CardTitle>{t("themeSettings")}</CardTitle>
            <CardDescription>{t("changeThemeToYourLiking")}</CardDescription>
          </CardHeader>
          <CardContent>
            <ThemeSelector />
          </CardContent>
        </Card>

        <Card className={cn("h-fit rounded-2xl relative", maxWidthOfCards)}>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsEditing(!isEditing)}
            className="absolute top-3 right-3"
          >
            {isEditing ? (
              <X className="w-5 h-5" />
            ) : (
              <Pencil className="w-5 h-5" />
            )}
          </Button>
          <CardHeader>
            <CardTitle>{t("profileDetails")}</CardTitle>
            <CardDescription>
              {t("changeYourProfileDetailsToYourLiking")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4 flex flex-col gap-4">
              {/* Profile Image Upload */}
              <div className="col-span-1 md:col-span-1 space-y-2 flex flex-col items-center row-span-1">
                <label htmlFor="profile-image" className="text-sm font-medium">
                  {t("profileImage")}
                </label>
                <div className="flex flex-col items-center gap-4">
                  <div
                    className={cn(
                      "relative w-24 h-24 overflow-hidden rounded-full",
                      isEditing && "border cursor-pointer"
                    )}
                    onClick={() =>
                      isEditing &&
                      document.getElementById("profile-upload")?.click()
                    }
                  >
                    {editedImage || userProfile?.image_url ? (
                      <Image
                        src={editedImage || userProfile?.image_url || ""}
                        alt="Profile"
                        fill
                        className="object-cover"
                      />
                    ) : (
                      <div className="flex items-center justify-center w-full h-full bg-gray-200 dark:bg-gray-800">
                        <span className="text-3xl text-gray-500 dark:text-gray-400">
                          {userProfile?.name?.[0]?.toUpperCase() || "?"}
                        </span>
                      </div>
                    )}
                  </div>
                  <input
                    id="profile-upload"
                    type="file"
                    className="hidden"
                    accept="image/jpeg,image/png,image/gif,image/webp"
                    onChange={handleImageUpload}
                  />
                  {/* {isEditing && (editedImage || userProfile?.image_url) && (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleRemoveImage}
                  >
                    Remove Image
                  </Button>
                )} */}
                </div>
              </div>

              {/* Profile Details */}
              <div className="flex flex-col gap-4">
                <FormField
                  label={t("name")}
                  id="name"
                  disabled={!isEditing}
                  value={editedName}
                  onChange={(e) => setEditedName(e)}
                  placeholder={t("name")}
                />

                {/* Email */}
                <FormField
                  label={t("email")}
                  id="email"
                  disabled={true}
                  value={userProfile?.email || ""}
                  placeholder={t("email")}
                />

                {/* Phone */}
                <FormField
                  label={t("phone")}
                  id="phone"
                  disabled={!isEditing}
                  value={editedPhone}
                  onChange={(value) => setEditedPhone(value)}
                  placeholder={t("phone")}
                  type="phone"
                />

                {/* Position */}
                <FormField
                  label={t("position")}
                  id="position"
                  disabled={!isEditing}
                  value={editedPosition}
                  onChange={(value) => setEditedPosition(value)}
                  placeholder={t("position")}
                />
              </div>
            </div>

            {/* Center buttons on mobile, right-aligned on desktop */}
            {isEditing && (
              <div className="flex flex-col sm:flex-row justify-center sm:justify-end space-y-2 sm:space-y-0 sm:space-x-2">
                <Button
                  variant="outline"
                  onClick={() => setIsEditing(false)}
                  className="w-full sm:w-auto"
                  disabled={isSaving}
                >
                  {t("cancel")}
                </Button>
                <Button
                  onClick={handleSaveChanges}
                  className="w-full sm:w-auto"
                  disabled={isSaving}
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      {t("saving")}
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      {t("saveChanges")}
                    </>
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Organization Admin View */}
        <OrganizationAdminView
          userProfile={userProfile}
          maxWidthOfCards={maxWidthOfCards}
        />

        {/* Settings Card */}
        <Card className={cn("h-fit rounded-2xl relative", maxWidthOfCards)}>
          <Button
            variant="ghost"
            size="icon"
            onClick={() =>
              setIsEditingOtherPreferences(!isEditingOtherPreferences)
            }
            className="absolute top-3 right-3"
          >
            {isEditingOtherPreferences ? (
              <X className="w-5 h-5" />
            ) : (
              <Pencil className="w-5 h-5" />
            )}
          </Button>
          <CardHeader>
            <CardTitle>{t("otherPreferences")}</CardTitle>
            <CardDescription>
              {t("changeYourOtherPreferencesToYourLiking")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4 ">
              <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
                <FormField
                  label={t("language")}
                  id="language"
                  type="select"
                  disabled={!isEditingOtherPreferences}
                  value={editedSettings.language}
                  onChange={(value) =>
                    setEditedSettings((prev) => ({ ...prev, language: value }))
                  }
                  options={languages}
                />

                <FormField
                  label={t("dateFormat")}
                  id="date_format"
                  type="select"
                  disabled={!isEditingOtherPreferences}
                  value={editedSettings.date_format}
                  onChange={(value) =>
                    setEditedSettings((prev) => ({
                      ...prev,
                      date_format: value,
                    }))
                  }
                  options={[
                    { value: "DD/MM/YYYY", label: "DD/MM/YYYY" },
                    { value: "MM/DD/YYYY", label: "MM/DD/YYYY" },
                    { value: "YYYY-MM-DD", label: "YYYY-MM-DD" },
                  ]}
                />

                <FormField
                  label={t("timezone")}
                  id="timezone"
                  type="select"
                  disabled={!isEditingOtherPreferences}
                  value={editedSettings.timezone}
                  onChange={(value) =>
                    setEditedSettings((prev) => ({ ...prev, timezone: value }))
                  }
                  options={[
                    { value: "UTC", label: "UTC" },
                    { value: "EST", label: "EST" },
                    { value: "PST", label: "PST" },
                  ]}
                />
              </div>

              {isEditingOtherPreferences && (
                <div className="flex flex-col sm:flex-row justify-center sm:justify-end space-y-2 sm:space-y-0 sm:space-x-2">
                  <Button
                    variant="outline"
                    onClick={() => setIsEditingOtherPreferences(false)}
                    className="w-full sm:w-auto"
                    disabled={isSavingSettings}
                  >
                    {t("cancel")}
                  </Button>
                  <Button
                    onClick={() => handleSaveSettings()}
                    className="w-full sm:w-auto"
                    disabled={isSavingSettings}
                  >
                    {isSavingSettings ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        {t("saving")}
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        {t("saveChanges")}
                      </>
                    )}
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Sign Out Card - Only shown when user hasn't joined an org */}
        {!user?.joined_org && (
          <Card>
            <CardHeader>
              <CardTitle>{t("accountActions")}</CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                variant="destructive"
                onClick={() => signOut()}
                className="w-full sm:w-auto"
              >
                {t("signOut")}
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
