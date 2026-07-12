import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Trash2, Brain } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { api, apiError } from "@/lib/api";
import type { QuestionBankStats } from "@/types";

interface GenStatus {
  status: "idle" | "running" | "done" | "error";
  generated?: number;
  source?: string;
  message?: string;
}

export function QuestionBankCard({ courseId }: { courseId: number }) {
  const qc = useQueryClient();
  const [count, setCount] = useState(25);
  const [polling, setPolling] = useState(false);

  const stats = useQuery({
    queryKey: ["question-stats", courseId],
    queryFn: async () =>
      (await api.get<QuestionBankStats>(`/courses/${courseId}/questions/stats`)).data,
  });

  const status = useQuery({
    queryKey: ["gen-status", courseId],
    queryFn: async () =>
      (await api.get<GenStatus>(`/courses/${courseId}/generation-status`)).data,
    refetchInterval: polling ? 2500 : false,
  });

  // Resume polling if a job is already running (e.g. page was reopened).
  useEffect(() => {
    if (status.data?.status === "running") setPolling(true);
  }, [status.data?.status]);

  // React to job completion.
  useEffect(() => {
    if (!polling || !status.data) return;
    if (status.data.status === "done") {
      setPolling(false);
      toast.success(status.data.message ?? "Questions generated");
      qc.invalidateQueries({ queryKey: ["question-stats", courseId] });
    } else if (status.data.status === "error") {
      setPolling(false);
      toast.error(status.data.message ?? "Generation failed");
    }
  }, [status.data, polling, qc, courseId]);

  const start = useMutation({
    mutationFn: async (replace: boolean) =>
      (
        await api.post(`/courses/${courseId}/generate-questions`, {
          count,
          replace_existing: replace,
        })
      ).data,
    onSuccess: () => {
      setPolling(true);
      toast.info("Generating questions in the background…");
    },
    onError: (e) => toast.error(apiError(e, "Could not start generation")),
  });

  const clear = useMutation({
    mutationFn: async () => api.delete(`/courses/${courseId}/questions`),
    onSuccess: () => {
      toast.success("Question bank cleared");
      qc.invalidateQueries({ queryKey: ["question-stats", courseId] });
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const s = stats.data;
  const busy = polling || start.isPending;

  return (
    <Card className="mt-5">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <Brain className="h-4 w-4 text-primary" /> AI Question Bank
          {s && <Badge variant="secondary">{s.total} questions</Badge>}
        </CardTitle>
        {s && s.total > 0 && !busy && (
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive"
            onClick={() => {
              if (confirm("Clear the entire question bank for this course?")) clear.mutate();
            }}
          >
            <Trash2 className="h-4 w-4" /> Clear
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Questions are generated <b>only from the uploaded material</b> using Claude AI (with a
          document-grounded offline fallback). Difficulty is balanced automatically.
        </p>

        {s && s.total > 0 && (
          <div className="flex flex-wrap gap-2 text-xs">
            {Object.entries(s.difficulty_breakdown).map(([k, v]) => (
              <Badge key={k} variant="outline">
                {k}: {v}
              </Badge>
            ))}
            {Object.entries(s.type_breakdown).map(([k, v]) => (
              <Badge key={k} variant="secondary">
                {k}: {v}
              </Badge>
            ))}
          </div>
        )}

        {busy ? (
          <div className="flex items-center gap-3 rounded-md border border-dashed bg-muted/40 p-4 text-sm">
            <Spinner className="h-5 w-5" />
            <div>
              <p className="font-medium">Generating questions in the background…</p>
              <p className="text-xs text-muted-foreground">
                This can take a minute for larger counts. You can keep using the app; the count
                updates when it finishes.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Target count</label>
              <Input
                type="number"
                min={1}
                max={300}
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className="w-28"
              />
            </div>
            <Button onClick={() => start.mutate(false)} disabled={busy}>
              <Sparkles className="h-4 w-4" /> Generate
            </Button>
            {s && s.total > 0 && (
              <Button variant="outline" onClick={() => start.mutate(true)} disabled={busy}>
                Regenerate (replace)
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
