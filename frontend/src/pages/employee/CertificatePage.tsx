import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Award, Download, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { api, apiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Certificate } from "@/types";

export default function CertificatePage() {
  const { id } = useParams();
  const courseId = Number(id);

  const cert = useQuery({
    queryKey: ["certificate", courseId],
    queryFn: async () => (await api.get<Certificate>(`/me/courses/${courseId}/certificate`)).data,
    retry: false,
  });

  const download = async () => {
    try {
      const res = await api.get(`/me/courses/${courseId}/certificate/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${cert.data?.certificate_number ?? "certificate"}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(apiError(e, "Download failed"));
    }
  };

  if (cert.isLoading) return <PageLoader />;

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        to={`/my-courses/${courseId}`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to course
      </Link>
      <PageHeader title="Certificate" />

      {cert.isError ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {apiError(cert.error, "Certificate is available only after you complete the course.")}
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="border-b-4 border-primary bg-gradient-to-br from-primary/10 to-transparent p-10 text-center">
            <Award className="mx-auto mb-3 h-16 w-16 text-primary" />
            <h2 className="text-xl font-bold">Certificate of Completion</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Certificate No. <span className="font-mono font-medium">{cert.data?.certificate_number}</span>
            </p>
          </div>
          <CardContent className="space-y-4 p-6">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Score</p>
                <p className="font-semibold">{cert.data?.score ?? "—"}%</p>
              </div>
              <div>
                <p className="text-muted-foreground">Issued</p>
                <p className="font-semibold">{formatDate(cert.data?.issued_at)}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-md bg-success/10 p-3 text-sm text-success">
              <ShieldCheck className="h-4 w-4" /> This certificate is verifiable via the QR code on the PDF.
            </div>
            <Button className="w-full" onClick={download}>
              <Download className="h-4 w-4" /> Download PDF certificate
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
