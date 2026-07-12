import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { api } from "@/lib/api";
import type { AssignmentTargetType, Department, Group, Page, User } from "@/types";

export interface AssignPayload {
  target_type: AssignmentTargetType;
  department_id?: number;
  group_id?: number;
  user_ids?: number[];
}

export function AssignDialog({
  open,
  onOpenChange,
  onAssign,
  submitting,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onAssign: (p: AssignPayload) => void;
  submitting: boolean;
}) {
  const [target, setTarget] = useState<AssignmentTargetType>("all");
  const [deptId, setDeptId] = useState<string>("");
  const [groupId, setGroupId] = useState<string>("");
  const [userIds, setUserIds] = useState<number[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (open) {
      setTarget("all");
      setDeptId("");
      setGroupId("");
      setUserIds([]);
      setSearch("");
    }
  }, [open]);

  const departments = useQuery({
    queryKey: ["departments", "assign"],
    queryFn: async () =>
      (await api.get<Page<Department>>("/departments", { params: { page_size: 100 } })).data,
    enabled: open,
  });
  const groups = useQuery({
    queryKey: ["groups", "assign"],
    queryFn: async () => (await api.get<Page<Group>>("/groups", { params: { page_size: 100 } })).data,
    enabled: open,
  });
  const employees = useQuery({
    queryKey: ["users", "assign", search],
    queryFn: async () =>
      (
        await api.get<Page<User>>("/users", {
          params: { role: "employee", q: search || undefined, page_size: 100 },
        })
      ).data,
    enabled: open && target === "individual",
  });

  const canSubmit =
    target === "all" ||
    (target === "department" && deptId) ||
    (target === "group" && groupId) ||
    (target === "individual" && userIds.length > 0);

  const submit = () => {
    const p: AssignPayload = { target_type: target };
    if (target === "department") p.department_id = Number(deptId);
    if (target === "group") p.group_id = Number(groupId);
    if (target === "individual") p.user_ids = userIds;
    onAssign(p);
  };

  const toggleUser = (id: number) =>
    setUserIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign course</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="space-y-2">
            <Label>Assign to</Label>
            <Select value={target} onValueChange={(v) => setTarget(v as AssignmentTargetType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All employees</SelectItem>
                <SelectItem value="department">A department</SelectItem>
                <SelectItem value="group">A group</SelectItem>
                <SelectItem value="individual">Specific employees</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {target === "department" && (
            <div className="space-y-2">
              <Label>Department</Label>
              <Select value={deptId} onValueChange={setDeptId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select department" />
                </SelectTrigger>
                <SelectContent>
                  {departments.data?.items.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {target === "group" && (
            <div className="space-y-2">
              <Label>Group</Label>
              <Select value={groupId} onValueChange={setGroupId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select group" />
                </SelectTrigger>
                <SelectContent>
                  {groups.data?.items.map((g) => (
                    <SelectItem key={g.id} value={String(g.id)}>
                      {g.name} ({g.member_count})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {target === "individual" && (
            <div className="space-y-2">
              <Label>Employees ({userIds.length} selected)</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-9"
                  placeholder="Search employees…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <div className="max-h-56 overflow-y-auto rounded-md border p-1">
                {employees.isLoading && (
                  <div className="flex justify-center p-4">
                    <Spinner />
                  </div>
                )}
                {employees.data?.items.map((u) => (
                  <label
                    key={u.id}
                    className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-[hsl(var(--primary))]"
                      checked={userIds.includes(u.id)}
                      onChange={() => toggleUser(u.id)}
                    />
                    <span className="flex-1">
                      {u.first_name} {u.last_name}
                    </span>
                    <span className="text-xs text-muted-foreground">{u.department?.name ?? "—"}</span>
                  </label>
                ))}
                {employees.data?.items.length === 0 && (
                  <p className="p-3 text-center text-xs text-muted-foreground">No employees</p>
                )}
              </div>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={submitting || !canSubmit}>
            {submitting && <Spinner />}
            Assign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
