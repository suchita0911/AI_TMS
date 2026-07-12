import {
  LayoutDashboard,
  Users,
  Building2,
  UsersRound,
  BookOpen,
  BarChart3,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import type { Role } from "@/types";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  roles: Role[];
}

// Nav grows as new phases land. Each item is gated by role.
export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard, roles: ["admin", "employee"] },
  { label: "My Courses", to: "/my-courses", icon: BookOpen, roles: ["employee"] },
  { label: "Courses", to: "/admin/courses", icon: BookOpen, roles: ["admin"] },
  { label: "Trending", to: "/admin/trending", icon: TrendingUp, roles: ["admin"] },
  { label: "Employees", to: "/admin/employees", icon: Users, roles: ["admin"] },
  { label: "Departments", to: "/admin/departments", icon: Building2, roles: ["admin"] },
  { label: "Groups", to: "/admin/groups", icon: UsersRound, roles: ["admin"] },
  { label: "Reports", to: "/admin/reports", icon: BarChart3, roles: ["admin"] },
];
