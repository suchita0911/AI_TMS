import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, ArrowLeft, RefreshCw, Trophy, Award } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader, Spinner } from "@/components/ui/spinner";
import { api, apiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { QuizResult, QuizView } from "@/types";

export default function QuizPage() {
  const { id } = useParams();
  const courseId = Number(id);
  const navigate = useNavigate();
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [result, setResult] = useState<QuizResult | null>(null);

  const quiz = useQuery({
    queryKey: ["quiz-start", courseId],
    queryFn: async () =>
      (await api.post<QuizView>(`/me/courses/${courseId}/quiz/start`)).data,
    retry: false,
    refetchOnMount: "always",
  });

  const answeredCount = Object.values(answers).filter(Boolean).length;
  const total = quiz.data?.questions.length ?? 0;

  const submit = useMutation({
    mutationFn: async () => {
      const payload = {
        answers: (quiz.data?.questions ?? []).map((q) => ({
          answer_id: q.answer_id,
          selected: answers[q.answer_id] ?? null,
        })),
      };
      return (await api.post<QuizResult>(`/me/quiz/${quiz.data!.attempt_id}/submit`, payload)).data;
    },
    onSuccess: (r) => {
      setResult(r);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    onError: (e) => toast.error(apiError(e, "Submission failed")),
  });

  const retry = () => {
    setAnswers({});
    setResult(null);
    quiz.refetch();
  };

  if (quiz.isLoading) return <PageLoader label="Preparing your quiz…" />;

  if (quiz.isError) {
    return (
      <div>
        <BackLink courseId={courseId} />
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {apiError(quiz.error, "Quiz is not available.")}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (result) {
    return (
      <ResultView
        result={result}
        courseId={courseId}
        onRetry={retry}
        onDone={() => navigate(`/my-courses/${courseId}`)}
      />
    );
  }

  const q = quiz.data!;
  return (
    <div className="mx-auto max-w-3xl">
      <BackLink courseId={courseId} />
      <PageHeader
        title={`Quiz: ${q.course_name}`}
        description={`${q.total_questions} questions · Attempt #${q.attempt_number} · Pass mark ${q.passing_percentage}%`}
        actions={
          <Badge variant={answeredCount === total ? "success" : "secondary"}>
            {answeredCount}/{total} answered
          </Badge>
        }
      />

      <div className="space-y-4">
        {q.questions.map((question, i) => (
          <Card key={question.answer_id}>
            <CardContent className="p-5">
              <div className="mb-3 flex items-start gap-2">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {i + 1}
                </span>
                <div className="flex-1">
                  <p className="font-medium">{question.question_text}</p>
                </div>
              </div>
              <div className="space-y-2 pl-8">
                {question.options.map((opt) => {
                  const selected = answers[question.answer_id] === opt;
                  return (
                    <label
                      key={opt}
                      className={cn(
                        "flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition-colors",
                        selected ? "border-primary bg-primary/5" : "hover:bg-accent"
                      )}
                    >
                      <input
                        type="radio"
                        name={`q-${question.answer_id}`}
                        className="h-4 w-4 accent-[hsl(var(--primary))]"
                        checked={selected}
                        onChange={() =>
                          setAnswers((a) => ({ ...a, [question.answer_id]: opt }))
                        }
                      />
                      {opt}
                    </label>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="sticky bottom-4 mt-6 flex items-center justify-between rounded-xl border bg-background/95 p-4 shadow-lg backdrop-blur">
        <span className="text-sm text-muted-foreground">
          {answeredCount < total
            ? `${total - answeredCount} question(s) unanswered`
            : "All questions answered"}
        </span>
        <Button
          onClick={() => {
            if (answeredCount < total && !confirm("Submit with unanswered questions?")) return;
            submit.mutate();
          }}
          disabled={submit.isPending}
        >
          {submit.isPending && <Spinner />} Submit quiz
        </Button>
      </div>
    </div>
  );
}

function BackLink({ courseId }: { courseId: number }) {
  return (
    <Link
      to={`/my-courses/${courseId}`}
      className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" /> Back to course
    </Link>
  );
}

function ResultView({
  result,
  courseId,
  onRetry,
  onDone,
}: {
  result: QuizResult;
  courseId: number;
  onRetry: () => void;
  onDone: () => void;
}) {
  return (
    <div className="mx-auto max-w-3xl">
      <Card className="mb-5">
        <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
          {result.passed ? (
            <Trophy className="h-14 w-14 text-success" />
          ) : (
            <XCircle className="h-14 w-14 text-destructive" />
          )}
          <h2 className="text-2xl font-bold">
            {result.passed ? "Congratulations, you passed!" : "You didn't pass this time"}
          </h2>
          <p className="text-4xl font-extrabold">{result.score_percentage}%</p>
          <p className="text-sm text-muted-foreground">
            {result.correct_count} / {result.total_questions} correct · pass mark{" "}
            {result.passing_percentage}%
          </p>
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            {result.passed ? (
              <>
                <Button asChild>
                  <Link to={`/my-courses/${courseId}/certificate`}>
                    <Award className="h-4 w-4" /> View certificate
                  </Link>
                </Button>
                <Button variant="outline" onClick={onDone}>
                  Back to course
                </Button>
              </>
            ) : result.can_retry ? (
              <>
                <Button onClick={onRetry}>
                  <RefreshCw className="h-4 w-4" /> Retry quiz ({result.attempts_used}/
                  {result.max_attempts} used)
                </Button>
                <Button variant="outline" onClick={onDone}>
                  Back to course
                </Button>
              </>
            ) : (
              <>
                <p className="text-sm text-destructive">No attempts remaining.</p>
                <Button variant="outline" onClick={onDone}>
                  Back to course
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Review</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {result.review.map((r, i) => (
            <div key={i} className="rounded-lg border p-4">
              <div className="mb-2 flex items-start gap-2">
                {r.is_correct ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                ) : (
                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                )}
                <p className="text-sm font-medium">
                  {i + 1}. {r.question_text}
                </p>
              </div>
              <div className="space-y-1 pl-6 text-sm">
                <p>
                  Your answer:{" "}
                  <span className={r.is_correct ? "text-success" : "text-destructive"}>
                    {r.selected || "— (skipped)"}
                  </span>
                </p>
                {!r.is_correct && (
                  <p>
                    Correct answer: <span className="text-success">{r.correct_answer}</span>
                  </p>
                )}
                {r.explanation && (
                  <p className="text-xs text-muted-foreground">💡 {r.explanation}</p>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
