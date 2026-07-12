import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import {
  Dialog,
  DialogContent,
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
import type { Course, CourseType } from "@/types";

export interface CoursePayload {
  name: string;
  description: string;
  category: string;
  trainer: string;
  course_type: CourseType;
  start_date: string;
  end_date: string;
  has_quiz: boolean;
  passing_percentage: number;
  quiz_question_count: number;
  allow_retry: boolean;
  retry_count: number;
}

const empty: CoursePayload = {
  name: "",
  description: "",
  category: "",
  trainer: "",
  course_type: "optional",
  start_date: "",
  end_date: "",
  has_quiz: true,
  passing_percentage: 50,
  quiz_question_count: 10,
  allow_retry: true,
  retry_count: 1,
};

export function CourseFormDialog({
  open,
  onOpenChange,
  initial,
  onSubmit,
  submitting,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initial?: Course | null;
  onSubmit: (payload: Partial<CoursePayload>) => void;
  submitting: boolean;
}) {
  const [form, setForm] = useState<CoursePayload>(empty);

  useEffect(() => {
    if (open) {
      setForm(
        initial
          ? {
              name: initial.name,
              description: initial.description ?? "",
              category: initial.category ?? "",
              trainer: initial.trainer ?? "",
              course_type: initial.course_type,
              start_date: initial.start_date ?? "",
              end_date: initial.end_date ?? "",
              has_quiz: initial.has_quiz,
              passing_percentage: initial.passing_percentage,
              quiz_question_count: initial.quiz_question_count,
              allow_retry: initial.allow_retry,
              retry_count: initial.retry_count,
            }
          : { ...empty }
      );
    }
  }, [open, initial]);

  const num = (k: keyof CoursePayload) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: Number(e.target.value) }));
  const str = (k: keyof CoursePayload) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = () => {
    const payload: any = {
      name: form.name,
      description: form.description || null,
      category: form.category || null,
      trainer: form.trainer || null,
      course_type: form.course_type,
      has_quiz: form.has_quiz,
      passing_percentage: form.passing_percentage,
      quiz_question_count: form.quiz_question_count,
      allow_retry: form.allow_retry,
      retry_count: form.retry_count,
    };
    payload.start_date = form.start_date || null;
    payload.end_date = form.end_date || null;
    onSubmit(payload);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{initial ? "Edit course" : "Create course"}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="space-y-2">
            <Label>Course name</Label>
            <Input value={form.name} onChange={str("name")} placeholder="e.g. POSH Awareness" />
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea value={form.description} onChange={str("description")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Category</Label>
              <Input value={form.category} onChange={str("category")} placeholder="Compliance" />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={form.course_type}
                onValueChange={(v) => setForm((f) => ({ ...f, course_type: v as CourseType }))}
              >
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
            <Label>Trainer <span className="text-xs font-normal text-muted-foreground">(optional)</span></Label>
            <Input value={form.trainer} onChange={str("trainer")} placeholder="e.g. Jane Smith" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Start date</Label>
              <Input type="date" value={form.start_date} onChange={str("start_date")} />
            </div>
            <div className="space-y-2">
              <Label>End date</Label>
              <Input type="date" value={form.end_date} onChange={str("end_date")} />
            </div>
          </div>
          <label className="flex items-center gap-2 rounded-md border bg-muted/30 p-3 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[hsl(var(--primary))]"
              checked={form.has_quiz}
              onChange={(e) => setForm((f) => ({ ...f, has_quiz: e.target.checked }))}
            />
            <span className="font-medium">This course has a quiz</span>
            <span className="text-muted-foreground">— uncheck for view-only courses (completed by finishing the material)</span>
          </label>
          {form.has_quiz && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Passing percentage</Label>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={form.passing_percentage}
                    onChange={num("passing_percentage")}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Quiz question count</Label>
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    value={form.quiz_question_count}
                    onChange={num("quiz_question_count")}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 items-end gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[hsl(var(--primary))]"
                    checked={form.allow_retry}
                    onChange={(e) => setForm((f) => ({ ...f, allow_retry: e.target.checked }))}
                  />
                  Allow retry
                </label>
                <div className="space-y-2">
                  <Label>Retry count</Label>
                  <Input
                    type="number"
                    min={0}
                    max={20}
                    value={form.retry_count}
                    disabled={!form.allow_retry}
                    onChange={num("retry_count")}
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
          <Button onClick={submit} disabled={submitting || !form.name || form.name.length < 2}>
            {submitting && <Spinner />}
            {initial ? "Save changes" : "Create course"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
