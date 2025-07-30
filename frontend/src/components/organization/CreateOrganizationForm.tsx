"use client";

import { useState, useEffect } from "react";
import { useAppSelector } from "@/store/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Upload, Search } from "lucide-react";
import {
  useCreateOrganizationMutation,
  useSearchOrganizationsQuery,
  useJoinOrganizationRequestMutation,
  useUploadOrganizationLogoMutation,
  Organization,
} from "@/store/services/organizationApi";
import { toast, useToast } from "@/hooks/use-toast";
import { useSession, signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useGetDomainOrganizationQuery } from "@/store/services/organizationApi";
import { FormField } from "@/components/FormField";
import { useTranslations } from "next-intl";

interface CreateOrganizationFormProps {
  userId: string;
}

export default function CreateOrganizationForm({
  userId,
}: CreateOrganizationFormProps) {
  const router = useRouter();
  const t = useTranslations("settings.organization.create");
  const { toast } = useToast();
  const [createOrg, { isLoading: isCreating }] =
    useCreateOrganizationMutation();
  const [joinOrgRequest, { isLoading: isJoining }] =
    useJoinOrganizationRequestMutation();
  const [uploadLogo] = useUploadOrganizationLogoMutation();

  const [orgData, setOrgData] = useState({
    name: "",
    address: "",
    phone: "",
    website: "",
    logo: "",
  });

  const [joinData, setJoinData] = useState({
    domain: "",
    selectedOrgId: "",
  });

  const [searchTerm, setSearchTerm] = useState("");
  const { data: searchResults = [] } = useSearchOrganizationsQuery(searchTerm, {
    skip: !searchTerm, // Skip the query if there's no search term
  });

  const { data: domainOrg, isLoading } = useGetDomainOrganizationQuery();
  const [showCreateForm, setShowCreateForm] = useState(false);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  const handleCreate = async () => {
    if (!orgData.name) {
      toast({
        title: t("validationError"),
        description: t("organizationNameRequired"),
        variant: "destructive",
      });
      return;
    }

    try {
      const createData = {
        name: orgData.name,
        ...(orgData.address && { address: orgData.address }),
        ...(orgData.phone && { phone: orgData.phone }),
        ...(orgData.website && { website: orgData.website }),
        ...(orgData.logo && { logo: orgData.logo }),
      };

      const result = await createOrg(createData).unwrap();

      if (!result.access_token || !result.refresh_token) {
        console.error("Missing tokens in response:", result);
        throw new Error(t("invalidResponseFromServer"));
      }

      const signInResult = await signIn("credentials", {
        access_token: result.access_token,
        refresh_token: result.refresh_token,
        redirect: false,
        callbackUrl: "/",
      });

      if (signInResult?.error) {
        throw new Error(signInResult.error);
      }

      toast({
        title: t("success"),
        description: t("organizationCreatedSuccessfully"),
      });

      // Force a hard navigation to the home page
      if (result) {
        window.location.href = "/";
      }
    } catch (err: any) {
      console.error("Organization creation error:", err);
      toast({
        title: t("error"),
        description:
          err.data?.message || err.message || t("failedToCreateOrganization"),
        variant: "destructive",
      });
    }
  };

  const handleSearch = () => {
    if (!joinData.domain) {
      toast({
        title: t("validationError"),
        description: t("pleaseEnterADomainToSearch"),
        variant: "destructive",
      });
      return;
    }

    setSearchTerm(joinData.domain);
  };

  const handleJoinRequest = async (orgId: string) => {
    try {
      // Show loading state
      toast({
        title: t("processing"),
        description: t("sendingJoinRequest"),
      });

      const result = await joinOrgRequest({
        orgId: orgId,
      }).unwrap();

      // Check if we got new tokens in the response
      if (result?.access_token && result?.refresh_token) {
        const signInResult = await signIn("credentials", {
          access_token: result.access_token,
          refresh_token: result.refresh_token,
          redirect: false,
          callbackUrl: "/",
        });

        if (signInResult?.error) {
          throw new Error(signInResult.error);
        }
      }

      toast({
        title: t("success"),
        description: t("successfullyJoinedOrganization"),
      });

      await new Promise((resolve) => setTimeout(resolve, 1000));

      router.push("/");
      router.refresh();
    } catch (err: any) {
      console.error("Join request failed with error:", err);
      console.error("Error details:", {
        data: err.data,
        message: err.message,
        status: err.status,
      });
      toast({
        title: t("error"),
        description:
          err.data?.message || err.message || t("failedToJoinOrganization"),
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
    const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
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
        setOrgData({
          ...orgData,
          logo: base64String,
        });
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

  return (
    <div className="container p-6 mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>{t("organizationManagement")}</CardTitle>
        </CardHeader>
        <CardContent>
          {domainOrg && !showCreateForm ? (
            <div className="space-y-4">
              <div className="p-4 border dark:border-primary/50 rounded-lg">
                <h3 className="text-lg font-medium">
                  {t("existingOrganizationFound")}
                </h3>
                <p className="mt-2">
                  {t("existingOrganizationFoundDescription")}
                </p>
                <div className="mt-4">
                  <strong>{t("name")}:</strong> {domainOrg.name}
                  {domainOrg.website && (
                    <div>
                      <strong>{t("website")}:</strong> {domainOrg.website}
                    </div>
                  )}
                </div>
                <div className="mt-4 flex justify-center">
                  <Button
                    variant="outline"
                    // className=" mt-4"
                    onClick={() => {
                      handleJoinRequest(domainOrg.id);
                    }}
                    disabled={isJoining}
                  >
                    {isJoining ? (
                      <>
                        <svg
                          className="w-5 h-5 mr-3 -ml-1 text-white animate-spin"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          />
                        </svg>
                        {t("joining")}
                      </>
                    ) : (
                      <>
                        {t("requestToJoin")} {domainOrg.name}
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <div className="text-center">
                <p className="mb-2 text-sm text-gray-500">or</p>
                <Button
                  variant="outline"
                  onClick={() => setShowCreateForm(true)}
                >
                  {t("createNewOrganization")}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">
                  {t("organizationName")}*
                </label>
                <Input
                  value={orgData.name}
                  onChange={(e) =>
                    setOrgData({ ...orgData, name: e.target.value })
                  }
                  placeholder={t("enterOrganizationName")}
                  className="mt-1"
                  required
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  {t("organizationAddress")}
                </label>
                <Input
                  value={orgData.address}
                  onChange={(e) =>
                    setOrgData({ ...orgData, address: e.target.value })
                  }
                  placeholder={t("enterOrganizationAddress")}
                  className="mt-1"
                />
              </div>

              <div>
                <FormField
                  label={t("phone")}
                  id="org-phone"
                  value={orgData.phone}
                  onChange={(value) => setOrgData({ ...orgData, phone: value })}
                  placeholder={t("enterOrganizationPhone")}
                  type="phone"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  {t("organizationWebsite")}
                </label>
                <Input
                  value={orgData.website}
                  onChange={(e) =>
                    setOrgData({ ...orgData, website: e.target.value })
                  }
                  placeholder={t("enterOrganizationWebsite")}
                  className="mt-1"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  {t("organizationLogo")}
                </label>
                <div className="flex items-center mt-1 space-x-4">
                  {orgData.logo && (
                    <img
                      src={orgData.logo}
                      alt="Organization logo"
                      className="object-cover w-16 h-16 rounded"
                    />
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      document.getElementById("logo-upload")?.click()
                    }
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    {t("uploadLogo")}
                  </Button>
                  <input
                    id="logo-upload"
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleLogoUpload}
                  />
                </div>
              </div>

              <div className="pt-4">
                <Button
                  onClick={handleCreate}
                  className="w-full"
                  disabled={!orgData.name || isCreating}
                >
                  {isCreating ? (
                    <>
                      <svg
                        className="w-5 h-5 mr-3 -ml-1 text-white animate-spin"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      {t("creating")}...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      {t("createOrganization")}
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
