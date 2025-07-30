import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import PrivacySection from "@/components/PrivacySection";
import { privacyPolicySections } from "@/constants/privacyPolicy";

const Page = () => {
  return (
    <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <a
          href="/"
          className="inline-flex items-center gap-2 mb-6 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors border py-2 px-3 rounded-lg border-transparent hover:border-foreground/20 hover:bg-background"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Back
        </a>
        <Card>
          <CardContent className="prose dark:prose-invert max-w-none p-4 md:p-8">
            <h1 className="text-3xl font-bold mb-8">
              Privacy Policy for MIPAL
            </h1>

            <div className="text-sm text-muted-foreground mb-8">
              <p>Effective Date: January 24, 2025</p>
              <p>Last Updated: April 1, 2025</p>
            </div>

            {privacyPolicySections.map((section, index) => (
              <PrivacySection
                key={index}
                title={section.title}
                subsections={section.subsections || []}
              />
            ))}

            <footer className="text-sm text-muted-foreground mt-12 pt-4 border-t">
              Last Updated: April 1, 2025
            </footer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Page;
