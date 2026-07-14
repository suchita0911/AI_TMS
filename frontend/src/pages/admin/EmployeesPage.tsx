import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, MoreHorizontal, UserCheck, UserX, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { UserStatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, apiError } from "@/lib/api";
import { DesignationSelect } from "@/components/DesignationSelect";
import { useConfirm } from "@/components/ConfirmDialog";
import { notifyDeleted } from "@/lib/notify";
import { useAuth } from "@/context/AuthContext";
import type { DepartmentBrief, Page, User } from "@/types";

const PAGE_SIZE = 10;
const emptyForm = {
  first_name: "",
  last_name: "",
  email: "",
  employee_id: "",
  designation: "",
  department_id: "",
  role: "employee",
  password: "",
};

const emptyEditForm = {
  first_name: "",
  last_name: "",
  email: "",
  employee_id: "",
  designation: "",
  department_id: "",
  role: "employee",
  password: "",
};

export default function EmployeesPage() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const { user: currentUser } = useAuth();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [editing, setEditing] = useState<User | null>(null);
  const [editForm, setEditForm] = useState({ ...emptyEditForm });

  const { data, isLoading } = useQuery({
    queryKey: ["users", { search, page }],
    queryFn: async () =>
      (
        await api.get<Page<User>>("/users", {
          params: { q: search || undefined, page, page_size: PAGE_SIZE },
        })
      ).data,
  });

  const departments = useQuery({
    queryKey: ["departments", "all"],
    queryFn: async () =>
      (await api.get<Page<{ id: number; name: string }>>("/departments", { params: { page_size: 100 } })).data,
  });

  const createUser = useMutation({
    mutationFn: async () => {
      const employeeId = form.employee_id.trim();
      if (!employeeId) {
        throw new Error("Employee ID is required.");
      }
      const payload: any = {
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email.trim(),
        role: form.role,
        employee_id: employeeId,
      };
      if (form.designation) payload.designation = form.designation;
      if (form.department_id) payload.department_id = Number(form.department_id);
      if (form.password) payload.password = form.password;
      return (await api.post<User & { setup_token?: string | null }>("/users", payload)).data;
    },
    onSuccess: () => {
      setDialogOpen(false);
      setForm({ ...emptyForm });
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("Employee created");
    },
    onError: (e) => toast.error(apiError(e, "Could not create user")),
  });

  const updateUser = useMutation({
    mutationFn: async () => {
      if (!editing) return;
      const payload: any = {
        first_name: editForm.first_name,
        last_name: editForm.last_name,
        email: editForm.email.trim(),
        role: editForm.role,
        designation: editForm.designation || null,
        department_id: editForm.department_id ? Number(editForm.department_id) : null,
        employee_id: editForm.employee_id || null,
      };
      if (editForm.password) payload.password = editForm.password;
      return (await api.patch<User>(`/users/${editing.id}`, payload)).data;
    },
    onSuccess: () => {
      toast.success("Employee updated");
      setEditing(null);
      qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e) => toast.error(apiError(e, "Could not update user")),
  });

  const openEdit = (u: User) => {
    setEditForm({
      first_name: u.first_name,
      last_name: u.last_name,
      email: u.email,
      employee_id: u.employee_id ?? "",
      designation: u.designation ?? "",
      department_id: u.department?.id ? String(u.department.id) : "",
      role: u.role,
      password: "",
    });
    setEditing(u);
  };

  const toggleActive = useMutation({
    mutationFn: async (u: User) =>
      api.post(`/users/${u.id}/${u.is_active ? "deactivate" : "activate"}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("Updated");
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const deleteUser = useMutation({
    mutationFn: async (u: User) => api.delete(`/users/${u.id}`),
    onSuccess: (_d, u) => {
      notifyDeleted("Employee", `${u.first_name} ${u.last_name}`);
      qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e) => toast.error(apiError(e, "Could not delete employee")),
  });

  const setField = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const setEditField = (k: keyof typeof editForm) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setEditForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div>
      <PageHeader
        title="Employees"
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" /> Add employee
          </Button>
        }
      />

      <Card>
        <div className="border-b p-4">
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search name, username or email…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center p-10">
            <Spinner className="h-6 w-6" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                    No employees found
                  </TableCell>
                </TableRow>
              )}
              {data?.items.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>
                    <Link
                      to={`/admin/employees/${u.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {u.first_name} {u.last_name}
                    </Link>
                    <div className="text-xs text-muted-foreground">{u.email}</div>
                  </TableCell>
                  <TableCell>{u.username}</TableCell>
                  <TableCell>{u.department?.name ?? "—"}</TableCell>
                  <TableCell>
                    <Badge variant={u.role === "admin" ? "default" : "secondary"}>{u.role}</Badge>
                  </TableCell>
                  <TableCell>
                    <UserStatusBadge status={u.status} />
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEdit(u)}>
                          <Pencil className="h-4 w-4" /> Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => toggleActive.mutate(u)}>
                          {u.is_active ? (
                            <>
                              <UserX className="h-4 w-4" /> Deactivate
                            </>
                          ) : (
                            <>
                              <UserCheck className="h-4 w-4" /> Activate
                            </>
                          )}
                        </DropdownMenuItem>
                        {currentUser?.id !== u.id && (
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={async () => {
                              if (
                                await confirm({
                                  title: "Delete employee",
                                  description: `Permanently delete ${u.first_name} ${u.last_name}? This removes their account and all their records, and can’t be undone.`,
                                  confirmText: "Delete",
                                })
                              )
                                deleteUser.mutate(u);
                            }}
                          >
                            <Trash2 className="h-4 w-4" /> Delete
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {data && (
          <div className="border-t px-4">
            <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPage={setPage} />
          </div>
        )}
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add employee</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>First name</Label>
                <Input value={form.first_name} onChange={setField("first_name")} />
              </div>
              <div className="space-y-2">
                <Label>Last name</Label>
                <Input value={form.last_name} onChange={setField("last_name")} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input type="email" value={form.email} onChange={setField("email")} />
              </div>
              <div className="space-y-2">
                <Label>Employee ID <span className="text-destructive">*</span></Label>
                <Input value={form.employee_id} onChange={setField("employee_id")} required />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Department</Label>
                <Select
                  value={form.department_id}
                  onValueChange={(v) => setForm((f) => ({ ...f, department_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select" />
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
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={form.role} onValueChange={(v) => setForm((f) => ({ ...f, role: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="employee">Employee</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Designation</Label>
              <DesignationSelect
                value={form.designation}
                onChange={(v) => setForm((f) => ({ ...f, designation: v }))}
                allowAdd
              />
              <p className="text-xs text-muted-foreground">
                Used to tailor AI course recommendations to the employee's role.
              </p>
            </div>
            <div className="space-y-2">
              <Label>Temporary password (optional)</Label>
              <Input
                type="password"
                value={form.password}
                onChange={setField("password")}
                placeholder="Leave blank to send a setup link"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => createUser.mutate()} disabled={createUser.isPending}>
              {createUser.isPending && <Spinner />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit employee */}
      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit employee</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>First name</Label>
                <Input value={editForm.first_name} onChange={setEditField("first_name")} />
              </div>
              <div className="space-y-2">
                <Label>Last name</Label>
                <Input value={editForm.last_name} onChange={setEditField("last_name")} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" value={editForm.email} onChange={setEditField("email")} />
            </div>
            <div className="space-y-2">
              <Label>Employee ID</Label>
              <Input value={editForm.employee_id} onChange={setEditField("employee_id")} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Department</Label>
                <Select
                  value={editForm.department_id}
                  onValueChange={(v) => setEditForm((f) => ({ ...f, department_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select" />
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
              <div className="space-y-2">
                <Label>Role</Label>
                <Select
                  value={editForm.role}
                  onValueChange={(v) => setEditForm((f) => ({ ...f, role: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="employee">Employee</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Designation</Label>
              <DesignationSelect
                value={editForm.designation}
                onChange={(v) => setEditForm((f) => ({ ...f, designation: v }))}
                allowAdd
              />
            </div>
            <div className="space-y-2">
              <Label>Set / reset password (optional)</Label>
              <Input
                type="password"
                value={editForm.password}
                onChange={setEditField("password")}
                placeholder="Leave blank to keep current password"
              />
              <p className="text-xs text-muted-foreground">
                Setting a password activates a pending account so the employee can sign in.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button onClick={() => updateUser.mutate()} disabled={updateUser.isPending}>
              {updateUser.isPending && <Spinner />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
