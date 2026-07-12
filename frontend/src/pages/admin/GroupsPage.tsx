import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, apiError } from "@/lib/api";
import type { Group, Page, User } from "@/types";

export default function GroupsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Group | null>(null);
  const [form, setForm] = useState({ name: "", description: "" });
  const [memberIds, setMemberIds] = useState<number[]>([]);

  const { data, isLoading } = useQuery({
    queryKey: ["groups"],
    queryFn: async () =>
      (await api.get<Page<Group>>("/groups", { params: { page_size: 100 } })).data,
  });

  const users = useQuery({
    queryKey: ["users", "all-for-groups"],
    queryFn: async () =>
      (await api.get<Page<User>>("/users", { params: { page_size: 100 } })).data,
    enabled: open,
  });

  useEffect(() => {
    if (open && editing) {
      api
        .get<User[]>(`/groups/${editing.id}/members`)
        .then((r) => setMemberIds(r.data.map((u) => u.id)))
        .catch(() => setMemberIds([]));
    }
  }, [open, editing]);

  const save = useMutation({
    mutationFn: async () => {
      const body = { name: form.name, description: form.description || null, member_ids: memberIds };
      if (editing) return api.patch(`/groups/${editing.id}`, body);
      return api.post("/groups", body);
    },
    onSuccess: () => {
      toast.success(editing ? "Group updated" : "Group created");
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["groups"] });
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const remove = useMutation({
    mutationFn: async (id: number) => api.delete(`/groups/${id}`),
    onSuccess: () => {
      toast.success("Group deleted");
      qc.invalidateQueries({ queryKey: ["groups"] });
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", description: "" });
    setMemberIds([]);
    setOpen(true);
  };
  const openEdit = (g: Group) => {
    setEditing(g);
    setForm({ name: g.name, description: g.description ?? "" });
    setMemberIds([]);
    setOpen(true);
  };

  const toggleMember = (id: number) =>
    setMemberIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));

  return (
    <div>
      <PageHeader
        title="Groups"
        description="Create cross-department groups for targeted assignment"
        actions={
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> New group
          </Button>
        }
      />
      <Card>
        {isLoading ? (
          <div className="flex justify-center p-10">
            <Spinner className="h-6 w-6" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Members</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center text-muted-foreground">
                    No groups yet
                  </TableCell>
                </TableRow>
              )}
              {data?.items.map((g) => (
                <TableRow key={g.id}>
                  <TableCell className="font-medium">{g.name}</TableCell>
                  <TableCell className="text-muted-foreground">{g.description ?? "—"}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      <Users className="mr-1 h-3 w-3" /> {g.member_count}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(g)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        onClick={() => {
                          if (confirm(`Delete group "${g.name}"?`)) remove.mutate(g.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Edit group" : "New group"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Members ({memberIds.length} selected)</Label>
              <div className="max-h-52 overflow-y-auto rounded-md border p-1">
                {users.isLoading && (
                  <div className="flex justify-center p-4">
                    <Spinner />
                  </div>
                )}
                {users.data?.items.map((u) => (
                  <label
                    key={u.id}
                    className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-[hsl(var(--primary))]"
                      checked={memberIds.includes(u.id)}
                      onChange={() => toggleMember(u.id)}
                    />
                    <span className="flex-1">
                      {u.first_name} {u.last_name}
                    </span>
                    <span className="text-xs text-muted-foreground">{u.department?.name ?? "—"}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => save.mutate()} disabled={save.isPending || !form.name}>
              {save.isPending && <Spinner />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
