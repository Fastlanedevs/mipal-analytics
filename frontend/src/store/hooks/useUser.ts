import { useAppSelector } from "@/store/hooks";
import { selectCurrentUser } from "@/store/services/userApi";

export const useUser = () => {
  const { data: user, isLoading } = useAppSelector(selectCurrentUser);
  return { user, isLoading };
};
