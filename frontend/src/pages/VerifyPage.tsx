import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, ShieldX, GraduationCap } from "lucide-react";
import { api } from "@/lib/api";
import { PageLoader } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import type { CertificateVerify } from "@/types";

export default function VerifyPage() {
  const { number } = useParams();

  const { data, isLoading } = useQuery({
    queryKey: ["verify", number],
    queryFn: async () =>
      (await api.get<CertificateVerify>(`/certificates/verify/${number}`)).data,
    retry: false,
  });

  if (isLoading) return <PageLoader label="Verifying certificate…" />;

  const valid = data?.valid;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary/10 via-background to-background p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <GraduationCap className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-bold">AI Powered TMS</h1>
          <p className="text-sm text-muted-foreground">Certificate Verification</p>
        </div>

        <div className="rounded-xl border bg-card p-8 text-center shadow-sm">
          {valid ? (
            <>
              <ShieldCheck className="mx-auto mb-3 h-14 w-14 text-success" />
              <h2 className="text-lg font-bold text-success">Valid Certificate</h2>
              <div className="mt-5 space-y-3 text-left text-sm">
                <Row label="Certificate No." value={data?.certificate_number} mono />
                <Row label="Awarded to" value={data?.employee_name} />
                <Row label="Course" value={data?.course_name} />
                <Row label="Score" value={data?.score != null ? `${data.score}%` : "—"} />
                <Row label="Issued" value={formatDate(data?.issued_at)} />
              </div>
            </>
          ) : (
            <>
              <ShieldX className="mx-auto mb-3 h-14 w-14 text-destructive" />
              <h2 className="text-lg font-bold text-destructive">Certificate Not Found</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                We couldn't verify certificate <span className="font-mono">{number}</span>. It may be
                invalid or revoked.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b pb-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono font-medium" : "font-medium"}>{value ?? "—"}</span>
    </div>
  );
}
