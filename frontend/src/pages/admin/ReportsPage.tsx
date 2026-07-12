import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  BookOpen,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  FileSpreadsheet,
  FileText,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, apiError } from "@/lib/api";

interface Overview {
  total_courses: number;
  active_courses: number;
  total_enrollments: number;
  completed: number;
  failed: number;
  in_progress: number;
  overdue: number;
  completion_rate: number;
  average_score: number;
  pass_percentage: number;
  fail_percentage: number;
}
interface DeptRow {
  department: string;
  total: number;
  completed: number;
  completion_rate: number;
}
interface EmpRow {
  user_id: number;
  name: string;
  email: string;
  department?: string | null;
  assigned: number;
  completed: number;
  completion_rate: number;
  average_score?: number | null;
}

export default function ReportsPage() {
  const overview = useQuery({
    queryKey: ["report-overview"],
    queryFn: async () => (await api.get<Overview>("/reports/overview")).data,
  });
  const depts = useQuery({
    queryKey: ["report-depts"],
    queryFn: async () => (await api.get<DeptRow[]>("/reports/departments")).data,
  });
  const emps = useQuery({
    queryKey: ["report-emps"],
    queryFn: async () => (await api.get<EmpRow[]>("/reports/employees")).data,
  });
  const trend = useQuery({
    queryKey: ["report-trend"],
    queryFn: async () =>
      (await api.get<{ month: string; completed: number }[]>("/reports/trend")).data,
  });

  const download = async (fmt: "excel" | "pdf") => {
    try {
      const res = await api.get(`/reports/export/${fmt}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fmt === "excel" ? "tms_report.xlsx" : "tms_report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(apiError(e, "Export failed"));
    }
  };

  if (overview.isLoading) return <PageLoader />;
  const o = overview.data!;

  return (
    <div>
      <PageHeader
        title="Reports & Analytics"
        description="Organisation-wide training insights"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => download("excel")}>
              <FileSpreadsheet className="h-4 w-4" /> Excel
            </Button>
            <Button variant="outline" onClick={() => download("pdf")}>
              <FileText className="h-4 w-4" /> PDF
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Courses" value={o.total_courses} icon={BookOpen} hint={`${o.active_courses} active`} />
        <StatCard label="Completed" value={o.completed} icon={CheckCircle2} tone="success" hint={`${o.completion_rate}% completion`} />
        <StatCard label="Failed" value={o.failed} icon={XCircle} tone="destructive" />
        <StatCard label="Overdue" value={o.overdue} icon={Clock} tone="warning" />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Enrollments" value={o.total_enrollments} icon={BookOpen} />
        <StatCard label="In Progress" value={o.in_progress} icon={Clock} tone="primary" />
        <StatCard label="Avg Score" value={`${o.average_score}%`} icon={TrendingUp} tone="success" />
        <StatCard label="Pass Rate" value={`${o.pass_percentage}%`} icon={CheckCircle2} tone="success" hint={`${o.fail_percentage}% fail`} />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Department completion</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {depts.data && depts.data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={depts.data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="department" fontSize={12} stroke="hsl(var(--muted-foreground))" />
                  <YAxis fontSize={12} stroke="hsl(var(--muted-foreground))" />
                  <Tooltip />
                  <Bar dataKey="completion_rate" name="Completion %" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Completion trend</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {trend.data && trend.data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trend.data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" fontSize={12} stroke="hsl(var(--muted-foreground))" />
                  <YAxis fontSize={12} stroke="hsl(var(--muted-foreground))" allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="completed" name="Completed" stroke="hsl(var(--primary))" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <Empty />
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-5">
        <CardHeader>
          <CardTitle className="text-base">Employee progress</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Assigned</TableHead>
                <TableHead>Completed</TableHead>
                <TableHead>Completion %</TableHead>
                <TableHead>Avg Score</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {emps.data?.map((e) => (
                <TableRow key={e.user_id}>
                  <TableCell>
                    <div className="font-medium">{e.name}</div>
                    <div className="text-xs text-muted-foreground">{e.email}</div>
                  </TableCell>
                  <TableCell>{e.department ?? "—"}</TableCell>
                  <TableCell>{e.assigned}</TableCell>
                  <TableCell>{e.completed}</TableCell>
                  <TableCell>{e.completion_rate}%</TableCell>
                  <TableCell>{e.average_score != null ? `${e.average_score}%` : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function Empty() {
  return (
    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
      No data yet
    </div>
  );
}
