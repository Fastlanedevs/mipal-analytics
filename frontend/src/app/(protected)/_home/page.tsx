"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Container } from "@/components/ui/container";
import { LandingPage } from "@/components/home/page";
import { useUser } from "@/store/hooks/useUser";

export default function HomePage() {
  const router = useRouter();
  const { user } = useUser();

  useEffect(() => {
    if (user && !user.joined_org) {
      router.push("/settings/profile");
    }
  }, [user, router]);

  return (
    <div className="flex h-full overflow-hidden ">
      <main className="flex-1 overflow-y-auto">
        <Container>
          <div className="max-w-screen-xl px-4 py-6 mx-auto md:px-8">
            <div className="max-w-4xl mx-auto">
              <LandingPage />
            </div>
          </div>
        </Container>
      </main>
    </div>
  );
}
