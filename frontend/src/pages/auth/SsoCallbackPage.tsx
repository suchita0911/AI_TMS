import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { PageLoader } from "@/components/ui/spinner";
import { tokenStore } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

/**
 * Landing page for the SSO redirect. The backend appends the issued tokens (or
 * an error) to the URL fragment; we store them, hydrate the session and move on.
 */
export default function SsoCallbackPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const error = params.get("error");
    const access = params.get("access_token");
    const refresh = params.get("refresh_token");

    // Strip the fragment so tokens don't linger in the URL or browser history.
    window.history.replaceState(null, "", window.location.pathname);

    if (error || !access || !refresh) {
      toast.error(error || "Single sign-on failed");
      navigate("/login", { replace: true });
      return;
    }

    tokenStore.set(access, refresh);
    refreshUser()
      .then(() => {
        toast.success("Signed in");
        navigate("/dashboard", { replace: true });
      })
      .catch(() => {
        tokenStore.clear();
        toast.error("Could not complete sign-in");
        navigate("/login", { replace: true });
      });
  }, [navigate, refreshUser]);

  return <PageLoader />;
}
