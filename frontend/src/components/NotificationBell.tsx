import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Bell, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api";
import { cn, formatDateTime } from "@/lib/utils";
import type { AppNotification } from "@/types";

export function NotificationBell() {
  const qc = useQueryClient();

  const unread = useQuery({
    queryKey: ["notif-unread"],
    queryFn: async () =>
      (await api.get<{ unread: number }>("/me/notifications/unread-count")).data.unread,
    refetchInterval: 30_000,
  });

  const list = useQuery({
    queryKey: ["notifications"],
    queryFn: async () => (await api.get<AppNotification[]>("/me/notifications")).data,
  });

  const markRead = useMutation({
    mutationFn: async (id: number) => api.post(`/me/notifications/${id}/read`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notif-unread"] });
    },
  });

  const markAll = useMutation({
    mutationFn: async () => api.post("/me/notifications/read-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notif-unread"] });
    },
  });

  const count = unread.data ?? 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="relative flex h-10 w-10 items-center justify-center rounded-md hover:bg-accent">
          <Bell className="h-5 w-5" />
          {count > 0 && (
            <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
              {count > 9 ? "9+" : count}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between border-b px-3 py-2">
          <span className="text-sm font-semibold">Notifications</span>
          {count > 0 && (
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => markAll.mutate()}>
              <CheckCheck className="h-3.5 w-3.5" /> Mark all read
            </Button>
          )}
        </div>
        <div className="max-h-96 overflow-y-auto">
          {list.data && list.data.length > 0 ? (
            list.data.map((n) => {
              const body = (
                <div
                  className={cn(
                    "border-b px-3 py-2.5 text-sm last:border-0",
                    !n.is_read && "bg-primary/5"
                  )}
                  onClick={() => !n.is_read && markRead.mutate(n.id)}
                >
                  <div className="flex items-start gap-2">
                    {!n.is_read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" />}
                    <div className="min-w-0">
                      <p className="font-medium">{n.title}</p>
                      <p className="line-clamp-2 text-xs text-muted-foreground">{n.message}</p>
                      <p className="mt-0.5 text-[10px] text-muted-foreground">
                        {formatDateTime(n.created_at)}
                      </p>
                    </div>
                  </div>
                </div>
              );
              return n.course_id ? (
                <Link key={n.id} to={`/my-courses/${n.course_id}`} className="block cursor-pointer hover:bg-accent">
                  {body}
                </Link>
              ) : (
                <div key={n.id} className="cursor-pointer hover:bg-accent">
                  {body}
                </div>
              );
            })
          ) : (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">No notifications</p>
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
