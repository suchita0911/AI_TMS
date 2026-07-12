import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CourseType } from "@/types";

export interface AICoursePayload {
  topic: string;
  extra_instructions: string | null;
  category: string | null;
  trainer: string | null;
  course_type: CourseType;
  start_date: string | null;
  end_date: string | null;
  has_quiz: boolean;
  passing_percentage: number;
  quiz_question_count: number;
  allow_retry: boolean;
  retry_count: number;
}

const empty: AICoursePayload = {
  topic: "",
  extra_instructions: null,
  category: null,
  trainer: null,
  course_type: "optional",
  start_date: null,
  end_date: null,
  has_quiz: true,
  passing_percentage: 50,
  quiz_question_count: 10,
  allow_retry: true,
  retry_count: 1,
};

export function AICourseDialog({
  open,
  onOpenChange,
  onSubmit,
  submitting,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onSubmit: (payload: AICoursePayload) => void;
  submitting: boolean;
}) {
  const [topic, setTopic] = useState("");
  const [extra, setExtra] = useState("");
  const [category, setCategory] = useState("");
  const [trainer, setTrainer] = useState("");
  const [courseType, setCourseType] = useState<CourseType>("optional");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [hasQuiz, setHasQuiz] = useState(true);
  const [passing, setPassing] = useState(50);
  const [questionCount, setQuestionCount] = useState(10);
  const [allowRetry, setAllowRetry] = useState(true);
  const [retryCount, setRetryCount] = useState(1);

  useEffect(() => {
    if (open) {
      setTopic("");
      setExtra("");
      setCategory("");
      setTrainer("");
      setCourseType(empty.course_type);
      setStartDate("");
      setEndDate("");
      setHasQuiz(true);
      setPassing(empty.passing_percentage);
      setQuestionCount(empty.quiz_question_count);
      setAllowRetry(empty.allow_retry);
      setRetryCount(empty.retry_count);
    }
  }, [open]);

  const submit = () => {
    onSubmit({
      topic: topic.trim(),
      extra_instructions: extra.trim() || null,
      category: category.trim() || null,
      trainer: trainer.trim() || null,
      course_type: courseType,
      start_date: startDate || null,
      end_date: endDate || null,
      has_quiz: hasQuiz,
      passing_percentage: passing,
      quiz_question_count: questionCount,
      allow_retry: allowRetry,
      retry_count: retryCount,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" /> Generate course with AI
          </DialogTitle>
          <DialogDescription>
            Describe a topic and AI will author the training material. It's created
            as a draft — you can review it, generate the quiz and publish afterwards.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="space-y-2">
            <Label>Topic</Label>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Workplace fire safety essentials"
            />
            <p className="text-xs text-muted-foreground">
              The course name and description are written by AI from this topic.
            </p>
          </div>
          <div className="space-y-2">
            <Label>Additional instructions (optional)</Label>
            <Textarea
              value={extra}
              onChange={(e) => setExtra(e.target.value)}
              placeholder="Tone, emphasis, company-specific policies to reflect…"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Category (optional)</Label>
              <Input
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="AI suggests one if left blank"
              />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={courseType} onValueChange={(v) => setCourseType(v as CourseType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mandatory">Mandatory</SelectItem>
                  <SelectItem value="optional">Optional</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Trainer (optional)</Label>
            <Input
              value={trainer}
              onChange={(e) => setTrainer(e.target.value)}
              placeholder="e.g. Jane Smith"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Start date</Label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>End date</Label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>
          <label className="flex items-center gap-2 rounded-md border bg-muted/30 p-3 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[hsl(var(--primary))]"
              checked={hasQuiz}
              onChange={(e) => setHasQuiz(e.target.checked)}
            />
            <span className="font-medium">This course has a quiz</span>
            <span className="text-muted-foreground">— uncheck for a view-only course</span>
          </label>
          {hasQuiz && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Passing percentage</Label>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={passing}
                    onChange={(e) => setPassing(Number(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Quiz question count</Label>
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    value={questionCount}
                    onChange={(e) => setQuestionCount(Number(e.target.value))}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 items-end gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[hsl(var(--primary))]"
                    checked={allowRetry}
                    onChange={(e) => setAllowRetry(e.target.checked)}
                  />
                  Allow retry
                </label>
                <div className="space-y-2">
                  <Label>Retry count</Label>
                  <Input
                    type="number"
                    min={0}
                    max={20}
                    value={retryCount}
                    disabled={!allowRetry}
                    onChange={(e) => setRetryCount(Number(e.target.value))}
                  />
                </div>
              </div>
            </>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={submitting || topic.trim().length < 3}>
            {submitting ? <Spinner /> : <Sparkles className="h-4 w-4" />}
            Generate course
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
