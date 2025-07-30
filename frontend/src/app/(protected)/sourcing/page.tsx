"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRouter } from "next/navigation";
import { FileText, ClipboardList, Users, FileCheck } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { useGetSourcingCategoriesQuery } from "@/store/services/sourcingApi";
import { Skeleton } from "@/components/ui/skeleton";

export default function SourcingPage() {
  const router = useRouter();
  const {
    data: categories,
    isLoading,
    error,
  } = useGetSourcingCategoriesQuery();

  const handleOptionClick = (id: string, name: string) => {
    router.push(`/sourcing/${name.toLowerCase().replace(/\s+/g, "-")}`);
  };

  if (isLoading) {
    return (
      <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="flex flex-col items-start justify-center py-8 space-y-8">
          <Skeleton className="h-12 w-64" />
          <Skeleton className="h-6 w-full max-w-md" />
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-2 w-full">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-48 w-full" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="flex flex-col items-start justify-center py-8 space-y-8">
          <PageHeader
            title="Sourcing"
            description="An error occurred while loading sourcing options"
          />
          <div className="text-red-500">
            Failed to load sourcing options. Please try again later.
          </div>
        </div>
      </div>
    );
  }

  const getIconForCategory = (name: string) => {
    switch (name.toLowerCase()) {
      case "rfp":
        return FileText;
      case "proposal":
        return ClipboardList;
      case "vendor evaluation":
        return Users;
      case "contract draft":
        return FileCheck;
      default:
        return FileText;
    }
  };

  const getColorForCategory = (name: string) => {
    switch (name.toLowerCase()) {
      case "rfp":
        return "text-blue-500";
      case "proposal":
        return "text-green-500";
      case "vendor evaluation":
        return "text-purple-500";
      case "contract draft":
        return "text-orange-500";
      default:
        return "text-gray-500";
    }
  };

  const notActiveCategories = categories?.filter(
    (category) =>
      category.name !== "Contract Draft" &&
      category.name !== "Vendor Evaluation" &&
      category.name !== "Proposal"
  );

  return (
    <div className="container px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
      <div className="flex flex-col items-start justify-center py-8 space-y-8">
        <PageHeader
          title="Sourcing"
          description="Choose a sourcing option to get started"
        />

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-2 w-full">
          {categories?.map((category) => {
            const Icon = getIconForCategory(category.name);
            const color = getColorForCategory(category.name);
            const isDisabled = category.name.toLowerCase() !== "rfp";
            return (
              <Card
                key={category.id}
                className={`cursor-pointer hover:scale-[101%] hover:shadow-md active:scale-[100%] active:shadow-sm transition-all duration-200 relative ${
                  isDisabled ? " cursor-default" : ""
                }`}
                onClick={() =>
                  !isDisabled && handleOptionClick(category.id, category.name)
                }
              >
                <CardHeader>
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg ${color}`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <CardTitle className="text-lg">{category.name}</CardTitle>
                    {isDisabled && (
                      <span className="text-xs font-medium px-2 py-0.5 bg-amber-100 text-amber-800 dark:bg-amber-800 dark:text-amber-200 rounded">
                        Coming Soon
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {category.description}
                  </p>
                </CardContent>
                {/* Overlay for disabled options */}
                {isDisabled && (
                  <div className="absolute inset-0 bg-black/5 dark:bg-black/20 flex items-center justify-center rounded-lg pointer-events-none"></div>
                )}
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
