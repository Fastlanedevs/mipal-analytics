"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Pencil, Save, X, Upload, Loader2 } from "lucide-react";
import {
  useGetOrganizationQuery,
  useUpdateOrganizationMutation,
  useInviteUserMutation,
  useGetJoinRequestsQuery,
  useRespondToJoinRequestMutation,
  useUploadOrganizationLogoMutation,
} from "@/store/services/organizationApi";
import { useToast } from "@/hooks/use-toast";
import LoadingScreen from "../common/LoadingScreen";
import { useGetUserProfileQuery, UserProfile } from "@/store/services/userApi";
import { FormField } from "@/components/FormField";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export default function OrganizationAdminView({
  userProfile,
  maxWidthOfCards,
}: {
  userProfile: UserProfile | undefined;
  maxWidthOfCards: string;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const { toast } = useToast();
  const t = useTranslations("settings.organization.adminView");
  const [uploadOrganizationLogo] = useUploadOrganizationLogoMutation();

  // const { data: userProfile } = useGetUserProfileQuery({});
  const { data: organization, isLoading } = useGetOrganizationQuery(
    userProfile?.user_id ?? "skip",
    { skip: !userProfile?.user_id }
  );

  const { data: joinRequests } = useGetJoinRequestsQuery(
    organization?.id ?? "skip",
    {
      skip: !organization?.id,
    }
  );

  const [updateOrg, { isLoading: isUpdatingOrg }] =
    useUpdateOrganizationMutation();
  const [inviteUser] = useInviteUserMutation();
  const [respondToJoinRequest] = useRespondToJoinRequestMutation();

  const [orgData, setOrgData] = useState({
    name: organization?.name || "",
    address: organization?.address || "",
    phone: organization?.phone || "",
    website: organization?.website || "",
    industry: organization?.industry || "",
    size: organization?.size || "",
    logo: organization?.logo || "",
  });

  const [inviteData, setInviteData] = useState({
    email: "",
    role: "MEMBER",
  });

  useEffect(() => {
    if (organization) {
      setOrgData({
        name: organization.name,
        address: organization.address || "",
        phone: organization.phone || "",
        website: organization.website || "",
        industry: organization.industry || "",
        size: organization.size || "",
        logo: organization.logo || "",
      });
    }
  }, [organization]);

  const handleSave = async () => {
    try {
      await updateOrg({
        orgId: organization?.id ?? "",
        data: orgData,
      }).unwrap();
      setIsEditing(false);
      toast({
        title: t("success"),
        description: t("organizationUpdatedSuccessfully"),
      });
    } catch (error) {
      toast({
        title: t("error"),
        description: t("failedToUpdateOrganization"),
        variant: "destructive",
      });
    }
  };

  const handleInvite = async () => {
    if (!inviteData.email || !organization?.id) return;

    // Check if email domain matches organization domain
    const orgDomain = organization.website?.split(".")[1] || "";
    const inviteeDomain = inviteData.email.split("@")[1];

    if (orgDomain && orgDomain !== inviteeDomain) {
      toast({
        title: t("error"),
        description: t("invitedUserMustBeFromTheSameDomain"),
        variant: "destructive",
      });
      return;
    }

    try {
      await inviteUser({
        organizationId: organization.id,
        email: inviteData.email,
        role: inviteData.role,
      }).unwrap();

      setShowInviteForm(false);
      setInviteData({ email: "", role: "MEMBER" });
      toast({
        title: t("success"),
        description: t("invitationSentSuccessfully"),
      });
    } catch (error) {
      toast({
        title: t("error"),
        description: t("failedToSendInvitation"),
        variant: "destructive",
      });
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file size (2MB = 2 * 1024 * 1024 bytes)
    const maxSize = 2 * 1024 * 1024; // 2MB

    if (file.size > maxSize) {
      toast({
        title: t("error"),
        description: t("imageSizeError"),
        variant: "destructive",
      });
      e.target.value = ""; // Reset the input
      return;
    }

    // Check file type
    const allowedTypes = [
      "image/jpeg",
      "image/jpg",
      "image/png",
      "image/gif",
      "image/webp",
    ];
    if (!allowedTypes.includes(file.type)) {
      toast({
        title: t("error"),
        description: t("imageTypeFormatError"),
        variant: "destructive",
      });
      e.target.value = ""; // Reset the input
      return;
    }

    try {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        setOrgData((prev) => ({
          ...prev,
          logo: base64String,
        }));
      };
      reader.readAsDataURL(file);
    } catch (error) {
      console.error("Failed to process image:", error);
      toast({
        title: t("error"),
        description: t("failedToUploadLogo"),
        variant: "destructive",
      });
      e.target.value = ""; // Reset the input on error
    }
  };

  if (isLoading || !userProfile) {
    return <LoadingScreen />;
  }

  return (
    <Card className={cn("h-fit relative", maxWidthOfCards)}>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsEditing(!isEditing)}
        className="absolute top-3 right-3"
      >
        {isEditing ? <X className="w-5 h-5" /> : <Pencil className="w-5 h-5" />}
      </Button>
      <CardHeader>
        <CardTitle>{t("organizationDetails")}</CardTitle>
        <CardDescription>{t("manageOrganizationDetails")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-4">
          <div className="flex flex-col gap-4">
            {/* Organization Name */}
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">
                {t("organizationName")}
              </label>
              <Input
                id="name"
                disabled={!isEditing}
                value={orgData.name}
                onChange={(e) =>
                  setOrgData({ ...orgData, name: e.target.value })
                }
                placeholder={t("organizationName")}
              />
            </div>

            {/* Website */}
            <div className="space-y-2">
              <label htmlFor="website" className="text-sm font-medium">
                {t("website")}
              </label>
              <Input
                id="website"
                disabled={!isEditing}
                value={orgData.website}
                onChange={(e) =>
                  setOrgData({ ...orgData, website: e.target.value })
                }
                placeholder={t("websiteURL")}
              />
            </div>

            {/* Address */}
            <div className="space-y-2">
              <label htmlFor="address" className="text-sm font-medium">
                {t("address")}
              </label>
              <Input
                id="address"
                disabled={!isEditing}
                value={orgData.address}
                onChange={(e) =>
                  setOrgData({ ...orgData, address: e.target.value })
                }
                placeholder={t("organizationAddress")}
              />
            </div>

            {/* Phone */}
            <div className="space-y-2">
              <FormField
                label={t("phone")}
                id="phone"
                disabled={!isEditing}
                value={orgData.phone}
                onChange={(value) => setOrgData({ ...orgData, phone: value })}
                placeholder={t("phoneNumber")}
                type="phone"
              />
            </div>

            {/* Industry */}
            {/* <div className="space-y-2">
                <label htmlFor="industry" className="text-sm font-medium">Industry</label>
                <Select
                  disabled={!isEditing}
                  value={orgData.industry}
                  onValueChange={(value) => setOrgData({ ...orgData, industry: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Industry" />
                  </SelectTrigger>
                  <SelectContent>
                    {industryOptions.map((industry) => (
                      <SelectItem key={industry.value} value={industry.value}>
                        {industry.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div> */}

            {/* Size */}
            {/* <div className="space-y-2">
                <label htmlFor="size" className="text-sm font-medium">Company Size</label>
                <Select
                  disabled={!isEditing}
                  value={orgData.size}
                  onValueChange={(value) => setOrgData({ ...orgData, size: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Size" />
                  </SelectTrigger>
                  <SelectContent>
                    {sizeOptions.map((size) => (
                      <SelectItem key={size.value} value={size.value}>
                        {size.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div> */}

            {/* Logo Upload */}
            <div className="space-y-2">
              <label htmlFor="logo" className="text-sm font-medium">
                {t("organizationLogo")}
              </label>
              <div className="flex items-center space-x-4">
                {orgData.logo && (
                  <img
                    src={orgData.logo}
                    alt={t("organizationLogo")}
                    className="object-cover w-16 h-16 rounded"
                  />
                )}
                {isEditing && (
                  <Button
                    variant="outline"
                    onClick={() =>
                      document.getElementById("logo-upload")?.click()
                    }
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    {t("uploadLogo")}
                  </Button>
                )}
                <input
                  id="logo-upload"
                  type="file"
                  className="hidden"
                  accept="image/*"
                  onChange={handleLogoUpload}
                />
              </div>
            </div>
          </div>
        </div>

        {isEditing && (
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => setIsEditing(false)}>
              {t("cancel")}
            </Button>
            <Button onClick={handleSave} disabled={isUpdatingOrg}>
              {isUpdatingOrg ? (
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
  );
}
