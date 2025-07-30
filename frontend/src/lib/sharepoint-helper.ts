import { msalConfig } from "./azure-config";
import { ConfidentialClientApplication } from "@azure/msal-node";

const msalInstance = new ConfidentialClientApplication(msalConfig);

export async function getSharePointSites(accessToken: string) {
  try {
    const response = await fetch(
      "https://graph.microsoft.com/v1.0/sites?search=*",
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error("Failed to fetch SharePoint sites");
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching SharePoint sites:", error);
    throw error;
  }
}

export async function getSharePointLists(siteId: string, accessToken: string) {
  try {
    const response = await fetch(
      `https://graph.microsoft.com/v1.0/sites/${siteId}/lists`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error("Failed to fetch SharePoint lists");
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching SharePoint lists:", error);
    throw error;
  }
}

export async function getSharePointItems(
  siteId: string,
  listId: string,
  accessToken: string
) {
  try {
    const response = await fetch(
      `https://graph.microsoft.com/v1.0/sites/${siteId}/lists/${listId}/items`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error("Failed to fetch SharePoint items");
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching SharePoint items:", error);
    throw error;
  }
}
