import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { AuthShell } from "./AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, apiError } from "@/lib/api";
import type { DepartmentBrief } from "@/types";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [departments, setDepartments] = useState<DepartmentBrief[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    employee_id: "",
    department_id: "",
  });

  useEffect(() => {
    api
      .get<DepartmentBrief[]>("/auth/departments")
      .then((r) => setDepartments(r.data))
      .catch(() => void 0);
  }, []);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload: any = {
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email.trim(),
        employee_id: form.employee_id.trim(),
      };
      if (form.department_id) payload.department_id = Number(form.department_id);
      await api.post("/auth/register", payload);
      toast.success(
        "Registration successful. Check your email for a link to set your password.",
      );
      navigate("/login", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Registration failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Create your account"
      subtitle="Register to start your training journey"
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label htmlFor="first_name">First name</Label>
            <Input id="first_name" value={form.first_name} onChange={set("first_name")} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="last_name">Last name</Label>
            <Input id="last_name" value={form.last_name} onChange={set("last_name")} required />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" value={form.email} onChange={set("email")} required />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label htmlFor="employee_id">Employee ID</Label>
            <Input id="employee_id" value={form.employee_id} onChange={set("employee_id")} required />
          </div>
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
                {departments.map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          We'll email you a secure link to set your password.
        </p>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading && <Spinner />}
          Register
        </Button>
      </form>
    </AuthShell>
  );
}
