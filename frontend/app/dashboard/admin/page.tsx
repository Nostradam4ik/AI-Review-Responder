"use client";

import { useEffect, useState } from "react";
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
  AlertTriangle,
} from "lucide-react";
import { adminApi, usersApi } from "@/lib/api";
import type { AdminStats, AdminUser, AdminUserList } from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function dateToInput(iso: string | null | undefined): string {
  if (!iso) return "";
  return iso.slice(0, 10); // "YYYY-MM-DD"
}

function inputToISO(date: string, endOfDay = false): string | null {
  if (!date) return null;
  return date + (endOfDay ? "T23:59:59Z" : "T00:00:00Z");
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

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
        <button onClick={onCancel} className="absolute top-4 right-4 text-slate-500 hover:text-white transition">
          <X className="w-4 h-4" />
        </button>
        <h3 className="text-base font-semibold text-white pr-6">{title}</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{message}</p>
        <div className="flex gap-2 pt-1">
          <button
            onClick={onConfirm}
            className={`flex-1 py-2.5 text-white text-sm font-semibold rounded-lg transition active:scale-95 ${
              danger ? "bg-rose-600 hover:bg-rose-500" : "bg-indigo-600 hover:bg-indigo-500"
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
// Edit user modal
// ---------------------------------------------------------------------------

function EditUserModal({
  user,
  onClose,
  onSaved,
}: {
  user: AdminUser;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isExpiredTrial = user.subscription_status === "trialing" && !user.is_trial;

  const [plan, setPlan] = useState(user.plan_name.toLowerCase());
  const [status, setStatus] = useState(
    isExpiredTrial ? "expired" : user.subscription_status === "none" ? "active" : user.subscription_status
  );
  const [subStart, setSubStart] = useState(dateToInput(user.subscription_start));
  const [subEnd, setSubEnd] = useState(dateToInput(user.subscription_end));
  const [noExpiry, setNoExpiry] = useState(
    user.subscription_status === "active" && user.subscription_end === null
  );
  const [trialEnd, setTrialEnd] = useState(dateToInput(user.trial_end));
  const [trialDays, setTrialDays] = useState("");
  const [unlimitedAi, setUnlimitedAi] = useState(user.ai_responses_limit === -1);
  const [aiLimit, setAiLimit] = useState(
    user.ai_responses_limit !== null && user.ai_responses_limit !== -1
      ? String(user.ai_responses_limit)
      : ""
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Quick trial-days helper → auto-fill trial end date
  useEffect(() => {
    const n = parseInt(trialDays);
    if (!n || n <= 0) return;
    const d = new Date();
    d.setDate(d.getDate() + n);
    setTrialEnd(d.toISOString().slice(0, 10));
  }, [trialDays]);

  // When switching to trialing, pre-fill trial end if empty
  useEffect(() => {
    if (status === "trialing" && !trialEnd) {
      const d = new Date();
      d.setDate(d.getDate() + 14);
      setTrialEnd(d.toISOString().slice(0, 10));
    }
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit() {
    if (status === "trialing" && !trialEnd) {
      setError("Trial end date is required when status is Trial.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await adminApi.editUser(user.id, {
        plan: plan || undefined,
        status: status || undefined,
        subscription_start: inputToISO(subStart) ?? undefined,
        subscription_end: noExpiry ? null : inputToISO(subEnd, true),
        trial_end: status === "trialing" ? inputToISO(trialEnd, true) : undefined,
        ai_responses_limit: unlimitedAi ? -1 : (aiLimit ? parseInt(aiLimit) : null),
      });
      onSaved();
      onClose();
    } catch {
      setError("Failed to save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const fieldCls =
    "w-full px-3 py-2 bg-[#0A0A0F] border border-[#2A2A3E] rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500/60 transition";
  const labelCls = "block text-xs font-medium text-slate-400 mb-1.5";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#111118] border border-[#2A2A3E] rounded-2xl w-full max-w-md shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2A2A3E]">
          <div>
            <h3 className="text-sm font-semibold text-white">Edit subscription</h3>
            <p className="text-[11px] text-slate-500 mt-0.5 truncate max-w-[300px]">
              {user.name || user.email}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Plan + Status row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Plan</label>
              <select value={plan} onChange={(e) => setPlan(e.target.value)} className={fieldCls}>
                <option value="starter">Starter</option>
                <option value="pro">Pro</option>
                <option value="agency">Agency</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Status</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)} className={fieldCls}>
                <option value="active">Active</option>
                <option value="trialing">Trial</option>
                <option value="expired">Expired</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>

          {/* Trial fields — only when status = trialing */}
          {status === "trialing" && (
            <div className="p-3 bg-blue-500/5 border border-blue-500/15 rounded-xl space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Trial ends</label>
                  <input
                    type="date"
                    value={trialEnd}
                    onChange={(e) => { setTrialEnd(e.target.value); setTrialDays(""); }}
                    className={fieldCls}
                  />
                </div>
                <div>
                  <label className={labelCls}>Or add days</label>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-slate-500">+</span>
                    <input
                      type="number"
                      min="1"
                      max="365"
                      value={trialDays}
                      onChange={(e) => setTrialDays(e.target.value)}
                      placeholder="14"
                      className={fieldCls}
                    />
                    <span className="text-xs text-slate-500 whitespace-nowrap">days</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Subscription period — only relevant for active */}
          {status === "active" && (
            <div className="p-3 bg-[#0A0A0F] border border-[#2A2A3E] rounded-xl space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Active from</label>
                  <input
                    type="date"
                    value={subStart}
                    onChange={(e) => setSubStart(e.target.value)}
                    className={fieldCls}
                  />
                </div>
                <div>
                  <label className={labelCls}>Active until</label>
                  <input
                    type="date"
                    value={noExpiry ? "" : subEnd}
                    onChange={(e) => { setSubEnd(e.target.value); setNoExpiry(false); }}
                    disabled={noExpiry}
                    placeholder="no expiry"
                    className={`${fieldCls} disabled:opacity-40`}
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={noExpiry}
                  onChange={(e) => { setNoExpiry(e.target.checked); if (e.target.checked) setSubEnd(""); }}
                  className="rounded border-[#2A2A3E] bg-[#0A0A0F] text-indigo-500"
                />
                <span className="text-xs text-slate-400">No expiry — unlimited access</span>
              </label>
            </div>
          )}

          {/* Warning: active + no expiry */}
          {status === "active" && noExpiry && (
            <div className="flex items-start gap-2.5 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-300 leading-relaxed">
                No expiry set — this account will have unlimited access until manually changed.
              </p>
            </div>
          )}

          {/* AI responses limit */}
          <div>
            <label className={labelCls}>AI responses / month</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                value={unlimitedAi ? "" : aiLimit}
                onChange={(e) => setAiLimit(e.target.value)}
                disabled={unlimitedAi}
                placeholder={unlimitedAi ? "∞ Unlimited" : "Plan default"}
                className={`flex-1 ${fieldCls} disabled:opacity-40`}
              />
              <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer whitespace-nowrap">
                <input
                  type="checkbox"
                  checked={unlimitedAi}
                  onChange={(e) => { setUnlimitedAi(e.target.checked); if (e.target.checked) setAiLimit(""); }}
                  className="rounded border-[#2A2A3E] bg-[#0A0A0F] text-indigo-500"
                />
                Unlimited
              </label>
            </div>
            <p className="text-[11px] text-slate-600 mt-1">
              Leave empty to use the plan&apos;s default limit.
            </p>
          </div>

          {/* Error */}
          {error && (
            <p className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-2 px-6 py-4 border-t border-[#2A2A3E]">
          <button
            onClick={submit}
            disabled={saving}
            className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition active:scale-95"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
          <button
            onClick={onClose}
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
// Skeleton row
// ---------------------------------------------------------------------------

function SkeletonRow() {
  return (
    <tr className="border-b border-[#2A2A3E]">
      {[180, 80, 80, 110, 50, 60, 90, 80].map((w, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3 bg-[#1A1A2E] rounded animate-pulse" style={{ width: w }} />
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

  const [accessChecked, setAccessChecked] = useState(false);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [tableLoading, setTableLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [confirm, setConfirm] = useState<{
    title: string;
    message: string;
    confirmLabel: string;
    danger: boolean;
    onConfirm: () => void;
  } | null>(null);

  useEffect(() => {
    usersApi.me()
      .then((u) => { if (!u.is_admin) router.replace("/dashboard"); else setAccessChecked(true); })
      .catch(() => router.replace("/dashboard"));
  }, [router]);

  useEffect(() => {
    if (!accessChecked) return;
    adminApi.stats().then(setStats).catch(() => {});
  }, [accessChecked]);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    if (!accessChecked) return;
    setTableLoading(true);
    adminApi
      .users({ search: debouncedSearch || undefined, status: statusFilter, page, limit: 20 })
      .then((d: AdminUserList) => { setUsers(d.users); setTotal(d.total); setPages(d.pages); })
      .catch(() => {})
      .finally(() => setTableLoading(false));
  }, [accessChecked, debouncedSearch, statusFilter, page]);

  function refreshUsers() {
    setTableLoading(true);
    adminApi
      .users({ search: debouncedSearch || undefined, status: statusFilter, page, limit: 20 })
      .then((d: AdminUserList) => { setUsers(d.users); setTotal(d.total); setPages(d.pages); })
      .catch(() => {})
      .finally(() => setTableLoading(false));
    adminApi.stats().then(setStats).catch(() => {});
  }

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
      <div className="flex items-center gap-3">
        <Shield className="w-5 h-5 text-rose-400" />
        <h1 className="text-2xl font-semibold text-white tracking-tight">Admin</h1>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard icon={Users} label="Total Users" value={stats?.total_users ?? "—"} color="bg-indigo-500/10 text-indigo-400" />
        <KpiCard icon={CreditCard} label="Active Subs" value={stats?.active_subscriptions ?? "—"} color="bg-emerald-500/10 text-emerald-400" />
        <KpiCard icon={TrendingUp} label="Trial Users" value={stats?.trial_users ?? "—"} color="bg-blue-500/10 text-blue-400" />
        <KpiCard icon={AlertCircle} label="Expired Trials" value={stats?.expired_trials ?? "—"} color="bg-rose-500/10 text-rose-400" />
        <KpiCard
          icon={Euro}
          label="MRR"
          value={stats ? `€${stats.mrr.toLocaleString("fr-FR", { minimumFractionDigits: 0 })}` : "—"}
          color="bg-amber-500/10 text-amber-400"
        />
        <KpiCard icon={UserPlus} label="New This Week" value={stats?.new_users_this_week ?? "—"} color="bg-violet-500/10 text-violet-400" />
      </div>

      {/* Users table */}
      <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl overflow-hidden">
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4 border-b border-[#2A2A3E]">
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
          <div className="flex items-center gap-1 flex-wrap">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => { setStatusFilter(tab.key); setPage(1); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  statusFilter === tab.key ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white hover:bg-[#1A1A2E]"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500 ml-auto whitespace-nowrap">{total} user{total !== 1 ? "s" : ""}</p>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead>
              <tr className="border-b border-[#2A2A3E] text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3 font-medium">User</th>
                <th className="text-left px-4 py-3 font-medium">Plan</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Expires</th>
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
                    onEdit={() => setEditingUser(u)}
                    onResetTrial={() => handleResetTrial(u)}
                    onDelete={() => handleDelete(u)}
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
            <span className="text-xs text-slate-500">Page {page} of {pages}</span>
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

      {/* Edit modal */}
      {editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onSaved={() => { setEditingUser(null); refreshUsers(); }}
        />
      )}

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
// User table row
// ---------------------------------------------------------------------------

function UserRow({
  user,
  onEdit,
  onResetTrial,
  onDelete,
}: {
  user: AdminUser;
  onEdit: () => void;
  onResetTrial: () => void;
  onDelete: () => void;
}) {
  const initials = (user.name || user.email).slice(0, 2).toUpperCase();
  const joined = fmtDate(user.created_at);

  const displayStatus =
    user.subscription_status === "trialing" && !user.is_trial
      ? "past_due"
      : user.subscription_status;

  // Expires column: trial_end for trialing, subscription_end for active
  let expiresContent: React.ReactNode;
  if (user.subscription_status === "trialing") {
    expiresContent = user.trial_end ? (
      <span className={`text-xs ${user.is_trial && (user.trial_days_remaining ?? 99) <= 3 ? "text-amber-400" : "text-slate-400"}`}>
        {fmtDate(user.trial_end)}
      </span>
    ) : (
      <span className="text-xs text-slate-600">—</span>
    );
  } else if (user.subscription_status === "active") {
    expiresContent = user.subscription_end ? (
      <span className="text-xs text-slate-400">{fmtDate(user.subscription_end)}</span>
    ) : (
      <span className="text-xs text-emerald-500 font-medium">∞</span>
    );
  } else {
    expiresContent = <span className="text-xs text-slate-600">—</span>;
  }

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

      {/* Expires */}
      <td className="px-4 py-3">{expiresContent}</td>

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
          <button
            onClick={onResetTrial}
            title="Reset trial"
            className="flex items-center justify-center w-7 h-7 rounded-md bg-[#1A1A2E] border border-[#2A2A3E] text-slate-400 hover:text-white hover:border-indigo-500/40 transition"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
          <button
            onClick={onEdit}
            title="Edit subscription"
            className="flex items-center justify-center w-7 h-7 rounded-md bg-[#1A1A2E] border border-[#2A2A3E] text-slate-400 hover:text-white hover:border-indigo-500/40 transition"
          >
            <Pencil className="w-3 h-3" />
          </button>
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
