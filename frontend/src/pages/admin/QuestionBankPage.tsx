import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Brain, ChevronDown, CheckCircle2, BookOpen } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { CourseDetail, Difficulty, Page, QuestionBankOut, QuestionType } from "@/types";

const PAGE_SIZE = 10;

const DIFFICULTY_VARIANT: Record<Difficulty, "success" | "warning" | "destructive"> = {
  easy: "success",
  medium: "warning",
  hard: "destructive",
};

const TYPE_LABEL: Record<QuestionType, string> = {
  mcq: "Multiple choice",
  true_false: "True / False",
  scenario: "Scenario",
};

export default function QuestionBankPage() {
  const { id } = useParams();
  const courseId = Number(id);
  const [page, setPage] = useState(1);
  const [difficulty, setDifficulty] = useState<string>("all");
  const [questionType, setQuestionType] = useState<string>("all");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const course = useQuery({
    queryKey: ["course", courseId],
    queryFn: async () => (await api.get<CourseDetail>(`/courses/${courseId}`)).data,
  });

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["questions", courseId, { difficulty, questionType, page }],
    queryFn: async () =>
      (
        await api.get<Page<QuestionBankOut>>(`/courses/${courseId}/questions`, {
          params: {
            difficulty: difficulty === "all" ? undefined : difficulty,
            question_type: questionType === "all" ? undefined : questionType,
            page,
            page_size: PAGE_SIZE,
          },
        })
      ).data,
  });

  const toggle = (qid: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(qid) ? next.delete(qid) : next.add(qid);
      return next;
    });

  const onFilter = (setter: (v: string) => void) => (v: string) => {
    setter(v);
    setPage(1);
    setExpanded(new Set());
  };

  const items = data?.items ?? [];

  return (
    <div>
      <Link
        to={`/admin/courses/${courseId}`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to course
      </Link>

      <PageHeader
        title="Question Bank"
        description={
          course.data
            ? `AI-generated questions for “${course.data.name}”`
            : "AI-generated questions for this course"
        }
        actions={
          data && (
            <Badge variant="secondary" className="text-sm">
              {data.total} question{data.total === 1 ? "" : "s"}
            </Badge>
          )
        }
      />

      <Card>
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 border-b p-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Difficulty</span>
            <Select value={difficulty} onValueChange={onFilter(setDifficulty)}>
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="easy">Easy</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="hard">Hard</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Type</span>
            <Select value={questionType} onValueChange={onFilter(setQuestionType)}>
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="mcq">Multiple choice</SelectItem>
                <SelectItem value="true_false">True / False</SelectItem>
                <SelectItem value="scenario">Scenario</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {isFetching && !isLoading && <Spinner className="h-4 w-4" />}
        </div>

        {/* Question list */}
        {isLoading ? (
          <div className="flex justify-center p-10">
            <Spinner className="h-6 w-6" />
          </div>
        ) : items.length === 0 ? (
          <div className="p-6">
            <div className="rounded-lg border border-dashed p-10 text-center">
              <Brain className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
              <p className="text-sm font-medium">No questions to show</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {difficulty !== "all" || questionType !== "all"
                  ? "No questions match the selected filters."
                  : "Generate a question bank from the course page to see questions here."}
              </p>
            </div>
          </div>
        ) : (
          <ul className="divide-y">
            {items.map((q, i) => {
              const isOpen = expanded.has(q.id);
              const number = (page - 1) * PAGE_SIZE + i + 1;
              return (
                <li key={q.id}>
                  <button
                    type="button"
                    onClick={() => toggle(q.id)}
                    className="flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-muted/40"
                    aria-expanded={isOpen}
                  >
                    <span className="mt-0.5 w-6 shrink-0 text-sm font-medium text-muted-foreground">
                      {number}.
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium">{q.question_text}</span>
                      <span className="mt-2 flex flex-wrap items-center gap-2">
                        <Badge variant={DIFFICULTY_VARIANT[q.difficulty]}>{q.difficulty}</Badge>
                        <Badge variant="outline">{TYPE_LABEL[q.question_type]}</Badge>
                        {q.topic && (
                          <span className="text-xs text-muted-foreground">{q.topic}</span>
                        )}
                      </span>
                    </span>
                    <ChevronDown
                      className={cn(
                        "mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                        isOpen && "rotate-180"
                      )}
                    />
                  </button>

                  {isOpen && (
                    <div className="space-y-4 border-t bg-muted/20 px-4 py-4 sm:pl-[3.25rem]">
                      {/* Options with the correct answer highlighted */}
                      {q.options.length > 0 && (
                        <ul className="space-y-2">
                          {q.options.map((opt, oi) => {
                            const correct = opt.trim() === q.correct_answer.trim();
                            return (
                              <li
                                key={oi}
                                className={cn(
                                  "flex items-start gap-2 rounded-md border px-3 py-2 text-sm",
                                  correct
                                    ? "border-success/40 bg-success/10 font-medium text-success"
                                    : "border-transparent bg-background"
                                )}
                              >
                                <span className="w-5 shrink-0 text-muted-foreground">
                                  {String.fromCharCode(65 + oi)}.
                                </span>
                                <span className="flex-1">{opt}</span>
                                {correct && (
                                  <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
                                )}
                              </li>
                            );
                          })}
                        </ul>
                      )}

                      {/* For questions without an options list, show the answer plainly */}
                      {q.options.length === 0 && (
                        <p className="text-sm">
                          <span className="text-muted-foreground">Correct answer: </span>
                          <span className="font-medium text-success">{q.correct_answer}</span>
                        </p>
                      )}

                      {q.explanation && (
                        <div className="flex gap-2 text-sm text-muted-foreground">
                          <BookOpen className="mt-0.5 h-4 w-4 shrink-0" />
                          <p>
                            <span className="font-medium text-foreground">Explanation: </span>
                            {q.explanation}
                          </p>
                        </div>
                      )}

                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        {q.reference_section && <span>Reference: {q.reference_section}</span>}
                        <span>Source: {q.generated_by === "ai" ? "Claude AI" : "Fallback"}</span>
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {data && data.total > 0 && (
          <div className="border-t px-4">
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPage={setPage} />
          </div>
        )}
      </Card>
    </div>
  );
}
