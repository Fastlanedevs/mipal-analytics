import React, { useCallback } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { ShareDashboardUser } from "@/store/services/dashboardApi";
import { useGetUserOrganizationsMembersQuery } from "@/store/services/userApi";
import { useGetSharedUsersQuery } from "@/store/services/dashboardApi";
import { useTranslations } from "next-intl";

interface ShareDashboardDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
  dashboardId: string;
  selectedUsers: Array<{ user_id: string; permission: "view" | "edit" }>;
  onUserPermissionChange: (userId: string, permission: "view" | "edit") => void;
  onShare: () => void;
  isSharingDashboardLoading: boolean;
  setSelectedUsers: (
    users: Array<{ user_id: string; permission: "view" | "edit" }>
  ) => void;
}

export const ShareDashboardDialog: React.FC<ShareDashboardDialogProps> = ({
  isOpen,
  onOpenChange,
  orgId,
  dashboardId,
  selectedUsers,
  onUserPermissionChange,
  onShare,
  isSharingDashboardLoading,
  setSelectedUsers,
}) => {
  const t = useTranslations("dashboard.shareDashboardDialog");
  // Fetch organization members
  const {
    data: orgMembers,
    isLoading: isLoadingOrgMembers,
    refetch: refetchOrgMembers,
    isFetching: isFetchingOrgMembers,
  } = useGetUserOrganizationsMembersQuery(
    { org_id: orgId },
    { skip: !orgId || !isOpen }
  );

  // Fetch the shared users
  const {
    data: sharedUsers,
    isLoading: isLoadingSharedUsers,
    refetch: refetchSharedUsers,
    isFetching: isFetchingSharedUsers,
  } = useGetSharedUsersQuery(dashboardId, {
    skip: !dashboardId || !isOpen,
  });

  // Refetch data when dialog opens
  React.useEffect(() => {
    if (isOpen) {
      if (orgMembers && orgMembers.length > 0) {
        refetchOrgMembers();
      }
      if (sharedUsers && sharedUsers.users.length > 0) {
        refetchSharedUsers();
      }
    }
  }, [isOpen, orgMembers, sharedUsers, refetchOrgMembers, refetchSharedUsers]);

  React.useEffect(() => {
    if (sharedUsers && sharedUsers.users.length > 0) {
      setSelectedUsers(sharedUsers.users);
    }
  }, [isOpen, sharedUsers, orgMembers]);

  const handleShareDashboard = useCallback(() => {
    // check if selectedUsers array values and sharedUsers.users array values are different
    if (!sharedUsers?.users || !selectedUsers) {
      return true; // If either is undefined, consider it a change
    }

    // Convert arrays to sets of stringified objects for comparison
    const sharedUsersSet = new Set(
      sharedUsers.users.map((user) =>
        JSON.stringify({ user_id: user.user_id, permission: user.permission })
      )
    );
    const selectedUsersSet = new Set(
      selectedUsers.map((user) =>
        JSON.stringify({ user_id: user.user_id, permission: user.permission })
      )
    );

    // Check if sets are different
    if (sharedUsersSet.size !== selectedUsersSet.size) {
      return true;
    }

    // Check if all selected users exist in shared users
    const selectedUsersArray = Array.from(selectedUsersSet);
    for (const user of selectedUsersArray) {
      if (!sharedUsersSet.has(user)) {
        return true;
      }
    }

    return false;
  }, [sharedUsers, selectedUsers]);

  return (
    <AlertDialog open={isOpen} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle>{t("shareDashboard")}</AlertDialogTitle>
          <AlertDialogDescription>
            {t("selectUsersFromYourOrganizationToShareThisDashboardWith")}
            {t("youCanGrantThemViewOrEditPermissions")}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="max-h-[300px] overflow-y-auto py-2">
          {isLoadingOrgMembers ||
          isFetchingOrgMembers ||
          isLoadingSharedUsers ||
          isFetchingSharedUsers ? (
            <div className="flex justify-center py-4">
              <LoadingSpinner size={24} />
            </div>
          ) : !orgMembers || orgMembers.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">
              {t("noOrganizationMembersFound")}
            </div>
          ) : (
            <div className="space-y-4">
              {orgMembers.map((member: any) => {
                // Check if user is already shared
                let isShared = null;
                let allShareUsers = [];
                let currentPermission = "";
                if (sharedUsers?.users) {
                  allShareUsers = sharedUsers?.users;
                  isShared = allShareUsers?.find(
                    (user: ShareDashboardUser) =>
                      user.user_id === member.user_id
                  );
                  if (isShared) {
                    currentPermission = isShared.permission;
                  }
                }

                return (
                  <div
                    key={member.user_id}
                    className="flex flex-col space-y-2 border-b pb-3"
                  >
                    <div className="flex items-center justify-between space-x-3">
                      <Label htmlFor={`user-${member.user_id}`}>
                        {member.email} {member.role && `(${member.role})`}
                      </Label>
                      <div className="flex items-center space-x-2">
                        <div className="border rounded-md overflow-hidden flex">
                          <Button
                            type="button"
                            variant={
                              selectedUsers.find(
                                (u) => u.user_id === member.user_id
                              )?.permission === "view"
                                ? "default"
                                : "ghost"
                            }
                            size="sm"
                            className="rounded-none px-3 h-8"
                            onClick={() =>
                              onUserPermissionChange(member.user_id, "view")
                            }
                          >
                            {t("view")}
                          </Button>
                          <div className="border-r h-full" />
                          <Button
                            type="button"
                            variant={
                              selectedUsers.find(
                                (u) => u.user_id === member.user_id
                              )?.permission === "edit"
                                ? "default"
                                : "ghost"
                            }
                            size="sm"
                            className="rounded-none px-3 h-8"
                            onClick={() =>
                              onUserPermissionChange(member.user_id, "edit")
                            }
                          >
                            {t("edit")}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {!isSharingDashboardLoading &&
          !isLoadingSharedUsers &&
          !isFetchingSharedUsers &&
          !isLoadingOrgMembers &&
          !isFetchingOrgMembers && (
            <AlertDialogFooter>
              <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
              <AlertDialogAction
                onClick={onShare}
                disabled={!handleShareDashboard()}
              >
                {isSharingDashboardLoading ? (
                  <>
                    <LoadingSpinner size={16} className="mr-2" />
                    {t("sharing")}
                  </>
                ) : (
                  t("share")
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          )}
      </AlertDialogContent>
    </AlertDialog>
  );
};
