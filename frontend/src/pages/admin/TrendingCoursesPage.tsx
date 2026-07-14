import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  TrendingUp,
  Sparkles,
  Plus,
  Search,
  GraduationCap,
  Lightbulb,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DesignationSelect } from "@/components/DesignationSelect";
import { api, apiError } from "@/lib/api";
import type {
  CourseDetail,
  TrendingCourse,
  TrendingRecommendations,
} from "@/types";

const levelVariant: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  beginner: "success",
  intermediate: "warning",
  advanced: "destructive",
};

export default function TrendingCoursesPage() {
  const navigate = useNavigate();
  const [focus, setFocus] = useState("");
  const [designation, setDesignation] = useState("");
  const [level, setLevel] = useState<"beginner" | "intermediate" | "advanced" | undefined>(undefined);
  const [result, setResult] = useState<TrendingRecommendations | null>(null);
  const [adding, setAdding] = useState<string | null>(null);

  const hasInput = Boolean((focus || "").trim() || designation || level);

  const recommend = useMutation({
    mutationFn: async () =>
      (
        await api.get<TrendingRecommendations>("/courses/trending", {
          params: {
            focus: focus.trim() || undefined,
            designation: designation || undefined,
            level: level || undefined,
            count: 6,
          },
        })
      ).data,
    onSuccess: (data) => setResult(data),
    onError: (e) => toast.error(apiError(e, "Could not load recommendations")),
  });

  // Turn a suggestion into a real draft course, reusing the AI course generator.
  const addToCatalog = useMutation({
    mutationFn: async (course: TrendingCourse) => {
      setAdding(course.title);
      const extra = [
        course.why ? `Why this matters: ${course.why}` : "",
        course.skills.length ? `Cover these skills: ${course.skills.join(", ")}.` : "",
        `Target level: ${course.level}.`,
      ]
        .filter(Boolean)
        .join(" ");
      return (
        await api.post<CourseDetail>("/courses/generate", {
          topic: course.title,
          extra_instructions: extra || null,
          category: course.category || null,
          course_type: "optional",
          start_date: null,
          end_date: null,
          passing_percentage: 50,
          quiz_question_count: 10,
          allow_retry: true,
          retry_count: 1,
        })
      ).data;
    },
    onSuccess: (course) => {
      toast.success("Added as a draft - review the material and generate the quiz");
      navigate(`/admin/courses/${course.id}`);
    },
    onError: (e) => toast.error(apiError(e, "Could not add course")),
    onSettled: () => setAdding(null),
  });

  return (
    <div>
      <PageHeader
        title="Trending Courses"
        description="AI-recommended, in-demand IT training you can roll out to your organisation"
        actions={
          <Button
            onClick={() => recommend.mutate()}
            disabled={recommend.isPending || !hasInput}
          >
            {recommend.isPending ? <Spinner /> : <Sparkles className="h-4 w-4" />}
            {result ? "Refresh" : "Get recommendations"}
          </Button>
        }
      />

      <div className="mb-2 flex flex-col gap-3 sm:flex-row">
        <div className="space-y-1.5">
          <DesignationSelect
            value={designation}
            onChange={(value) => {
              setDesignation(value);
              if (!value) {
                setLevel(undefined);
              }
              setResult(null);
            }}
            allowAdd
            triggerClassName="sm:w-72"
            placeholder="Select a designation"
          />
        </div>
        <div className="space-y-1.5">
          <Select
            value={level}
            onValueChange={(value) => {
              const normalized = value as "beginner" | "intermediate" | "advanced";
              setLevel(normalized);
              setResult(null);
            }}
          >
            <SelectTrigger className="sm:w-56">
              <SelectValue placeholder="Select level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="beginner">Beginner</SelectItem>
              <SelectItem value="intermediate">Intermediate</SelectItem>
              <SelectItem value="advanced">Advanced</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="relative flex-1 sm:max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Focus area (optional) - e.g. Cloud, Security, AI/ML"
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && hasInput && recommend.mutate()}
          />
        </div>
      </div>
      <p className="mb-6 text-sm text-muted-foreground">
        {hasInput
          ? "Now click “Get recommendations” to see courses tailored to your input."
          : "Enter a focus area or choose a designation to get recommendations."}
      </p>

      {result?.source === "fallback" && result.items.length > 0 && (
        <div className="mb-5 flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Showing a curated sample list. Set a valid <code>ANTHROPIC_API_KEY</code> in
            the backend to get live, AI-generated recommendations tailored to your focus.
          </span>
        </div>
      )}

      {!result && !recommend.isPending && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <TrendingUp className="h-10 w-10 opacity-40" />
            <p className="max-w-md">
              Discover trending, high-value courses for the IT industry. Optionally set a
              focus area, then get AI recommendations you can add to your catalogue in one
              click.
            </p>
          </CardContent>
        </Card>
      )}

      {recommend.isPending && (
        <div className="flex justify-center p-16">
          <Spinner className="h-6 w-6" />
        </div>
      )}

      {result && (result.designation || result.focus) && (
        <p className="mb-4 text-sm text-muted-foreground">
          Tailored for
          {result.designation && (
            <span className="font-medium text-foreground"> {result.designation}</span>
          )}
          {result.designation && result.focus && " · "}
          {result.focus && <span className="font-medium text-foreground">{result.focus}</span>}
        </p>
      )}

      {result && result.items.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <Search className="h-10 w-10 opacity-40" />
            <p className="max-w-md font-medium text-foreground">Course not found</p>
            <p className="max-w-md text-sm">
              No trending courses matched{" "}
              {result.focus ? (
                <span className="font-medium">“{result.focus}”</span>
              ) : (
                "your input"
              )}
              . Try a real technology topic like “Cloud”, “Security”, or “AI/ML”.
            </p>
          </CardContent>
        </Card>
      )}

      {result && result.items.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {result.items.map((c) => (
            <Card key={c.title} className="flex h-full flex-col">
              <CardContent className="flex h-full flex-col gap-3 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <GraduationCap className="h-5 w-5" />
                  </div>
                  <Badge variant={levelVariant[c.level] ?? "secondary"} className="capitalize">
                    {c.level}
                  </Badge>
                </div>

                <div>
                  <h3 className="font-semibold leading-snug">{c.title}</h3>
                  {c.category && (
                    <span className="mt-1 inline-block text-xs text-muted-foreground">
                      {c.category}
                    </span>
                  )}
                </div>

                {c.description && (
                  <p className="text-sm text-muted-foreground">{c.description}</p>
                )}

                {c.why && (
                  <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
                    <TrendingUp className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                    <span>{c.why}</span>
                  </p>
                )}

                {c.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {c.skills.map((s) => (
                      <Badge key={s} variant="secondary" className="font-normal">
                        {s}
                      </Badge>
                    ))}
                  </div>
                )}

                <div className="mt-auto border-t pt-3">
                  <Button
                    size="sm"
                    className="w-full"
                    variant="outline"
                    disabled={addToCatalog.isPending}
                    onClick={() => addToCatalog.mutate(c)}
                  >
                    {adding === c.title ? <Spinner /> : <Plus className="h-4 w-4" />}
                    Add to catalogue
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
