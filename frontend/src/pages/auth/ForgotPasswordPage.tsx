import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { AuthShell } from "./AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { api, apiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email: email.trim() });
      setSent(true);
      setDevToken(data.reset_token ?? null);
      toast.success("If the email exists, a reset link has been sent.");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Forgot password"
      subtitle="We'll send a reset link to your email"
      footer={
        <Link to="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      {sent ? (
        <div className="space-y-4 text-sm">
          <p className="text-muted-foreground">
            If an account exists for <span className="font-medium text-foreground">{email}</span>, a
            reset link has been sent.
          </p>
          {devToken && (
            <div className="rounded-md border border-dashed bg-muted/50 p-3">
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                Development mode — use this link:
              </p>
              <Link
                to={`/reset-password?token=${encodeURIComponent(devToken)}`}
                className="break-all text-xs font-medium text-primary hover:underline"
              >
                /reset-password?token={devToken.slice(0, 24)}…
              </Link>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading && <Spinner />}
            Send reset link
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
