import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { AuthShell } from "./AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { api, apiError } from "@/lib/api";

export default function SetPasswordPage({ mode = "setup" }: { mode?: "setup" | "reset" }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const endpoint = mode === "setup" ? "/auth/set-password" : "/auth/reset-password";
  const title = mode === "setup" ? "Set your password" : "Reset your password";

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pw !== confirm) {
      toast.error("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      await api.post(endpoint, { token, new_password: pw });
      toast.success("Password saved. Please sign in.");
      navigate("/login", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Could not set password"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title={title}
      subtitle="Choose a strong password (min 8 chars, letters and numbers)"
      footer={
        <Link to="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        {!params.get("token") && (
          <div className="space-y-2">
            <Label htmlFor="token">Token</Label>
            <Input id="token" value={token} onChange={(e) => setToken(e.target.value)} required />
          </div>
        )}
        <div className="space-y-2">
          <Label htmlFor="pw">New password</Label>
          <Input id="pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirm">Confirm password</Label>
          <Input
            id="confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
        </div>
        <Button type="submit" className="w-full" disabled={loading || !token}>
          {loading && <Spinner />}
          Save password
        </Button>
      </form>
    </AuthShell>
  );
}
