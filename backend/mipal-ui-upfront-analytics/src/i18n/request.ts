import { getRequestConfig } from "next-intl/server";
import { headers } from "next/headers";

export default getRequestConfig(async () => {
  // Get the Accept-Language header from the request
  const headersList = headers();
  const acceptLanguage = headersList.get("accept-language");
  const locale = acceptLanguage?.split(",")[0]?.split("-")[0] || "en";

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
