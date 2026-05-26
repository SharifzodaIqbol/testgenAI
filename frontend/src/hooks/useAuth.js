import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useAuth() {
  const { data: user, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: api.auth.me,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  return { user, isLoading };
}