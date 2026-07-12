import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Eye, EyeOff } from "lucide-react";
import { AuthShell } from "./AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/context/AuthContext";
import { api, apiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [ssoDomains, setSsoDomains] = useState<string[]>([]);

  useEffect(() => {
    api
      .get<{ enabled: boolean; domains?: string[] }>("/auth/sso/status")
      .then((r) => {
        setSsoEnabled(r.data.enabled);
        setSsoDomains(r.data.domains ?? []);
      })
      .catch(() => {
        setSsoEnabled(false);
        setSsoDomains([]);
      });
  }, []);

  // The SSO button is enabled only once the entered email belongs to a
  // domain that is configured for SSO (or, if no domains are listed, any
  // email when SSO is fully configured).
  const emailDomain = username.includes("@")
    ? username.split("@")[1]?.trim().toLowerCase()
    : "";
  // Only surface SSO when it is fully configured (real Entra credentials).
  const ssoOffered = ssoEnabled;
  // Stricter: enable only when SSO is fully configured AND the email belongs to
  // an SSO domain (or any domain if no domain list is set).
  const ssoEligible =
    ssoEnabled &&
    !!emailDomain &&
    (ssoDomains.length > 0 ? ssoDomains.includes(emailDomain) : true);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(username.trim(), password);
      toast.success(`Welcome back, ${user.first_name}!`);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Sign in"
      subtitle="Enter your credentials to access your workspace"
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Register
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="you@company.com"
            autoComplete="email"
            required
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link to="/forgot-password" className="text-xs text-primary hover:underline">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              className="pr-10"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={showPassword ? "Hide password" : "Show password"}
              tabIndex={-1}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading && <Spinner />}
          Sign in
        </Button>
      </form>

      {ssoOffered && (
        <>
          <div className="my-4 flex items-center gap-3 text-xs text-muted-foreground">
            <span className="h-px flex-1 bg-border" />
            or
            <span className="h-px flex-1 bg-border" />
          </div>
          <Button
            type="button"
            variant="outline"
            className="w-full"
            disabled={!ssoEligible}
            onClick={() => {
              window.location.href =
                "/api/v1/auth/sso/login" +
                (username.trim() ? `?login_hint=${encodeURIComponent(username.trim())}` : "");
            }}
          >
            <svg className="h-4 w-4" viewBox="0 0 21 21" aria-hidden="true">
              <rect x="1" y="1" width="9" height="9" fill="#f25022" />
              <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
              <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
              <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
            </svg>
            Sign in with Microsoft
          </Button>
          {!ssoEligible && (
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Enter your organisation email to sign in with Microsoft.
            </p>
          )}
        </>
      )}
    </AuthShell>
  );
}
