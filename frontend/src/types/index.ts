export type Status = "Active" | "Pending" | "Inactive";

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  status: Status;
}
