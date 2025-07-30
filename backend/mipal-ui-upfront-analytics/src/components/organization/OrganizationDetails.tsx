"use client";

import { useState } from "react";
import {
  Organization,
  useUpdateOrganizationMutation,
} from "@/store/services/organizationApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Edit2, Save, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { jwtDecode } from "jwt-decode";
import { useSession } from "next-auth/react";
import { FormField } from "@/components/FormField";

interface DecodedToken {
  role: string;
}

export default function OrganizationDetails({
  organization,
}: {
  organization: Organization;
}) {
  const { data: session } = useSession();
  const { toast } = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [updateOrg, { isLoading: isUpdating }] =
    useUpdateOrganizationMutation();

  const [editData, setEditData] = useState({
    name: organization.name,
    address: organization.address || "",
    phone: organization.phone || "",
    website: organization.website || "",
  });

  // Decode token to check role - check session.user first, fall back to session.accessToken
  const accessToken = session?.accessToken ?? session?.user?.access_token;
  const decodedToken = accessToken
    ? (jwtDecode(accessToken) as DecodedToken)
    : null;
  const isAdmin = decodedToken?.role === "ADMIN";

  const handleUpdate = async () => {
    try {
      await updateOrg({
        orgId: organization.id,
        data: editData,
      }).unwrap();

      toast({
        title: "Success",
        description: "Organization updated successfully",
      });
      setIsEditing(false);
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.data?.message || "Failed to update organization",
        variant: "destructive",
      });
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Organization Details</CardTitle>
        {isAdmin && !isEditing && (
          <Button variant="outline" onClick={() => setIsEditing(true)}>
            <Edit2 className="w-4 h-4 mr-2" />
            Edit
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">Organization Name</label>
            {isEditing ? (
              <Input
                value={editData.name}
                onChange={(e) =>
                  setEditData({ ...editData, name: e.target.value })
                }
                className="mt-1"
              />
            ) : (
              <p className="mt-1">{organization.name}</p>
            )}
          </div>

          <div>
            <label className="text-sm font-medium">Address</label>
            {isEditing ? (
              <Input
                value={editData.address}
                onChange={(e) =>
                  setEditData({ ...editData, address: e.target.value })
                }
                className="mt-1"
              />
            ) : (
              <p className="mt-1">{organization.address || "Not specified"}</p>
            )}
          </div>

          <div>
            <label className="text-sm font-medium">Phone</label>
            {isEditing ? (
              <FormField
                label=""
                id="org-phone"
                value={editData.phone}
                onChange={(value) => setEditData({ ...editData, phone: value })}
                placeholder="Enter phone number"
                type="phone"
              />
            ) : (
              <p className="mt-1">{organization.phone || "Not specified"}</p>
            )}
          </div>

          <div>
            <label className="text-sm font-medium">Website</label>
            {isEditing ? (
              <Input
                value={editData.website}
                onChange={(e) =>
                  setEditData({ ...editData, website: e.target.value })
                }
                className="mt-1"
              />
            ) : (
              <p className="mt-1">{organization.website || "Not specified"}</p>
            )}
          </div>

          {isEditing && (
            <div className="flex justify-end space-x-2 pt-4">
              <Button
                variant="outline"
                onClick={() => setIsEditing(false)}
                disabled={isUpdating}
              >
                <X className="w-4 h-4 mr-2" />
                Cancel
              </Button>
              <Button onClick={handleUpdate} disabled={isUpdating}>
                {isUpdating ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
