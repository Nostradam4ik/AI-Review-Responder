"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  Users,
  CreditCard,
  TrendingUp,
  AlertCircle,
  UserPlus,
  Euro,
  Search,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import { adminApi, usersApi } from "@/lib/api";
import type { AdminStats, AdminUser, AdminUserList } from "@/lib/api";

// ---------------------------------------------------------------------------
// Confirm modal
// ---------------------------------------------------------------------------

interface ConfirmModalProps {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmModal({
  title,
  message,
  confirmLabel = "Confirm",
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-[#111118] border border-[#2A2A3E] rounded-2xl p-6 w-full max-w-sm shadow-xl space-y-4">
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-slate-500 hover:text-white transition"
        >
          <X className="w-4 h-4" />
        </button>
        <h3 className="text-base font-semibold text-white pr-6">{title}</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{message}</p>
        <div className="flex gap-2 pt-1">
          <button
            onClick={onConfirm}
            className={`flex-1 py-2.5 text-white text-sm font-semibold rounded-lg transition active:scale-95 ${
              danger
                ? "bg-rose-600 hover:bg-rose-500"
                : "bg-indigo-600 hover:bg-indigo-500"
            }`}
          >
            {confirmLabel}
          </button>
          <button
            onClick={onCancel}
            className="px-4 py-2.5 border border-[#2A2A3E] text-slate-400 hover:text-white text-sm font-medium rounded-lg transition"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    trialing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    past_due: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    cancelled: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    none: "bg-slate-500/10 text-slate-500 border-slate-500/20",
  };
  const labels: Record<string, string> = {
    active: "Active",
    trialing: "Trial",
    past_due: "Expired",
    cancelled: "Cancelled",
    none: "None",
  };
  const cls = map[status] ?? map.none;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${cls}`}>
      {labels[status] ?? status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// KPI card
// ---------------------------------------------------------------------------

function KpiCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
  color: string;
}) {
  return (
    <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-5 flex items-start gap-4">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wider truncate">{label}</p>
        <p className="text-2xl font-bold text-white mt-0.5">{value}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Change plan inline dropdown
// ---------------------------------------------------------------------------

function ChangePlanDropdown({
  userId,
  currentPlan,
  onDone,
}: {
  userId: string;
  currentPlan: string;
  onDone: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function pick(plan: string) {
    setLoading(true);
    setOpen(false);
    try {
      await adminApi.changePlan(userId, plan, "admin override");
      onDone();
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  const plans = ["starter", "pro", "agency"];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={loading}
        title="Change plan"
        className="flex items-center justify-center w-7 h-7 rounded-md bg-[#1A1A2E] border border-[#2A2A3E] text-slate-400 hover:text-white hover:border-indigo-500/40 transition disabled:opacity-40"
      >
        <Pencil className="w-3 h-3" />
      </button>
      {open && (
        <div className="absolute right-0 top-8 z-20 bg-[#111118] border border-[#2A2A3E] rounded-xl shadow-xl overflow-hidden min-w-[120px]">
          {plans.map((p) => (
            <button
              key={p}
              onClick={() => pick(p)}
              className={`w-full text-left px-3 py-2 text-xs font-medium transition-colors ${
                p === currentPlan.toLowerCase()
                  ? "text-indigo-400 bg-indigo-500/10"
                  : "text-slate-300 hover:bg-[#1A1A2E] hover:text-white"
              }`}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton row
// ---------------------------------------------------------------------------

function SkeletonRow() {
  return (
    <tr className="border-b border-[#2A2A3E]">
      {[180, 80, 80, 60, 50, 60, 90, 100].map((w, i) => (
        <td key={i} className="px-4 py-3">
          <div className={`h-3 bg-[#1A1A2E] rounded animate-pulse`} style={{ width: w }} />
        </td>
      ))}
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const STATUS_TABS = [
  { key: "all", label: "All" },
  { key: "trial", label: "Trial" },
  { key: "active", label: "Active" },
  { key: "expired", label: "Expired" },
  { key: "cancelled", label: "Cancelled" },
];

export default function AdminPage() {
  const router = useRouter();

  // Access guard
  const [accessChecked, setAccessChecked] = useState(false);

  // Stats
  const [stats, setStats] = useState<AdminStats | null>(null);

  // Users table
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [tableLoading, setTableLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Confirm modal state
  const [confirm, setConfirm] = useState<{
    title: string;
    message: string;
    confirmLabel: string;
    danger: boolean;
    onConfirm: () => void;
  } | null>(null);

  // ── Access guard ──────────────────────────────────────────────────────────
  useEffect(() => {
    usersApi.me()
      .then((u) => {
        if (!u.is_admin) {
          router.replace("/dashboard");
        } else {
          setAccessChecked(true);
        }
      })
      .catch(() => router.replace("/dashboard"));
  }, [router]);

  // ── Stats ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!accessChecked) return;
    adminApi.stats().then(setStats).catch(() => {});
  }, [accessChecked]);

  // ── Debounce search ───────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  // ── Users list ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!accessChecked) return;
    setTableLoading(true);
    adminApi
      .users({ search: debouncedSearch || undefined, status: statusFilter, page, limit: 20 })
      .then((d: AdminUserList) => {
        setUsers(d.users);
        setTotal(d.total);
        setPages(d.pages);
      })
      .catch(() => {})
      .finally(() => setTableLoading(false));
  }, [accessChecked, debouncedSearch, statusFilter, page]);

  function refreshUsers() {
    setTableLoading(true);
    adminApi
      .users({ search: debouncedSearch || undefined, status: statusFilter, page, limit: 20 })
      .then((d: AdminUserList) => {
        setUsers(d.users);
        setTotal(d.total);
        setPages(d.pages);
      })
      .catch(() => {})
      .finally(() => setTableLoading(false));
    adminApi.stats().then(setStats).catch(() => {});
  }

  // ── Actions ───────────────────────────────────────────────────────────────
  function handleResetTrial(user: AdminUser) {
    setConfirm({
      title: "Reset trial",
      message: `Reset the 14-day trial for ${user.name || user.email}? Their subscription status will become "trialing".`,
      confirmLabel: "Reset trial",
      danger: false,
      onConfirm: async () => {
        setConfirm(null);
        await adminApi.resetTrial(user.id, 14).catch(() => {});
        refreshUsers();
      },
    });
  }

  function handleDelete(user: AdminUser) {
    setConfirm({
      title: "Delete user",
      message: `Permanently delete ${user.name || user.email}? Their account will be anonymised and they will not be able to log in. This cannot be undone.`,
      confirmLabel: "Delete",
      danger: true,
      onConfirm: async () => {
        setConfirm(null);
        await adminApi.deleteUser(user.id).catch(() => {});
        refreshUsers();
      },
    });
  }

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (!accessChecked) {
    return (
      <div className="space-y-6 max-w-7xl">
        <div className="h-8 w-32 bg-[#1A1A2E] rounded-lg animate-pulse" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-[84px] bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-72 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Shield className="w-5 h-5 text-rose-400" />
        <h1 className="text-2xl font-semibold text-white tracking-tight">Admin</h1>
      </div>

      {/* ── Stats grid ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard
          icon={Users}
          label="Total Users"
          value={stats?.total_users ?? "—"}
          color="bg-indigo-500/10 text-indigo-400"
        />
        <KpiCard
          icon={CreditCard}
          label="Active Subs"
          value={stats?.active_subscriptions ?? "—"}
          color="bg-emerald-500/10 text-emerald-400"
        />
        <KpiCard
          icon={TrendingUp}
          label="Trial Users"
          value={stats?.trial_users ?? "—"}
          color="bg-blue-500/10 text-blue-400"
        />
        <KpiCard
          icon={AlertCircle}
          label="Expired Trials"
          value={stats?.expired_trials ?? "—"}
          color="bg-rose-500/10 text-rose-400"
        />
        <KpiCard
          icon={Euro}
          label="MRR"
          value={
            stats
              ? `€${stats.mrr.toLocaleString("fr-FR", { minimumFractionDigits: 0 })}`
              : "—"
          }
          color="bg-amber-500/10 text-amber-400"
        />
        <KpiCard
          icon={UserPlus}
          label="New This Week"
          value={stats?.new_users_this_week ?? "—"}
          color="bg-violet-500/10 text-violet-400"
        />
      </div>

      {/* ── Users table ── */}
      <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl overflow-hidden">
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4 border-b border-[#2A2A3E]">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search email or name…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-8 pr-3 py-2 bg-[#0A0A0F] border border-[#2A2A3E] rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition"
            />
          </div>

          {/* Status tabs */}
          <div className="flex items-center gap-1 flex-wrap">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => { setStatusFilter(tab.key); setPage(1); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  statusFilter === tab.key
                    ? "bg-indigo-600 text-white"
                    : "text-slate-400 hover:text-white hover:bg-[#1A1A2E]"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <p className="text-xs text-slate-500 ml-auto whitespace-nowrap">{total} user{total !== 1 ? "s" : ""}</p>
        </div>

        {/* Table (horizontally scrollable on mobile) */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-sm">
            <thead>
              <tr className="border-b border-[#2A2A3E] text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3 font-medium">User</th>
                <th className="text-left px-4 py-3 font-medium">Plan</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-right px-4 py-3 font-medium">Trial days</th>
                <th className="text-right px-4 py-3 font-medium">Locs</th>
                <th className="text-right px-4 py-3 font-medium">Reviews</th>
                <th className="text-left px-4 py-3 font-medium">Joined</th>
                <th className="text-right px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tableLoading ? (
                Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-16 text-center">
                    <div className="flex flex-col items-center gap-3 text-slate-500">
                      <Search className="w-8 h-8 opacity-30" />
                      <p className="text-sm">No users found</p>
                    </div>
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <UserRow
                    key={u.id}
                    user={u}
                    onResetTrial={() => handleResetTrial(u)}
                    onDelete={() => handleDelete(u)}
                    onPlanChanged={refreshUsers}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-[#2A2A3E]">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Previous
            </button>
            <span className="text-xs text-slate-500">
              Page {page} of {pages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Confirm modal */}
      {confirm && (
        <ConfirmModal
          title={confirm.title}
          message={confirm.message}
          confirmLabel={confirm.confirmLabel}
          danger={confirm.danger}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// User table row (extracted to avoid inline closure re-renders)
// ---------------------------------------------------------------------------

function UserRow({
  user,
  onResetTrial,
  onDelete,
  onPlanChanged,
}: {
  user: AdminUser;
  onResetTrial: () => void;
  onDelete: () => void;
  onPlanChanged: () => void;
}) {
  const initials = (user.name || user.email).slice(0, 2).toUpperCase();
  const joined = new Date(user.created_at).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  // Determine real display status (expired trials show as expired)
  const displayStatus =
    user.subscription_status === "trialing" && !user.is_trial
      ? "past_due"
      : user.subscription_status;

  return (
    <tr className="border-b border-[#2A2A3E]/60 hover:bg-[#0A0A0F]/40 transition-colors">
      {/* User */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[10px] font-bold shrink-0">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-medium text-white truncate max-w-[160px]">
              {user.name || <span className="text-slate-500 italic">no name</span>}
            </p>
            <p className="text-[11px] text-slate-500 truncate max-w-[160px]">{user.email}</p>
          </div>
          {user.is_admin && (
            <span className="ml-1 text-[10px] font-bold text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded px-1 py-0.5 leading-none shrink-0">
              ADMIN
            </span>
          )}
        </div>
      </td>

      {/* Plan */}
      <td className="px-4 py-3">
        <span className="text-xs text-slate-300">{user.plan_name}</span>
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <StatusBadge status={displayStatus} />
      </td>

      {/* Trial days */}
      <td className="px-4 py-3 text-right">
        {user.is_trial && user.trial_days_remaining !== null ? (
          <span className={`text-xs font-medium ${user.trial_days_remaining <= 3 ? "text-amber-400" : "text-slate-300"}`}>
            {user.trial_days_remaining}d
          </span>
        ) : (
          <span className="text-xs text-slate-600">—</span>
        )}
      </td>

      {/* Locations */}
      <td className="px-4 py-3 text-right">
        <span className="text-xs text-slate-300">{user.locations_count}</span>
      </td>

      {/* Reviews */}
      <td className="px-4 py-3 text-right">
        <span className="text-xs text-slate-300">{user.reviews_count}</span>
      </td>

      {/* Joined */}
      <td className="px-4 py-3">
        <span className="text-xs text-slate-400">{joined}</span>
      </td>

      {/* Actions */}
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-1.5">
          {/* Reset trial */}
          <button
            onClick={onResetTrial}
            title="Reset trial"
            className="flex items-center justify-center w-7 h-7 rounded-md bg-[#1A1A2E] border border-[#2A2A3E] text-slate-400 hover:text-white hover:border-indigo-500/40 transition"
          >
            <RotateCcw className="w-3 h-3" />
          </button>

          {/* Change plan */}
          <ChangePlanDropdown
            userId={user.id}
            currentPlan={user.plan_name}
            onDone={onPlanChanged}
          />

          {/* Delete */}
          {!user.is_admin && (
            <button
              onClick={onDelete}
              title="Delete user"
              className="flex items-center justify-center w-7 h-7 rounded-md bg-[#1A1A2E] border border-[#2A2A3E] text-slate-400 hover:text-rose-400 hover:border-rose-500/40 transition"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
